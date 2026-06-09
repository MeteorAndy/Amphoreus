"""Tests for T2-⑦: prop-lifecycle / Chekhov-gun tracking.

Twins the T2-⑤ tension scorer's shape: post-write, report-only, opt-in,
transient (no persistence). The deterministic classifier + report builder are
pure; the mention extractor is one LLM call that degrades to [] on any error
(mirrors ProseFactExtractor). Run as a targeted file — full suite hangs:
    uv run pytest tests/test_prop_lifecycle.py -v
"""

from __future__ import annotations

import json

import pytest
from unittest.mock import AsyncMock

from app.services.narrative.prop_lifecycle import (
    PropMention,
    PropLifecycle,
    PropLifecycleReport,
    PropMentionExtractor,
    classify_props,
    build_prop_lifecycle_report,
)


# --- record invariants ----------------------------------------------------

def test_propmention_rejects_bad_predicate():
    with pytest.raises(ValueError):
        PropMention(object_name="ring", predicate="NOPE", chapter=1)


def test_proplifecycle_rejects_bad_status():
    with pytest.raises(ValueError):
        PropLifecycle(object_name="ring", introduced_in_chapter=1, status="BOGUS",
                      use_count=0, mention_chapters=[1], last_chapter=1)


def test_proplifecycle_roundtrip():
    p = PropLifecycle(object_name="ring", introduced_in_chapter=2, status="PAID_OFF",
                      use_count=1, mention_chapters=[2, 4], last_chapter=4)
    assert PropLifecycle.from_dict(p.to_dict()) == p
    rep = PropLifecycleReport(props=[p], unresolved=[])
    assert "props" in rep.to_dict() and "unresolved" in rep.to_dict()


# --- deterministic classifier ---------------------------------------------

def test_classify_introduce_then_use_is_paid_off():
    mentions = [
        PropMention("the ring", "INTRODUCE", 2),
        PropMention("the ring", "USE", 4),
    ]
    props = classify_props(mentions)
    assert len(props) == 1
    p = props[0]
    assert p.status == "PAID_OFF"
    assert p.introduced_in_chapter == 2
    assert p.use_count == 1


def test_classify_introduce_only_is_unresolved():
    props = classify_props([PropMention("a dagger", "INTRODUCE", 1)])
    assert props[0].status == "UNRESOLVED"
    report = build_prop_lifecycle_report_sync(props)
    assert "a dagger" in report.unresolved


def test_classify_abandon_is_deliberate_not_flagged():
    mentions = [
        PropMention("the locket", "INTRODUCE", 1),
        PropMention("the locket", "ABANDON", 5),
    ]
    props = classify_props(mentions)
    assert props[0].status == "ABANDONED"
    report = build_prop_lifecycle_report_sync(props)
    assert "the locket" not in report.unresolved


def test_classify_normalizes_names():
    mentions = [
        PropMention("the Ring", "INTRODUCE", 1),
        PropMention("The ring", "USE", 2),
        PropMention("  Ring ", "USE", 3),
    ]
    props = classify_props(mentions)
    assert len(props) == 1
    assert props[0].use_count == 2


def test_classify_use_before_introduce_edgecase():
    mentions = [
        PropMention("sword", "USE", 5),
        PropMention("sword", "INTRODUCE", 2),
    ]
    props = classify_props(mentions)
    assert props[0].introduced_in_chapter == 2  # earliest chapter wins
    assert props[0].status == "PAID_OFF"


# --- LLM extractor (graceful degrade) -------------------------------------

def _extractor(payload):
    llm = AsyncMock()
    llm.chat_json = AsyncMock(return_value=payload)
    return PropMentionExtractor(llm)


@pytest.mark.asyncio
async def test_extractor_parses_valid_mentions():
    ex = _extractor({"mentions": [
        {"object_name": "银钥匙", "predicate": "INTRODUCE", "chapter": 2, "evidence": "她拿出银钥匙"},
        {"object_name": "银钥匙", "predicate": "USE", "chapter": 4},
    ]})
    out = await ex.extract("prose")
    assert len(out) == 2
    assert out[0].object_name == "银钥匙" and out[0].predicate == "INTRODUCE"


@pytest.mark.asyncio
async def test_extractor_drops_bad_predicate_and_dupes():
    ex = _extractor({"mentions": [
        {"object_name": "ring", "predicate": "FROBNICATE", "chapter": 1},  # bad predicate
        {"object_name": "ring", "predicate": "INTRODUCE", "chapter": 1},
        {"object_name": "ring", "predicate": "INTRODUCE", "chapter": 1},   # dupe
        {"predicate": "USE", "chapter": 2},                                 # missing name
    ]})
    out = await ex.extract("prose")
    assert len(out) == 1


@pytest.mark.asyncio
async def test_extractor_degrades_on_llm_error():
    llm = AsyncMock()
    llm.chat_json = AsyncMock(side_effect=RuntimeError("boom"))
    out = await PropMentionExtractor(llm).extract("prose")
    assert out == []


@pytest.mark.asyncio
async def test_extractor_empty_prose_no_call():
    ex = _extractor({"mentions": []})
    out = await ex.extract("   ")
    assert out == []
    ex._llm.chat_json.assert_not_called()


# --- end-to-end builder ----------------------------------------------------

@pytest.mark.asyncio
async def test_build_report_end_to_end_and_degrades():
    llm = AsyncMock()
    llm.chat_json = AsyncMock(return_value={"mentions": [
        {"object_name": "the map", "predicate": "INTRODUCE", "chapter": 1},
        {"object_name": "the map", "predicate": "USE", "chapter": 3},
        {"object_name": "the whistle", "predicate": "INTRODUCE", "chapter": 2},
    ]})
    report = await build_prop_lifecycle_report(llm, "some prose")
    names = {p.object_name for p in report.props}
    assert "the map" in names and "the whistle" in names
    assert "the whistle" in report.unresolved  # introduced, never used
    json.dumps(report.to_dict())  # serializable

    # degrade: a raising llm yields an empty report, never raises
    bad = AsyncMock()
    bad.chat_json = AsyncMock(side_effect=RuntimeError("boom"))
    empty = await build_prop_lifecycle_report(bad, "some prose")
    assert empty.props == [] and empty.unresolved == []


# --- helper: sync report assembly from already-classified props -----------

def build_prop_lifecycle_report_sync(props):
    """Local convenience mirroring the report's unresolved-derivation, so the
    classifier tests don't need an LLM."""
    return PropLifecycleReport(
        props=props,
        unresolved=[p.object_name for p in props if p.status == "UNRESOLVED"],
    )
