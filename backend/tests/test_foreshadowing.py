"""Tests for the Foreshadowing registry primitive (PART A)."""

from __future__ import annotations

import dataclasses

import pytest

from app.services.narrative.foreshadowing import (
    Foreshadowing,
    ForeshadowingRegistry,
)


def _f(id: str, planted: int, importance: str = "MEDIUM", **kw) -> Foreshadowing:
    return Foreshadowing(
        id=id,
        planted_in_chapter=planted,
        description=f"thread {id}",
        importance=importance,
        status=kw.pop("status", "PLANTED"),
        **kw,
    )


def test_post_init_resolved_before_planted_raises():
    with pytest.raises(ValueError):
        Foreshadowing("a", 5, "x", "LOW", "RESOLVED", resolved_in_chapter=3)


def test_post_init_resolved_status_requires_resolved_chapter():
    with pytest.raises(ValueError):
        Foreshadowing("a", 1, "x", "LOW", "RESOLVED")


def test_post_init_valid_resolved_ok():
    f = Foreshadowing("a", 2, "x", "LOW", "RESOLVED", resolved_in_chapter=4)
    assert f.resolved_in_chapter == 4


def test_frozen_immutable():
    f = _f("a", 1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        f.status = "RESOLVED"  # type: ignore[misc]


def test_register_rejects_duplicate_id():
    reg = ForeshadowingRegistry([_f("a", 1)])
    with pytest.raises(ValueError):
        reg.register(_f("a", 2))


def test_mark_resolved_returns_new_immutable_and_replaces():
    original = _f("a", 1)
    reg = ForeshadowingRegistry([original])
    resolved = reg.mark_resolved("a", 5)
    assert original.status == "PLANTED"
    assert resolved is not original
    assert resolved.status == "RESOLVED"
    assert resolved.resolved_in_chapter == 5
    assert reg.items[0].status == "RESOLVED"


def test_mark_resolved_unknown_id_raises():
    reg = ForeshadowingRegistry()
    with pytest.raises(KeyError):
        reg.mark_resolved("ghost", 3)


def test_get_unresolved_excludes_resolved_and_abandoned():
    reg = ForeshadowingRegistry(
        [
            _f("a", 1),
            _f("b", 1, status="ABANDONED"),
            Foreshadowing("c", 1, "x", "LOW", "RESOLVED", resolved_in_chapter=2),
        ]
    )
    assert [i.id for i in reg.get_unresolved()] == ["a"]


def test_get_ready_to_resolve():
    reg = ForeshadowingRegistry(
        [_f("a", 1, suggested_resolve_chapter=5), _f("b", 1, suggested_resolve_chapter=9)]
    )
    assert [i.id for i in reg.get_ready_to_resolve(5)] == ["a"]


def test_get_overdue():
    reg = ForeshadowingRegistry(
        [_f("a", 1, suggested_resolve_chapter=4), _f("b", 1, suggested_resolve_chapter=6)]
    )
    assert [i.id for i in reg.get_overdue(6)] == ["a"]


def test_get_upcoming_window():
    reg = ForeshadowingRegistry(
        [
            _f("now", 1, suggested_resolve_chapter=6),
            _f("soon", 1, suggested_resolve_chapter=9),
            _f("far", 1, suggested_resolve_chapter=10),
        ]
    )
    assert [i.id for i in reg.get_upcoming(6)] == ["soon"]


def test_apply_ttl_downgrade_low_past_1x_abandoned():
    reg = ForeshadowingRegistry([_f("a", 0, "LOW")])
    reg.apply_ttl_downgrade(current=16, ttl=15)
    assert reg.items[0].status == "ABANDONED"


def test_apply_ttl_downgrade_medium_past_1_2x():
    reg = ForeshadowingRegistry([_f("a", 0, "MEDIUM"), _f("b", 0, "MEDIUM")])
    reg.apply_ttl_downgrade(current=18, ttl=15)
    assert reg.items[0].status == "PLANTED"
    reg.apply_ttl_downgrade(current=19, ttl=15)
    assert all(i.status == "ABANDONED" for i in reg.items)


def test_apply_ttl_downgrade_high_critical_never():
    reg = ForeshadowingRegistry([_f("a", 0, "HIGH"), _f("b", 0, "CRITICAL")])
    reg.apply_ttl_downgrade(current=999, ttl=15)
    assert all(i.status == "PLANTED" for i in reg.items)


def test_get_t0_eligible_ranking():
    reg = ForeshadowingRegistry(
        [
            _f("other", 8, "HIGH"),
            _f("imminent", 7, "LOW", suggested_resolve_chapter=10),
            _f("overdue", 1, "LOW", suggested_resolve_chapter=5),
        ]
    )
    assert [i.id for i in reg.get_t0_eligible(current=9)] == [
        "overdue",
        "imminent",
        "other",
    ]


def test_get_t0_eligible_tiebreak_importance_then_age():
    reg = ForeshadowingRegistry(
        [
            _f("low_new", 8, "LOW", suggested_resolve_chapter=2),
            _f("high_any", 7, "HIGH", suggested_resolve_chapter=2),
            _f("low_old", 1, "LOW", suggested_resolve_chapter=2),
        ]
    )
    assert [i.id for i in reg.get_t0_eligible(current=9)] == [
        "high_any",
        "low_old",
        "low_new",
    ]


def test_get_t0_eligible_caps_at_max_items():
    reg = ForeshadowingRegistry([_f(f"f{n}", 1) for n in range(10)])
    assert len(reg.get_t0_eligible(current=5)) == 6


def test_to_dict_from_dict_roundtrip():
    reg = ForeshadowingRegistry(
        [
            _f("a", 1, "HIGH", suggested_resolve_chapter=5),
            Foreshadowing("b", 2, "y", "LOW", "RESOLVED", resolved_in_chapter=4),
        ]
    )
    restored = ForeshadowingRegistry.from_dict(reg.to_dict())
    assert {i.id: (i.status, i.resolved_in_chapter) for i in restored.items} == {
        "a": ("PLANTED", None),
        "b": ("RESOLVED", 4),
    }
