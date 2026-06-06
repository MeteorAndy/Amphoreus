"""Tests for T1-③: deterministic structure planner."""

from app.services.plot_architect.structure_planner import (
    _bracket,
    format_structure_directive,
    plan,
)
from app.services.plot_architect.types import NarrativeStructure


def test_short_story_single_act():
    p = plan(3, NarrativeStructure.THREE_ACT)
    assert p.total_acts == 1 and p.target_chapters == 3


def test_medium_novel_three_acts():
    p = plan(12, NarrativeStructure.HERO_JOURNEY)
    assert p.total_acts == 3 and p.scenes_total == 12


def test_large_novel_five_acts():
    p = plan(150, NarrativeStructure.SAVE_THE_CAT)
    assert p.total_acts == 5


def test_bracket_floor_is_one():
    acts, spa, total, _, _ = _bracket(1)
    assert acts >= 1 and total >= 1


def test_directive_empty_for_short_story():
    p = plan(2, NarrativeStructure.QI_CHENG_ZHUAN_HE)
    assert format_structure_directive(p, True) == ""


def test_directive_zh_contains_counts():
    p = plan(40, NarrativeStructure.THREE_ACT)
    d = format_structure_directive(p, True)
    assert "40" in d and "幕" in d
    # 31-60 chapter bracket → 2500-3500字
    assert p.words_zh == "2500-3500字"


def test_template_value_preserved():
    assert plan(10, NarrativeStructure.HERO_JOURNEY).template == "hero_journey"
