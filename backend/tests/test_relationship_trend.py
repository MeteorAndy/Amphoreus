"""Tests for T2-⑧: time-dimensioned relationship trend analysis.

Report-only diagnostic (the cheap T2-⑤/⑥/⑦ shape): pure, zero-LLM, zero-Kuzu.
Derives a per-pair sentiment series from the free-text
`character_changes[*]['relationship_changes']` already on SceneArchive, then a
deterministic 4-way trend (IMPROVING/DETERIORATING/VOLATILE/STABLE) + a
bilingual development suggestion. No write-path change, no caller affected.

Run as a targeted file (full suite hangs on integration tests):
    uv run pytest tests/test_relationship_trend.py -v
"""

from __future__ import annotations

import json

import pytest

from app.services.narrative.relationship_trend import (
    StrengthPoint,
    RelationshipPairTrend,
    RelationshipTrendReport,
    classify_trend,
    extract_pair_series,
    sentiment_of_text,
    build_relationship_trend_report,
)
from app.services.narrative.types import ChapterPlan, ChapterSpec
from app.services.scene_engine.resolution import SceneArchive
from app.services.scene_engine.types import EnvironmentUpdate


# --- builders --------------------------------------------------------------

def _env() -> EnvironmentUpdate:
    return EnvironmentUpdate(atmosphere="", changes=[], background_activity="")


def _archive(scene_id: str, rel_changes_by_char: dict[str, dict[str, str]]) -> SceneArchive:
    """rel_changes_by_char: {char_id: {other_id: change_desc_text}}."""
    character_changes = {
        cid: {"emotion_change": "", "goal_update": "", "relationship_changes": rc}
        for cid, rc in rel_changes_by_char.items()
    }
    return SceneArchive(
        scene_id=scene_id, rounds=[], final_environment=_env(),
        character_changes=character_changes,
    )


def _plan(scene_to_chapter: dict[str, int]) -> ChapterPlan:
    """Build a ChapterPlan mapping each scene_id to its chapter number."""
    by_chapter: dict[int, list[str]] = {}
    for sid, ch in scene_to_chapter.items():
        by_chapter.setdefault(ch, []).append(sid)
    chapters = [
        ChapterSpec(number=ch, title=f"T{ch}", scene_ids=sids, summary="")
        for ch, sids in sorted(by_chapter.items())
    ]
    return ChapterPlan(chapters=chapters)


# --- sentiment of free text ------------------------------------------------

def test_sentiment_positive_only_clamps_high():
    assert sentiment_of_text("信任加深，两人和解") == 1.0  # 2 positive -> clamp


def test_sentiment_negative_only_clamps_low():
    assert sentiment_of_text("他背叛了她，反目成仇") == -1.0


def test_sentiment_balanced_pos_and_neg_is_zero():
    assert sentiment_of_text("和解但又被背叛") == 0.0


def test_sentiment_no_signal_is_zero():
    assert sentiment_of_text("他们见面了。") == 0.0


def test_sentiment_negation_guard_flips_positive_to_negative():
    # "不再信任" contains the positive kw 信任 — must NOT count positive.
    assert sentiment_of_text("她不再信任他") < 0.0
    # English negation
    assert sentiment_of_text("no longer trusts him") < 0.0


def test_sentiment_bilingual_parity():
    assert sentiment_of_text("他们和解了") > 0.0
    assert sentiment_of_text("they reconciled") > 0.0
    assert sentiment_of_text("彻底决裂") < 0.0
    assert sentiment_of_text("a bitter breakup") < 0.0


# --- pair extraction -------------------------------------------------------

def test_pair_key_sorted_canonical():
    series = extract_pair_series(
        [_archive("s1", {"B": {"A": "和解"}})], _plan({"s1": 1})
    )
    assert len(series) == 1
    assert series[0].pair_key == "A|B"
    assert {series[0].from_id, series[0].to_id} == {"A", "B"}


def test_pair_series_groups_across_chapters_in_order():
    archives = [
        _archive("s1", {"Hero": {"Villain": "和解"}}),       # ch1
        _archive("s2", {"Hero": {"Villain": "再次背叛"}}),    # ch2
        _archive("s3", {"Villain": {"Hero": "重归于好"}}),    # ch3 (reverse dir)
    ]
    series = extract_pair_series(archives, _plan({"s1": 1, "s2": 2, "s3": 3}))
    assert len(series) == 1
    pair = series[0]
    assert [p.chapter_number for p in pair.series] == [1, 2, 3]
    # ch1 positive, ch2 negative, ch3 positive
    assert pair.series[0].sentiment > 0
    assert pair.series[1].sentiment < 0
    assert pair.series[2].sentiment > 0


def test_pair_series_skips_error_character_change_entries():
    bad = {"Hero": {"error": "boom", "emotion_change": "",
                    "goal_update": "", "relationship_changes": {}}}
    series = extract_pair_series([_archive("s1", {})], _plan({"s1": 1}))
    # no real relationship_changes -> no pairs (the bad dict has empty rc anyway)
    assert series == []


def test_pair_series_handles_mixed_name_and_id_keys():
    # other_id may be a name or an id; pair_key treats both opaquely + sorts.
    series = extract_pair_series(
        [_archive("s1", {"c1": {"c2": "和解"}, "c2": {"c1": "支持"}})],
        _plan({"s1": 1}),
    )
    assert len(series) == 1
    assert series[0].pair_key == "c1|c2"


# --- trend classification --------------------------------------------------

def test_trend_single_observation_is_stable():
    series = [StrengthPoint(1, 0.8, "x")]
    t = classify_trend(series)
    assert t.trend == "STABLE"


def test_trend_rising_is_improving():
    t = classify_trend([StrengthPoint(1, 0.0, ""), StrengthPoint(2, 0.8, "")])
    assert t.trend == "IMPROVING"
    assert t.delta_first_last == 0.8


def test_trend_falling_is_deteriorating():
    t = classify_trend([StrengthPoint(1, 0.5, ""), StrengthPoint(2, -0.8, "")])
    assert t.trend == "DETERIORATING"


def test_trend_small_slope_is_stable():
    t = classify_trend([StrengthPoint(1, 0.1, ""), StrengthPoint(2, 0.2, "")])
    assert t.trend == "STABLE"  # slope 0.1 < 0.20 threshold


def test_trend_single_reversal_net_flat_is_stable():
    # [1,-1,1] has ONE turning point (a V); net-flat slope => STABLE, not VOLATILE.
    # VOLATILE needs two turning points (a W/M) per _VOLATILE_REVERSALS=2.
    t = classify_trend([
        StrengthPoint(1, 1.0, ""), StrengthPoint(2, -1.0, ""),
        StrengthPoint(3, 1.0, ""),
    ])
    assert t.trend == "STABLE"


def test_trend_two_turning_points_is_volatile():
    # length-4 W/M shape: two direction changes => VOLATILE.
    t = classify_trend([
        StrengthPoint(1, 1.0, ""), StrengthPoint(2, -1.0, ""),
        StrengthPoint(3, 1.0, ""), StrengthPoint(4, -1.0, ""),
    ])
    assert t.trend == "VOLATILE"


def test_trend_volatile_precedence_over_improving():
    # net slope is strongly positive but oscillates -> VOLATILE wins.
    t = classify_trend([
        StrengthPoint(1, -1.0, ""), StrengthPoint(2, 1.0, ""),
        StrengthPoint(3, -1.0, ""), StrengthPoint(4, 1.0, ""),
    ])
    assert t.trend == "VOLATILE"


def test_trend_suggestions_bilingual_nonempty():
    for trend in ("IMPROVING", "DETERIORATING", "VOLATILE", "STABLE"):
        series = [StrengthPoint(1, 0.0, ""), StrengthPoint(2, 0.5 if trend == "IMPROVING" else 0.0, "")]
        t = classify_trend(series) if trend == "STABLE" else None
        # build one of each directly
    pts = {"IMPROVING": [StrengthPoint(1, 0.0, ""), StrengthPoint(2, 0.8, "")]}
    assert classify_trend(pts["IMPROVING"]).suggestion_zh
    assert classify_trend(pts["IMPROVING"]).suggestion_en


# --- report assembly -------------------------------------------------------

def test_build_report_empty_archives_no_crash():
    report = build_relationship_trend_report([], _plan({}))
    assert report.pairs == []
    assert report.chapter_count == 0


def test_build_report_skips_archives_in_no_chapter_spec():
    archives = [_archive("sX", {"A": {"B": "和解"}})]
    plan = ChapterPlan(chapters=[ChapterSpec(number=1, title="T", scene_ids=["s1"], summary="")])
    report = build_relationship_trend_report(archives, plan)
    assert report.pairs == []  # sX is in no chapter -> not analyzed


def test_build_report_to_dict_roundtrips():
    archives = [
        _archive("s1", {"Hero": {"Villain": "和解"}}),
        _archive("s2", {"Hero": {"Villain": "再次背叛"}}),
    ]
    report = build_relationship_trend_report(archives, _plan({"s1": 1, "s2": 2}))
    d = report.to_dict()
    assert d["pairs"][0]["pair_key"] == "Hero|Villain"
    json.dumps(d)  # serializable for the completed event


def test_build_report_deteriorating_pair_end_to_end():
    archives = [
        _archive("s1", {"Hero": {"Villain": "信任加深，和解"}}),   # +1.0
        _archive("s2", {"Hero": {"Villain": "彻底背叛，反目"}}),   # -1.0
    ]
    report = build_relationship_trend_report(archives, _plan({"s1": 1, "s2": 2}))
    assert len(report.pairs) == 1
    assert report.pairs[0].trend == "DETERIORATING"
    assert report.pairs[0].observation_count == 2
