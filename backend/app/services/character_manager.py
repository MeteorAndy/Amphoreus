from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.core.llm_client import LLMClient
from app.models.character import Big5, CharacterProfile, Personality
from app.services.memory import MemoryManager
from app.services.world_builder import WorldState

_GENERATION_SYSTEM_PROMPT = """\
You are a character designer for a story world. Given the following world context, \
create compelling characters that fit naturally into this world.

For each character, provide:
- id: a unique URL-safe slug (e.g. "li-qingyun")
- name: the character's full name
- role: one of "protagonist", "antagonist", "supporting", "minor"
- appearance: a physical description
- personality: the character's personality including Big Five traits (0-1 scale), \
MBTI type, 3-5 core traits, and emotional pattern
- core_desire: what they want most
- deep_fear: what they are most afraid of
- voice_sample: a ~200 character example of their dialogue showing their voice
- secrets: 1-3 things only they know
- knowledge_scope: list of world knowledge topics or IDs they have access to
- arc_stage: current stage in their character arc (e.g. "introduction", \
"rising_action", "climax", "resolution")

You MUST respond ONLY with valid JSON in this exact format:
{"characters": [...]}"""

_REFINEMENT_SYSTEM_PROMPT = """\
You are a character editor. Given a character profile and user feedback, \
update the character profile to address the feedback while keeping the character's \
core identity intact. Preserve the character's id.

You MUST respond ONLY with valid JSON in this exact format:
{"character": {...}}"""


class CharacterManager:
    """Generates and manages character profiles from world data."""

    def __init__(self, llm_client: LLMClient, memory_manager: MemoryManager) -> None:
        self._llm = llm_client
        self._ov = memory_manager.openviking
        self._kuzu = memory_manager.kuzu

    async def generate_characters(
        self, world: WorldState, count: int = 5
    ) -> list[CharacterProfile]:
        """Generate character suggestions from world state using the LLM."""
        prompt = self._build_generation_prompt(world, count)
        result = await self._llm.chat_json(prompt)

        raw_characters: list[dict[str, Any]] = result.get("characters", [])
        if not raw_characters:
            return []

        profiles: list[CharacterProfile] = []
        now = datetime.now(timezone.utc).isoformat()

        for raw in raw_characters[: count]:
            profile = self._parse_character(raw, now)
            self._save_character(profile, raw)
            profiles.append(profile)

        return profiles

    async def get_character(self, char_id: str) -> CharacterProfile | None:
        """Retrieve a character by its ID."""
        try:
            entry = self._ov.read_entry(f"chars/{char_id}/profile/full")
        except Exception:
            return None
        try:
            data = json.loads(entry.l2)
        except (json.JSONDecodeError, TypeError):
            return None
        return CharacterProfile(**data)

    async def update_character(
        self, char_id: str, profile: CharacterProfile
    ) -> None:
        """Replace the stored profile for an existing character."""
        profile.updated_at = datetime.now(timezone.utc).isoformat()
        self._save_character(profile, profile.model_dump())

    async def delete_character(self, char_id: str) -> None:
        """Remove a character from both stores."""
        base = f"chars/{char_id}"
        for suffix in ("profile/identity", "profile/personality", "profile/full"):
            self._ov.delete_entry(f"{base}/{suffix}")
        self._kuzu.delete_node(char_id)

    async def list_characters(self) -> list[CharacterProfile]:
        """List all stored character profiles."""
        rows = self._kuzu.query_cypher(
            "MATCH (n:Character) RETURN n.name AS id ORDER BY id"
        )
        profiles: list[CharacterProfile] = []
        for row in rows:
            char_id: str = row.get("id", "")
            if char_id:
                profile = await self.get_character(char_id)
                if profile is not None:
                    profiles.append(profile)
        return profiles

    async def refine_character(
        self, char_id: str, feedback: str
    ) -> CharacterProfile:
        """Send a character profile back to the LLM with refinement feedback."""
        current = await self.get_character(char_id)
        if current is None:
            msg = f"Character '{char_id}' not found"
            raise ValueError(msg)

        prompt = self._build_refinement_prompt(current, feedback)
        result = await self._llm.chat_json(prompt)

        raw: dict[str, Any] = result.get("character", result)
        now = datetime.now(timezone.utc).isoformat()
        profile = self._parse_character(raw, now)
        profile.id = char_id
        self._save_character(profile, raw)
        return profile

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_generation_prompt(
        self, world: WorldState, count: int
    ) -> list[dict[str, str]]:
        world_desc = json.dumps(
            {
                "rules": world.rules,
                "locations": world.locations,
                "factions": world.factions,
                "timeline": world.timeline,
            },
            indent=2,
            ensure_ascii=False,
        )
        return [
            {"role": "system", "content": _GENERATION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"World context:\n{world_desc}\n\n"
                    f"Generate {count} characters for this world."
                ),
            },
        ]

    def _build_refinement_prompt(
        self, current: CharacterProfile, feedback: str
    ) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": _REFINEMENT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Current profile:\n{current.model_dump_json(indent=2, ensure_ascii=False)}\n\n"
                    f"Feedback:\n{feedback}\n\n"
                    "Return the updated character profile."
                ),
            },
        ]

    def _parse_character(self, raw: dict[str, Any], timestamp: str) -> CharacterProfile:
        personality_data: dict[str, Any] = raw.get("personality", {})
        big5_data: dict[str, Any] = personality_data.get("big5", {})

        return CharacterProfile(
            id=raw.get("id", ""),
            name=raw.get("name", ""),
            role=raw.get("role", "supporting"),
            appearance=raw.get("appearance", ""),
            personality=Personality(
                big5=Big5(
                    openness=big5_data.get("openness", 0.5),
                    conscientiousness=big5_data.get("conscientiousness", 0.5),
                    extraversion=big5_data.get("extraversion", 0.5),
                    agreeableness=big5_data.get("agreeableness", 0.5),
                    neuroticism=big5_data.get("neuroticism", 0.5),
                ),
                mbti=personality_data.get("mbti", ""),
                core_traits=personality_data.get("core_traits", []),
                emotional_pattern=personality_data.get("emotional_pattern", ""),
            ),
            core_desire=raw.get("core_desire", ""),
            deep_fear=raw.get("deep_fear", ""),
            voice_sample=raw.get("voice_sample", ""),
            secrets=raw.get("secrets", []),
            knowledge_scope=raw.get("knowledge_scope", []),
            arc_stage=raw.get("arc_stage", "introduction"),
            created_at=timestamp,
            updated_at=timestamp,
        )

    def _save_character(
        self, profile: CharacterProfile, raw_data: dict[str, Any]
    ) -> None:
        base = f"chars/{profile.id}"

        # Identity (L0 tier)
        identity_content = json.dumps(
            {
                "id": profile.id,
                "name": profile.name,
                "role": profile.role,
                "core_desire": profile.core_desire,
            },
            ensure_ascii=False,
        )
        l0, l1 = self._generate_tiers_safe(
            identity_content, f"{profile.name} - {profile.role}"
        )
        self._ov.write_entry(
            f"{base}/profile/identity",
            identity_content,
            l0=l0,
            l1=l1,
        )

        # Personality (L1 tier)
        personality_content = json.dumps(
            {
                "id": profile.id,
                "name": profile.name,
                "personality": profile.personality.model_dump(),
                "voice_sample": profile.voice_sample,
            },
            ensure_ascii=False,
        )
        l0_p, l1_p = self._generate_tiers_safe(
            personality_content, f"{profile.name} personality"
        )
        self._ov.write_entry(
            f"{base}/profile/personality",
            personality_content,
            l0=l0_p,
            l1=l1_p,
        )

        # Full profile (L2 tier)
        full_content = profile.model_dump_json(ensure_ascii=False)
        l0_f, l1_f = self._generate_tiers_safe(full_content, profile.name)
        self._ov.write_entry(
            f"{base}/profile/full",
            full_content,
            l0=l0_f,
            l1=l1_f,
        )

        # Kuzu node (MERGE semantics)
        self._kuzu.create_node(
            "Character",
            {
                "name": profile.id,
                "display_name": profile.name,
                "role": profile.role,
                "arc_stage": profile.arc_stage,
            },
        )

    def _generate_tiers_safe(
        self, content: str, fallback_title: str
    ) -> tuple[str, str]:
        try:
            return self._ov.generate_tiers(content)
        except Exception:
            return (fallback_title, "")
