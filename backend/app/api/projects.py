"""Project Management API — create, list, load, save, delete story projects.

Storage layout:
  $THE_WORLD_PROJECTS_DIR/index.json          — list of project metadata
  $THE_WORLD_PROJECTS_DIR/{id}/state.json     — full project state

The storage root defaults to ~/.the-world/projects/ but can be overridden
via the THE_WORLD_PROJECTS_DIR environment variable (used in tests).
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/projects", tags=["projects"])

# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------


def _projects_dir() -> Path:
    env = os.environ.get("THE_WORLD_PROJECTS_DIR")
    if env:
        return Path(env)
    return Path.home() / ".the-world" / "projects"


def _index_path() -> Path:
    return _projects_dir() / "index.json"


def _state_path(project_id: str) -> Path:
    return _projects_dir() / project_id / "state.json"


def _load_index() -> list[dict[str, Any]]:
    path = _index_path()
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_index(index: list[dict[str, Any]]) -> None:
    path = _index_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(index, indent=2, ensure_ascii=False), "utf-8")


def _load_state(project_id: str) -> dict[str, Any] | None:
    path = _state_path(project_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _save_state(state: dict[str, Any]) -> None:
    path = _state_path(state["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), "utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class CreateProjectRequest(BaseModel):
    name: str
    seed_idea: str


class UpdateProjectRequest(BaseModel):
    name: str | None = None
    seed_idea: str | None = None
    last_stage: str | None = None
    world_state: dict[str, Any] | None = None
    characters: list[Any] | None = None
    relationships: list[Any] | None = None
    plot_outline: dict[str, Any] | None = None
    scene_archives: dict[str, Any] | None = None
    written_output: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", status_code=201)
async def create_project(req: CreateProjectRequest) -> dict[str, Any]:
    """Create a new project and persist it."""
    now = _now_iso()
    project_id = str(uuid.uuid4())

    state: dict[str, Any] = {
        "id": project_id,
        "name": req.name,
        "seed_idea": req.seed_idea,
        "created_at": now,
        "updated_at": now,
        "last_stage": "idle",
        "world_state": None,
        "characters": None,
        "relationships": None,
        "plot_outline": None,
        "scene_archives": None,
        "written_output": None,
    }
    _save_state(state)

    index = _load_index()
    index.append({
        "id": project_id,
        "name": req.name,
        "created_at": now,
        "updated_at": now,
        "last_stage": "idle",
    })
    _save_index(index)

    return {"id": project_id, "name": req.name, "created_at": now}


@router.get("")
async def list_projects() -> dict[str, Any]:
    """Return metadata for all projects."""
    return {"projects": _load_index()}


@router.get("/{project_id}")
async def get_project(project_id: str) -> dict[str, Any]:
    """Return full state for a project."""
    state = _load_state(project_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return state


@router.put("/{project_id}")
async def update_project(
    project_id: str, req: UpdateProjectRequest
) -> dict[str, Any]:
    """Partially update a project's state."""
    state = _load_state(project_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Project not found")

    updates = req.model_dump(exclude_unset=True)
    state.update(updates)
    state["updated_at"] = _now_iso()
    _save_state(state)

    # Sync index metadata
    index = _load_index()
    for entry in index:
        if entry["id"] == project_id:
            entry["updated_at"] = state["updated_at"]
            if "name" in updates:
                entry["name"] = state["name"]
            if "last_stage" in updates:
                entry["last_stage"] = state["last_stage"]
            break
    _save_index(index)

    return state


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str) -> None:
    """Delete a project and its state file."""
    state = _load_state(project_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Project not found")

    state_file = _state_path(project_id)
    try:
        state_file.unlink(missing_ok=True)
        state_file.parent.rmdir()
    except OSError:
        pass

    index = _load_index()
    index = [e for e in index if e["id"] != project_id]
    _save_index(index)
