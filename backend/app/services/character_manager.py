from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.core.i18n import get_lang, Lang
from app.core.llm_client import LLMClient
from app.models.character import Big5, CharacterProfile, Personality
from app.services.memory import MemoryManager
from app.services.world_builder import WorldState

_GENERATION_SYSTEM_PROMPT_EN = """\
You are a character designer for a story world. Given the following world context, \
create compelling characters that fit naturally into this world.

For each character, provide:
- id: a unique URL-safe slug (e.g. "lin-chen")
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

_GENERATION_SYSTEM_PROMPT_ZH = """\
你是一个故事世界的角色设计师。根据给定的世界背景，创作出自然融入该世界的引人入胜的角色。

每个角色需要提供以下内容：
- id: 唯一的 URL 安全标识（例如 "lin-chen"）
- name: 角色的中文全名
- role: 角色类型，可选 "protagonist"（主角）、"antagonist"（反派）、"supporting"（配角）、"minor"（次要角色）
- appearance: 外貌描写（使用中文）
- personality: 角色性格，包含大五人格特质（0-1 量表）、MBTI 类型、3-5 个核心特质和情绪模式
- core_desire: 最渴望的东西（使用中文）
- deep_fear: 最恐惧的东西（使用中文）
- voice_sample: 约 200 字的对话示例，展现角色说话风格（使用中文）
- secrets: 只有角色自己知道的 1-3 件事（使用中文）
- knowledge_scope: 角色能接触到的世界知识主题或 ID 列表
- arc_stage: 角色弧光的当前阶段（如 "introduction", "rising_action", "climax", "resolution"）

重要提示：
- 角色名称必须使用中文姓名（如"林辰"、"苏婉清"）
- 所有文本内容（name, appearance, core_desire, deep_fear, voice_sample, secrets）必须使用简体中文
- JSON 字段名保持英文，但字段值必须为中文
- 角色对话示例要听起来像真实的中文口语

你必须严格按照以下 JSON 格式回复，且只回复 JSON：
{"characters": [...]}"""

_REFINEMENT_SYSTEM_PROMPT_EN = """\
You are a character editor. Given a character profile and user feedback, \
update the character profile to address the feedback while keeping the character's \
core identity intact. Preserve the character's id.

You MUST respond ONLY with valid JSON in this exact format:
{"character": {...}}"""

_REFINEMENT_SYSTEM_PROMPT_ZH = """\
你是一个角色编辑器。根据给定的角色档案和用户反馈，更新角色档案以响应用户意见，同时保持角色的核心身份不变。保留角色的 id。

所有更新的文本内容（name, appearance, core_desire, deep_fear, voice_sample 等）必须使用简体中文。
JSON 字段名保持英文，字段值使用中文。

你必须严格按照以下 JSON 格式回复，且只回复 JSON：
{"character": {...}}"""


def _get_generation_prompt() -> str:
    return _GENERATION_SYSTEM_PROMPT_ZH if get_lang() == Lang.ZH else _GENERATION_SYSTEM_PROMPT_EN


def _get_refinement_prompt() -> str:
    return _REFINEMENT_SYSTEM_PROMPT_ZH if get_lang() == Lang.ZH else _REFINEMENT_SYSTEM_PROMPT_EN


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
            {"role": "system", "content": _get_generation_prompt()},
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
            {"role": "system", "content": _get_refinement_prompt()},
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
        if isinstance(personality_data, str):
            personality_data = {}
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
