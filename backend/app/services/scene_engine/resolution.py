from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.memory import MemoryManager
from app.services.scene_engine.types import EnvironmentUpdate, RoundEntry, SceneSetup

_RESOLUTION_SYSTEM_PROMPT = """\
You are a story character reflecting on a scene that just ended. Based on your \
personality, your goals, and what happened, produce an honest in-character \
reflection.

Consider:
1. Did you achieve what you wanted in this scene?
2. How did the events change your emotional state?
3. Did any other character change how you see them?
4. What did you learn or take away from this scene?

Respond ONLY with valid JSON in this format:
{
  "goal_achieved": true or false,
  "goal_reflection": "why you succeeded or failed in your goal",
  "emotion_change": "how your emotional state shifted during the scene",
  "relationship_changes": {
    "other_character_id": "how your view of them changed"
  },
  "key_takeaway": "one insight or lesson from this scene"
}"""


@dataclass
class SceneArchive:
    """Complete archive of a finished scene, including outcomes and character deltas."""

    scene_id: str
    rounds: list[RoundEntry]
    final_environment: EnvironmentUpdate
    character_changes: dict[str, dict[str, Any]]  # char_id -> {emotion_change, goal_update, relationship_changes}


class SceneResolution:
    """Post-scene memory update, world state update, and log archival.

    Resolution pipeline:
      1. For each participating character, call LLM for scene reflection.
      2. Write updated memories to OpenViking (chars/{id}/memories/{scene_id}).
      3. Update Kuzu relationship edges if relationships changed.
      4. Archive complete scene log to viking://story/scenes/{scene_id}/.
      5. Return SceneArchive.

    DI: LLMClient + MemoryManager injected at construction.
    """

    def __init__(self, llm_client: LLMClient, memory_manager: MemoryManager) -> None:
        self._llm = llm_client
        self._ov = memory_manager.openviking
        self._kuzu = memory_manager.kuzu

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def resolve(
        self,
        scene_id: str,
        setup: SceneSetup,
        rounds: list[RoundEntry],
        final_environment: EnvironmentUpdate,
        characters: list[CharacterProfile],
    ) -> SceneArchive:
        """Resolve a complete scene: reflect, persist, and archive."""
        char_by_id = {c.id: c for c in characters}
        scene_summary = self._build_scene_summary(rounds, setup)

        # Step 1: Parallel LLM reflection for each character present
        char_tasks = []
        for char in characters:
            if char.id not in setup.character_goals:
                continue
            char_tasks.append(
                self._reflect_character(
                    char=char,
                    scene_summary=scene_summary,
                    location=setup.location,
                    character_goal=setup.character_goals[char.id],
                )
            )

        reflection_results = await asyncio.gather(*char_tasks, return_exceptions=True)

        # Step 2-3: Persist memories + update relationships
        character_changes: dict[str, dict[str, Any]] = {}

        persist_tasks = []
        for char, result in zip(
            [c for c in characters if c.id in setup.character_goals],
            reflection_results,
        ):
            if isinstance(result, Exception):
                character_changes[char.id] = {
                    "error": str(result),
                    "emotion_change": "",
                    "goal_update": "",
                    "relationship_changes": {},
                }
                continue

            character_changes[char.id] = {
                "emotion_change": result.get("emotion_change", ""),
                "goal_update": result.get("goal_reflection", ""),
                "relationship_changes": result.get("relationship_changes", {}),
            }

            persist_tasks.append(
                self._persist_character_memory(char, scene_id, result, rounds)
            )

            # Update Kuzu relationships
            rel_changes = result.get("relationship_changes", {})
            for other_id, change_desc in rel_changes.items():
                if other_id in char_by_id:
                    persist_tasks.append(
                        self._update_relationship(char.id, other_id, change_desc)
                    )

        # Step 4: Archive scene log
        persist_tasks.append(self._archive_scene(scene_id, setup, rounds, final_environment))

        await asyncio.gather(*persist_tasks, return_exceptions=True)

        # Step 5: Return SceneArchive
        return SceneArchive(
            scene_id=scene_id,
            rounds=rounds,
            final_environment=final_environment,
            character_changes=character_changes,
        )

    # ------------------------------------------------------------------
    # Internal: character reflection
    # ------------------------------------------------------------------

    async def _reflect_character(
        self,
        char: CharacterProfile,
        scene_summary: str,
        location: str,
        character_goal: str,
    ) -> dict[str, Any]:
        """Call LLM for a single character's post-scene reflection."""
        prompt_text = (
            f"Your name: {char.name}\n"
            f"Your core desire: {char.core_desire}\n"
            f"Your deep fear: {char.deep_fear}\n"
            f"Your personality: {', '.join(char.personality.core_traits)}\n\n"
            f"Scene location: {location}\n"
            f"Your goal in this scene: {character_goal}\n\n"
            f"Scene summary of key events:\n{scene_summary}\n\n"
            "Reflect on this scene from your character's perspective."
        )

        messages = [
            {"role": "system", "content": _RESOLUTION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text},
        ]

        return await self._llm.chat_json(messages)

    # ------------------------------------------------------------------
    # Internal: persistence
    # ------------------------------------------------------------------

    async def _persist_character_memory(
        self,
        char: CharacterProfile,
        scene_id: str,
        reflection: dict[str, Any],
        rounds: list[RoundEntry],
    ) -> None:
        """Write the character's scene memory to OpenViking."""
        memory_content = json.dumps(
            {
                "scene_id": scene_id,
                "reflection": reflection,
                "character_state": {
                    "emotion_change": reflection.get("emotion_change", ""),
                    "goal_achieved": reflection.get("goal_achieved", False),
                    "key_takeaway": reflection.get("key_takeaway", ""),
                },
            },
            ensure_ascii=False,
        )
        memory_path = f"chars/{char.id}/memories/{scene_id}"
        self._ov.write_entry(
            memory_path,
            memory_content,
            l0="chars",
            l1=f"char-{char.id}",
        )

    async def _update_relationship(
        self, from_id: str, to_id: str, change_description: str
    ) -> None:
        """Update or create a Kuzu RELATES_TO edge with the change description."""
        self._kuzu.create_edge(
            from_id=from_id,
            to_id=to_id,
            rel_type="RELATES_TO",
            properties={
                "updated_at": self._now(),
                "change": change_description,
            },
        )

    async def _archive_scene(
        self,
        scene_id: str,
        setup: SceneSetup,
        rounds: list[RoundEntry],
        final_environment: EnvironmentUpdate,
    ) -> None:
        """Write the complete scene log to OpenViking."""
        archive = {
            "scene_id": scene_id,
            "location": setup.location,
            "location_description": setup.location_description,
            "cast": setup.cast,
            "conflict_seed": setup.conflict_seed,
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
                            "reactor_id": rct.reactor_id,
                            "reactor_name": rct.reactor_name,
                            "visible_reaction": rct.visible_reaction,
                            "inner_thought": rct.inner_thought,
                        }
                        for rct in r.reactions
                    ],
                }
                for r in rounds
            ],
            "final_environment": {
                "atmosphere": final_environment.atmosphere,
                "changes": final_environment.changes,
                "background_activity": final_environment.background_activity,
            },
        }
        archive_content = json.dumps(archive, ensure_ascii=False)
        archive_path = f"story/scenes/{scene_id}"
        self._ov.write_entry(
            archive_path,
            archive_content,
            l0="story",
            l1=f"scene-{scene_id}",
        )

    # ------------------------------------------------------------------
    # Internal: helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_scene_summary(rounds: list[RoundEntry], setup: SceneSetup) -> str:
        """Produce a concise summary of the scene's key events for reflection."""
        if not rounds:
            return "(scene had no dialogue rounds)"

        lines: list[str] = []
        for entry in rounds:
            react_summary = ""
            if entry.reactions:
                names = ", ".join(r.reactor_name for r in entry.reactions[:3])
                remaining = len(entry.reactions) - 3
                if remaining > 0:
                    react_summary = f" [reactions from: {names} +{remaining} more]"
                else:
                    react_summary = f" [reactions from: {names}]"
            lines.append(
                f"Round {entry.round_num}: {entry.actor_name} "
                f"(\"{entry.dialogue}\") [{entry.action}] "
                f"— {entry.emotion}{react_summary}"
            )
        return "\n".join(lines)

    @staticmethod
    def _now() -> str:
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()
