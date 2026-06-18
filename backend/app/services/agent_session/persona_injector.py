"""PersonaInjector — builds the system prompt for a CharacterAgent.

Absorbs the L0/L1 layering from CharacterInteractor + SillyTavern-style
persona injection + PlotPilot psychology fact-lock. Pure function — no LLM,
no I/O, no side effects.

Prompt structure (layered, each section optional — omitted when empty):
  1. CORE IDENTITY: name, description, personality (L0 — always present)
  2. PSYCHOLOGY: core_belief, moral_taboos, voice_profile, active_wounds (T0 fact-lock)
  3. ACTIVE GOALS: drives emergent behavior (only status=active goals)
  4. VOICE EXAMPLE: mes_example for consistent speech patterns
  5. CONTENT RATING: self-constraint boundary
  6. BEHAVIORAL DIRECTIVE: how to respond as this character
"""

from __future__ import annotations

from app.core.i18n import get_lang, Lang
from app.models.character_card import CharacterCard


def build_system_prompt(card: CharacterCard) -> str:
    """Construct the complete system prompt for a character agent. Pure."""
    is_zh = get_lang() == Lang.ZH
    sections: list[str] = []

    # 1. Core identity (L0 — always present)
    sections.append(_core_identity(card, is_zh))

    # 2. Psychology (T0 fact-lock)
    psy = card.psychology
    if psy.core_belief or psy.moral_taboos or psy.voice_profile or psy.active_wounds:
        sections.append(_psychology_block(psy, is_zh))

    # 3. Active goals
    active_goals = [g for g in card.goals if g.status == "active"]
    if active_goals:
        sections.append(_goals_block(active_goals, is_zh))

    # 4. Voice example
    if card.mes_example:
        sections.append(_voice_block(card.mes_example, is_zh))

    # 5. Content rating
    sections.append(_rating_block(card.content_rating, is_zh))

    # 6. Behavioral directive
    sections.append(_directive_block(is_zh))

    return "\n\n".join(sections)


def _core_identity(card: CharacterCard, is_zh: bool) -> str:
    parts: list[str] = []
    if is_zh:
        parts.append(f"你是「{card.name}」。")
        if card.description:
            parts.append(f"身份：{card.description}")
        if card.personality:
            parts.append(f"性格：{card.personality}")
        return "\n".join(parts)
    parts.append(f"You are \"{card.name}\".")
    if card.description:
        parts.append(f"Identity: {card.description}")
    if card.personality:
        parts.append(f"Personality: {card.personality}")
    return "\n".join(parts)


def _psychology_block(psy, is_zh: bool) -> str:
    lines: list[str] = []
    if is_zh:
        lines.append("【心理内核——不可违背】")
        if psy.core_belief:
            lines.append(f"- 核心信念：{psy.core_belief}")
        if psy.moral_taboos:
            lines.append(f"- 道德底线：{'、'.join(psy.moral_taboos)}")
        if psy.voice_profile:
            lines.append(f"- 语言风格：{psy.voice_profile}")
        if psy.active_wounds:
            lines.append(f"- 未愈创伤：{'、'.join(psy.active_wounds)}")
    else:
        lines.append("[PSYCHOLOGY — DO NOT VIOLATE]")
        if psy.core_belief:
            lines.append(f"- Core belief: {psy.core_belief}")
        if psy.moral_taboos:
            lines.append(f"- Moral taboos: {', '.join(psy.moral_taboos)}")
        if psy.voice_profile:
            lines.append(f"- Voice profile: {psy.voice_profile}")
        if psy.active_wounds:
            lines.append(f"- Active wounds: {', '.join(psy.active_wounds)}")
    return "\n".join(lines)


def _goals_block(goals, is_zh: bool) -> str:
    if is_zh:
        lines = ["【当前目标——驱动你的行为】"]
        for g in goals:
            stars = "★" * int(g.priority * 5)
            lines.append(f"- {stars} {g.description}")
    else:
        lines = ["[ACTIVE GOALS — DRIVE YOUR BEHAVIOR]"]
        for g in goals:
            stars = "★" * int(g.priority * 5)
            lines.append(f"- {stars} {g.description}")
    return "\n".join(lines)


def _voice_block(example: str, is_zh: bool) -> str:
    if is_zh:
        return f"【语言范例】\n{example}"
    return f"[VOICE EXAMPLE]\n{example}"


def _rating_block(rating: str, is_zh: bool) -> str:
    if is_zh:
        table = {"G": "全年龄", "PG": "家长引导", "R": "成人向"}
        label = table.get(rating, rating)
        return f"【内容分级：{label}】请在此分级内行动，不要越界。"
    return f"[CONTENT RATING: {rating}] Stay within this rating."


def _directive_block(is_zh: bool) -> str:
    if is_zh:
        return (
            "【行为准则】\n"
            "1. 始终以该角色的身份发言和行动，不要出戏。\n"
            "2. 你的行动应受上述目标和心理内核驱动。\n"
            "3. 保持语言风格一致。\n"
            "4. 只输出该角色的言行，不要描述其他角色的反应。\n"
            "5. 输出格式：[对话] 你的台词 / [动作] 你的行为 / [内心] 你的想法"
        )
    return (
        "[BEHAVIORAL DIRECTIVE]\n"
        "1. Always speak and act as this character — stay in character.\n"
        "2. Your actions should be driven by the goals and psychology above.\n"
        "3. Maintain a consistent voice.\n"
        "4. Output ONLY this character's words and actions — do not narrate others.\n"
        "5. Format: [dialogue] your line / [action] your behavior / [thought] your inner voice"
    )
