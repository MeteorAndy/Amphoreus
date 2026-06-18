"""Tests for PersonaInjector (Phase 1).

Pure prompt construction from CharacterCard — no LLM, no I/O.
"""

from __future__ import annotations

from app.models.character_card import (
    AgentConfig,
    AmphoreusExtension,
    CharacterCard,
    Goal,
    Psychology,
)
from app.models.character import Personality, Big5
from app.services.agent_session.persona_injector import build_system_prompt


def _card() -> CharacterCard:
    return CharacterCard(
        id="c1", name="陈漠",
        description="废土拾荒者，琥珀色眼睛，瘦削",
        personality="谨慎、执拗、压抑后爆发",
        first_mes="...",
        mes_example="「滚。」他只说了一个字。",
        psychology=Psychology(
            core_belief="信任是奢侈品",
            moral_taboos=["不伤害无辜"],
            voice_profile="简短，从不多说一个字",
            active_wounds=["父亲死于干涸议会"],
        ),
        goals=[
            Goal(description="找到翡翠眼绿洲", priority=0.9),
            Goal(description="保护苏静", priority=0.6, status="suspended"),
        ],
        content_rating="PG",
        extensions=AmphoreusExtension(
            personality=Personality(big5=Big5(openness=0.8)),
        ),
    )


def test_persona_contains_name_and_description():
    prompt = build_system_prompt(_card())
    assert "陈漠" in prompt
    assert "废土拾荒者" in prompt


def test_persona_contains_psychology():
    prompt = build_system_prompt(_card())
    assert "信任是奢侈品" in prompt
    assert "不伤害无辜" in prompt
    assert "简短" in prompt


def test_persona_contains_active_goals():
    prompt = build_system_prompt(_card())
    assert "翡翠眼绿洲" in prompt
    # Suspended goals should NOT appear
    assert "保护苏静" not in prompt


def test_persona_excludes_suspended_goals():
    prompt = build_system_prompt(_card())
    # Suspended goal should not be in the active goals section
    assert prompt.count("保护苏静") == 0 or "suspended" not in prompt.lower()


def test_persona_contains_content_rating():
    prompt = build_system_prompt(_card())
    # ZH mode translates PG to 家长引导; check either
    assert "PG" in prompt or "家长引导" in prompt


def test_persona_contains_mes_example():
    prompt = build_system_prompt(_card())
    assert "「滚。」" in prompt


def test_persona_is_bilingual_aware():
    from app.core.i18n import set_lang, Lang
    set_lang(Lang.EN)
    card = CharacterCard(id="c1", name="Chen", description="A scavenger")
    prompt_en = build_system_prompt(card)
    assert "scavenger" in prompt_en
    set_lang(Lang.ZH)


def test_persona_minimal_card():
    """A card with only id + name should still produce a valid prompt."""
    card = CharacterCard(id="c1", name="Anonymous")
    prompt = build_system_prompt(card)
    assert "Anonymous" in prompt
    assert len(prompt) > 50  # not empty / not just the name
