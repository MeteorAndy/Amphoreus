from __future__ import annotations

import textwrap
from typing import Any

from app.core.llm_client import LLMClient
from app.services.memory import MemoryManager
from app.services.scene_engine.types import EnvironmentUpdate, RoundEntry, SceneSetup

_SYSTEM_PROMPT = """\
You are the environment agent for a story scene. Your job is to generate vivid \
sensory and atmospheric descriptions that ground the scene's mood and location.

Generate ONLY the JSON fields described. Keep descriptions evocative but \
concise — 2-4 sentences at a time. Use all five senses when relevant. \
Respond ONLY with valid JSON."""

_INITIAL_PROMPT_TEMPLATE = """\
Generate the initial atmosphere for a scene.

Scene location: {location}
Location description from setup: {location_description}
Characters present: {cast_names}
Conflict seed: {conflict_seed}
Character goals: {character_goals}

Respond with JSON in this exact format:
{{
  "atmosphere": "evoking mood, sensory details, lighting, sounds, smells",
  "changes": [],
  "background_activity": "weather, ambient NPC actions, distant sounds"
}}"""

_UPDATE_PROMPT_TEMPLATE = """\
Update the scene's atmosphere based on recent events.

Previous atmosphere: {previous_atmosphere}
Previous background activity: {previous_background_activity}

Recent round (most recent action in the scene):
- Actor: {actor_name}
- Dialogue: {dialogue}
- Action: {action}
- Emotion: {emotion}

Respond with JSON in this exact format:
{{
  "atmosphere": "how the mood / sensory landscape has shifted",
  "changes": ["what physically or atmospherically changed this round"],
  "background_activity": "ongoing ambient details, weather shifts, NPC movements"
}}"""


class EnvironmentAgent:
    """Manages scene atmosphere and sensory details.

    Generates initial atmosphere from scene setup, then updates it
    round-by-round based on character actions and dialogue.
    """

    def __init__(self, llm_client: LLMClient, memory_manager: MemoryManager) -> None:
        self._llm = llm_client
        # memory_manager is available for future persistence needs
        self._storage = memory_manager.openviking

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def initial_atmosphere(self, scene_setup: SceneSetup) -> EnvironmentUpdate:
        """Generate the opening sensory description for a scene."""
        cast_names = ", ".join(scene_setup.cast)
        goals_text = "\n".join(
            f"  - {cid}: {goal}"
            for cid, goal in scene_setup.character_goals.items()
        )

        prompt_text = _INITIAL_PROMPT_TEMPLATE.format(
            location=scene_setup.location,
            location_description=scene_setup.location_description,
            cast_names=cast_names,
            conflict_seed=scene_setup.conflict_seed,
            character_goals=goals_text,
        )

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text},
        ]

        result = await self._llm.chat_json(messages)
        return self._parse_environment_update(result)

    async def update(
        self,
        previous: EnvironmentUpdate,
        round_log: list[RoundEntry],
    ) -> EnvironmentUpdate:
        """Generate the updated atmosphere after one round of action."""
        if not round_log:
            return previous

        latest = round_log[-1]

        # Truncate dialogue/action to keep prompt size manageable
        dialogue = self._truncate(latest.dialogue, 300)
        action = self._truncate(latest.action, 200)

        prompt_text = _UPDATE_PROMPT_TEMPLATE.format(
            previous_atmosphere=previous.atmosphere,
            previous_background_activity=previous.background_activity,
            actor_name=latest.actor_name,
            dialogue=dialogue,
            action=action,
            emotion=latest.emotion,
        )

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text},
        ]

        result = await self._llm.chat_json(messages)
        return self._parse_environment_update(result)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_environment_update(
        self, data: dict[str, Any]
    ) -> EnvironmentUpdate:
        return EnvironmentUpdate(
            atmosphere=data.get("atmosphere", ""),
            changes=data.get("changes", []),
            background_activity=data.get("background_activity", ""),
        )

    @staticmethod
    def _truncate(text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        return textwrap.shorten(text, width=max_chars, placeholder="...")
