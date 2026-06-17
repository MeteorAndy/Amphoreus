"""AI-slop adaptive pattern detection — report-only (T3-③).

Surfaces THIS novel's recurring cliche tics as a diagnostic: which patterns
appear >= threshold times across the whole-novel ClicheReport, their share of
the total, sampled excerpts, and a category distribution. It helps an author see
"this novel leans heavily on mouth-corner curls and frozen-air beats" — the
per-novel equivalent of PlotPilot's anti_ai_learning, without the risk.

The auto-promote (warning->critical by chapter-fraction) + approve/reject
persistence loop is DELIBERATELY DEFERRED: it is the only write-path piece
(mutating cliche_scanner._RULES / severity) and must be gated on the T3-⑤
OOC-vs-Breakout boundary so an intentional Breakout/Scar scene is never promoted
into a learned "pattern". This slice only REPORTS; _RULES is never touched.

Honest scope note: WrittenOutput carries ONE whole-novel ClicheReport (not
per-chapter), so there is no chapter-fraction to compute; recurrence is measured
as observed_count within the single scan. Cross-session history is also deferred.
"""

from __future__ import annotations

import dataclasses
from collections import Counter
from dataclasses import dataclass, field

from .cliche_scanner import ClicheReport

# A cliche must recur this many times within the novel to be "adaptive-worthy".
_THRESHOLD = 2
_EXCERPT_CAP = 3


@dataclass(frozen=True)
class AdaptivePattern:
    """One recurring cliche tic observed in this novel."""

    name: str
    category: str
    observed_count: int
    share_of_total: float          # count / total_hits
    sampled_excerpts: list[str]


@dataclass
class AdaptivePatternReport:
    """This novel's recurring AI-flavor profile. Advisory; never mutates rules."""

    patterns: list[AdaptivePattern] = field(default_factory=list)
    total_hits: int = 0
    ai_flavor_score: float = 0.0
    category_distribution: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


def analyze_cliche_report(report: ClicheReport) -> AdaptivePatternReport:
    """Aggregate a whole-novel ClicheReport into recurring patterns. Pure."""
    hits = report.hits if report else []
    if not hits:
        return AdaptivePatternReport(ai_flavor_score=report.ai_flavor_score if report else 0.0)

    total = len(hits)
    by_name: dict[str, list] = {}
    for h in hits:
        by_name.setdefault(h.name, []).append(h)

    patterns: list[AdaptivePattern] = []
    for name, group in by_name.items():
        if len(group) < _THRESHOLD:
            continue
        patterns.append(AdaptivePattern(
            name=name,
            category=group[0].category,
            observed_count=len(group),
            share_of_total=round(len(group) / total, 4),
            sampled_excerpts=[h.span_excerpt for h in group[:_EXCERPT_CAP]],
        ))
    patterns.sort(key=lambda p: p.observed_count, reverse=True)

    cat_dist = dict(Counter(h.category for h in hits))

    return AdaptivePatternReport(
        patterns=patterns,
        total_hits=total,
        ai_flavor_score=report.ai_flavor_score,
        category_distribution=cat_dist,
    )
