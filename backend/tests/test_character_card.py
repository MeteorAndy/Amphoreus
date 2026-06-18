"""Tests for CharacterCard + CharacterProfile converter (Phase 0)."""

from __future__ import annotations

from app.models.character import CharacterProfile, Personality, Big5
from app.models.character_card import CharacterCard, Goal, Psychology, AgentConfig
from app.models.character_converter import profile_to_card, card_to_profile


def _profile() -> CharacterProfile:
    return CharacterProfile(
        id="c1", name="陈漠", role="protagonist",
        appearance="瘦削，琥珀色眼睛",
        personality=Personality(
            big5=Big5(openness=0.8, neuroticism=0.7),
            mbti="INTJ", core_traits=["谨慎", "执拗"],
            emotional_pattern="压抑后爆发",
        ),
        core_desire="找到翡翠眼绿洲",
        deep_fear="被遗忘",
        voice_sample="简短，从不多说一个字。",
        secrets=["父亲死于干涸议会"],
        knowledge_scope=["废土地形", "旧世界技术"],
        arc_stage="refusal",
        public_profile="废土拾荒者",
    )


# --- CharacterCard model ---

def test_card_defaults():
    c = CharacterCard(id="c1", name="Test")
    assert c.content_rating == "PG"
    assert c.agent_config.activation_strategy == "round_robin"
    assert c.agent_config.memory_budget_tokens == 2000
    assert c.psychology.core_belief == ""
    assert c.goals == []


def test_card_with_goals_and_psychology():
    c = CharacterCard(
        id="c1", name="Test",
        psychology=Psychology(
            core_belief="信任是奢侈品",
            moral_taboos=["不伤害无辜"],
            voice_profile="低沉，停顿多",
            active_wounds=["失去家园"],
        ),
        goals=[
            Goal(description="找到绿洲", priority=0.9),
            Goal(description="保护妹妹", priority=0.7, status="suspended"),
        ],
    )
    assert len(c.goals) == 2
    assert c.goals[0].priority == 0.9
    assert c.psychology.active_wounds == ["失去家园"]


# --- profile_to_card (lossless forward) ---

def test_profile_to_card_preserves_identity():
    p = _profile()
    c = profile_to_card(p)
    assert c.id == "c1"
    assert c.name == "陈漠"


def test_profile_to_card_derives_goals():
    p = _profile()
    c = profile_to_card(p)
    assert len(c.goals) == 2
    assert "翡翠眼" in c.goals[0].description
    assert c.goals[0].priority == 0.8
    assert "遗忘" in c.goals[1].description


def test_profile_to_card_preserves_all_fields_in_extensions():
    p = _profile()
    c = profile_to_card(p)
    ext = c.extensions
    assert ext.role == "protagonist"
    assert ext.appearance == "瘦削，琥珀色眼睛"
    assert ext.personality.mbti == "INTJ"
    assert ext.core_desire == "找到翡翠眼绿洲"
    assert ext.deep_fear == "被遗忘"
    assert ext.secrets == ["父亲死于干涸议会"]
    assert ext.knowledge_scope == ["废土地形", "旧世界技术"]
    assert ext.arc_stage == "refusal"


def test_profile_to_card_psychology_from_personality():
    p = _profile()
    c = profile_to_card(p)
    assert c.psychology.core_belief == "找到翡翠眼绿洲"
    assert c.psychology.voice_profile == "简短，从不多说一个字。"


# --- card_to_profile (lossy reverse) ---

def test_card_to_profile_preserves_extensions():
    p = _profile()
    c = profile_to_card(p)
    p2 = card_to_profile(c)
    assert p2.id == p.id
    assert p2.name == p.name
    assert p2.role == p.role
    assert p2.core_desire == p.core_desire
    assert p2.secrets == p.secrets
    assert p2.personality.mbti == p.personality.mbti


def test_roundtrip_is_identity_for_extensions():
    p = _profile()
    c = profile_to_card(p)
    p2 = card_to_profile(c)
    c2 = profile_to_card(p2)
    # Extensions survive the roundtrip
    assert c2.extensions.role == c.extensions.role
    assert c2.extensions.secrets == c.extensions.secrets
    assert c2.extensions.personality.mbti == c.extensions.personality.mbti


def test_card_to_profile_falls_back_to_card_fields():
    """When extensions are empty, card fields fill in."""
    c = CharacterCard(
        id="c2", name="铁颅",
        description="机械臂军阀",
        psychology=Psychology(core_belief="力量即正义", voice_profile="粗粝"),
    )
    p = card_to_profile(c)
    assert p.appearance == "机械臂军阀"
    assert p.core_desire == "力量即正义"
    assert p.voice_sample == "粗粝"
