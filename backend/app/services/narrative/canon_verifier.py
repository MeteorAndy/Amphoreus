"""Post-generation canon verifier — deterministic, zero-LLM violation report.

The WRITE-TIME counterpart to the canon adjudicator: it reads generated
`content` back against the in-scope subset of `CanonicalFacts` and reports where
the prose contradicts (or merely fails to confirm) an adjudicated fact.

Two checks per in-scope fact (`facts._facts_for(target_format)`):
  (a) rejected-proposition hit -> 'contradiction' (high): a `rejected_answers`
      string appears literally in `content`. Since the adjudicator was tightened
      so rejected_answers are FULL wrong propositions (not bare entity names),
      literal substring matching is meaningful. Matching stays conservative:
      stripped rejected len>=2, case-insensitive substring containment.
  (b) canonical-absence signal -> 'unconfirmed' (low): NONE of the canonical
      answer tokens (ZH + EN pooled) appear anywhere. This is a HINT, not a
      violation — the writer may simply not have mentioned the fact.

Contract: `clean = not any(v.kind == 'contradiction')`. A report can be
clean=True with a non-empty `violations` list (unconfirmed-only). Callers/UI
must NOT treat clean==True as 'no notes'.

The `llm_client` param on `verify` is an unused seam for a future semantic pass:
accepted, defaulted to None, never invoked in this version.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from app.core.llm_client import LLMClient

from .types import CanonicalFacts

_TOKEN_SPLIT = re.compile(r"[\s，、。；：,;:/()（）「」【】]+")
_MIN_TOKEN_LEN = 2


@dataclass
class Violation:
    """One canon issue found in generated content."""

    fact_id: str
    topic: str
    kind: str  # "contradiction" | "unconfirmed"
    severity: str  # "high" for contradiction, "low" for unconfirmed
    evidence: str


@dataclass
class CanonReport:
    """Result of a post-generation canon check.

    `clean` is True iff there are no 'contradiction' violations; 'unconfirmed'
    notes are hints and do NOT make a report unclean.
    """

    violations: list[Violation] = field(default_factory=list)
    checked: int = 0
    clean: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


def _tokenize(answer: str) -> list[str]:
    """Split a canonical answer into lowercased tokens of length >= 2."""
    if not answer:
        return []
    parts = _TOKEN_SPLIT.split(answer.lower())
    return [p for p in parts if len(p) >= _MIN_TOKEN_LEN]


def _excerpt(content: str, needle: str, window: int = 40) -> str:
    """Return a window around the first literal hit of `needle` in `content`."""
    i = content.lower().find(needle.lower())
    if i < 0:
        return ""
    return content[max(0, i - window): i + len(needle) + window].strip()


def verify(
    content: str,
    facts: CanonicalFacts,
    target_format: str,
    llm_client: LLMClient | None = None,
) -> CanonReport:
    """Check generated `content` against in-scope canonical facts.

    Deterministic and zero-LLM. `llm_client` is an unused seam for a future
    semantic pass and is never invoked here.

    For each in-scope fact: flag a 'contradiction' (high) when any rejected
    proposition appears literally in `content`; otherwise, when none of the
    canonical answer tokens appear, emit an 'unconfirmed' (low) hint. A fact
    that is neither contradicted nor unconfirmed produces no violation.
    """
    in_scope = facts._facts_for(target_format) if facts else []
    lowered = content.lower() if content else ""
    violations: list[Violation] = []

    for fact in in_scope:
        hit = None
        for rejected in fact.rejected_answers:
            needle = rejected.strip()
            if len(needle) >= _MIN_TOKEN_LEN and needle.lower() in lowered:
                hit = needle
                break
        if hit is not None:
            violations.append(
                Violation(
                    fact_id=fact.id,
                    topic=fact.topic,
                    kind="contradiction",
                    severity="high",
                    evidence=_excerpt(content, hit),
                )
            )
            continue

        tokens = _tokenize(fact.canonical_answer_zh) + _tokenize(
            fact.canonical_answer_en
        )
        if tokens and not any(tok in lowered for tok in tokens):
            violations.append(
                Violation(
                    fact_id=fact.id,
                    topic=fact.topic,
                    kind="unconfirmed",
                    severity="low",
                    evidence="",
                )
            )

    clean = not any(v.kind == "contradiction" for v in violations)
    return CanonReport(violations=violations, checked=len(in_scope), clean=clean)
