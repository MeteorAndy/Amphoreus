"""Pipeline API — headless autonomous story generation via SSE."""
from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.llm_client import LLMClient
from app.services.memory import MemoryManager
from app.core.config import get_settings
from app.services.pipeline_orchestrator import (
    PipelineConfig,
    PipelineOrchestrator,
)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


class PipelineRunRequest(BaseModel):
    seed_idea: str = Field(..., min_length=1)
    lang: str = "zh"
    character_count: int = Field(default=5, ge=1, le=20)
    narrative_structure: str = "three_act"
    output_format: str = "novel"
    max_rounds_per_scene: int = Field(default=15, ge=3, le=50)
    auto_refine: bool = True
    session_id: str | None = None


async def _event_stream(config: PipelineConfig) -> AsyncIterator[str]:
    llm = LLMClient()
    settings = get_settings()
    memory = MemoryManager(settings)
    await memory.initialize()
    orchestrator = PipelineOrchestrator(llm, memory)

    async for event in orchestrator.run(config):
        data = json.dumps({
            "stage": event.stage,
            "type": event.type,
            "data": event.data,
            "progress": event.progress,
            "session_id": event.session_id,
        }, ensure_ascii=False)
        yield f"data: {data}\n\n"

    yield "data: [DONE]\n\n"


@router.post("/run")
async def pipeline_run(req: PipelineRunRequest) -> StreamingResponse:
    config = PipelineConfig(
        seed_idea=req.seed_idea,
        lang=req.lang,
        character_count=req.character_count,
        narrative_structure=req.narrative_structure,
        output_format=req.output_format,
        max_rounds_per_scene=req.max_rounds_per_scene,
        auto_refine=req.auto_refine,
        session_id=req.session_id,
    )
    return StreamingResponse(
        _event_stream(config),
        media_type="text/event-stream",
    )
