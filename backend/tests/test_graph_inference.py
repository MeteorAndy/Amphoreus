"""Tests for T3-④: graph-inference channel (deterministic, read-only).

Runs a few Cypher rules over the Kuzu graph to surface high-confidence
structural facts (co-faction, co-location, transitive cause) as a report.
Read-only: MATCH/RETURN only — never writes. Validates with a REAL embedded
Kuzu DB (the invalidate_chapter lesson: mock tests can't catch a query that
matches nothing or silently writes).

    uv run pytest tests/test_graph_inference.py -v
"""

from __future__ import annotations

import json

import pytest

from app.services.narrative.graph_inference import (
    GraphInferenceEngine,
    GraphInferenceReport,
)


def _count(kuzu, cypher):
    return kuzu.query_cypher(cypher)[0].get("count", 0) if kuzu.query_cypher(cypher) else 0


def test_empty_graph_yields_empty_report(real_kuzu):
    report = GraphInferenceEngine(real_kuzu).run()
    assert report.facts == []
    assert report.rule_ids_run


def test_co_faction_inferred(real_kuzu):
    real_kuzu.create_node("Character", {"name": "A"})
    real_kuzu.create_node("Character", {"name": "B"})
    real_kuzu.create_node("Faction", {"name": "Guild"})
    real_kuzu.create_edge("A", "Guild", "BELONGS_TO", {})
    real_kuzu.create_edge("B", "Guild", "BELONGS_TO", {})

    report = GraphInferenceEngine(real_kuzu).run()
    co = [f for f in report.facts if f.relation == "co_faction"]
    assert len(co) == 1
    assert {co[0].subject, co[0].object} == {"A", "B"}
    assert co[0].confidence > 0
    assert co[0].evidence_path  # non-empty chain


def test_co_location_inferred(real_kuzu):
    real_kuzu.create_node("Character", {"name": "A"})
    real_kuzu.create_node("Character", {"name": "B"})
    real_kuzu.create_node("Location", {"name": "Tavern"})
    real_kuzu.create_edge("A", "Tavern", "LOCATED_AT", {})
    real_kuzu.create_edge("B", "Tavern", "LOCATED_AT", {})

    report = GraphInferenceEngine(real_kuzu).run()
    co = [f for f in report.facts if f.relation == "co_location"]
    assert len(co) == 1
    assert {co[0].subject, co[0].object} == {"A", "B"}


def test_transitive_cause_inferred(real_kuzu):
    real_kuzu.create_node("Event", {"name": "E1"})
    real_kuzu.create_node("Event", {"name": "E2"})
    real_kuzu.create_node("Event", {"name": "E3"})
    real_kuzu.create_edge("E1", "E2", "CAUSED_BY", {})
    real_kuzu.create_edge("E2", "E3", "CAUSED_BY", {})

    report = GraphInferenceEngine(real_kuzu).run()
    chain = [f for f in report.facts if f.relation == "indirect_cause"]
    assert len(chain) == 1
    assert chain[0].subject == "E1" and chain[0].object == "E3"


def test_inference_is_read_only(real_kuzu):
    """Running the engine must not create or delete any node/edge."""
    real_kuzu.create_node("Character", {"name": "A"})
    real_kuzu.create_node("Character", {"name": "B"})
    real_kuzu.create_node("Faction", {"name": "G"})
    real_kuzu.create_edge("A", "G", "BELONGS_TO", {})
    real_kuzu.create_edge("B", "G", "BELONGS_TO", {})

    nodes_before = _count(real_kuzu, "MATCH (n) RETURN count(n) AS count")
    edges_before = _count(real_kuzu, "MATCH ()-[e]->() RETURN count(e) AS count")

    GraphInferenceEngine(real_kuzu).run()

    nodes_after = _count(real_kuzu, "MATCH (n) RETURN count(n) AS count")
    edges_after = _count(real_kuzu, "MATCH ()-[e]->() RETURN count(e) AS count")
    assert nodes_after == nodes_before
    assert edges_after == edges_before


def test_report_to_dict_serializable(real_kuzu):
    real_kuzu.create_node("Character", {"name": "A"})
    real_kuzu.create_node("Character", {"name": "B"})
    real_kuzu.create_node("Faction", {"name": "G"})
    real_kuzu.create_edge("A", "G", "BELONGS_TO", {})
    real_kuzu.create_edge("B", "G", "BELONGS_TO", {})
    report = GraphInferenceEngine(real_kuzu).run()
    d = report.to_dict()
    json.dumps(d)
    assert "facts" in d and "rule_ids_run" in d
