"""Reader simulation — post-write first-reader experience diagnostic (T2-⑥).

Simulates how a first-time reader experiences the finished novel: where they get
confused, which questions they're left holding (dangling threads), a per-chapter
engagement/momentum curve, and a predicted-retention score. Report-only, opt-in,
and — like T2-⑤ tension and T2-⑦ props — it attaches synchronously in
_convert_novel and rides the WRITING 'completed' event. (The fire-and-forget
post-write background channel persists to Kuzu but nothing reads it back, so it
cannot deliver a diagnostic to a consumer.)

Two layers:
- _ground_signals (pure, zero-LLM): pre-computes concrete anchors — chapter
  count, per-chapter question-mark density, length outliers — by parsing the
  same '## 第N章' / '## Chapter N:' headings the assembler emits, falling back
  to chapter_plan when none parse. These ground the LLM so it reasons over facts
  rather than vibes, and the layer cannot raise.
- ReaderSimulator (ONE LLM call, temp 0.1): judges the subjective experience.
  Mirrors PropMentionExtractor's graceful degrade — any LLM/parse error or
  malformed payload yields an empty report; bad rows are dropped, never fatal.

build_reader_sim_report orchestrates extract→report and NEVER raises, so the
write path and completed event are never broken.
"""

from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass, field

from app.core.i18n import get_lang, Lang
from app.core.llm_client import LLMClient, LLMError

from .prompts import _get_reader_sim_prompt
from .types import ChapterPlan

_VALID_SEVERITY = {"low", "medium", "high"}
# Chapter headings exactly as _assemble_novel emits them (writer.py:272-275).
_HEADING_RE = re.compile(r"^##\s+(?:第\s*\d+\s*章|Chapter\s+\d+)", re.MULTILINE)
_QUESTION_CHARS = ("?", "？")
_SHORT_CHARS = 400    # below this a chapter reads abrupt
_LONG_CHARS = 6000    # above this a chapter reads bloated


# --- data shapes (mirror PropLifecycleReport / TensionReport) -------------

@dataclass(frozen=True)
class ConfusionPoint:
    """A passage a first-time reader would find unclear."""

    chapter: int
    description: str
    severity: str  # low | medium | high

    def __post_init__(self) -> None:
        if self.severity not in _VALID_SEVERITY:
            raise ValueError(f"unknown severity: {self.severity!r}")


@dataclass(frozen=True)
class DanglingThread:
    """An unanswered question / unresolved thread the reader is left holding."""

    question: str
    introduced_chapter: int
    severity: str  # low | medium | high

    def __post_init__(self) -> None:
        if self.severity not in _VALID_SEVERITY:
            raise ValueError(f"unknown severity: {self.severity!r}")


@dataclass(frozen=True)
class EngagementPoint:
    """One point on the engagement/momentum curve — one per chapter."""

    chapter: int
    momentum: float  # 0.0-1.0
    note: str = ""


@dataclass(frozen=True)
class ReaderSimReport:
    """The simulated first-reader experience."""

    confusion_points: list[ConfusionPoint] = field(default_factory=list)
    dangling_threads: list[DanglingThread] = field(default_factory=list)
    engagement_curve: list[EngagementPoint] = field(default_factory=list)
    predicted_retention: float = 0.0  # 0.0-1.0
    summary: str = ""

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


# --- helpers --------------------------------------------------------------

def _clamp01(value: object, default: float = 0.0) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _split_chapters(prose: str) -> list[str]:
    """Split prose into chapter chunks on the assembler's heading lines.

    The text before the first heading (title block) is dropped. Returns [] when
    no heading parses, so callers can fall back to the chapter plan.
    """
    matches = list(_HEADING_RE.finditer(prose))
    if not matches:
        return []
    bounds = [m.start() for m in matches] + [len(prose)]
    return [prose[bounds[i]:bounds[i + 1]] for i in range(len(matches))]


# --- deterministic grounding (pure, never raises) -------------------------

def _ground_signals(prose: str, chapter_plan: ChapterPlan) -> str:
    """Pre-compute concrete anchors to inject into the LLM user message.

    Pure and side-effect-free; on empty/headless prose it falls back to the
    chapter plan so the count is always meaningful."""
    chunks = _split_chapters(prose)
    total = len(chunks) if chunks else len(chapter_plan.chapters)
    zh = get_lang() == Lang.ZH

    lines: list[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        q = sum(chunk.count(c) for c in _QUESTION_CHARS)
        n = len(chunk)
        flags = []
        if q:
            flags.append(f"{q} 个问句" if zh else f"{q} questions")
        if n < _SHORT_CHARS:
            flags.append("偏短" if zh else "very short")
        elif n > _LONG_CHARS:
            flags.append("偏长" if zh else "very long")
        if flags:
            label = f"第{idx}章" if zh else f"Chapter {idx}"
            lines.append(f"- {label}: {', '.join(flags)}")

    if zh:
        header = f"已检测到 {total} 章。客观信号："
        none = "（无显著信号）"
    else:
        header = f"Detected {total} chapters. Objective signals:"
        none = "(no notable signals)"
    body = "\n".join(lines) if lines else none
    return f"{header}\n{body}"


# --- LLM simulator (graceful degrade, mirrors PropMentionExtractor) -------

class ReaderSimulator:
    """Judges the first-reader experience via one low-temp LLM call."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def simulate(self, prose: str, grounded_signals: str) -> ReaderSimReport:
        """Return a ReaderSimReport for *prose*. Never raises."""
        messages = [
            {"role": "system", "content": _get_reader_sim_prompt()},
            {"role": "user", "content": f"{grounded_signals}\n\n---\n\n{prose}"},
        ]
        try:
            payload = await self._llm.chat_json(messages, temperature=0.1)
        except (LLMError, Exception):
            return ReaderSimReport()
        if not isinstance(payload, dict):
            return ReaderSimReport()

        return ReaderSimReport(
            confusion_points=_parse_confusion(payload.get("confusion_points")),
            dangling_threads=_parse_dangling(payload.get("dangling_threads")),
            engagement_curve=_parse_curve(payload.get("engagement_curve")),
            predicted_retention=_clamp01(payload.get("predicted_retention", 0.0)),
            summary=str(payload.get("summary", "")).strip(),
        )


def _parse_confusion(rows: object) -> list[ConfusionPoint]:
    if not isinstance(rows, list):
        return []
    out: list[ConfusionPoint] = []
    seen: set[tuple[int, str]] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        desc = str(row.get("description", "")).strip()
        severity = str(row.get("severity", "")).strip().lower()
        if not desc or severity not in _VALID_SEVERITY:
            continue
        try:
            chapter = int(row["chapter"])
        except (KeyError, TypeError, ValueError):
            continue
        key = (chapter, desc)
        if key in seen:
            continue
        seen.add(key)
        out.append(ConfusionPoint(chapter=chapter, description=desc, severity=severity))
    return out


def _parse_dangling(rows: object) -> list[DanglingThread]:
    if not isinstance(rows, list):
        return []
    out: list[DanglingThread] = []
    seen: set[tuple[str, int]] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        question = str(row.get("question", "")).strip()
        severity = str(row.get("severity", "")).strip().lower()
        if not question or severity not in _VALID_SEVERITY:
            continue
        try:
            intro = int(row.get("introduced_chapter", 0))
        except (TypeError, ValueError):
            intro = 0
        key = (question, intro)
        if key in seen:
            continue
        seen.add(key)
        out.append(DanglingThread(question=question, introduced_chapter=intro, severity=severity))
    return out


def _parse_curve(rows: object) -> list[EngagementPoint]:
    """One point per chapter; first occurrence of a chapter wins (deterministic)."""
    if not isinstance(rows, list):
        return []
    out: list[EngagementPoint] = []
    seen: set[int] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            chapter = int(row["chapter"])
        except (KeyError, TypeError, ValueError):
            continue
        if chapter in seen:
            continue
        seen.add(chapter)
        out.append(EngagementPoint(
            chapter=chapter,
            momentum=_clamp01(row.get("momentum", 0.0)),
            note=str(row.get("note", "")).strip(),
        ))
    return out


# --- async orchestrator ----------------------------------------------------

async def build_reader_sim_report(
    llm: LLMClient, prose: str, chapter_plan: ChapterPlan
) -> ReaderSimReport:
    """Ground → simulate → report. Never raises; degrades to an empty report."""
    if not prose or not prose.strip():
        return ReaderSimReport()
    signals = _ground_signals(prose, chapter_plan)
    return await ReaderSimulator(llm).simulate(prose, signals)
