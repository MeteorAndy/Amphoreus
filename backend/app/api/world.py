from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.dependencies import get_llm_client, get_memory_manager
from app.core.llm_client import LLMClient
from app.services.document_parser import DocumentParser
from app.services.memory import MemoryManager
from app.services.world_builder import WorldBuilder, WorldBuilderSession

router = APIRouter(prefix="/api/world", tags=["world"])

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class StartBuildRequest(BaseModel):
    seed_idea: str


class ContinueBuildRequest(BaseModel):
    session_id: str
    user_input: str


class FinalizeBuildRequest(BaseModel):
    session_id: str


class SessionResponse(BaseModel):
    session_id: str
    stage: str
    next_question: str
    rules: list[dict[str, Any]] = []
    locations: list[dict[str, Any]] = []
    factions: list[dict[str, Any]] = []
    timeline: list[dict[str, Any]] = []
    completeness: float = 0.0


class WorldStateResponse(BaseModel):
    rules: list[dict[str, Any]] = []
    locations: list[dict[str, Any]] = []
    factions: list[dict[str, Any]] = []
    timeline: list[dict[str, Any]] = []
    completeness: float = 0.0


class FormatsResponse(BaseModel):
    formats: list[str]


# ---------------------------------------------------------------------------
# Injectable factories
# ---------------------------------------------------------------------------


async def _get_world_builder(
    llm: LLMClient = Depends(get_llm_client),
    memory: MemoryManager = Depends(get_memory_manager),
) -> WorldBuilder:
    return WorldBuilder(llm, memory)


async def _get_document_parser(
    llm: LLMClient = Depends(get_llm_client),
) -> DocumentParser:
    return DocumentParser(llm)


# ---------------------------------------------------------------------------
# World building endpoints
# ---------------------------------------------------------------------------


@router.post("/build/start")
async def build_start(
    req: StartBuildRequest,
    builder: WorldBuilder = Depends(_get_world_builder),
) -> SessionResponse:
    session = await builder.start_new_world(req.seed_idea)
    return _session_to_response(session)


@router.post("/build/continue")
async def build_continue(
    req: ContinueBuildRequest,
    builder: WorldBuilder = Depends(_get_world_builder),
) -> SessionResponse:
    session = await builder.continue_session(req.session_id, req.user_input)
    return _session_to_response(session)


@router.post("/build/finalize")
async def build_finalize(
    req: FinalizeBuildRequest,
    builder: WorldBuilder = Depends(_get_world_builder),
) -> WorldStateResponse:
    world = await builder.finalize_world(req.session_id)
    return WorldStateResponse(
        rules=world.rules,
        locations=world.locations,
        factions=world.factions,
        timeline=world.timeline,
        completeness=world.completeness,
    )


@router.get("/build/{session_id}")
async def build_get(
    session_id: str,
    builder: WorldBuilder = Depends(_get_world_builder),
) -> SessionResponse:
    session = await builder.get_session(session_id)
    return _session_to_response(session)


# ---------------------------------------------------------------------------
# Document parsing endpoints
# ---------------------------------------------------------------------------


@router.post("/parse")
async def parse_document(
    file: UploadFile = File(...),
    parser: DocumentParser = Depends(_get_document_parser),
) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in parser.supported_formats():
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported format '{ext}'. "
                f"Supported: {', '.join(parser.supported_formats())}"
            ),
        )

    content = await file.read()
    temp_path = os.path.join("/tmp", file.filename)
    with open(temp_path, "wb") as f:
        f.write(content)

    try:
        parsed = await parser.parse(temp_path)
    finally:
        os.remove(temp_path)

    return {
        "raw_text": parsed.raw_text[:2000],
        "extracted_world": {
            "rules": parsed.extracted_world.rules,
            "locations": parsed.extracted_world.locations,
            "factions": parsed.extracted_world.factions,
            "timeline": parsed.extracted_world.timeline,
            "completeness": parsed.extracted_world.completeness,
        },
        "entities": parsed.entities,
    }


@router.get("/formats")
async def formats(
    parser: DocumentParser = Depends(_get_document_parser),
) -> FormatsResponse:
    return FormatsResponse(formats=parser.supported_formats())


# ---------------------------------------------------------------------------
# World data query endpoints
# ---------------------------------------------------------------------------


@router.get("/rules")
async def get_rules(
    memory: MemoryManager = Depends(get_memory_manager),
) -> list[dict[str, Any]]:
    results = memory.openviking.search("rule", scope="world")
    return [{"path": r.path, "l0": r.l0, "score": r.score} for r in results]


@router.get("/locations")
async def get_locations(
    memory: MemoryManager = Depends(get_memory_manager),
) -> list[dict[str, Any]]:
    return memory.kuzu.query_cypher(
        "MATCH (n:Location) RETURN n.name, n.properties"
    )


@router.get("/factions")
async def get_factions(
    memory: MemoryManager = Depends(get_memory_manager),
) -> list[dict[str, Any]]:
    return memory.kuzu.query_cypher(
        "MATCH (n:Faction) RETURN n.name, n.properties"
    )


@router.get("/timeline")
async def get_timeline(
    memory: MemoryManager = Depends(get_memory_manager),
) -> list[dict[str, Any]]:
    return memory.kuzu.query_cypher("MATCH (n:Event) RETURN n.name, n.properties")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _session_to_response(session: WorldBuilderSession) -> SessionResponse:
    return SessionResponse(
        session_id=session.session_id,
        stage=session.stage,
        next_question=session.next_question,
        rules=session.extracted_data.rules,
        locations=session.extracted_data.locations,
        factions=session.extracted_data.factions,
        timeline=session.extracted_data.timeline,
        completeness=session.extracted_data.completeness,
    )
