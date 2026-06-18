"""Graph-inference channel — deterministic, read-only (T3-④).

Runs a small set of Cypher rules over the Kuzu knowledge graph to surface
high-confidence STRUCTURAL facts the prose didn't state outright — co-faction
allegiance, co-location, and transitive causality — as an InferenceReport. It
only READS (MATCH/RETURN); it writes no nodes or edges, so it cannot pollute the
graph (the read-only contract is enforced by a write-keyword guard + a node/edge
count test). Reuses KuzuStore.query_cypher — zero new dependencies.

Report-only in v1 (attached to WrittenOutput when opted in). Feeding these
inferred facts into canon_verifier as extra context is a future, separately-
gated step.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Callable

_WRITE_KEYWORDS = ("create", "merge", "delete", " set ", "remove")


@dataclass(frozen=True)
class InferredFact:
    """One inferred structural fact, with the evidence chain that produced it."""

    rule_id: str
    subject: str
    relation: str
    object: str
    evidence_path: list[dict[str, str]]   # [{subject, relation, object}, ...]
    confidence: float


@dataclass
class GraphInferenceReport:
    facts: list[InferredFact] = field(default_factory=list)
    rule_ids_run: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


# A rule: (rule_id, read-only cypher, relation label, confidence, row->facts)
# Cypher uses only forward edges + shared-node joins (no reverse-edge syntax) so
# it is portable across Kuzu versions.
def _co_faction_facts(row: dict, confidence: float) -> list[InferredFact]:
    a, b, f = row["a"], row["b"], row["f"]
    return [InferredFact(
        rule_id="co_faction", subject=a, relation="co_faction", object=b,
        evidence_path=[
            {"subject": a, "relation": "BELONGS_TO", "object": f},
            {"subject": b, "relation": "BELONGS_TO", "object": f},
        ],
        confidence=confidence,
    )]


def _co_location_facts(row: dict, confidence: float) -> list[InferredFact]:
    a, b = row["a"], row["b"]
    loc = row.get("l") or row.get("loc") or ""
    return [InferredFact(
        rule_id="co_location", subject=a, relation="co_location", object=b,
        evidence_path=[
            {"subject": a, "relation": "LOCATED_AT", "object": loc},
            {"subject": b, "relation": "LOCATED_AT", "object": loc},
        ],
        confidence=confidence,
    )]


def _indirect_cause_facts(row: dict, confidence: float) -> list[InferredFact]:
    return [InferredFact(
        rule_id="indirect_cause", subject=row["e1"], relation="indirect_cause",
        object=row["e3"],
        evidence_path=[
            {"subject": row["e1"], "relation": "CAUSED_BY", "object": row["e2"]},
            {"subject": row["e2"], "relation": "CAUSED_BY", "object": row["e3"]},
        ],
        confidence=confidence,
    )]


_RULES: list[tuple[str, str, float, Callable[[dict, float], list[InferredFact]]]] = [
    (
        "co_faction",
        "MATCH (a:Character)-[:BELONGS_TO]->(f:Faction), "
        "(b:Character)-[:BELONGS_TO]->(f) "
        "WHERE a.name < b.name RETURN a.name AS a, f.name AS f, b.name AS b",
        0.8, _co_faction_facts,
    ),
    (
        "co_location",
        "MATCH (a:Character)-[:LOCATED_AT]->(l:Location), "
        "(b:Character)-[:LOCATED_AT]->(l) "
        "WHERE a.name < b.name RETURN a.name AS a, l.name AS l, b.name AS b",
        0.7, _co_location_facts,
    ),
    (
        "indirect_cause",
        "MATCH (e1:Event)-[:CAUSED_BY]->(e2:Event)-[:CAUSED_BY]->(e3:Event) "
        "WHERE e1.name < e3.name "
        "RETURN e1.name AS e1, e2.name AS e2, e3.name AS e3",
        0.75, _indirect_cause_facts,
    ),
]


class GraphInferenceEngine:
    """Runs the read-only inference rules over a KuzuStore-like graph."""

    def __init__(self, kuzu: Any) -> None:
        self._kuzu = kuzu

    def run(self) -> GraphInferenceReport:
        facts: list[InferredFact] = []
        run: list[str] = []
        for rule_id, cypher, confidence, mapper in _RULES:
            if not _is_readonly(cypher):
                # Defense in depth: never execute a write-keyword query.
                continue
            run.append(rule_id)
            try:
                rows = self._kuzu.query_cypher(cypher)
            except Exception:
                continue
            for row in rows or []:
                try:
                    facts.extend(mapper(row, confidence))
                except Exception:
                    continue
        return GraphInferenceReport(facts=facts, rule_ids_run=run)


def _is_readonly(cypher: str) -> bool:
    low = cypher.lower()
    return not any(kw in low for kw in _WRITE_KEYWORDS)
