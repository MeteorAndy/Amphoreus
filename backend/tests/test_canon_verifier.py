"""Tests for the deterministic post-generation canon verifier."""

from __future__ import annotations

import json

from app.services.narrative.canon_verifier import verify, CanonReport, Violation
from app.services.narrative.types import CanonicalFact, CanonicalFacts


def _facts(scope: str = "all") -> CanonicalFacts:
    return CanonicalFacts(
        facts=[
            CanonicalFact(
                id="f1",
                topic="作者之死",
                question="是谁把它写进书里？",
                canonical_answer_zh="母亲，第97页",
                canonical_answer_en="The mother, page 97",
                rejected_answers=["父亲把自己写进了书"],
                scope=scope,
            )
        ]
    )


def test_rejected_proposition_flags_contradiction():
    facts = _facts()
    content = "在那个夜里，父亲把自己写进了书，无人察觉。"
    report = verify(content=content, facts=facts, target_format="novel")
    assert report.clean is False
    assert report.checked == 1
    assert len(report.violations) == 1
    v = report.violations[0]
    assert v.kind == "contradiction"
    assert v.fact_id == "f1"
    assert v.severity == "high"
    assert v.evidence and "父亲把自己写进了书" in v.evidence


def test_content_honoring_canon_is_clean():
    facts = _facts()
    content = "母亲终于承认，那段文字写在第97页，无可更改。"
    report = verify(content=content, facts=facts, target_format="novel")
    assert report.clean is True
    assert report.violations == []
    assert report.checked == 1


def test_canonical_absent_emits_unconfirmed_note():
    facts = _facts()
    content = "海风吹过石阶，少年沉默地走向灯塔，什么也没有说。"
    report = verify(content=content, facts=facts, target_format="novel")
    assert report.checked == 1
    assert report.clean is True
    assert len(report.violations) == 1
    v = report.violations[0]
    assert v.kind == "unconfirmed"
    assert v.severity == "low"
    assert v.fact_id == "f1"


def test_empty_facts_is_clean_zero_checked():
    report = verify(content="任意正文", facts=CanonicalFacts(), target_format="novel")
    assert report.checked == 0
    assert report.clean is True
    assert report.violations == []


def test_scope_filtering_ignores_out_of_scope_fact():
    facts = _facts(scope="novel")
    content = "在那个夜里，父亲把自己写进了书，无人察觉。"
    sp = verify(content=content, facts=facts, target_format="screenplay")
    assert sp.checked == 0
    assert sp.violations == []
    nv = verify(content=content, facts=facts, target_format="novel")
    assert nv.checked == 1
    assert any(v.kind == "contradiction" for v in nv.violations)


def test_report_to_dict_shape():
    report = CanonReport(
        violations=[
            Violation("f1", "t1", "contradiction", "high", "片段"),
            Violation("f2", "t2", "unconfirmed", "low", ""),
        ],
        checked=2,
        clean=False,
    )
    d = report.to_dict()
    assert set(d.keys()) == {"violations", "checked", "clean"}
    assert isinstance(d["checked"], int)
    assert isinstance(d["clean"], bool)
    assert d["violations"][0]["fact_id"] == "f1"
    assert d["violations"][0]["kind"] == "contradiction"
    json.dumps(d)
