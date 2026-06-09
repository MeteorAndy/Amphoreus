"""Tests for T2-⑤: dramatic tension scoring (zero-LLM, deterministic).

Run as a targeted file — the full suite hangs on integration tests:
    uv run pytest tests/test_tension_scorer.py -v

All inputs are fabricated directly (no LLM, no MemoryManager). The scorer reads
only fields SceneResolution already populates on SceneArchive.
"""

from __future__ import annotations

import json

from app.services.narrative.tension_scorer import (
    TensionScore,
    ChapterTension,
    TensionReport,
    phase_for_chapter,
    score_scene_tension,
    aggregate_chapter_tension,
    build_tension_report,
)
from app.services.narrative.types import ChapterSpec, ChapterPlan
from app.services.scene_engine.types import RoundEntry, EnvironmentUpdate
from app.services.scene_engine.resolution import SceneArchive


# --- builders -------------------------------------------------------------

def _round(n: int) -> RoundEntry:
    return RoundEntry(
        round_num=n, actor_id="c1", actor_name="Ada",
        dialogue="...", action="...", inner_thought="...", emotion="neutral",
    )


def _env(atmosphere: str = "", changes=None, bg: str = "") -> EnvironmentUpdate:
    return EnvironmentUpdate(
        atmosphere=atmosphere, changes=changes or [], background_activity=bg
    )


def _archive(
    scene_id: str = "s1", n_rounds: int = 0, atmosphere: str = "",
    char_changes: dict | None = None,
) -> SceneArchive:
    return SceneArchive(
        scene_id=scene_id,
        rounds=[_round(i) for i in range(n_rounds)],
        final_environment=_env(atmosphere),
        character_changes=char_changes if char_changes is not None else {},
    )


# --- scene scoring --------------------------------------------------------

def test_score_scene_empty_rounds_low_intensity():
    s = score_scene_tension(_archive(n_rounds=0))
    assert s.intensity < 0.05
    assert s.direction == "stable"


def test_high_round_count_raises_intensity():
    few = score_scene_tension(_archive(n_rounds=1))
    many = score_scene_tension(_archive(n_rounds=8))
    assert many.intensity > few.intensity
    assert "high_round_count" in many.conflict_signals
    # monotonic up to a cap: 20 rounds is not higher than the 10-round cap point
    capped = score_scene_tension(_archive(n_rounds=10))
    over = score_scene_tension(_archive(n_rounds=20))
    assert over.intensity == capped.intensity


def test_relationship_shifts_increase_intensity():
    changes = {
        "c1": {"emotion_change": "", "goal_update": "", "relationship_changes": {"c2": "betrayal"}},
        "c2": {"emotion_change": "", "goal_update": "", "relationship_changes": {"c1": "distrust"}},
    }
    shifted = score_scene_tension(_archive(char_changes=changes))
    flat = score_scene_tension(_archive())
    assert shifted.intensity > flat.intensity
    assert "relationship_shift" in shifted.conflict_signals


def test_escalating_atmosphere_direction_rising():
    s = score_scene_tension(_archive(atmosphere="气氛骤然紧张，危机逼近，对峙一触即发"))
    assert s.direction == "rising"
    assert "climactic_atmosphere" in s.conflict_signals


def test_resolution_atmosphere_direction_falling():
    s = score_scene_tension(_archive(atmosphere="尘埃落定，一切归于平静，众人释然"))
    assert s.direction == "falling"


def test_emotion_volatility_bilingual():
    zh = score_scene_tension(_archive(char_changes={
        "c1": {"emotion_change": "陷入愤怒与绝望", "goal_update": "", "relationship_changes": {}},
    }))
    en = score_scene_tension(_archive(char_changes={
        "c1": {"emotion_change": "overwhelmed by rage and despair", "goal_update": "", "relationship_changes": {}},
    }))
    base = score_scene_tension(_archive(char_changes={
        "c1": {"emotion_change": "calm", "goal_update": "", "relationship_changes": {}},
    }))
    assert zh.intensity > base.intensity
    assert en.intensity > base.intensity
    assert "emotional_volatility" in zh.conflict_signals
    assert "emotional_volatility" in en.conflict_signals


def test_error_reflection_entry_handled_gracefully():
    # SceneResolution writes this shape when a character reflection raises.
    err = {"c1": {"error": "boom", "emotion_change": "", "goal_update": "", "relationship_changes": {}}}
    s = score_scene_tension(_archive(char_changes=err))  # must not raise
    assert s.intensity < 0.05
    assert "emotional_volatility" not in s.conflict_signals


def test_intensity_clamped_0_1():
    pathological = {f"c{i}": {
        "emotion_change": "rage fury terror despair", "goal_update": "fail thwart",
        "relationship_changes": {f"o{j}": "x" for j in range(5)},
    } for i in range(10)}
    s = score_scene_tension(_archive(n_rounds=50, atmosphere="climax escalating crisis", char_changes=pathological))
    assert 0.0 <= s.intensity <= 1.0
    assert s.intensity == 1.0


# --- phase SSOT -----------------------------------------------------------

def test_phase_for_chapter_boundaries():
    assert phase_for_chapter(1, 10) == "opening"       # 0.10
    assert phase_for_chapter(5, 10) == "development"   # 0.50
    assert phase_for_chapter(9, 10) == "convergence"   # 0.90 boundary inclusive
    assert phase_for_chapter(10, 10) == "finale"       # 1.00
    assert phase_for_chapter(3, 4) == "development"    # 0.75 dev boundary inclusive
    assert phase_for_chapter(4, 4) == "finale"
    # short-story total<3: still returns a valid phase, never crashes
    assert phase_for_chapter(1, 1) in {"opening", "development", "convergence", "finale"}


# --- chapter aggregation --------------------------------------------------

def test_chapter_tension_flat_when_below_phase_floor():
    low = [TensionScore("s1", 0.1, "stable", []), TensionScore("s2", 0.1, "stable", [])]
    ch = aggregate_chapter_tension(low, chapter_number=9, total=10)  # convergence
    assert ch.expected_phase == "convergence"
    assert ch.flat is True


def test_chapter_tension_not_flat_in_opening():
    modest = [TensionScore("s1", 0.3, "stable", [])]
    ch = aggregate_chapter_tension(modest, chapter_number=1, total=10)  # opening
    assert ch.expected_phase == "opening"
    assert ch.flat is False


# --- report assembly ------------------------------------------------------

def test_build_tension_report_maps_scenes_to_chapters():
    archives = [_archive("s1", n_rounds=2), _archive("s2", n_rounds=3), _archive("s3", n_rounds=8)]
    plan = ChapterPlan(chapters=[
        ChapterSpec(number=1, title="A", scene_ids=["s1", "s2"], summary=""),
        ChapterSpec(number=2, title="B", scene_ids=["s3"], summary=""),
    ])
    report = build_tension_report(archives, plan)
    assert len(report.chapters) == 2
    assert len(report.chapters[0].scene_scores) == 2
    assert len(report.chapters[1].scene_scores) == 1
    assert len(report.scenes) == 3


def test_chapter_with_no_matching_archives_yields_zero():
    archives = [_archive("s1", n_rounds=5)]
    plan = ChapterPlan(chapters=[
        ChapterSpec(number=1, title="A", scene_ids=["sX"], summary=""),  # absent
    ])
    report = build_tension_report(archives, plan)
    assert report.chapters[0].tension == 0.0
    assert report.chapters[0].scene_scores == []


def test_tension_report_to_dict_shape():
    archives = [_archive("s1", n_rounds=4, atmosphere="紧张升级")]
    plan = ChapterPlan(chapters=[ChapterSpec(number=1, title="A", scene_ids=["s1"], summary="")])
    d = build_tension_report(archives, plan).to_dict()
    assert "scenes" in d and "chapters" in d
    assert "scene_scores" in d["chapters"][0]
    json.dumps(d)  # must be serializable
