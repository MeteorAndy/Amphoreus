"""Tests for T3-6: read-only entity event sourcing (CharacterEventHistory).

Derives an append-only event stream from the character_changes already on each
SceneArchive (zero write-path change). Pure, zero-LLM.

Run as a targeted file (full suite hangs on integration tests):
    uv run pytest tests/test_entity_events.py -v
"""

from __future__ import annotations

import json

from app.services.narrative.entity_events import (
    EntityEvent,
    CharacterEventHistory,
    build_entity_event_history,
)
from app.services.narrative.types import ChapterPlan, ChapterSpec
from app.services.scene_engine.resolution import SceneArchive
from app.services.scene_engine.types import EnvironmentUpdate


def _env() -> EnvironmentUpdate:
    return EnvironmentUpdate(atmosphere="", changes=[], background_activity="")


def _archive(scene_id: str, changes: dict) -> SceneArchive:
    return SceneArchive(
        scene_id=scene_id, rounds=[], final_environment=_env(),
        character_changes=changes,
    )


def _plan(mapping: dict[str, int]) -> ChapterPlan:
    by_ch: dict[int, list[str]] = {}
    for sid, ch in mapping.items():
        by_ch.setdefault(ch, []).append(sid)
    chapters = [
        ChapterSpec(number=ch, title=f"T{ch}", scene_ids=sids, summary="")
        for ch, sids in sorted(by_ch.items())
    ]
    return ChapterPlan(chapters=chapters)


# --- extraction -----------------------------------------------------------

def test_empty_archives_yield_no_events():
    h = build_entity_event_history([], _plan({}))
    assert h.events == []


def test_emotion_shift_extracted():
    h = build_entity_event_history(
        [_archive("s1", {"c1": {"emotion_change": "从平静转为愤怒",
                                 "goal_update": "", "relationship_changes": {}}})],
        _plan({"s1": 1}),
    )
    kinds = [e.kind for e in h.events if e.character_id == "c1"]
    assert "emotion_shift" in kinds


def test_empty_changes_not_extracted():
    h = build_entity_event_history(
        [_archive("s1", {"c1": {"emotion_change": "", "goal_update": "",
                                 "relationship_changes": {}}})],
        _plan({"s1": 1}),
    )
    # only a reveal (first appearance) — no emotion/goal/rel events
    assert [e.kind for e in h.events if e.character_id == "c1"] == ["reveal"]


def test_error_entry_skipped():
    bad = {"c1": {"error": "boom", "emotion_change": "",
                  "goal_update": "", "relationship_changes": {}}}
    h = build_entity_event_history([_archive("s1", bad)], _plan({"s1": 1}))
    assert h.events == []


def test_goal_update_and_relationship_delta_extracted():
    h = build_entity_event_history(
        [_archive("s1", {"c1": {"emotion_change": "", "goal_update": "决心复仇",
                                 "relationship_changes": {"c2": "决裂"}}})],
        _plan({"s1": 1}),
    )
    kinds = sorted(e.kind for e in h.events if e.character_id == "c1")
    assert kinds == ["goal_update", "relationship_delta", "reveal"]


def test_reveal_only_on_first_appearance():
    h = build_entity_event_history(
        [
            _archive("s1", {"c1": {"emotion_change": "a", "goal_update": "",
                                    "relationship_changes": {}}}),
            _archive("s2", {"c1": {"emotion_change": "b", "goal_update": "",
                                    "relationship_changes": {}}}),
        ],
        _plan({"s1": 1, "s2": 2}),
    )
    reveals = [e for e in h.events if e.kind == "reveal" and e.character_id == "c1"]
    assert len(reveals) == 1
    assert reveals[0].chapter == 1


# --- queries --------------------------------------------------------------

def test_get_events_filters_character_and_chapter_range():
    h = build_entity_event_history(
        [
            _archive("s1", {"c1": {"emotion_change": "a", "goal_update": "",
                                    "relationship_changes": {}}}),
            _archive("s2", {"c1": {"emotion_change": "b", "goal_update": "",
                                    "relationship_changes": {}}}),
            _archive("s3", {"c2": {"emotion_change": "z", "goal_update": "",
                                    "relationship_changes": {}}}),
        ],
        _plan({"s1": 1, "s2": 2, "s3": 3}),
    )
    c1_all = h.get_events("c1")
    assert all(e.character_id == "c1" for e in c1_all)
    c1_ch1 = h.get_events("c1", from_chapter=1, to_chapter=1)
    assert all(e.chapter == 1 for e in c1_ch1)
    assert h.get_events("nope") == []


def test_get_arc_transitions_returns_state_changes():
    h = build_entity_event_history(
        [_archive("s1", {"c1": {"emotion_change": "愤怒", "goal_update": "复仇",
                                 "relationship_changes": {"c2": "决裂"}}})],
        _plan({"s1": 1}),
    )
    arcs = h.get_arc_transitions("c1")
    kinds = {e.kind for e in arcs}
    assert "emotion_shift" in kinds and "relationship_delta" in kinds
    assert "reveal" not in kinds  # reveal is not an arc transition


def test_reconstruct_state_replays_cumulative():
    h = build_entity_event_history(
        [
            _archive("s1", {"c1": {"emotion_change": "愤怒", "goal_update": "复仇",
                                    "relationship_changes": {"c2": "决裂"}}}),
            _archive("s2", {"c1": {"emotion_change": "释然", "goal_update": "",
                                    "relationship_changes": {"c2": "和解"}}}),
        ],
        _plan({"s1": 1, "s2": 2}),
    )
    after_1 = h.reconstruct_state("c1", at_chapter=1)
    assert "愤怒" in after_1.get("emotion", "")
    assert after_1["relationships"].get("c2") == "决裂"
    after_2 = h.reconstruct_state("c1", at_chapter=2)
    assert "释然" in after_2["emotion"]
    assert after_2["relationships"]["c2"] == "和解"  # overwritten


# --- serialization --------------------------------------------------------

def test_to_dict_round_trips():
    h = build_entity_event_history(
        [_archive("s1", {"c1": {"emotion_change": "x", "goal_update": "",
                                 "relationship_changes": {}}})],
        _plan({"s1": 1}),
    )
    d = h.to_dict()
    json.dumps(d)
    restored = CharacterEventHistory.from_dict(d)
    assert len(restored.events) == len(h.events)
    assert restored.events[0].character_id == "c1"
