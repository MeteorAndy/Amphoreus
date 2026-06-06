"""Serialization for pipeline artifacts that must survive a cross-process resume.

The orchestrator's _save_state persists only boolean stage flags, so on a fresh
process the WRITING stage's inputs (archives/outline/characters/world_state) are
gone. These helpers give each artifact a faithful to_dict/from_dict so the
orchestrator can persist them to OpenViking and rehydrate on resume — which is
also what lets a novel run and a screenplay run read the same locked source.

Reuses existing round-trip contracts where they exist (the novel writer's
_parse_archive_json for SceneArchive; the architect's outline dict helpers).
"""

from __future__ import annotations

from typing import Any

from app.models.character import CharacterProfile
from app.services.scene_engine.resolution import SceneArchive
from app.services.scene_engine.types import EnvironmentUpdate, Reaction, RoundEntry
from app.services.world_builder import WorldState


# --- SceneArchive (faithful; mirrors novel_writer._parse_archive_json) ---

def archive_to_dict(a: SceneArchive) -> dict[str, Any]:
    return {
        "scene_id": a.scene_id,
        "rounds": [
            {
                "round_num": r.round_num,
                "actor_id": r.actor_id,
                "actor_name": r.actor_name,
                "dialogue": r.dialogue,
                "action": r.action,
                "inner_thought": r.inner_thought,
                "emotion": r.emotion,
                "reactions": [
                    {
                        "reactor_id": rx.reactor_id,
                        "reactor_name": rx.reactor_name,
                        "visible_reaction": rx.visible_reaction,
                        "inner_thought": rx.inner_thought,
                    }
                    for rx in r.reactions
                ],
            }
            for r in a.rounds
        ],
        "final_environment": {
            "atmosphere": a.final_environment.atmosphere,
            "changes": a.final_environment.changes,
            "background_activity": a.final_environment.background_activity,
        },
        "character_changes": a.character_changes,
    }


def archive_from_dict(data: dict[str, Any]) -> SceneArchive:
    rounds = [
        RoundEntry(
            round_num=r["round_num"], actor_id=r["actor_id"], actor_name=r["actor_name"],
            dialogue=r.get("dialogue", ""), action=r.get("action", ""),
            inner_thought=r.get("inner_thought", ""), emotion=r.get("emotion", ""),
            reactions=[
                Reaction(
                    reactor_id=rx["reactor_id"], reactor_name=rx["reactor_name"],
                    visible_reaction=rx.get("visible_reaction", ""),
                    inner_thought=rx.get("inner_thought", ""),
                )
                for rx in r.get("reactions", [])
            ],
        )
        for r in data.get("rounds", [])
    ]
    fe = data.get("final_environment", {})
    return SceneArchive(
        scene_id=data["scene_id"],
        rounds=rounds,
        final_environment=EnvironmentUpdate(
            atmosphere=fe.get("atmosphere", ""),
            changes=fe.get("changes", []),
            background_activity=fe.get("background_activity", ""),
        ),
        character_changes=data.get("character_changes", {}),
    )


# --- WorldState (flat dataclass) ---

def world_state_to_dict(w: WorldState) -> dict[str, Any]:
    return {
        "rules": w.rules,
        "locations": w.locations,
        "factions": w.factions,
        "timeline": w.timeline,
        "completeness": w.completeness,
    }


def world_state_from_dict(data: dict[str, Any]) -> WorldState:
    return WorldState(
        rules=data.get("rules", []),
        locations=data.get("locations", []),
        factions=data.get("factions", []),
        timeline=data.get("timeline", []),
        completeness=data.get("completeness", 0.0),
    )


# --- CharacterProfile (pydantic) ---

def character_to_dict(c: CharacterProfile) -> dict[str, Any]:
    return c.model_dump()


def character_from_dict(data: dict[str, Any]) -> CharacterProfile:
    return CharacterProfile(**data)


# --- PlotOutline (reuse the architect's existing round-trip helpers) ---

def outline_to_dict(outline) -> dict[str, Any]:
    from app.services.plot_architect.architect import PlotArchitect
    return PlotArchitect._outline_to_dict(outline)


def outline_from_dict(data: dict[str, Any]):
    from app.services.plot_architect.architect import PlotArchitect
    return PlotArchitect._dict_to_outline(data)
