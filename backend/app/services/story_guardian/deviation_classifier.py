"""OOC-vs-Breakout deviation classifier — report-only (T3-⑤).

Distinguishes a character deviation that should be PULLED BACK (OOC — a genuine
inconsistency) from one that is an EARNED arc moment to keep (BREAKOUT_SCAR — a
deliberate breakout / scar the story set up). PlotPilot's insight: a consistency
checker that flags every character change as an issue will smother intentional
character arcs.

The classifier is text-overlap based: a character-consistency issue whose
description overlaps an "earned-deviation" evidence text (an arc beat, a planted
foreshadowing, or a recorded arc-transition event) is tagged BREAKOUT_SCAR;
otherwise OOC. Issues are NOT character-anchored (GuardianIssue carries no
character_id), so this is a best-effort hint, not a gate — and it is REPORT-ONLY:
the guardian's verdict and severities are never changed, only deviation_kind is
stamped. Non-character dimensions (relationship_logic / world_rules / pacing)
stay UNCLASSIFIED (they are not character deviations).
"""

from __future__ import annotations

import re
from enum import Enum

from .types import GuardianIssue

_CJK_RE = re.compile(r"[一-鿿㐀-䶿]")
_LATIN_WORD_RE = re.compile(r"[A-Za-z]{2,}")
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for",
    "with", "will", "is", "was", "are", "be", "he", "she", "it", "his", "her",
}

# Dimensions that represent a CHARACTER deviation (candidate for OOC/Breakout).
_CHARACTER_DIMENSIONS = {"core_desire", "deep_fear", "personality", "arc_integrity"}


class DeviationKind(str, Enum):
    UNCLASSIFIED = "UNCLASSIFIED"   # not a character deviation
    OOC = "OOC"                     # genuine inconsistency — pull back
    BREAKOUT_SCAR = "BREAKOUT_SCAR"  # earned arc moment — keep tension


def _tokens(text: str) -> set[str]:
    """Match tokens as BIGRAMS: consecutive Latin word-pairs (stopwords filtered)
    + consecutive CJK char-pairs. A single common word ("hero") can't trigger a
    match — only a shared phrase ("dark power") does, which is far more
    indicative of an earned setup."""
    if not text:
        return set()
    low = text.lower()
    toks: set[str] = set()

    words = [w for w in _LATIN_WORD_RE.findall(low) if w not in _STOPWORDS]
    for i in range(len(words) - 1):
        toks.add(f"{words[i]} {words[i + 1]}")

    cjk = _CJK_RE.findall(low)
    for i in range(len(cjk) - 1):
        toks.add(cjk[i] + cjk[i + 1])
    return toks


def classify_issue(issue: GuardianIssue, evidence_texts: list[str]) -> DeviationKind:
    """Classify one issue. Pure — returns a kind, never mutates the issue."""
    if issue.dimension not in _CHARACTER_DIMENSIONS:
        return DeviationKind.UNCLASSIFIED

    desc_tokens = _tokens(issue.description)
    if not desc_tokens:
        return DeviationKind.OOC

    for ev in evidence_texts or []:
        if not ev or not ev.strip():
            continue
        if desc_tokens & _tokens(ev):
            return DeviationKind.BREAKOUT_SCAR
    return DeviationKind.OOC


def classify_issues(
    issues: list[GuardianIssue], evidence_texts: list[str]
) -> list[DeviationKind]:
    """Classify a list of issues; returns a parallel list of kinds (pure)."""
    return [classify_issue(i, evidence_texts) for i in issues]
