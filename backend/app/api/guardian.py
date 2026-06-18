from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.dependencies import get_llm_client, get_memory_manager
from app.core.llm_client import LLMClient
from app.services.memory import MemoryManager
from app.services.story_guardian import (
    GuardianIssue,
    GuardianResult,
    Severity,
    StoryGuardian,
    Verdict,
)

router = APIRouter(prefix="/api/guardian", tags=["guardian"])

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class EvaluateRequest(BaseModel):
    proposed_plot: str
    affected_characters: list[str]
    world_id: str | None = None


class SceneInterventionRequest(BaseModel):
    scene_id: str
    intervention: str
    characters: list[str]


class GuardianIssueResponse(BaseModel):
    severity: str
    dimension: str
    description: str
    suggestion: str


class GuardianResultResponse(BaseModel):
    verdict: str
    issues: list[GuardianIssueResponse]
    can_override: bool


def _to_response(result: GuardianResult) -> GuardianResultResponse:
    return GuardianResultResponse(
        verdict=result.verdict.value,
        issues=[
            GuardianIssueResponse(
                severity=i.severity.value,
                dimension=i.dimension,
                description=i.description,
                suggestion=i.suggestion,
            )
            for i in result.issues
        ],
        can_override=result.can_override,
    )


# ---------------------------------------------------------------------------
# Injectable factory
# ---------------------------------------------------------------------------


async def _get_story_guardian(
    llm: LLMClient = Depends(get_llm_client),
    memory: MemoryManager = Depends(get_memory_manager),
) -> StoryGuardian:
    return StoryGuardian(llm, memory, classify_deviations=True)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/evaluate", response_model=GuardianResultResponse)
async def evaluate_plot(
    req: EvaluateRequest,
    guardian: StoryGuardian = Depends(_get_story_guardian),
) -> GuardianResultResponse:
    result = await guardian.evaluate(
        proposed_plot=req.proposed_plot,
        affected_characters=req.affected_characters,
        world_id=req.world_id,
    )
    return _to_response(result)


@router.post("/evaluate/scene", response_model=GuardianResultResponse)
async def evaluate_scene_intervention(
    req: SceneInterventionRequest,
    guardian: StoryGuardian = Depends(_get_story_guardian),
) -> GuardianResultResponse:
    result = await guardian.evaluate_scene_intervention(
        scene_id=req.scene_id,
        intervention=req.intervention,
        characters=req.characters,
    )
    return _to_response(result)
