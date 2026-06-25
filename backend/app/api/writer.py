"""Writer API — convert scene archives to narrative prose and export.

Endpoints:
  POST /api/writer/convert  — {scene_ids, character_ids, options} → WrittenOutput
  POST /api/writer/export   — {output, format} → FileResponse download
  GET  /api/writer/formats  — supported export formats per writing format

Maintainability:
  - Clean route separation, single router
  - Type hints on all endpoint signatures
  - FastAPI Depends for DI
  - No WHAT comments
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.dependencies import get_llm_client, get_memory_manager
from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.memory import MemoryManager
from app.services.narrative_writer import (
    NarrativeWriter,
    WritingOptions,
    WrittenOutput,
)
from app.services.narrative.token_budget import TokenBudgetConfig
from app.services.narrative.novel_writer import _load_scene_archive

router = APIRouter(prefix="/api/writer", tags=["writer"])

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class ConvertRequest(BaseModel):
    scene_ids: list[str]
    character_ids: list[str]
    format: str = "novel"
    narrative_voice: str = "third_person_limited"
    enhance: bool = False
    chapter_title: str | None = None


class ConvertResponse(BaseModel):
    content: str
    format: str
    word_count: int
    scene_count: int
    export_formats: list[str]
    cliche_report: dict | None = None
    canon_report: dict | None = None
    tension_report: dict | None = None
    prop_lifecycle_report: dict | None = None
    reader_sim_report: dict | None = None
    budget_report: dict | None = None
    relationship_trend_report: dict | None = None
    entity_event_report: dict | None = None
    graph_inference_report: dict | None = None
    adaptive_pattern_report: dict | None = None


class ExportRequest(BaseModel):
    content: str
    format: str  # writing format ("novel" or "screenplay")
    export_format: str  # target export format ("md", "txt", "fountain")


class FormatsResponse(BaseModel):
    formats: dict[str, list[str]]


# ---------------------------------------------------------------------------
# Injectable factory
# ---------------------------------------------------------------------------


async def _get_narrative_writer(
    llm: LLMClient = Depends(get_llm_client),
    memory: MemoryManager = Depends(get_memory_manager),
) -> NarrativeWriter:
    return NarrativeWriter(llm, memory)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/convert", response_model=ConvertResponse)
async def convert_scene_archives(
    req: ConvertRequest,
    writer: NarrativeWriter = Depends(_get_narrative_writer),
    memory: MemoryManager = Depends(get_memory_manager),
) -> ConvertResponse:
    """Convert scene archives to novel or screenplay format.

    Loads scene archives and character profiles from OpenViking storage
    by ID, then runs the selected writer (novel or screenplay) with
    the provided writing options.
    """
    if not req.scene_ids:
        raise HTTPException(
            status_code=400, detail="At least one scene_id is required"
        )
    if len(req.character_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 character IDs are required",
        )
    if req.format not in ("novel", "screenplay"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{req.format}'. Use 'novel' or 'screenplay'.",
        )

    # Load scene archives from OpenViking
    scene_archives = []
    for sid in req.scene_ids:
        try:
            archive = _load_scene_archive(memory, sid)
            scene_archives.append(archive)
        except Exception as exc:
            raise HTTPException(
                status_code=404,
                detail=f"Scene archive '{sid}' not found: {exc}",
            ) from exc

    # Load character profiles from OpenViking
    characters: list[CharacterProfile] = []
    for cid in req.character_ids:
        try:
            entry = memory.openviking.read_entry(f"chars/{cid}/profile/full")
            data = json.loads(entry.l2)
            characters.append(CharacterProfile(**data))
        except Exception as exc:
            raise HTTPException(
                status_code=404,
                detail=f"Character profile '{cid}' not found: {exc}",
            ) from exc

    options = WritingOptions(
        format=req.format,
        narrative_voice=req.narrative_voice,
        enhance=req.enhance,
        chapter_title=req.chapter_title,
        score_tension=True,
        analyze_relationship_trends=True,
        token_budget=TokenBudgetConfig(enabled=True),
        learn_adaptive_patterns=True,
        enable_graph_inference=True,
        track_entity_events=True,
    )

    output = await writer.convert(scene_archives, characters, options)

    def _report_dict(rep: object | None) -> dict | None:
        if rep is None:
            return None
        to_dict = getattr(rep, "to_dict", None)
        if callable(to_dict):
            return to_dict()
        if hasattr(rep, "__dict__"):
            return {k: v for k, v in rep.__dict__.items() if not k.startswith("_")}
        return None

    return ConvertResponse(
        content=output.content,
        format=output.format,
        word_count=output.word_count,
        scene_count=output.scene_count,
        export_formats=output.export_formats,
        cliche_report=_report_dict(output.cliche_report),
        canon_report=_report_dict(output.canon_report),
        tension_report=_report_dict(output.tension_report),
        prop_lifecycle_report=_report_dict(output.prop_lifecycle_report),
        reader_sim_report=_report_dict(output.reader_sim_report),
        budget_report=_report_dict(output.budget_report),
        relationship_trend_report=_report_dict(output.relationship_trend_report),
        entity_event_report=_report_dict(output.entity_event_report),
        graph_inference_report=_report_dict(output.graph_inference_report),
        adaptive_pattern_report=_report_dict(output.adaptive_pattern_report),
    )


@router.post("/export")
async def export_written_output(
    req: ExportRequest,
    writer: NarrativeWriter = Depends(_get_narrative_writer),
) -> FileResponse:
    """Export written output as a downloadable file.

    The request provides the content and format; the server converts
    to the target export format (md, txt, fountain) and returns a file.
    """
    if req.format not in ("novel", "screenplay"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported writing format '{req.format}'",
        )

    supported = writer.supported_export_formats().get(req.format, [])
    if req.export_format not in supported:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported export format '{req.export_format}' "
                f"for '{req.format}' writing. "
                f"Supported: {', '.join(supported)}"
            ),
        )

    output = WrittenOutput(
        content=req.content,
        format=req.format,
        word_count=len(req.content.split()),
        scene_count=0,  # not available at export time; cosmetic
        export_formats=supported,
    )

    media_type_map = {
        "md": "text/markdown",
        "txt": "text/plain",
        "fountain": "text/plain",
    }
    filename_map = {
        "md": "narrative.md",
        "txt": "narrative.txt",
        "fountain": "screenplay.fountain",
    }

    try:
        filepath = writer.export_to_temp(output, req.export_format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return FileResponse(
        path=filepath,
        media_type=media_type_map.get(req.export_format, "text/plain"),
        filename=filename_map.get(req.export_format, "export.txt"),
    )


@router.get("/formats", response_model=FormatsResponse)
async def get_export_formats() -> FormatsResponse:
    """Return supported export formats per writing format."""
    return FormatsResponse(
        formats=NarrativeWriter.supported_export_formats()
    )
