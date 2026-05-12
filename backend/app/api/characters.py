from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.dependencies import get_llm_client, get_memory_manager
from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.character_manager import CharacterManager
from app.services.memory import MemoryManager
from app.services.relationship_builder import (
    NetworkGraph,
    PathStep,
    Relationship,
    RelationshipBuilder,
)
from app.services.world_builder import WorldState

router = APIRouter(prefix="/api/characters", tags=["characters"])

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class GenerateRequest(BaseModel):
    world_id: str
    count: int = 5


class RefineRequest(BaseModel):
    feedback: str


class BuildRelationshipsRequest(BaseModel):
    character_ids: list[str]


class RelationshipData(BaseModel):
    from_id: str
    to_id: str
    rel_type: str
    strength: float
    description: str
    established_event: str


class PathStepData(BaseModel):
    from_id: str
    to_id: str
    rel_type: str
    description: str


class NetworkData(BaseModel):
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []


# ---------------------------------------------------------------------------
# Injectable factories
# ---------------------------------------------------------------------------


async def _get_character_manager(
    llm: LLMClient = Depends(get_llm_client),
    memory: MemoryManager = Depends(get_memory_manager),
) -> CharacterManager:
    return CharacterManager(llm, memory)


async def _get_relationship_builder(
    llm: LLMClient = Depends(get_llm_client),
    memory: MemoryManager = Depends(get_memory_manager),
) -> RelationshipBuilder:
    return RelationshipBuilder(llm, memory)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_world_state(world_id: str, memory: MemoryManager) -> WorldState:
    """Load a WorldState from a persisted world-building session."""
    try:
        entry = memory.openviking.read_entry(f"world/sessions/{world_id}/state")
    except Exception:
        raise HTTPException(
            status_code=404, detail=f"World session '{world_id}' not found"
        ) from None

    try:
        data = json.loads(entry.l2)
    except (json.JSONDecodeError, TypeError) as exc:
        raise HTTPException(
            status_code=500, detail="Corrupt world session data"
        ) from exc

    extracted = data.get("extracted_data", {})
    return WorldState(
        rules=extracted.get("rules", []),
        locations=extracted.get("locations", []),
        factions=extracted.get("factions", []),
        timeline=extracted.get("timeline", []),
        completeness=extracted.get("completeness", 0.0),
    )


def _to_relationship_data(rel: Relationship) -> RelationshipData:
    return RelationshipData(
        from_id=rel.from_id,
        to_id=rel.to_id,
        rel_type=rel.rel_type,
        strength=rel.strength,
        description=rel.description,
        established_event=rel.established_event,
    )


def _to_path_step_data(step: PathStep) -> PathStepData:
    return PathStepData(
        from_id=step.from_id,
        to_id=step.to_id,
        rel_type=step.rel_type,
        description=step.description,
    )


# ---------------------------------------------------------------------------
# Character CRUD endpoints
# ---------------------------------------------------------------------------


@router.post("/generate", response_model=list[CharacterProfile])
async def generate_characters(
    req: GenerateRequest,
    char_mgr: CharacterManager = Depends(_get_character_manager),
    memory: MemoryManager = Depends(get_memory_manager),
) -> list[CharacterProfile]:
    world = _load_world_state(req.world_id, memory)
    profiles = await char_mgr.generate_characters(world, req.count)
    return profiles


@router.get("", response_model=list[CharacterProfile])
async def list_characters(
    char_mgr: CharacterManager = Depends(_get_character_manager),
) -> list[CharacterProfile]:
    return await char_mgr.list_characters()


@router.get("/{char_id}", response_model=CharacterProfile)
async def get_character(
    char_id: str,
    char_mgr: CharacterManager = Depends(_get_character_manager),
) -> CharacterProfile:
    profile = await char_mgr.get_character(char_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Character '{char_id}' not found")
    return profile


@router.put("/{char_id}", response_model=CharacterProfile)
async def update_character(
    char_id: str,
    profile: CharacterProfile,
    char_mgr: CharacterManager = Depends(_get_character_manager),
) -> CharacterProfile:
    existing = await char_mgr.get_character(char_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Character '{char_id}' not found")
    profile.id = char_id
    await char_mgr.update_character(char_id, profile)
    updated = await char_mgr.get_character(char_id)
    if updated is None:
        raise HTTPException(status_code=500, detail="Failed to read back updated character")
    return updated


@router.delete("/{char_id}", status_code=204)
async def delete_character(
    char_id: str,
    char_mgr: CharacterManager = Depends(_get_character_manager),
) -> None:
    existing = await char_mgr.get_character(char_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Character '{char_id}' not found")
    await char_mgr.delete_character(char_id)


@router.post("/{char_id}/refine", response_model=CharacterProfile)
async def refine_character(
    char_id: str,
    req: RefineRequest,
    char_mgr: CharacterManager = Depends(_get_character_manager),
) -> CharacterProfile:
    try:
        return await char_mgr.refine_character(char_id, req.feedback)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Relationship endpoints
# ---------------------------------------------------------------------------


@router.post("/relationships/build", response_model=list[RelationshipData])
async def build_relationships(
    req: BuildRelationshipsRequest,
    rel_builder: RelationshipBuilder = Depends(_get_relationship_builder),
    char_mgr: CharacterManager = Depends(_get_character_manager),
    memory: MemoryManager = Depends(get_memory_manager),
) -> list[RelationshipData]:
    # Load characters
    characters: list[CharacterProfile] = []
    for cid in req.character_ids:
        profile = await char_mgr.get_character(cid)
        if profile is not None:
            characters.append(profile)

    if len(characters) < 2:
        raise HTTPException(
            status_code=400,
            detail="Need at least 2 valid character IDs to build relationships",
        )

    # Load world from the first character's storage context
    # (use an empty world as fallback; the caller can refine later)
    world = WorldState()

    relationships = await rel_builder.build_relationships(characters, world)
    return [_to_relationship_data(r) for r in relationships]


@router.get("/relationships/{char_id}", response_model=NetworkData)
async def character_network(
    char_id: str,
    depth: int = 2,
    rel_builder: RelationshipBuilder = Depends(_get_relationship_builder),
) -> NetworkData:
    network = await rel_builder.get_character_network(char_id, depth)
    return NetworkData(nodes=network.nodes, edges=network.edges)


@router.get("/relationships/path", response_model=list[PathStepData])
async def relationship_path(
    from_id: str,
    to_id: str,
    rel_builder: RelationshipBuilder = Depends(_get_relationship_builder),
) -> list[PathStepData]:
    steps = await rel_builder.get_relationship_path(from_id, to_id)
    return [_to_path_step_data(s) for s in steps]
