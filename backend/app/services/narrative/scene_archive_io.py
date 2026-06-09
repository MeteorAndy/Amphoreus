"""Scene-archive I/O helpers for the novel writer.

Pure reconstruction / loading / flattening utilities split out of novel_writer
to keep that module focused on prose generation (and under the 500-line cap).
Re-exported from novel_writer for backward compatibility with existing importers.
"""

from __future__ import annotations

import json
from typing import Any

from app.services.memory import MemoryManager
from app.services.plot_architect import PlotOutline, SceneSpec
from app.services.scene_engine.resolution import SceneArchive
from app.services.scene_engine.types import EnvironmentUpdate, Reaction, RoundEntry


def parse_archive_json(l2_content: str) -> SceneArchive:
    """Reconstruct a SceneArchive dataclass from stored JSON."""
    data: dict[str, Any] = json.loads(l2_content)

    rounds: list[RoundEntry] = [
        RoundEntry(
            round_num=r["round_num"],
            actor_id=r["actor_id"],
            actor_name=r["actor_name"],
            dialogue=r.get("dialogue", ""),
            action=r.get("action", ""),
            inner_thought=r.get("inner_thought", ""),
            emotion=r.get("emotion", ""),
            reactions=[
                Reaction(
                    reactor_id=rx["reactor_id"],
                    reactor_name=rx["reactor_name"],
                    visible_reaction=rx.get("visible_reaction", ""),
                    inner_thought=rx.get("inner_thought", ""),
                )
                for rx in r.get("reactions", [])
            ],
        )
        for r in data.get("rounds", [])
    ]

    fe_data = data.get("final_environment", {})
    final_environment = EnvironmentUpdate(
        atmosphere=fe_data.get("atmosphere", ""),
        changes=fe_data.get("changes", []),
        background_activity=fe_data.get("background_activity", ""),
    )

    return SceneArchive(
        scene_id=data["scene_id"],
        rounds=rounds,
        final_environment=final_environment,
        character_changes=data.get("character_changes", {}),
    )


def load_scene_archive(memory: MemoryManager, scene_id: str) -> SceneArchive:
    """Load a single scene archive from OpenViking and return a SceneArchive."""
    entry = memory.openviking.read_entry(f"story/scenes/{scene_id}")
    return parse_archive_json(entry.l2)


def flatten_scenes(outline: PlotOutline) -> dict[str, SceneSpec]:
    """Flatten all SceneSpecs from a PlotOutline into a scene_id -> SceneSpec map."""
    result: dict[str, SceneSpec] = {}
    for act in outline.acts:
        for scene in act.scenes:
            result[scene.id] = scene
    return result
