from __future__ import annotations

import textwrap
from typing import Any

from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.memory import MemoryManager
from app.services.plot_architect import SceneSpec
from app.services.scene_engine.types import (
    Adjudication,
    RoundEntry,
    SceneSetup,
)

_SETUP_SYSTEM_PROMPT = """\
You are a scene director for a story engine. Given a scene specification and \
the character profiles involved, you prepare the scene by defining:

1. A vivid location description — sensory details that bring the setting to life.
2. Private goals for each character — aligned with their core_desire.
3. Hidden information — what secrets each character knows that others don't.
4. A conflict seed — the initial tension that drives the scene forward.
5. End conditions — concrete triggers that signal the scene is resolved.

Rules:
- Each character's goal should feel personal and rooted in their core_desire.
- Hidden info should be drawn from the character's secrets or knowledge_scope \
when available, or derived from the conflict.
- The conflict seed should create immediate dramatic tension among the cast.
- End conditions must be observable / checkable during scene execution.
- Do NOT write dialogue or narration — this is scene setup only.

Respond ONLY with valid JSON in this format:
{
  "location_description": "vivid sensory description of the location",
  "character_goals": {
    "character_id": "their private goal for this scene"
  },
  "hidden_info": {
    "character_id": ["fact_id_1", "fact_id_2"]
  },
  "conflict_seed": "the initial tension that starts the scene",
  "end_conditions": [
    "condition 1 that triggers scene end",
    "condition 2 that triggers scene end"
  ]
}"""

_ADJUDICATE_SYSTEM_PROMPT = """\
You are the adjudicating director for a story scene. After each round of \
character interaction, you evaluate the state of the scene and decide how \
to proceed.

Evaluate:
1. Conflict advancement — Is the dramatic tension escalating or resolved?
2. Character consistency — Did anyone act out of character (OOC)?
3. Next speaker — Which character has the strongest motivation to act now?
4. External events — Should something unexpected happen (knock, message, weather)?
5. Pacing — Is the scene dragging or rushing?
6. End conditions — Have any end conditions been met?

Rules:
- Only suggest a next_speaker if the round didn't already set someone up to respond.
- OOC warnings are for notable breaks only — not every minor deviation.
- inject_event should be used sparingly — only when the scene needs a jolt.
- If end conditions are met, set should_continue to false.

Consider the character goals set up at the start:
{goals_summary}

Respond ONLY with valid JSON in this format:
{{
  "should_continue": true or false,
  "reason": "brief justification of the ruling",
  "next_speaker": "character_id or null",
  "inject_event": "description of external event or null",
  "pacing_note": "observation about current pacing",
  "ooc_warnings": ["description of any OOC behavior"]
}}"""


class Director:
    """Scene director — setup and per-round adjudication.

    Public interface:
      - async setup_scene(scene_spec, characters) -> SceneSetup
      - async adjudicate(round_log, setup, scene_history) -> Adjudication
    """

    def __init__(self, llm_client: LLMClient, memory_manager: MemoryManager) -> None:
        self._llm = llm_client
        # memory_manager available for future persistence needs
        self._storage = memory_manager.openviking

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def setup_scene(
        self,
        scene_spec: SceneSpec,
        characters: list[CharacterProfile],
    ) -> SceneSetup:
        """Generate the complete scene setup from a scene spec and character profiles."""
        char_summary = self._format_characters(characters)
        conflict_seed_from_spec = scene_spec.conflict

        prompt_text = (
            f"Scene ID: {scene_spec.id}\n"
            f"Title: {scene_spec.title}\n"
            f"Location: {scene_spec.location}\n"
            f"Cast: {', '.join(scene_spec.cast)}\n"
            f"Conflict: {conflict_seed_from_spec}\n"
            f"Goal: {scene_spec.goal}\n"
            f"Expected outcome: {scene_spec.expected_outcome}\n"
            f"Causal chain: {', '.join(scene_spec.causal_chain)}\n\n"
            f"Character profiles:\n{char_summary}"
        )

        messages = [
            {"role": "system", "content": _SETUP_SYSTEM_PROMPT},
            {"role": "user", "content": prompt_text},
        ]

        result = await self._llm.chat_json(messages)
        return self._parse_setup(scene_spec, result)

    async def adjudicate(
        self,
        round_log: list[RoundEntry],
        setup: SceneSetup,
        scene_history: str,
    ) -> Adjudication:
        """Evaluate the latest round and return a ruling."""
        latest_round = round_log[-1] if round_log else None
        recent_history = self._format_recent_history(round_log)

        goals_summary = "\n".join(
            f"  - {cid}: {goal}"
            for cid, goal in setup.character_goals.items()
        )

        prompt_text = (
            f"Scene: {setup.scene_id} at {setup.location}\n"
            f"Conflict seed: {setup.conflict_seed}\n"
            f"End conditions: {', '.join(setup.end_conditions)}\n\n"
            f"Scene history (summary):\n{scene_history}\n\n"
            f"Recent rounds:\n{recent_history}\n\n"
        )

        if latest_round is not None:
            prompt_text += (
                f"Latest round:\n"
                f"  Actor: {latest_round.actor_name} ({latest_round.actor_id})\n"
                f"  Dialogue: {self._truncate(latest_round.dialogue, 300)}\n"
                f"  Action: {self._truncate(latest_round.action, 200)}\n"
                f"  Emotion: {latest_round.emotion}\n\n"
            )

        prompt_text += "Evaluate and adjudicate this round."

        messages = [
            {"role": "system", "content": _ADJUDICATE_SYSTEM_PROMPT.format(
                goals_summary=goals_summary
            )},
            {"role": "user", "content": prompt_text},
        ]

        result = await self._llm.chat_json(messages)
        return self._parse_adjudication(result)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_setup(
        self, scene_spec: SceneSpec, data: dict[str, Any]
    ) -> SceneSetup:
        return SceneSetup(
            scene_id=scene_spec.id,
            location=scene_spec.location,
            location_description=data.get("location_description", ""),
            cast=list(scene_spec.cast),
            character_goals=data.get("character_goals", {}),
            hidden_info=data.get("hidden_info", {}),
            conflict_seed=data.get("conflict_seed", scene_spec.conflict),
            end_conditions=data.get("end_conditions", []),
        )

    @staticmethod
    def _parse_adjudication(data: dict[str, Any]) -> Adjudication:
        return Adjudication(
            should_continue=data.get("should_continue", True),
            reason=data.get("reason", ""),
            next_speaker=data.get("next_speaker"),
            inject_event=data.get("inject_event"),
            pacing_note=data.get("pacing_note", ""),
            ooc_warnings=data.get("ooc_warnings", []),
        )

    @staticmethod
    def _format_characters(characters: list[CharacterProfile]) -> str:
        lines: list[str] = []
        for c in characters:
            lines.append(
                f"  - {c.name} ({c.id}): desire={c.core_desire}, "
                f"fear={c.deep_fear}, role={c.role}"
            )
            if c.secrets:
                secrets_str = "; ".join(c.secrets)
                lines.append(f"    secrets: {secrets_str}")
            if c.knowledge_scope:
                scope_str = "; ".join(c.knowledge_scope)
                lines.append(f"    knowledge: {scope_str}")
        return "\n".join(lines)

    @staticmethod
    def _format_recent_history(round_log: list[RoundEntry]) -> str:
        if not round_log:
            return "(no rounds yet)"

        lines: list[str] = []
        for entry in round_log:
            lines.append(
                f"  Round {entry.round_num} — {entry.actor_name}:\n"
                f"    Dialogue: \"{entry.dialogue}\"\n"
                f"    Action: {entry.action}\n"
                f"    Emotion: {entry.emotion}"
            )
        return "\n".join(lines)

    @staticmethod
    def _truncate(text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        return textwrap.shorten(text, width=max_chars, placeholder="...")
