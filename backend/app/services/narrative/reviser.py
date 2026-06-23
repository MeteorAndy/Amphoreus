"""Post-generation revise logic (T1-①) — pure, zero-LLM, side-effect free.

Closes the quality loop: PR1 already produces a `ClicheReport` and `CanonReport`
per chapter, and `post_processor.find_repeated_fragments` already finds verbatim
repeats — but all three were discarded. This module turns those diagnostics into
a decision (does this chapter need a rewrite?) and a compact, bilingual revise
directive (what specifically to fix). The LLM rewrite call itself is NOT here —
it lives in `NovelWriter`, which injects this directive into a second-pass
prompt. Keeping the logic pure makes it unit-testable in milliseconds without an
LLM, matching the project's zero-LLM diagnostic discipline (cliche_scanner,
canon_verifier).

`build_revise_directive` returns "" when nothing crosses threshold, so the caller
skips the rewrite entirely (no wasted LLM call on already-clean prose).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .canon_verifier import CanonReport
from .cliche_scanner import ClicheReport
from .types import ReviseConfig

if TYPE_CHECKING:
    from .fact_checker import FactReport
    from .logic_reviewer import LogicReport


def needs_revision(
    cliche: ClicheReport | None,
    canon: CanonReport | None,
    repeats: list[tuple[str, int]],
    config: ReviseConfig,
    logic: "LogicReport | None" = None,
    facts: "FactReport | None" = None,
) -> bool:
    """True iff any diagnostic crosses a revise threshold.

    Triggers on: a hard canon contradiction, any critical cliche hit, an
    ai_flavor_score over threshold, a verbatim repeat at/over the trigger
    count, any critical/major logic-plausibility issue, or a confirmed factual
    contradiction. 'unconfirmed' canon notes, 'minor' logic issues, and
    'unverifiable' facts never trigger (they are hints, not faults).
    """
    if not config.enabled:
        return False
    if canon is not None and any(
        v.kind == "contradiction" for v in canon.violations
    ):
        return True
    if cliche is not None:
        if cliche.ai_flavor_score >= config.ai_flavor_threshold:
            return True
        if any(h.severity == "critical" for h in cliche.hits):
            return True
    if any(n >= config.repeat_trigger_count for _, n in repeats):
        return True
    if logic is not None and logic.needs_rewrite:
        return True
    if facts is not None and facts.needs_rewrite:
        return True
    return False


def build_revise_directive(
    cliche: ClicheReport | None,
    canon: CanonReport | None,
    repeats: list[tuple[str, int]],
    config: ReviseConfig,
    is_zh: bool,
    logic: "LogicReport | None" = None,
    facts: "FactReport | None" = None,
) -> str:
    """Build a compact, bilingual revise directive from the diagnostics.

    Returns "" when nothing crosses threshold (caller then skips the rewrite).
    The directive lists concrete, deduped problems — canon contradictions first
    (highest priority), then critical/scored cliche hits with their existing
    replacement_hint, then verbatim repeats, then logic-plausibility issues,
    then factual contradictions — capped at `max_directives` lines so an
    overloaded chapter cannot produce an unbounded prompt.
    """
    if not needs_revision(cliche, canon, repeats, config, logic, facts):
        return ""

    lines: list[str] = []
    _append_canon(lines, canon, is_zh)
    _append_cliche(lines, cliche, config, is_zh)
    _append_repeats(lines, repeats, config, is_zh)
    _append_logic(lines, logic, is_zh)
    _append_facts(lines, facts, is_zh)

    if not lines:
        return ""
    lines = lines[: config.max_directives]
    return _wrap(lines, is_zh)


def _append_canon(lines: list[str], canon: CanonReport | None, is_zh: bool) -> None:
    """Add one line per hard canon contradiction (highest priority)."""
    if canon is None:
        return
    for v in canon.violations:
        if v.kind != "contradiction":
            continue
        ev = f"（{v.evidence}）" if v.evidence else ""
        if is_zh:
            lines.append(f"事实冲突·{v.topic}：改写与权威设定矛盾之处{ev}")
        else:
            lines.append(f"Canon conflict · {v.topic}: rewrite the passage that "
                         f"contradicts the locked fact{(' ' + ev) if ev else ''}")


def _append_cliche(
    lines: list[str], cliche: ClicheReport | None, config: ReviseConfig, is_zh: bool
) -> None:
    """Add deduped critical (and, when score is high, warning) cliche hits.

    Each hit carries its scanner-provided replacement_hint, so the directive
    tells the model what to write instead — not merely what to avoid.
    """
    if cliche is None:
        return
    over = cliche.ai_flavor_score >= config.ai_flavor_threshold
    seen: set[str] = set()
    for h in cliche.hits:
        take = h.severity == "critical" or (over and h.severity == "warning")
        if not take or h.name in seen:
            continue
        seen.add(h.name)
        if is_zh:
            lines.append(f"套话·{h.span_excerpt}：{h.replacement_hint}")
        else:
            lines.append(f"Cliche · '{h.span_excerpt}': {h.replacement_hint}")


def _append_repeats(
    lines: list[str],
    repeats: list[tuple[str, int]],
    config: ReviseConfig,
    is_zh: bool,
) -> None:
    """Add one line per verbatim fragment repeated >= trigger_count times."""
    for frag, n in repeats:
        if n < config.repeat_trigger_count:
            continue
        if is_zh:
            lines.append(f"重复·“{frag}”出现{n}次：改写其中多数，避免雷同。")
        else:
            lines.append(f"Repetition · '{frag}' appears {n}×: reword most "
                         f"occurrences to avoid verbatim echo.")


def _append_logic(lines: list[str], logic: "LogicReport | None", is_zh: bool) -> None:
    """Add one line per critical/major logic-plausibility issue.

    minor issues are notes and are intentionally excluded — they would cost an
    LLM rewrite without a clear quality payoff. Each surviving issue carries its
    reviewer-provided fix_hint so the directive tells the model what to write
    instead, not merely what to avoid.
    """
    if logic is None:
        return
    for issue in logic.issues:
        if issue.severity not in ("critical", "major"):
            continue
        if is_zh:
            lines.append(
                f"逻辑·{issue.category}「{issue.location}」：{issue.problem}"
                + (f"；建议：{issue.fix_hint}" if issue.fix_hint else "")
            )
        else:
            lines.append(
                f"Logic · {issue.category} ['{issue.location}']: {issue.problem}"
                + (f"; suggested fix: {issue.fix_hint}" if issue.fix_hint else "")
            )


def _append_facts(lines: list[str], facts: "FactReport | None", is_zh: bool) -> None:
    """Add one line per confirmed factual contradiction.

    Only contradictions are actionable for a rewrite; confirmed/unverifiable
    are notes and excluded. Each carries the original claim and the evidence
    snippet so the rewrite can correct the specific anachronism.
    """
    if facts is None:
        return
    for chk in facts.checks:
        if chk.verdict != "contradiction":
            continue
        ev = f"（证据：{chk.evidence[:80]}）" if chk.evidence else ""
        if is_zh:
            lines.append(f"事实错误「{chk.claim}」：与现实世界矛盾{ev}")
        else:
            lines.append(f"Fact error ['{chk.claim}']: contradicts the real world{(' ' + ev) if ev else ''}")


def _wrap(lines: list[str], is_zh: bool) -> str:
    """Frame the directive lines as a single revise instruction block."""
    if is_zh:
        header = (
            "以下是对上一稿的质量诊断，请据此重写这一章：修正每一处问题，"
            "保持情节、人物与篇幅不变，只返回改写后的正文，不要解释。"
        )
    else:
        header = (
            "The following are quality issues found in the draft above. Rewrite "
            "this chapter to fix each one, keeping plot, characters, and length "
            "unchanged. Return ONLY the rewritten prose, no explanations."
        )
    return header + "\n" + "\n".join(f"- {ln}" for ln in lines)

