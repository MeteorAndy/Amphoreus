"""Token-budget accounting — measure-only generation diagnostic (T2-④, phase a).

This is the FIRST, deliberately conservative increment of the token-budget
feature. Unlike the post-write diagnostics (T2-⑤/⑥/⑦), token budgeting lives on
the GENERATION HOT PATH: every chapter prompt flows through it. A bug in a
prompt-MUTATING allocator would silently and consistently degrade every chapter
of a run (e.g. drop canon and let the writer contradict established truth), and
the codebase cannot even detect over-budget calls today (LLMClient.chat never
reads response.usage; the model truncates input silently).

So this phase MEASURES ONLY. It estimates per-section token cost over the
already-assembled prompt and emits an advisory BudgetReport: how big each context
contributor is, whether the prompt is over a stated budget, and which low-value
sections WOULD be trimmed under the priority policy. It NEVER mutates the message
list. The prompt-mutating allocator (phase b) is deferred until this report's
data proves trimming is warranted and validates the priority ranking on real
prompts.

The estimator reuses count_words() (already calibrated for mixed CJK/Latin), so
no tokenizer dependency (tiktoken) is added for this phase. Everything here is
pure and unit-testable without an LLM.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

from .types import count_words

# Current behavior: measure-only remains the default. Prompt mutation happens
# only when TokenBudgetConfig.apply_trimming is explicitly true.

# Average tokens per "word" as count_words() counts it. CJK chars count ~1:1 to
# tokens; Latin words run ~1.3 tokens. count_words already collapses both into a
# single integer, so a single blended ratio is a reasonable heuristic. A small
# per-message envelope covers role/formatting overhead.
_LATIN_RATIO = 1.3
_MSG_ENVELOPE = 4

# Priority ranking by NARRATIVE VALUE (higher = more important = kept longer).
# The advisory trim walk removes from the LOWEST value upward, and critical /
# baseline sections are excluded from the candidate set entirely (see
# _DROPPABLE). canon + foreshadowing outrank transition summaries because
# dropping them corrupts the story silently; system prompt + scene logs are the
# irreducible base material and are never auto-trimmed.
PRIORITY_TIERS: dict[str, int] = {
    "canon": 100,
    "foreshadowing": 90,
    "system": 80,        # baseline — counted, never trimmed
    "scene_logs": 70,    # baseline — the story itself, never auto-trimmed
    "character_context": 65,
    "phase": 40,
    "prev_summary": 30,
    "next_summary": 30,
}

# Only these sections may appear in `would_trim`. Critical context (canon,
# foreshadowing) and baseline material (system, scene_logs) are never candidates.
_DROPPABLE = {"phase", "prev_summary", "next_summary"}
_TRUNCATABLE = {"scene_logs"}


@dataclass(frozen=True)
class TokenBudgetConfig:
    """Opt-in config for token accounting. All defaults make it a no-op.

    Attached to WritingOptions.token_budget; when None (the default) the writer
    runs zero budget code and prompts are byte-for-byte unchanged.
    """

    enabled: bool = False
    budget_tokens: int = 0
    strategy: str = "prioritize_canon"
    safety_margin: int = 4000
    apply_trimming: bool = False


@dataclass(frozen=True)
class BudgetSection:
    """One context contributor's estimated cost."""

    name: str
    tier: str  # critical | high | medium | baseline
    tokens: int


@dataclass(frozen=True)
class ChapterBudget:
    """Per-chapter accounting. `would_trim` is ADVISORY — nothing is mutated."""

    chapter_number: int
    sections: list[BudgetSection]
    total_tokens: int
    budget_tokens: int | None
    over_by: int
    would_trim: list[str] = field(default_factory=list)
    applied_trim: list[str] = field(default_factory=list)
    final_tokens: int | None = None
    final_over_by: int = 0


@dataclass(frozen=True)
class BudgetReport:
    """Whole-novel budget accounting, attached to WrittenOutput.budget_report."""

    per_chapter: list[ChapterBudget] = field(default_factory=list)
    any_over: bool = False
    total_tokens: int = 0

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


def estimate_tokens(text: str, is_zh: bool) -> int:
    """Heuristic token estimate for mixed CJK/Latin text. Pure; never raises.

    Reuses count_words() (CJK char = 1, Latin run = 1 token-word) and scales by
    a blended ratio. is_zh is accepted for future per-language calibration; the
    current ratio is language-blended so both paths share it."""
    if not text:
        return 0
    words = count_words(text)
    return int(words * _LATIN_RATIO) + _MSG_ENVELOPE


def account_prompt(
    chapter_number: int,
    sections: list[BudgetSection],
    budget: int | None,
) -> ChapterBudget:
    """Sum section costs and compute an advisory trim list. Pure; never mutates.

    The trim walk drops droppable sections in ascending priority until the total
    fits `budget`. Critical and baseline sections are never candidates, so a
    prompt whose undroppable core exceeds budget still reports over_by > 0 with a
    `would_trim` that excludes them — the signal that phase-b must fail loud
    rather than cut a critical block."""
    total = sum(s.tokens for s in sections)
    if budget is None:
        return ChapterBudget(
            chapter_number=chapter_number,
            sections=list(sections),
            total_tokens=total,
            budget_tokens=None,
            over_by=0,
            would_trim=[],
        )

    over_by = max(0, total - budget)
    would_trim: list[str] = []
    if over_by > 0:
        candidates = [s for s in sections if s.name in _DROPPABLE]
        # lowest narrative value first
        candidates.sort(key=lambda s: PRIORITY_TIERS.get(s.name, 0))
        running = total
        for s in candidates:
            if running <= budget:
                break
            would_trim.append(s.name)
            running -= s.tokens

    return ChapterBudget(
        chapter_number=chapter_number,
        sections=list(sections),
        total_tokens=total,
        budget_tokens=budget,
        over_by=over_by,
        would_trim=would_trim,
    )


def measure_chapter_sections(
    chapter_number: int,
    *,
    is_zh: bool,
    budget_tokens: int,
    parts: dict[str, str],
) -> ChapterBudget:
    """Estimate each context contributor and return an advisory ChapterBudget.

    Measure-only (T2-④): the caller passes the SAME rendered strings it sends to
    the LLM via `parts` (keys: system, canon, foreshadowing, phase,
    character_context, prev_summary, next_summary, scene_logs), so the
    accounting cannot diverge from the real prompt. Nothing is mutated.
    A budget_tokens <= 0 means "no budget"."""
    tiers = {
        "system": "baseline", "canon": "critical", "foreshadowing": "critical",
        "phase": "high", "character_context": "high",
        "prev_summary": "medium", "next_summary": "medium",
        "scene_logs": "baseline",
    }
    sections = [
        BudgetSection(name, tier, estimate_tokens(parts.get(name, ""), is_zh))
        for name, tier in tiers.items()
    ]
    budget = budget_tokens if budget_tokens > 0 else None
    return account_prompt(chapter_number, sections, budget)


def allocate_chapter_sections(
    chapter_number: int,
    *,
    is_zh: bool,
    budget_tokens: int,
    parts: dict[str, str],
) -> tuple[dict[str, str], ChapterBudget]:
    """Apply the T0/T1/T2/T3 budget policy to rendered prompt sections.

    T0 sections (system, canon, foreshadowing) are never changed. T2/T3
    transition context is dropped first. If the prompt is still too large, the
    T1 scene log is middle-truncated so both setup and latest consequences are
    retained.
    """
    original = dict(parts)
    budget = budget_tokens if budget_tokens > 0 else None
    initial = measure_chapter_sections(
        chapter_number, is_zh=is_zh, budget_tokens=budget_tokens, parts=original
    )
    if budget is None or initial.total_tokens <= budget:
        return original, dataclasses.replace(
            initial,
            final_tokens=initial.total_tokens,
            final_over_by=initial.over_by,
        )

    allocated = dict(original)
    applied: list[str] = []

    for name in _trim_order(initial.sections):
        if _estimate_parts(allocated, is_zh) <= budget:
            break
        if name in _DROPPABLE and allocated.get(name):
            allocated[name] = ""
            applied.append(name)

    if _estimate_parts(allocated, is_zh) > budget:
        fixed = _estimate_parts(
            {k: v for k, v in allocated.items() if k != "scene_logs"}, is_zh
        )
        scene_budget = max(0, budget - fixed)
        scene_logs = allocated.get("scene_logs", "")
        if scene_logs and "scene_logs" in _TRUNCATABLE:
            trimmed = _trim_middle_to_budget(scene_logs, scene_budget, is_zh)
            if trimmed != scene_logs:
                allocated["scene_logs"] = trimmed
                applied.append("scene_logs")

    final_total = _estimate_parts(allocated, is_zh)
    return allocated, dataclasses.replace(
        initial,
        applied_trim=applied,
        final_tokens=final_total,
        final_over_by=max(0, final_total - budget),
    )


def _trim_order(sections: list[BudgetSection]) -> list[str]:
    candidates = [s for s in sections if s.name in _DROPPABLE]
    candidates.sort(key=lambda s: PRIORITY_TIERS.get(s.name, 0))
    return [s.name for s in candidates]


def _estimate_parts(parts: dict[str, str], is_zh: bool) -> int:
    return sum(estimate_tokens(text, is_zh) for text in parts.values() if text)


def _trim_middle_to_budget(text: str, budget_tokens: int, is_zh: bool) -> str:
    if not text or budget_tokens <= 0:
        return ""
    if estimate_tokens(text, is_zh) <= budget_tokens:
        return text

    marker = (
        "\n\n[上下文预算裁剪：中间场景日志已省略。]\n\n"
        if is_zh else
        "\n\n[Context budget trim: middle scene log omitted.]\n\n"
    )
    marker_tokens = estimate_tokens(marker, is_zh)
    remaining = max(0, budget_tokens - marker_tokens)
    if remaining <= 0:
        return marker.strip()

    lo = 0
    hi = len(text)
    best = ""
    while lo <= hi:
        keep = (lo + hi) // 2
        head_len = keep // 2
        tail_len = keep - head_len
        candidate = text[:head_len].rstrip() + marker + text[-tail_len:].lstrip()
        if estimate_tokens(candidate, is_zh) <= budget_tokens:
            best = candidate
            lo = keep + 1
        else:
            hi = keep - 1
    return best or marker.strip()
