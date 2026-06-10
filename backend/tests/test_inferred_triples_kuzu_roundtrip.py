"""REAL-Kuzu round-trip tests for chapter invalidation (T2-① follow-up fix).

The mock-only test in test_post_write_extraction.py asserts the Cypher template
shape but never executes it — so a CONTAINS fragment that matches nothing still
passes. These tests run against an embedded Kuzu DB on a temp dir and prove the
deletion actually happens, is chapter-precise, is source_type-gated, and cleans
up only true orphan endpoints.

Run targeted (full suite hangs on integration tests):
    uv run pytest tests/test_inferred_triples_kuzu_roundtrip.py -v
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from app.services.memory.kuzu_store import props_fragment
from app.services.narrative.inferred_triples_store import InferredTriplesStore
from app.services.narrative.types_post_write import InferredTriple


# --- serializer/matcher symmetry (the drift guard) -------------------------

def test_props_fragment_is_substring_of_serialized_props():
    cases = [
        {"chapter_id": "s1", "confidence": 0.9, "source_type": "chapter_inferred"},
        {"chapter_id": "第一章", "source_type": "chapter_inferred"},
        {"chapter_id": 'quo"te', "source_type": "chapter_inferred"},
        {"chapter_id": "back\\slash", "source_type": "chapter_inferred"},
    ]
    for props in cases:
        serialized = json.dumps(props, ensure_ascii=False, separators=(", ", ": "))
        frag = props_fragment("chapter_id", props["chapter_id"])
        assert frag in serialized, f"{frag!r} not in {serialized!r}"


# --- real-Kuzu helpers ------------------------------------------------------

def _memory_with(kuzu):
    mem = MagicMock()
    mem.kuzu = kuzu
    mem.openviking = MagicMock()
    return mem


def _triple(subject, predicate, obj, s_type, o_type):
    return InferredTriple(
        subject=subject, predicate=predicate, object_=obj,
        subject_type=s_type, object_type=o_type, chapter_id="ignored",
    )


def _edges(kuzu, label):
    """All edges of `label` as decoded property dicts (assertion path does NOT
    use CONTAINS, so it can't share a bug with the mechanism under test)."""
    rows = kuzu.query_cypher(
        f"MATCH (a)-[e:{label}]->(b) RETURN a.name AS a, b.name AS b, e.properties AS p"
    )
    return [{"a": r["a"], "b": r["b"], **json.loads(r["p"])} for r in rows]


def _node_exists(kuzu, label, name):
    rows = kuzu.query_cypher(
        f"MATCH (n:{label}) WHERE n.name = $name RETURN n.name", {"name": name}
    )
    return len(rows) > 0


# --- THE headline round-trip ------------------------------------------------

@pytest.mark.asyncio
async def test_invalidate_deletes_target_chapter_only(real_kuzu):
    store = InferredTriplesStore(_memory_with(real_kuzu))

    # s1: Hero->Villain (RELATES_TO), Hero->Harbor (LOCATED_AT)
    await store.persist([
        _triple("Hero", "RELATES_TO", "Villain", "Character", "Character"),
        _triple("Hero", "LOCATED_AT", "Harbor", "Character", "Location"),
    ], "s1")
    # s2: Hero->Mentor (RELATES_TO)
    await store.persist([
        _triple("Hero", "RELATES_TO", "Mentor", "Character", "Character"),
    ], "s2")
    # a MANUAL edge in s1's chapter — must survive (source_type gating)
    real_kuzu.create_edge("Hero", "Villain", "RELATES_TO",
                          {"chapter_id": "s1", "source_type": "manual"})

    await store.invalidate_chapter("s1")

    relates = _edges(real_kuzu, "RELATES_TO")
    located = _edges(real_kuzu, "LOCATED_AT")
    # s1 chapter_inferred edges gone
    assert not [e for e in relates
                if e.get("chapter_id") == "s1"
                and e.get("source_type") == "chapter_inferred"]
    assert not [e for e in located if e.get("chapter_id") == "s1"]
    # s2 edge survives
    assert [e for e in relates if e.get("chapter_id") == "s2"]
    # manual edge survives (gating proof)
    assert [e for e in relates if e.get("source_type") == "manual"]
    # shared / still-referenced nodes survive
    assert _node_exists(real_kuzu, "Character", "Hero")      # alive via s2
    assert _node_exists(real_kuzu, "Character", "Villain")   # alive via manual
    # exclusive endpoint of the invalidated chapter is a true orphan -> removed
    assert not _node_exists(real_kuzu, "Location", "Harbor")


@pytest.mark.asyncio
async def test_invalidate_preserves_preexisting_core_node(real_kuzu):
    """A node owned by earlier pipeline stages is not an inferred orphan."""
    real_kuzu.create_node("Character", {
        "name": "Hero",
        "display_name": "Hero Prime",
        "role": "lead",
    })
    store = InferredTriplesStore(_memory_with(real_kuzu))
    await store.persist([
        _triple("Hero", "LOCATED_AT", "Harbor", "Character", "Location"),
    ], "s1")

    before = real_kuzu.get_node("Hero")
    assert before["role"] == "lead"
    assert "source_type" not in before

    await store.invalidate_chapter("s1")

    after = real_kuzu.get_node("Hero")
    assert after["role"] == "lead"
    assert _node_exists(real_kuzu, "Character", "Hero")
    assert not _node_exists(real_kuzu, "Location", "Harbor")


@pytest.mark.asyncio
async def test_invalidate_chinese_chapter_id(real_kuzu):
    """ensure_ascii symmetry — the twin of the separator bug. A ZH chapter id
    must round-trip: stored raw UTF-8, matched raw UTF-8."""
    store = InferredTriplesStore(_memory_with(real_kuzu))
    await store.persist([
        _triple("林辰", "LOCATED_AT", "回响之井", "Character", "Location"),
    ], "第一章")

    await store.invalidate_chapter("第一章")

    assert _edges(real_kuzu, "LOCATED_AT") == []


@pytest.mark.asyncio
async def test_invalidate_does_not_match_prefix_chapter(real_kuzu):
    """The closing quote in the JSON fragment must keep 's1' from matching 's10'."""
    store = InferredTriplesStore(_memory_with(real_kuzu))
    await store.persist([
        _triple("Hero", "RELATES_TO", "Villain", "Character", "Character"),
    ], "s1")
    await store.persist([
        _triple("Hero", "RELATES_TO", "Mentor", "Character", "Character"),
    ], "s10")

    await store.invalidate_chapter("s1")

    survivors = _edges(real_kuzu, "RELATES_TO")
    assert [e for e in survivors if e.get("chapter_id") == "s10"]
    assert not [e for e in survivors if e.get("chapter_id") == "s1"]
