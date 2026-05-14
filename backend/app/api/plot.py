from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.dependencies import get_llm_client, get_memory_manager
from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.memory import MemoryManager
from app.services.plot_architect import (
    Act,
    NarrativeStructure,
    PlotArchitect,
    PlotOutline,
    SceneSpec,
)
from app.services.world_builder import WorldState

router = APIRouter(prefix="/api/plot", tags=["plot"])

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class GenerateRequest(BaseModel):
    world_id: str
    structure: str = "three_act"
    character_ids: list[str] = []


class RefineRequest(BaseModel):
    plot_id: str
    feedback: str


class CheckRequest(BaseModel):
    plot_id: str
    scene_id: str


class AddSceneRequest(BaseModel):
    title: str
    location: str
    cast: list[str] = []
    conflict: str = ""
    goal: str = ""
    expected_outcome: str = ""
    causal_chain: list[str] = []


class UpdatePlotRequest(BaseModel):
    acts: list[dict[str, Any]] | None = None
    character_arcs: dict[str, list[str]] | None = None


class SceneSpecResponse(BaseModel):
    id: str
    title: str
    location: str
    cast: list[str]
    conflict: str
    goal: str
    expected_outcome: str
    causal_chain: list[str]


class ActResponse(BaseModel):
    name: str
    description: str
    scenes: list[SceneSpecResponse]


class PlotOutlineResponse(BaseModel):
    plot_id: str
    structure: str
    acts: list[ActResponse]
    character_arcs: dict[str, list[str]]


class CheckResponse(BaseModel):
    scene_id: str
    consistent: bool
    issues: list[str] = []
    suggested_fixes: list[str] = []


class TemplatesResponse(BaseModel):
    templates: dict[str, str]


# ---------------------------------------------------------------------------
# Injectable factory
# ---------------------------------------------------------------------------


async def _get_plot_architect(
    llm: LLMClient = Depends(get_llm_client),
    memory: MemoryManager = Depends(get_memory_manager),
) -> PlotArchitect:
    return PlotArchitect(llm, memory)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_world_state(world_id: str, memory: MemoryManager) -> WorldState:
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


def _to_plot_response(plot_id: str, outline: PlotOutline) -> PlotOutlineResponse:
    return PlotOutlineResponse(
        plot_id=plot_id,
        structure=outline.structure.value,
        acts=[
            ActResponse(
                name=a.name,
                description=a.description,
                scenes=[
                    SceneSpecResponse(
                        id=s.id,
                        title=s.title,
                        location=s.location,
                        cast=s.cast,
                        conflict=s.conflict,
                        goal=s.goal,
                        expected_outcome=s.expected_outcome,
                        causal_chain=s.causal_chain,
                    )
                    for s in a.scenes
                ],
            )
            for a in outline.acts
        ],
        character_arcs=outline.character_arcs,
    )


def _dict_to_acts(raw_acts: list[dict[str, Any]]) -> list[Act]:
    acts: list[Act] = []
    for raw in raw_acts:
        raw_scenes: list[dict[str, Any]] = raw.get("scenes", [])
        scenes = [SceneSpec(**s) for s in raw_scenes]
        acts.append(
            Act(
                name=raw.get("name", ""),
                description=raw.get("description", ""),
                scenes=scenes,
            )
        )
    return acts


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/templates", response_model=TemplatesResponse)
async def list_templates(
    arch: PlotArchitect = Depends(_get_plot_architect),
) -> TemplatesResponse:
    templates = arch.get_structure_templates()
    return TemplatesResponse(templates=templates)


@router.post("/generate", response_model=PlotOutlineResponse)
async def generate_plot(
    req: GenerateRequest,
    arch: PlotArchitect = Depends(_get_plot_architect),
    memory: MemoryManager = Depends(get_memory_manager),
) -> PlotOutlineResponse:
    # Validate structure
    try:
        structure = NarrativeStructure(req.structure)
    except ValueError:
        valid = [s.value for s in NarrativeStructure]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid structure '{req.structure}'. Valid: {', '.join(valid)}",
        )

    # Load world
    world = _load_world_state(req.world_id, memory)

    # Load characters
    characters: list[CharacterProfile] = []
    for cid in req.character_ids:
        try:
            entry = memory.openviking.read_entry(f"chars/{cid}/profile/full")
            data = json.loads(entry.l2)
            characters.append(CharacterProfile(**data))
        except Exception:
            raise HTTPException(
                status_code=404,
                detail=f"Character '{cid}' not found",
            ) from None

    outline = await arch.generate_plot(world, characters, structure)
    plot_id = arch.save_plot(outline)
    return _to_plot_response(plot_id, outline)


@router.post("/refine", response_model=PlotOutlineResponse)
async def refine_plot(
    req: RefineRequest,
    arch: PlotArchitect = Depends(_get_plot_architect),
) -> PlotOutlineResponse:
    outline = arch.load_plot(req.plot_id)
    if outline is None:
        raise HTTPException(
            status_code=404, detail=f"Plot '{req.plot_id}' not found"
        )

    refined = await arch.refine_plot(outline, req.feedback)
    arch.save_plot_with_id(req.plot_id, refined)
    return _to_plot_response(req.plot_id, refined)


@router.get("/{plot_id}", response_model=PlotOutlineResponse)
async def get_plot(
    plot_id: str,
    arch: PlotArchitect = Depends(_get_plot_architect),
) -> PlotOutlineResponse:
    outline = arch.load_plot(plot_id)
    if outline is None:
        raise HTTPException(
            status_code=404, detail=f"Plot '{plot_id}' not found"
        )
    return _to_plot_response(plot_id, outline)


@router.put("/{plot_id}", response_model=PlotOutlineResponse)
async def update_plot(
    plot_id: str,
    req: UpdatePlotRequest,
    arch: PlotArchitect = Depends(_get_plot_architect),
) -> PlotOutlineResponse:
    outline = arch.load_plot(plot_id)
    if outline is None:
        raise HTTPException(
            status_code=404, detail=f"Plot '{plot_id}' not found"
        )

    if req.acts is not None:
        outline.acts = _dict_to_acts(req.acts)
    if req.character_arcs is not None:
        outline.character_arcs = req.character_arcs

    arch.save_plot_with_id(plot_id, outline)
    return _to_plot_response(plot_id, outline)


@router.delete("/{plot_id}", status_code=204)
async def delete_plot(
    plot_id: str,
    arch: PlotArchitect = Depends(_get_plot_architect),
) -> None:
    outline = arch.load_plot(plot_id)
    if outline is None:
        raise HTTPException(
            status_code=404, detail=f"Plot '{plot_id}' not found"
        )
    arch.delete_plot(plot_id)


@router.post("/check", response_model=CheckResponse)
async def check_consistency(
    req: CheckRequest,
    arch: PlotArchitect = Depends(_get_plot_architect),
) -> CheckResponse:
    outline = arch.load_plot(req.plot_id)
    if outline is None:
        raise HTTPException(
            status_code=404, detail=f"Plot '{req.plot_id}' not found"
        )

    # Verify scene exists
    all_scenes = await arch.generate_scene_specs(outline)
    scene_ids = {s.id for s in all_scenes}
    if req.scene_id not in scene_ids:
        raise HTTPException(
            status_code=404, detail=f"Scene '{req.scene_id}' not found in plot"
        )

    prompt = arch._build_check_prompt(outline, req.scene_id)
    result = await arch._llm.chat_json(prompt)

    return CheckResponse(
        scene_id=req.scene_id,
        consistent=result.get("consistent", True),
        issues=result.get("issues", []),
        suggested_fixes=result.get("suggested_fixes", []),
    )


@router.post("/{plot_id}/scenes", response_model=PlotOutlineResponse)
async def add_scene(
    plot_id: str,
    req: AddSceneRequest,
    arch: PlotArchitect = Depends(_get_plot_architect),
) -> PlotOutlineResponse:
    outline = arch.load_plot(plot_id)
    if outline is None:
        raise HTTPException(
            status_code=404, detail=f"Plot '{plot_id}' not found"
        )

    all_scenes = await arch.generate_scene_specs(outline)
    next_num = len(all_scenes) + 1

    new_scene = SceneSpec(
        id=f"scene_{next_num}",
        title=req.title,
        location=req.location,
        cast=req.cast,
        conflict=req.conflict,
        goal=req.goal,
        expected_outcome=req.expected_outcome,
        causal_chain=req.causal_chain,
    )

    # Append to the last act, or create a new act if empty
    if outline.acts:
        outline.acts[-1].scenes.append(new_scene)
    else:
        outline.acts.append(
            Act(
                name="New Act",
                description=f"Act containing {new_scene.id}",
                scenes=[new_scene],
            )
        )

    arch.save_plot_with_id(plot_id, outline)
    return _to_plot_response(plot_id, outline)


@router.delete(
    "/{plot_id}/scenes/{scene_id}",
    response_model=PlotOutlineResponse,
)
async def delete_scene(
    plot_id: str,
    scene_id: str,
    arch: PlotArchitect = Depends(_get_plot_architect),
) -> PlotOutlineResponse:
    outline = arch.load_plot(plot_id)
    if outline is None:
        raise HTTPException(
            status_code=404, detail=f"Plot '{plot_id}' not found"
        )

    # Find and remove the scene, checking for causal dependencies
    found = False
    for act in outline.acts:
        for scene in act.scenes:
            if scene_id in scene.causal_chain:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Cannot remove scene '{scene_id}': "
                        f"scene '{scene.id}' depends on it via causal chain"
                    ),
                )
        original_count = len(act.scenes)
        act.scenes = [s for s in act.scenes if s.id != scene_id]
        if len(act.scenes) < original_count:
            found = True

    if not found:
        raise HTTPException(
            status_code=404, detail=f"Scene '{scene_id}' not found in plot"
        )

    arch.save_plot_with_id(plot_id, outline)
    return _to_plot_response(plot_id, outline)
