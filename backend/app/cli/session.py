"""CLI session persistence."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

SESSION_DIR = Path.home() / ".amphoreus" / "cli-sessions"


@dataclass
class CliSession:
    session_id: str
    created_at: str
    updated_at: str
    seed_idea: str = ""
    world_session_id: str = ""
    current_stage: str = "rules"
    character_ids: list[str] = field(default_factory=list)
    plot_id: str = ""
    narrative_structure: str = "three_act"
    completed_scene_ids: list[str] = field(default_factory=list)
    output_path: str = ""
    last_step: str = ""


def _session_path(session_id: str) -> Path:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    return SESSION_DIR / f"{session_id}.json"


def _save_cli_session(session: CliSession) -> None:
    session.updated_at = datetime.now().isoformat()
    data = {
        "session_id": session.session_id,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "seed_idea": session.seed_idea,
        "world_session_id": session.world_session_id,
        "current_stage": session.current_stage,
        "character_ids": session.character_ids,
        "plot_id": session.plot_id,
        "narrative_structure": session.narrative_structure,
        "completed_scene_ids": session.completed_scene_ids,
        "output_path": session.output_path,
        "last_step": session.last_step,
    }
    _session_path(session.session_id).write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _load_cli_session(session_id: str) -> CliSession | None:
    path = _session_path(session_id)
    if not path.exists():
        return None
    try:
        return CliSession(**json.loads(path.read_text("utf-8")))
    except (json.JSONDecodeError, KeyError):
        return None


def _list_saved_sessions() -> list[CliSession]:
    if not SESSION_DIR.exists():
        return []
    sessions: list[CliSession] = []
    for f in sorted(SESSION_DIR.iterdir(), key=os.path.getmtime, reverse=True):
        if f.suffix == ".json":
            s = _load_cli_session(f.stem)
            if s is not None:
                sessions.append(s)
    return sessions
