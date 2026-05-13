from __future__ import annotations

import asyncio
import textwrap
from dataclasses import dataclass, field
from typing import Any

from app.core.i18n import get_lang, Lang
from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.memory import MemoryManager
from app.services.scene_engine.knowledge_matrix import KnowledgeMatrix
from app.services.scene_engine.types import EnvironmentUpdate, Reaction, RoundEntry

_ACTION_SYSTEM_PROMPT_EN = """\
You are inside the mind of a story character. Your job is to decide what this \
character says, does, and feels next — in character, driven by their desires, \
fears, and the current dramatic moment.

You are given three layers of context:
- L0 (core layer): Who you are right now — current identity, goal, and emotion.
- L1 (deep layer): Full personality, relationships with others present, and \
relevant scene memories.
- Scene layer: Where you are, what's happening, and the specific private goal \
you are trying to achieve in this scene.

Produce a single character action that advances the scene while staying true to \
the character's nature. Use dialogue that reflects their voice. Use physical \
action that fits the setting. Use inner_thought to reveal their genuine \
feelings (not visible to other characters).

Rules:
- Stay in character at all times — the character's personality, voice, and \
core_desire should guide every word and action.
- Dialogue should sound like this character, not generic prose.
- Action descriptions should be concrete and sensory (what an observer would see).
- The action should serve the character's goal or react to obstacles.
- target_id should be set if the character is directing their words/actions at \
a specific person; null if addressing the room or no one in particular.

Respond ONLY with valid JSON in this format:
{
  "dialogue": "what the character says aloud",
  "action": "physical action description (what an observer sees)",
  "inner_thought": "private thought not visible to others",
  "emotion": "the character's current emotional state",
  "target_id": "character_id or null"
}"""

_ACTION_SYSTEM_PROMPT_ZH = """\
你身处一个故事角色的内心。你的任务是决定这个角色接下来说什么、做什么、感受什么——必须符合角色性格，由其欲望、恐惧和当下的戏剧时刻驱动。

你会获得三层背景信息：
- L0（核心层）：你现在是谁——当前身份、目标和情绪。
- L1（深层）：完整人格、与在场其他人的关系以及相关的场景记忆。
- 场景层：你在哪里、正在发生什么、以及你在本场景中试图达成的具体私密目标。

产生一个推动场景前进且忠于角色本性的单一角色行动。对话要反映角色的语气。肢体行动要符合场景设置。内心想法要揭示角色的真实感受（对其他角色不可见）。

规则：
- 始终保持在角色中——角色的个性、语气和核心欲望应指导每一个字和行动。
- 对话应听起来像这个角色，而不是通用的散文。
- 行动描写应具体且感官化（观察者能看到什么）。
- 行动应服务于角色的目标或对障碍做出反应。
- 如果角色针对特定人物说话/行动，应设置 target_id；如果是对全场或无人说话则设为 null。

重要提示：所有对话、行动、内心想法和情绪描述必须使用简体中文。角色对话要听起来像真实的中文口语。
JSON 字段名保持英文，字段值使用中文。

严格按照以下 JSON 格式回复：
{
  "dialogue": "角色说出来的话（使用中文）",
  "action": "肢体行动描述（观察者所见，使用中文）",
  "inner_thought": "他人不可见的内心想法（使用中文）",
  "emotion": "角色当前的情绪状态（使用中文）",
  "target_id": "角色ID 或 null"
}"""

_REACTION_SYSTEM_PROMPT_EN = """\
You are inside the mind of a story character witnessing another character's \
action. Your job is to produce a natural, in-character reaction to what just \
happened.

You see and hear everything the acting character says and does. Based on your \
personality, your relationship with the actor, and what you know, produce:
- A visible_reaction — what other characters can observe (expression, words, \
body language).
- An inner_thought — your private, honest feelings about what just happened.

Rules:
- React in character — your personality, desires, and fears shape your response.
- The visible reaction may differ from your inner thought (a character might \
hide their true feelings).
- Keep visible_reaction to 1-3 sentences.
- Keep inner_thought to 1-2 sentences.

Respond ONLY with valid JSON in this format:
{
  "visible_reaction": "what others observe",
  "inner_thought": "private thought"
}"""

_REACTION_SYSTEM_PROMPT_ZH = """\
你身处一个故事角色的内心，目睹了另一个角色的行动。你的任务是产生一个自然的、符合角色的反应。

你看到并听到了行动角色所说所做的一切。基于你角色的个性、你与行动者的关系以及你所知道的信息，产生：
- visible_reaction — 其他角色可以观察到的东西（表情、话语、肢体语言）（使用中文）
- inner_thought — 你对刚才发生的事情的私密真实感受（使用中文）

规则：
- 反应要符合角色——你的个性、欲望和恐惧决定了你的回应方式。
- 外在反应可能与内心想法不同（角色可能隐藏真实感受）。
- visible_reaction 保持在 1-3 句。
- inner_thought 保持在 1-2 句。

重要提示：所有内容（visible_reaction, inner_thought）必须使用简体中文。JSON 字段名保持英文。

严格按照以下 JSON 格式回复：
{
  "visible_reaction": "他人观察到的反应（使用中文）",
  "inner_thought": "私密想法（使用中文）"
}"""

_RESOLUTION_CHARACTER_PROMPT_EN = """\
You are a story character reflecting on a scene that just ended.

Scene location: {location}
Scene summary of key events:
{scene_summary}

Your character's goal in this scene was: {character_goal}

Reflect honestly in character:
1. Did you achieve your goal? Why or why not?
2. How did your emotions change during this scene?
3. Did your view of any other character change?

Respond ONLY with valid JSON in this format:
{{
  "goal_achieved": true or false,
  "goal_reflection": "why you succeeded or failed",
  "emotion_change": "how your emotional state shifted",
  "relationship_changes": {{
    "other_character_id": "how your view of them changed"
  }},
  "key_takeaway": "one insight or lesson from this scene"
}}"""

_RESOLUTION_CHARACTER_PROMPT_ZH = """\
你是一个故事角色，正在反思刚刚结束的一场戏。

场景地点：{location}
关键事件摘要：
{scene_summary}

你在这个场景中的目标是：{character_goal}

以角色身份诚实反思：
1. 你达成目标了吗？为什么成功或失败？
2. 在这个场景中你的情绪如何变化？
3. 你对其他角色的看法有改变吗？

重要提示：所有文本内容（goal_reflection, emotion_change, relationship_changes 值, key_takeaway）必须使用简体中文。
JSON 字段名保持英文。

严格按照以下 JSON 格式回复：
{{
  "goal_achieved": true 或 false,
  "goal_reflection": "为什么成功或失败（使用中文）",
  "emotion_change": "情绪状态如何变化（使用中文）",
  "relationship_changes": {{
    "other_character_id": "对他们看法如何改变（使用中文）"
  }},
  "key_takeaway": "从这个场景中获得的一个领悟或教训（使用中文）"
}}"""


_ACTION_PROMPTS = {Lang.ZH: _ACTION_SYSTEM_PROMPT_ZH, Lang.EN: _ACTION_SYSTEM_PROMPT_EN}
_REACTION_PROMPTS = {Lang.ZH: _REACTION_SYSTEM_PROMPT_ZH, Lang.EN: _REACTION_SYSTEM_PROMPT_EN}
_RESOLUTION_CHAR_PROMPTS = {Lang.ZH: _RESOLUTION_CHARACTER_PROMPT_ZH, Lang.EN: _RESOLUTION_CHARACTER_PROMPT_EN}


def _get_action_prompt() -> str:
    return _ACTION_PROMPTS[get_lang()]


def _get_reaction_prompt() -> str:
    return _REACTION_PROMPTS[get_lang()]


def _get_resolution_char_prompt() -> str:
    return _RESOLUTION_CHAR_PROMPTS[get_lang()]


@dataclass
class CharacterAction:
    """A single character's action in a scene round — what they say, do, and feel."""

    actor_id: str
    actor_name: str
    dialogue: str
    action: str  # physical description
    inner_thought: str
    emotion: str
    target_id: str | None  # who they're addressing (if anyone)


class CharacterInteractor:
    """Generates character actions and reactions in scene context.

    Two-phase operation:
      1. generate_action — the next speaking character acts.
      2. generate_reactions — every other present character reacts in parallel.

    DI: LLMClient + MemoryManager injected at construction.
    """

    def __init__(self, llm_client: LLMClient, memory_manager: MemoryManager) -> None:
        self._llm = llm_client
        # memory_manager available for future memory retrieval needs
        self._storage = memory_manager.openviking

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_action(
        self,
        char: CharacterProfile,
        round_log: list[RoundEntry],
        environment: EnvironmentUpdate,
        known_facts: set[str],
        character_goal: str,
        hidden_info: list[str],
    ) -> CharacterAction:
        """Generate the next action for *char* given current scene state."""
        l0_context = self._build_l0(char, character_goal)
        l1_context = self._build_l1(char, round_log)
        scene_context = self._build_scene_context(
            char, environment, round_log, character_goal, hidden_info, known_facts,
        )

        prompt_text = (
            f"--- L0: Core Identity ---\n{l0_context}\n\n"
            f"--- L1: Deep Context ---\n{l1_context}\n\n"
            f"--- Scene Context ---\n{scene_context}\n\n"
            "What do you do next? Respond with the JSON action."
        )

        messages = [
            {"role": "system", "content": _get_action_prompt()},
            {"role": "user", "content": prompt_text},
        ]

        result = await self._llm.chat_json(messages)
        return self._parse_action(char.id, char.name, result)

    async def generate_reactions(
        self,
        action: CharacterAction,
        present_characters: list[CharacterProfile],
        round_log: list[RoundEntry],
        environment: EnvironmentUpdate,
        knowledge_matrix: KnowledgeMatrix,
        character_goals: dict[str, str],
        hidden_info: dict[str, list[str]],
    ) -> list[Reaction]:
        """Generate parallel reactions from all present characters except the actor.

        Each reactor receives their own tailored context (their personality,
        their relationship with the actor, what they know).
        """
        reactors = [c for c in present_characters if c.id != action.actor_id]

        tasks = [
            self._generate_reaction(
                reactor=reactor,
                action=action,
                round_log=round_log,
                environment=environment,
                knowledge_matrix=knowledge_matrix,
                character_goal=character_goals.get(reactor.id, ""),
                reactor_hidden=hidden_info.get(reactor.id, []),
            )
            for reactor in reactors
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        reactions: list[Reaction] = []
        for reactor_id, result in zip([c.id for c in reactors], results):
            if isinstance(result, Reaction):
                reactions.append(result)
            elif isinstance(result, Exception):
                # Log and continue — a single failed reaction shouldn't crash the scene
                reactions.append(
                    Reaction(
                        reactor_id=reactor_id,
                        reactor_name="",
                        visible_reaction="(no visible reaction)",
                        inner_thought=str(result),
                    )
                )
        return reactions

    # ------------------------------------------------------------------
    # Internal: reaction generation (one per reactor)
    # ------------------------------------------------------------------

    async def _generate_reaction(
        self,
        reactor: CharacterProfile,
        action: CharacterAction,
        round_log: list[RoundEntry],
        environment: EnvironmentUpdate,
        knowledge_matrix: KnowledgeMatrix,
        character_goal: str,
        reactor_hidden: list[str],
    ) -> Reaction:
        """Generate a single character's reaction to an action."""
        known_facts = knowledge_matrix.get_known_facts(reactor.id)

        prompt_text = (
            f"Your character: {reactor.name} ({reactor.id})\n"
            f"Core desire: {reactor.core_desire}\n"
            f"Deep fear: {reactor.deep_fear}\n"
            f"Personality traits: {', '.join(reactor.personality.core_traits)}\n"
            f"Current goal in this scene: {character_goal}\n"
            f"Voice: {reactor.voice_sample}\n\n"
            f"What you witnessed:\n"
            f"  {action.actor_name} says: \"{action.dialogue}\"\n"
            f"  {action.actor_name} does: {action.action}\n"
            f"  {action.actor_name} appears: {action.emotion}\n"
            f"  Directed at: {action.target_id if action.target_id else 'the room'}\n\n"
            f"Current atmosphere: {environment.atmosphere}\n"
            f"Background: {environment.background_activity}\n\n"
            f"What you know (private facts): {', '.join(known_facts) if known_facts else 'nothing special'}\n"
            f"Your secrets: {', '.join(reactor_hidden) if reactor_hidden else 'none revealed yet'}\n\n"
            "How does your character react to what they just witnessed?"
        )

        messages = [
            {"role": "system", "content": _get_reaction_prompt()},
            {"role": "user", "content": prompt_text},
        ]

        result = await self._llm.chat_json(messages)
        return Reaction(
            reactor_id=reactor.id,
            reactor_name=reactor.name,
            visible_reaction=result.get("visible_reaction", ""),
            inner_thought=result.get("inner_thought", ""),
        )

    # ------------------------------------------------------------------
    # Internal: context builders for action generation
    # ------------------------------------------------------------------

    @staticmethod
    def _build_l0(char: CharacterProfile, character_goal: str) -> str:
        """L0 layer: ~200 tokens of core identity, current goal, emotion."""
        return (
            f"Name: {char.name}\n"
            f"Role: {char.role}\n"
            f"Core desire: {char.core_desire}\n"
            f"Deep fear: {char.deep_fear}\n"
            f"Arc stage: {char.arc_stage}\n"
            f"Current goal: {character_goal}"
        )

    @staticmethod
    def _build_l1(char: CharacterProfile, round_log: list[RoundEntry]) -> str:
        """L1 layer: full personality, voice, last 3-5 scene memories."""
        big5 = char.personality.big5
        traits = char.personality.core_traits

        text = (
            f"Big 5: O={big5.openness:.2f} C={big5.conscientiousness:.2f} "
            f"E={big5.extraversion:.2f} A={big5.agreeableness:.2f} N={big5.neuroticism:.2f}\n"
            f"MBTI: {char.personality.mbti}\n"
            f"Core traits: {', '.join(traits)}\n"
            f"Emotional pattern: {char.personality.emotional_pattern}\n"
            f"Voice sample: \"{char.voice_sample}\"\n"
            f"Appearance: {char.appearance}\n"
            f"Secrets: {'; '.join(char.secrets) if char.secrets else 'none'}\n"
            f"Knowledge scope: {'; '.join(char.knowledge_scope) if char.knowledge_scope else 'general'}\n"
        )

        # Attach last 3-5 rounds
        recent = round_log[-5:] if round_log else []
        if recent:
            text += "\nRecent scene memory (last few rounds):\n"
            for entry in recent:
                text += (
                    f"  Round {entry.round_num} — {entry.actor_name}: "
                    f"\"{CharacterInteractor._truncate(entry.dialogue, 150)}\" "
                    f"[{entry.action}] "
                    f"({entry.emotion})\n"
                )

        return text

    @staticmethod
    def _build_scene_context(
        char: CharacterProfile,
        environment: EnvironmentUpdate,
        round_log: list[RoundEntry],
        character_goal: str,
        hidden_info: list[str],
        known_facts: set[str],
    ) -> str:
        """Scene layer: location, atmosphere, recent dialogue, character's private goal."""
        context = (
            f"Atmosphere: {environment.atmosphere}\n"
            f"Background: {environment.background_activity}\n"
            f"Recent changes: {'; '.join(environment.changes) if environment.changes else 'none yet'}\n"
            f"Your private goal: {character_goal}\n"
            f"Secrets only you know: {'; '.join(hidden_info) if hidden_info else 'none'}\n"
            f"Facts you are aware of: {'; '.join(known_facts) if known_facts else 'nothing unusual'}\n"
        )

        # Recent dialogue history (last 2 rounds for conversational continuity)
        recent = round_log[-2:] if round_log else []
        if recent:
            context += "\nRecent dialogue:\n"
            for entry in recent:
                target = f" -> {entry.actor_name}" if entry.reactions else ""
                context += (
                    f"  {entry.actor_name}: \"{CharacterInteractor._truncate(entry.dialogue, 200)}\""
                    f"{target}\n"
                )

        return context

    # ------------------------------------------------------------------
    # Internal: parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_action(
        actor_id: str, actor_name: str, data: dict[str, Any]
    ) -> CharacterAction:
        return CharacterAction(
            actor_id=actor_id,
            actor_name=actor_name,
            dialogue=data.get("dialogue", ""),
            action=data.get("action", ""),
            inner_thought=data.get("inner_thought", ""),
            emotion=data.get("emotion", ""),
            target_id=data.get("target_id"),
        )

    @staticmethod
    def _truncate(text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        return textwrap.shorten(text, width=max_chars, placeholder="...")
