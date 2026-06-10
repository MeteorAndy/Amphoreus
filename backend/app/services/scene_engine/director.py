from __future__ import annotations

import textwrap
from typing import Any

from app.core.i18n import get_lang, Lang
from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.memory import MemoryManager
from app.services.plot_architect import SceneSpec
from app.services.scene_engine.types import (
    Adjudication,
    RoundEntry,
    SceneSetup,
)

_SETUP_SYSTEM_PROMPT_EN = """\
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

_SETUP_SYSTEM_PROMPT_ZH = """\
你是一个故事引擎的场景导演。根据给定的场景规格和涉及的角色档案，你通过定义以下内容来准备场景：

1. 生动的场景描述——让场景活灵活现的感官细节（使用中文）
2. 每个角色的私密目标——与其核心欲望保持一致（使用中文）
3. 隐藏信息——每个角色知道而他人不知道的秘密（使用中文）
4. 冲突种子——推动场景前进的初始张力（使用中文）
5. 结束条件——表示场景已经解决的触发条件（使用中文）

规则：
- 每个角色的目标应是个人的、根植于其核心欲望。
- 隐藏信息应尽可能从角色的秘密或知识范围中提取，或从冲突中衍生。
- 冲突种子应在角色之间制造即时的戏剧张力。
- 结束条件必须是在场景执行过程中可观察/可检查的。
- 不要写对话或叙述——这仅是场景设置。

重要提示：
- 所有文本内容必须使用简体中文
- JSON 字段名保持英文，字段值使用中文
- 地点描述应使用富有文学性的中文描写

严格按照以下 JSON 格式回复：
{
  "location_description": "生动的场景感官描述（使用中文）",
  "character_goals": {
    "character_id": "该角色的私密目标（使用中文）"
  },
  "hidden_info": {
    "character_id": ["秘密1", "秘密2"]
  },
  "conflict_seed": "启动场景的初始张力（使用中文）",
  "end_conditions": [
    "触发场景结束的条件1（使用中文）",
    "触发场景结束的条件2（使用中文）"
  ]
}"""

_ADJUDICATE_SYSTEM_PROMPT_EN = """\
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

_ADJUDICATE_SYSTEM_PROMPT_ZH = """\
你是一个故事场景的裁决导演。在每一轮角色互动之后，你评估场景的状态并决定如何推进。

评估内容：
1. 冲突进展——戏剧张力是在升级还是已经解决？
2. 角色一致性——是否有人做出不符合角色的行为（OOC）？
3. 下一发言者——哪个角色此时有最强的动机行动？
4. 外部事件——是否应该发生一些意外事件（敲门、消息、天气变化等）？
5. 节奏——场景是拖沓还是过于仓促？
6. 结束条件——是否有任何结束条件已经满足？

规则：
- 只有当本轮没有设置好回应对象时，才建议 next_speaker。
- OOC 警告仅针对显著的偏差——不是每个小偏离都需要。
- inject_event 应谨慎使用——只在场景需要冲击时才使用。
- 如果结束条件已满足，将 should_continue 设为 false。

考虑在场景开始时设置的角色目标：
{goals_summary}

重要提示：
- 所有文本内容（reason, inject_event, pacing_note, ooc_warnings）必须使用简体中文
- JSON 字段名保持英文，字段值使用中文

严格按照以下 JSON 格式回复：
{{
  "should_continue": true 或 false,
  "reason": "裁决的简要理由（使用中文）",
  "next_speaker": "角色ID 或 null",
  "inject_event": "外部事件描述（使用中文）或 null",
  "pacing_note": "对当前节奏的观察（使用中文）",
  "ooc_warnings": ["任何 OOC 行为描述（使用中文）"]
}}"""


def _get_setup_prompt() -> str:
    return _SETUP_SYSTEM_PROMPT_ZH if get_lang() == Lang.ZH else _SETUP_SYSTEM_PROMPT_EN


def _get_adjudicate_prompt() -> str:
    return _ADJUDICATE_SYSTEM_PROMPT_ZH if get_lang() == Lang.ZH else _ADJUDICATE_SYSTEM_PROMPT_EN


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
            {"role": "system", "content": _get_setup_prompt()},
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
            {"role": "system", "content": _get_adjudicate_prompt().format(
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
    def _truncate(text: str | None, max_chars: int) -> str:
        if not text:
            return ""
        if len(text) <= max_chars:
            return text
        return textwrap.shorten(text, width=max_chars, placeholder="...")
