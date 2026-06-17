"""Tests for T3-⑤: OOC-vs-Breakout deviation classifier (report-only).

Re-labels character-consistency GuardianIssues into OOC (pull back) vs
BREAKOUT_SCAR (earned arc moment — keep tension) using text overlap between the
issue description and "earned-deviation" evidence (arc beats / foreshadowing /
event text). Pure; verdict is NEVER changed — only deviation_kind is stamped.

Run as a targeted file (full suite hangs on integration tests):
    uv run pytest tests/test_deviation_classifier.py -v
"""

from __future__ import annotations

from app.services.story_guardian.deviation_classifier import (
    DeviationKind,
    classify_issue,
    classify_issues,
)
from app.services.story_guardian.types import GuardianIssue, Severity


def _issue(dimension: str, description: str) -> GuardianIssue:
    return GuardianIssue(
        severity=Severity.WARNING, dimension=dimension,
        description=description, suggestion="...",
    )


# --- dimension gating -----------------------------------------------------

def test_non_character_dimension_stays_unclassified():
    issue = _issue("relationship_logic", "A and B suddenly allies with no setup")
    assert classify_issue(issue, evidence_texts=["A and B allies"]) == DeviationKind.UNCLASSIFIED


def test_character_dimension_with_no_evidence_is_ooc():
    issue = _issue("personality", "hero acts out of character: suddenly cowardly")
    assert classify_issue(issue, evidence_texts=[]) == DeviationKind.OOC


# --- evidence overlap -> BREAKOUT_SCAR ------------------------------------

def test_evidence_overlap_classified_breakout():
    issue = _issue("arc_integrity", "hero embraces the dark power within")
    evidence = ["the hero will eventually embrace the dark power"]
    assert classify_issue(issue, evidence) == DeviationKind.BREAKOUT_SCAR


def test_no_overlap_stays_ooc():
    issue = _issue("core_desire", "hero suddenly wants revenge, contradicting prior selflessness")
    evidence = ["the hero learns to forgive"]  # unrelated
    assert classify_issue(issue, evidence) == DeviationKind.OOC


def test_bilingual_evidence_overlap():
    issue = _issue("personality", "主角觉醒了内心黑暗的力量")
    evidence = ["主角终将觉醒内心黑暗的力量"]
    assert classify_issue(issue, evidence) == DeviationKind.BREAKOUT_SCAR


def test_empty_evidence_strings_ignored():
    issue = _issue("personality", "hero changes drastically embrace power")
    # only whitespace/empty evidence -> no real overlap -> OOC
    assert classify_issue(issue, ["", "   "]) == DeviationKind.OOC


# --- batch + purity -------------------------------------------------------

def test_classify_issues_returns_parallel_list():
    issues = [
        _issue("personality", "embrace dark power"),
        _issue("world_rules", "breaks a world rule"),
        _issue("arc_integrity", "totally unrelated thing"),
    ]
    kinds = classify_issues(issues, evidence_texts=["embrace dark power"])
    assert kinds == [DeviationKind.BREAKOUT_SCAR, DeviationKind.UNCLASSIFIED, DeviationKind.OOC]


def test_classify_does_not_mutate_issues():
    issue = _issue("personality", "embrace dark power")
    kind = classify_issue(issue, ["embrace dark power"])
    # the classifier is pure: it RETURNS a kind, never edits the issue
    assert kind == DeviationKind.BREAKOUT_SCAR
    assert issue.deviation_kind == "UNCLASSIFIED"  # unchanged from default
