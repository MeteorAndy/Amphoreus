"""Wiring tests for PR3: prose fact extraction -> Kuzu/OpenViking persistence.

Covers ProseFactExtractor (parse/filter/degrade) and InferredTriplesStore
(node upsert + schema-valid edges only, async thread isolation, chapter
invalidation via CONTAINS).
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.narrative.prose_fact_extractor import ProseFactExtractor
from app.services.narrative.inferred_triples_store import InferredTriplesStore
from app.services.narrative.types_post_write import InferredTriple


def _extractor(payload):
    llm = AsyncMock()
    llm.chat_json = AsyncMock(return_value=payload)
    return ProseFactExtractor(llm)


@pytest.mark.asyncio
async def test_extract_parses_valid_triples():
    ex = _extractor({"triples": [
        {"subject": "林辰", "predicate": "LOCATED_AT", "object": "回响之井",
         "subject_type": "Character", "object_type": "Location", "confidence": 0.8},
    ]})
    out = await ex.extract("林辰站在回响之井旁。", "s1")
    assert len(out) == 1
    assert out[0].subject == "林辰" and out[0].object_ == "回响之井"
    assert out[0].chapter_id == "s1" and out[0].edge_is_valid()


@pytest.mark.asyncio
async def test_extract_drops_bad_types_and_dupes():
    ex = _extractor({"triples": [
        {"subject": "A", "predicate": "X", "object": "B",
         "subject_type": "Nonsense", "object_type": "Location"},  # bad type
        {"subject": "A", "predicate": "RELATES_TO", "object": "C",
         "subject_type": "Character", "object_type": "Character"},
        {"subject": "A", "predicate": "RELATES_TO", "object": "C",
         "subject_type": "Character", "object_type": "Character"},  # dupe
        {"object": "missing subject"},  # incomplete
    ]})
    out = await ex.extract("prose", "s1")
    assert len(out) == 1


@pytest.mark.asyncio
async def test_extract_degrades_on_llm_error():
    llm = AsyncMock()
    llm.chat_json = AsyncMock(side_effect=RuntimeError("boom"))
    out = await ProseFactExtractor(llm).extract("prose", "s1")
    assert out == []


@pytest.mark.asyncio
async def test_extract_empty_prose_no_call():
    ex = _extractor({"triples": []})
    out = await ex.extract("   ", "s1")
    assert out == []
    ex._llm.chat_json.assert_not_called()


def _store():
    mem = MagicMock()
    mem.kuzu = MagicMock()
    mem.openviking = MagicMock()
    return InferredTriplesStore(mem), mem


@pytest.mark.asyncio
async def test_persist_upserts_nodes_and_valid_edge():
    store, mem = _store()
    t = InferredTriple(
        subject="林辰", predicate="LOCATED_AT", object_="回响之井",
        subject_type="Character", object_type="Location", chapter_id="s1",
    )
    await store.persist([t], "s1")
    # both endpoints upserted as nodes
    labels = [c.args[0] for c in mem.kuzu.create_node.call_args_list]
    assert "Character" in labels and "Location" in labels
    # valid edge written, OpenViking mirrored
    assert mem.kuzu.create_edge.call_count == 1
    assert mem.openviking.write_entry.call_count == 1


@pytest.mark.asyncio
async def test_persist_skips_invalid_edge_but_keeps_nodes():
    store, mem = _store()
    # CAUSED_BY requires Event->Event; Character->Location is invalid
    t = InferredTriple(
        subject="林辰", predicate="CAUSED_BY", object_="回响之井",
        subject_type="Character", object_type="Location", chapter_id="s1",
    )
    await store.persist([t], "s1")
    assert mem.kuzu.create_node.call_count == 2
    assert mem.kuzu.create_edge.call_count == 0  # edge dropped


@pytest.mark.asyncio
async def test_persist_empty_noop():
    store, mem = _store()
    await store.persist([], "s1")
    mem.kuzu.create_node.assert_not_called()
    mem.openviking.write_entry.assert_not_called()


@pytest.mark.asyncio
async def test_invalidate_chapter_uses_contains():
    store, mem = _store()
    mem.kuzu.query_cypher = MagicMock(return_value=[])
    await store.invalidate_chapter("s1")
    # one edge deletion per edge label, via CONTAINS on edge.properties
    # (edges are CREATE, never MERGE, so properties are per-chapter)
    assert mem.kuzu.query_cypher.call_count == 4
    for call in mem.kuzu.query_cypher.call_args_list:
        assert "CONTAINS" in call.args[0] and "DELETE e" in call.args[0]
        assert "s1" in call.args[1]["frag"]
    mem.openviking.delete_entry.assert_called_once()

