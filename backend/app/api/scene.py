"""Scene Engine API — run scenes, stream in real-time via WebSocket, and intervene.

REST:
  POST   /api/scene/run               — synchronous scene execution
  GET    /api/scene/{id}/archive       — archived scene log from OpenViking
  GET    /api/scene/{id}/rounds        — all round entries
  GET    /api/scene/{id}/rounds/{num}  — a specific round
  POST   /api/scene/intervene          — inject user direction into running scene

WebSocket:
  WS     /api/scene/ws/run             — real-time scene streaming

Maintainability:
  - Clean route separation, one router
  - Type hints on all endpoint signatures
  - FastAPI Depends for DI
  - No WHAT comments
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.dependencies import get_llm_client, get_memory_manager
from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.memory import MemoryManager
from app.services.plot_architect import PlotArchitect, SceneSpec
from app.services.scene_engine import SceneEngine
from app.services.scene_engine.resolution import SceneArchive
from app.services.scene_engine.types import Reaction, RoundEntry

router = APIRouter(prefix="/api/scene", tags=["scene"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class RunSceneRequest(BaseModel):
    scene_spec_id: str
    plot_id: str
    character_ids: list[str]
    max_rounds: int = 30


class InterveneRequest(BaseModel):
    scene_id: str
    intervention: str


class ReactionResponse(BaseModel):
    reactor_id: str
    reactor_name: str
    visible_reaction: str
    inner_thought: str


class RoundEntryResponse(BaseModel):
    round_num: int
    actor_id: str
    actor_name: str
    dialogue: str
    action: str
    inner_thought: str
    emotion: str
    reactions: list[ReactionResponse] = []


class EnvironmentUpdateResponse(BaseModel):
    atmosphere: str
    changes: list[str]
    background_activity: str


class SceneArchiveResponse(BaseModel):
    scene_id: str
    rounds: list[RoundEntryResponse]
    final_environment: EnvironmentUpdateResponse
    character_changes: dict[str, Any]


class InterventionResponse(BaseModel):
    scene_id: str
    intervention: str
    status: str


# ---------------------------------------------------------------------------
# Injectable factories
# ---------------------------------------------------------------------------


async def _get_plot_architect(
    llm: LLMClient = Depends(get_llm_client),
    memory: MemoryManager = Depends(get_memory_manager),
) -> PlotArchitect:
    return PlotArchitect(llm, memory)


async def _get_scene_engine(
    memory_manager: MemoryManager = Depends(get_memory_manager),
    llm_client: LLMClient = Depends(get_llm_client),
) -> SceneEngine:
    return SceneEngine(llm_client=llm_client, memory_manager=memory_manager)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_scene_spec(
    plot_id: str, scene_spec_id: str, arch: PlotArchitect
) -> SceneSpec:
    """Locate a SceneSpec by its ID within a stored plot outline. 404 if not found."""
    outline = arch.load_plot(plot_id)
    if outline is None:
        raise HTTPException(
            status_code=404, detail=f"Plot '{plot_id}' not found"
        )

    for act in outline.acts:
        for scene in act.scenes:
            if scene.id == scene_spec_id:
                return scene

    raise HTTPException(
        status_code=404,
        detail=f"Scene spec '{scene_spec_id}' not found in plot '{plot_id}'",
    )


def _load_characters(
    character_ids: list[str], memory: MemoryManager
) -> list[CharacterProfile]:
    """Load CharacterProfiles from OpenViking by ID. 404 on first miss."""
    if len(character_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 character IDs are required to run a scene",
        )

    characters: list[CharacterProfile] = []
    for cid in character_ids:
        try:
            entry = memory.openviking.read_entry(f"chars/{cid}/profile/full")
            data = json.loads(entry.l2)
            characters.append(CharacterProfile(**data))
        except Exception:
            raise HTTPException(
                status_code=404, detail=f"Character '{cid}' not found"
            ) from None
    return characters


def _round_to_response(r: RoundEntry) -> RoundEntryResponse:
    return RoundEntryResponse(
        round_num=r.round_num,
        actor_id=r.actor_id,
        actor_name=r.actor_name,
        dialogue=r.dialogue,
        action=r.action,
        inner_thought=r.inner_thought,
        emotion=r.emotion,
        reactions=[
            ReactionResponse(
                reactor_id=re.reactor_id,
                reactor_name=re.reactor_name,
                visible_reaction=re.visible_reaction,
                inner_thought=re.inner_thought,
            )
            for re in r.reactions
        ],
    )


def _archive_to_response(archive: SceneArchive) -> SceneArchiveResponse:
    return SceneArchiveResponse(
        scene_id=archive.scene_id,
        rounds=[_round_to_response(r) for r in archive.rounds],
        final_environment=EnvironmentUpdateResponse(
            atmosphere=archive.final_environment.atmosphere,
            changes=list(archive.final_environment.changes),
            background_activity=archive.final_environment.background_activity,
        ),
        character_changes=archive.character_changes,
    )


def _parse_archive_entry(l2_content: str) -> SceneArchiveResponse:
    """Parse a stored scene archive JSON string into the response model."""
    try:
        data = json.loads(l2_content)
    except (json.JSONDecodeError, TypeError) as exc:
        raise HTTPException(
            status_code=500, detail="Corrupt scene archive data"
        ) from exc

    rounds_data = data.get("rounds", [])
    final_env_data = data.get("final_environment", {})

    return SceneArchiveResponse(
        scene_id=data["scene_id"],
        rounds=[
            RoundEntryResponse(
                round_num=r["round_num"],
                actor_id=r["actor_id"],
                actor_name=r["actor_name"],
                dialogue=r.get("dialogue", ""),
                action=r.get("action", ""),
                inner_thought=r.get("inner_thought", ""),
                emotion=r.get("emotion", ""),
                reactions=[
                    ReactionResponse(
                        reactor_id=rx["reactor_id"],
                        reactor_name=rx["reactor_name"],
                        visible_reaction=rx.get("visible_reaction", ""),
                        inner_thought=rx.get("inner_thought", ""),
                    )
                    for rx in r.get("reactions", [])
                ],
            )
            for r in rounds_data
        ],
        final_environment=EnvironmentUpdateResponse(
            atmosphere=final_env_data.get("atmosphere", ""),
            changes=final_env_data.get("changes", []),
            background_activity=final_env_data.get("background_activity", ""),
        ),
        character_changes=data.get("character_changes", {}),
    )


# In-memory intervention buffer: scene_id -> list of pending intervention strings.
# The Director checks this before adjudicating each round.
_pending_interventions: dict[str, list[str]] = {}


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------


@router.post("/run", response_model=SceneArchiveResponse)
async def run_scene(
    req: RunSceneRequest,
    engine: SceneEngine = Depends(_get_scene_engine),
    arch: PlotArchitect = Depends(_get_plot_architect),
    memory: MemoryManager = Depends(get_memory_manager),
) -> SceneArchiveResponse:
    """Execute a scene synchronously and return the complete SceneArchive."""
    scene_spec = _find_scene_spec(req.plot_id, req.scene_spec_id, arch)
    characters = _load_characters(req.character_ids, memory)

    # Register intervention buffer for this scene
    _pending_interventions[scene_spec.id] = []

    try:
        archive = await engine.run_scene(scene_spec, characters, req.max_rounds)
    finally:
        _pending_interventions.pop(scene_spec.id, None)

    return _archive_to_response(archive)


@router.get("/{scene_id}/archive", response_model=SceneArchiveResponse)
async def get_scene_archive(
    scene_id: str,
    memory: MemoryManager = Depends(get_memory_manager),
) -> SceneArchiveResponse:
    """Retrieve a completed scene archive from OpenViking storage."""
    try:
        entry = memory.openviking.read_entry(f"story/scenes/{scene_id}")
    except Exception:
        raise HTTPException(
            status_code=404, detail=f"Scene archive '{scene_id}' not found"
        ) from None

    return _parse_archive_entry(entry.l2)


@router.get("/{scene_id}/rounds", response_model=list[RoundEntryResponse])
async def get_scene_rounds(
    scene_id: str,
    memory: MemoryManager = Depends(get_memory_manager),
) -> list[RoundEntryResponse]:
    """Get all round entries for a completed scene."""
    archive = await get_scene_archive(scene_id, memory)
    return archive.rounds


@router.get("/{scene_id}/rounds/{round_num}", response_model=RoundEntryResponse)
async def get_scene_round(
    scene_id: str,
    round_num: int,
    memory: MemoryManager = Depends(get_memory_manager),
) -> RoundEntryResponse:
    """Get a specific round entry from a completed scene."""
    archive = await get_scene_archive(scene_id, memory)
    for r in archive.rounds:
        if r.round_num == round_num:
            return r
    raise HTTPException(
        status_code=404,
        detail=f"Round {round_num} not found in scene '{scene_id}'",
    )


@router.post("/intervene", response_model=InterventionResponse)
async def intervene_scene(
    req: InterveneRequest,
) -> InterventionResponse:
    """Queue a user intervention for an active running scene.

    The intervention is stored in memory and checked by the Director before
    adjudicating the next round.
    """
    if req.scene_id not in _pending_interventions:
        raise HTTPException(
            status_code=404,
            detail=f"No active scene '{req.scene_id}' to intervene in",
        )

    _pending_interventions[req.scene_id].append(req.intervention)

    return InterventionResponse(
        scene_id=req.scene_id,
        intervention=req.intervention,
        status="queued",
    )


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@router.websocket("/ws/run")
async def scene_ws(websocket: WebSocket) -> None:
    """Stream a scene in real-time over WebSocket.

    Client sends one JSON message with the scene parameters:
      {scene_spec_id, plot_id, character_ids, max_rounds}

    Server streams:
      {type: "setup",       data: SceneSetup}
      {type: "environment", data: EnvironmentUpdate}
      {type: "round",       data: RoundEntry}
      {type: "resolution",  data: SceneArchive}
      {type: "complete",    data: {scene_id}}
    """
    await websocket.accept()

    # Read initial message
    try:
        message = await websocket.receive_json()
    except Exception:
        await websocket.close(code=1003)
        return

    scene_spec_id: str | None = message.get("scene_spec_id")
    plot_id: str | None = message.get("plot_id")
    character_ids: list[str] = message.get("character_ids", [])
    max_rounds: int = message.get("max_rounds", 30)

    if not scene_spec_id or not plot_id or not character_ids:
        await websocket.send_json(
            {
                "type": "error",
                "data": "Missing required fields: scene_spec_id, plot_id, character_ids",
            }
        )
        await websocket.close(code=1003)
        return

    if len(character_ids) < 2:
        await websocket.send_json(
            {"type": "error", "data": "At least 2 character IDs are required"}
        )
        await websocket.close(code=1003)
        return

    # Manual DI — Depends is not available in WebSocket handlers
    settings = get_settings()
    llm_client = LLMClient()
    memory_manager = MemoryManager(settings)
    await memory_manager.initialize()

    # Resolve scene spec
    try:
        arch = PlotArchitect(llm_client, memory_manager)
        scene_spec = _find_scene_spec(plot_id, scene_spec_id, arch)
    except HTTPException as exc:
        await websocket.send_json({"type": "error", "data": exc.detail})
        await websocket.close(code=1003)
        return

    # Resolve characters
    characters: list[CharacterProfile] = []
    for cid in character_ids:
        try:
            entry = memory_manager.openviking.read_entry(
                f"chars/{cid}/profile/full"
            )
            data = json.loads(entry.l2)
            characters.append(CharacterProfile(**data))
        except Exception:
            await websocket.send_json(
                {"type": "error", "data": f"Character '{cid}' not found"}
            )
            await websocket.close(code=1003)
            return

    engine = SceneEngine(llm_client=llm_client, memory_manager=memory_manager)

    try:
        async for chunk in engine.run_scene_stream(
            scene_spec, characters, max_rounds
        ):
            try:
                await websocket.send_json(chunk)
            except WebSocketDisconnect:
                return
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "data": str(exc)})
        except WebSocketDisconnect:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
