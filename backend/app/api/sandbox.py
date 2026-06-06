"""Sandbox observation mode — free character wandering with event injection."""
from __future__ import annotations

import json
import uuid
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])

# In-memory session store
_sessions: dict[str, dict] = {}


class SandboxStartRequest(BaseModel):
    world_id: str = Field(..., min_length=1)
    character_ids: list[str] = Field(..., min_length=1)
    location: str | None = None


class SandboxInjectRequest(BaseModel):
    session_id: str
    event: str = Field(..., min_length=1)


class SandboxStopRequest(BaseModel):
    session_id: str


@router.post("/start")
async def sandbox_start(req: SandboxStartRequest):
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "world_id": req.world_id,
        "character_ids": req.character_ids,
        "location": req.location,
        "events": [],
        "rounds": 0,
        "status": "running",
    }
    return {"session_id": session_id, "status": "running"}


@router.post("/inject")
async def sandbox_inject(req: SandboxInjectRequest):
    if req.session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    _sessions[req.session_id]["events"].append(req.event)
    return {"ok": True}


@router.post("/stop")
async def sandbox_stop(req: SandboxStopRequest):
    if req.session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = _sessions.pop(req.session_id)
    return {"ok": True, "rounds": session["rounds"]}


async def _sandbox_feed(session_id: str) -> AsyncIterator[str]:
    """Generate SSE events for one observation snapshot.

    Yields a connected event, drains any pending injected events, emits one
    action per character, then closes.  Clients reconnect for subsequent
    rounds; this keeps the stream finite and testable.
    """
    if session_id not in _sessions:
        yield f"data: {json.dumps({'type': 'error', 'content': 'Session not found'})}\n\n"
        return

    session = _sessions[session_id]

    if session["status"] != "running":
        yield f"data: {json.dumps({'type': 'stopped', 'rounds': session['rounds']})}\n\n"
        return

    # Advance round counter
    session["rounds"] += 1
    round_num = session["rounds"]

    yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id, 'round': round_num})}\n\n"

    # Drain injected events
    while session["events"]:
        event = session["events"].pop(0)
        yield f"data: {json.dumps({'type': 'injected', 'event': event, 'round': round_num})}\n\n"

    # Emit one action per character
    for char_id in session["character_ids"]:
        payload = json.dumps({
            "type": "action",
            "character": char_id,
            "content": f"Character {char_id} observes surroundings",
            "round": round_num,
        })
        yield f"data: {payload}\n\n"

    yield f"data: {json.dumps({'type': 'round_end', 'round': round_num})}\n\n"


@router.get("/{session_id}/feed")
async def sandbox_feed(session_id: str):
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return StreamingResponse(
        _sandbox_feed(session_id),
        media_type="text/event-stream",
    )
