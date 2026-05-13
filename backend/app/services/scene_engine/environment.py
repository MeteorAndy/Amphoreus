from __future__ import annotations

import textwrap
from typing import Any

from app.core.i18n import get_lang, Lang
from app.core.llm_client import LLMClient
from app.services.memory import MemoryManager
from app.services.scene_engine.types import EnvironmentUpdate, RoundEntry, SceneSetup

_SYSTEM_PROMPT_EN = """\
You are the environment agent for a story scene. Your job is to generate vivid \
sensory and atmospheric descriptions that ground the scene's mood and location.

Generate ONLY the JSON fields described. Keep descriptions evocative but \
concise — 2-4 sentences at a time. Use all five senses when relevant. \
Respond ONLY with valid JSON."""

_SYSTEM_PROMPT_ZH = """\
你是一个故事场景的环境代理。你的工作是生成生动的感官和氛围描写，为场景的情调和地点提供真实感。

只生成描述的 JSON 字段。保持描写富有感染力但简洁——每次 2-4 句。在相关时使用所有五种感官。

重要提示：所有文本内容必须使用简体中文。JSON 字段名保持英文，字段值使用中文。

只回复有效的 JSON。"""

_INITIAL_PROMPT_TEMPLATE_EN = """\
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

_INITIAL_PROMPT_TEMPLATE_ZH = """\
生成场景的初始氛围。

场景地点：{location}
场景设定中的地点描述：{location_description}
在场角色：{cast_names}
冲突种子：{conflict_seed}
角色目标：{character_goals}

严格按照以下 JSON 格式回复。所有文本内容使用简体中文：
{{
  "atmosphere": "唤起情绪、感官细节、光线、声音、气味（使用中文）",
  "changes": [],
  "background_activity": "天气、周围NPC活动、远处的声音（使用中文）"
}}"""

_UPDATE_PROMPT_TEMPLATE_EN = """\
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

_UPDATE_PROMPT_TEMPLATE_ZH = """\
根据最近的事件更新场景氛围。

之前的氛围：{previous_atmosphere}
之前的背景活动：{previous_background_activity}

最近一轮（场景中最新的行动）：
- 角色：{actor_name}
- 对话：{dialogue}
- 行动：{action}
- 情绪：{emotion}

严格按照以下 JSON 格式回复。所有文本内容使用简体中文：
{{
  "atmosphere": "情绪/感官氛围如何变化（使用中文）",
  "changes": ["本轮在物理或氛围上发生了哪些变化（使用中文）"],
  "background_activity": "持续的周围细节、天气变化、NPC活动（使用中文）"
}}"""


_PROMPT_TEMPLATES = {
    Lang.ZH: (_SYSTEM_PROMPT_ZH, _INITIAL_PROMPT_TEMPLATE_ZH, _UPDATE_PROMPT_TEMPLATE_ZH),
    Lang.EN: (_SYSTEM_PROMPT_EN, _INITIAL_PROMPT_TEMPLATE_EN, _UPDATE_PROMPT_TEMPLATE_EN),
}


def _get_env_prompts() -> tuple[str, str, str]:
    return _PROMPT_TEMPLATES[get_lang()]


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

        sys_prompt, initial_tmpl, _ = _get_env_prompts()
        prompt_text = initial_tmpl.format(
            location=scene_setup.location,
            location_description=scene_setup.location_description,
            cast_names=cast_names,
            conflict_seed=scene_setup.conflict_seed,
            character_goals=goals_text,
        )

        messages = [
            {"role": "system", "content": sys_prompt},
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

        _, _, update_tmpl = _get_env_prompts()
        prompt_text = update_tmpl.format(
            previous_atmosphere=previous.atmosphere,
            previous_background_activity=previous.background_activity,
            actor_name=latest.actor_name,
            dialogue=dialogue,
            action=action,
            emotion=latest.emotion,
        )

        sys_prompt, _, _ = _get_env_prompts()
        messages = [
            {"role": "system", "content": sys_prompt},
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
