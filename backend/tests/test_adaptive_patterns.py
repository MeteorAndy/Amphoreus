"""Tests for T3-③: AI-slop adaptive pattern detection (report-only).

Surfaces THIS novel's recurring cliche tics (patterns appearing >= threshold
times in the whole-novel ClicheReport) + a category distribution, as a
diagnostic. Does NOT mutate cliche_scanner._RULES or any severity — the
auto-promote/approve write loop is deliberately deferred (it is the only
write-path piece and is gated on the T3-⑤ OOC/Breakout boundary).

Run as a targeted file (full suite hangs on integration tests):
    uv run pytest tests/test_adaptive_patterns.py -v
"""

from __future__ import annotations

import json

from app.services.narrative.adaptive_patterns import (
    AdaptivePattern,
    AdaptivePatternReport,
    analyze_cliche_report,
)
from app.services.narrative.cliche_scanner import ClicheHit, ClicheReport, _RULES
from app.services.narrative.types import WritingOptions, WrittenOutput


def _hit(name, category="facial_cliche", excerpt="..."):
    rule = next((r for r in _RULES if r.name == name), None)
    return ClicheHit(
        name=name, severity=rule.severity if rule else "warning",
        category=category, span_excerpt=excerpt,
        replacement_hint=rule.replacement_hint if rule else "x",
    )


def _report(hits):
    return ClicheReport(hits=hits, ai_flavor_score=5.0)


# --- analyzer -------------------------------------------------------------

def test_empty_report_yields_no_patterns():
    rep = analyze_cliche_report(ClicheReport())
    assert rep.patterns == []
    assert rep.total_hits == 0


def test_single_occurrence_not_surfaced():
    # a cliche appearing once is not "recurring" — below threshold
    rep = analyze_cliche_report(_report([_hit("mouth_corner_curl")]))
    assert rep.patterns == []


def test_recurring_pattern_surfaced_with_share_and_excerpts():
    hits = [
        _hit("mouth_corner_curl", excerpt="a"),
        _hit("mouth_corner_curl", excerpt="b"),
        _hit("mouth_corner_curl", excerpt="c"),
    ]
    rep = analyze_cliche_report(_report(hits))
    assert len(rep.patterns) == 1
    p = rep.patterns[0]
    assert p.name == "mouth_corner_curl"
    assert p.observed_count == 3
    assert p.share_of_total == 1.0
    assert len(p.sampled_excerpts) <= 3 and p.sampled_excerpts  # capped, non-empty


def test_category_distribution_computed():
    hits = [
        _hit("mouth_corner_curl", "facial_cliche"),
        _hit("mouth_corner_curl", "facial_cliche"),
        _hit("deep_breath", "breath"),
        _hit("deep_breath", "breath"),
    ]
    rep = analyze_cliche_report(_report(hits))
    assert rep.category_distribution.get("facial_cliche") == 2
    assert rep.category_distribution.get("breath") == 2


def test_patterns_sorted_by_observed_count_desc():
    hits = [
        _hit("air_freeze", "atmosphere"), _hit("air_freeze", "atmosphere"),
        _hit("air_freeze", "atmosphere"),
        _hit("mouth_corner_curl"), _hit("mouth_corner_curl"),
    ]
    rep = analyze_cliche_report(_report(hits))
    names = [p.name for p in rep.patterns]
    assert names[0] == "air_freeze"  # 3 > 2
    assert names[1] == "mouth_corner_curl"


# --- purity / no mutation of _RULES --------------------------------------

def test_analyze_does_not_mutate_rules():
    before = [(_RULES[i].name, _RULES[i].severity) for i in range(len(_RULES))]
    analyze_cliche_report(_report([_hit("mouth_corner_curl")] * 5))
    after = [(_RULES[i].name, _RULES[i].severity) for i in range(len(_RULES))]
    assert before == after  # _RULES untouched (the whole point of this slice)


# --- serialization + opt-in default ---------------------------------------

def test_report_to_dict_serializable():
    rep = analyze_cliche_report(_report([_hit("mouth_corner_curl")] * 2))
    d = rep.to_dict()
    json.dumps(d)
    assert "patterns" in d and "category_distribution" in d


def test_writing_option_defaults_off():
    assert WritingOptions(format="novel").learn_adaptive_patterns is False
    assert WrittenOutput(content="", format="novel", word_count=0,
                         scene_count=0).adaptive_pattern_report is None
