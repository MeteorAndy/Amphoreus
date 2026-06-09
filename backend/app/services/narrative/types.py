"""Data types for narrative writing — shared across all writers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# CJK ranges: Unified ideographs + Ext-A + compatibility + kana (for mixed text).
_CJK_RANGES = r"一-鿿㐀-䶿豈-﫿぀-ヿ"
_CJK_RE = re.compile(rf"[{_CJK_RANGES}]")


def count_words(text: str) -> int:
    """Count 'words' meaningfully for mixed CJK / Latin text.

    `len(text.split())` is meaningless for Chinese — it has no spaces between
    words, so an entire novel counts as ~1 token. Here each CJK character counts
    as one word (the conventional 字数), and remaining non-CJK runs are counted
    as whitespace-delimited tokens (Latin words, numbers).
    """
    if not text:
        return 0
    cjk = len(_CJK_RE.findall(text))
    latin = len(_CJK_RE.sub(" ", text).split())
    return cjk + latin


@dataclass
class WritingOptions:
    """Configuration for the narrative conversion process."""

    format: str  # "novel" or "screenplay"
    narrative_voice: str = "third_person_limited"
    enhance: bool = False
    chapter_title: str | None = None
    canonical_facts: "CanonicalFacts | None" = None
    # Optional foreshadowing registry; when present the writers inject a
    # per-chapter T0 block. String-annotated to avoid an import cycle.
    foreshadowing_registry: "ForeshadowingRegistry | None" = None
    # Optional post-generation quality loop (T1-①): when present and enabled,
    # each chapter's cliche/canon/repeat diagnostics drive a bounded rewrite.
    # Off by default, so existing callers are unchanged. NOTE: currently wired
    # into the novel pipeline only (NovelWriter); the screenplay path ignores it.
    revise: "ReviseConfig | None" = None
    # Optional dramatic-tension scoring (T2-⑤): when True, the novel writer
    # attaches a zero-LLM TensionReport to the output. Off by default, so
    # existing callers are unchanged. Novel-only for v1.
    score_tension: bool = False
    # Optional prop-lifecycle / Chekhov-gun tracking (T2-⑦): when True, the
    # novel writer runs one post-write LLM pass and attaches a
    # PropLifecycleReport. Off by default; novel-only for v1.
    extract_props: bool = False
    # Optional reader simulation (T2-⑥): when True, the novel writer runs one
    # post-write LLM pass and attaches a ReaderSimReport (confusion points,
    # dangling threads, engagement curve, retention). Off by default; novel-only.
    simulate_reader: bool = False


@dataclass(frozen=True)
class ReviseConfig:
    """Thresholds and bounds for the post-generation revise loop (T1-①).

    Pure config — the decision/directive logic lives in `reviser.py` and the
    LLM rewrite seam in `NovelWriter`. Disabled by default; a caller opts in by
    attaching one to `WritingOptions.revise`.

    `ai_flavor_threshold` is read against `ClicheReport.ai_flavor_score`, which
    cliche_scanner computes as (weight_sum / char_count) * 1000 — i.e. a
    per-char density, NOT an absolute count. A full ZH chapter is ~2500-4000
    chars, so on a 3000-char chapter weight_sum 9 (≈3 critical hits, each 3.0)
    scores 3.0. The default 3.0 therefore means "≈3 critical-equivalents of
    cliche density"; it both lets the score independently trigger a revise and
    opens the gate that folds warning-severity hits into the directive. (The old
    value 12.0 was calibrated to a ~200-char page and was effectively inert at
    chapter scale, silently dropping the entire warning layer.)
    """

    enabled: bool = True
    max_rounds: int = 1
    ai_flavor_threshold: float = 3.0
    repeat_min_len: int = 8
    repeat_trigger_count: int = 3
    max_directives: int = 12


@dataclass
class WrittenOutput:
    """Result of a narrative conversion."""

    content: str
    format: str
    word_count: int
    scene_count: int
    title: str = ""
    title_candidates: list[str] = field(default_factory=list)
    export_formats: list[str] = field(default_factory=list)
    # Post-generation diagnostics (PR1). Populated after content assembly by the
    # writer (or explicitly by the CLI path, which bypasses NarrativeWriter.convert).
    # String-annotated to avoid a types<->canon_verifier import cycle.
    cliche_report: "ClicheReport | None" = None
    canon_report: "CanonReport | None" = None
    # Dramatic-tension diagnostics (T2-⑤). Populated by the novel writer when
    # WritingOptions.score_tension is set. String-annotated to avoid a cycle.
    tension_report: "TensionReport | None" = None
    # Prop-lifecycle diagnostics (T2-⑦). Populated by the novel writer when
    # WritingOptions.extract_props is set. String-annotated to avoid a cycle.
    prop_lifecycle_report: "PropLifecycleReport | None" = None
    # Reader-simulation diagnostics (T2-⑥). Populated by the novel writer when
    # WritingOptions.simulate_reader is set. String-annotated to avoid a cycle.
    reader_sim_report: "ReaderSimReport | None" = None


@dataclass
class ChapterSpec:
    """One chapter in a chapter plan."""

    number: int
    title: str
    scene_ids: list[str]
    summary: str


@dataclass
class ChapterPlan:
    """Complete chapter plan — groups scenes into chapters."""

    chapters: list[ChapterSpec] = field(default_factory=list)

    @property
    def is_short_story(self) -> bool:
        total = sum(len(c.scene_ids) for c in self.chapters)
        return total < 3


@dataclass
class CanonicalFact:
    """One adjudicated, authoritative story fact both writers must obey.

    The schema is deliberately generic: `topic`/`scope` are free `str`, so a
    given story's contested axes (page numbers, parentage, fates) enter as
    runtime *values*, never as types. Reusing this for another story needs no
    change to the dataclass.
    """

    id: str
    topic: str
    question: str
    canonical_answer_zh: str
    canonical_answer_en: str
    rejected_answers: list[str] = field(default_factory=list)
    scope: str = "all"  # "all" | "novel" | "screenplay"
    rationale: str = ""  # audit/human-review only — never injected into prompts


@dataclass
class OpenConflict:
    """A load-bearing contradiction the adjudicator could not resolve.

    Surfaced explicitly rather than silently dropped, so a human-review hook can
    consume it. Writers receive no constraint for these, and may still diverge.
    """

    topic: str
    question: str
    candidates: list[str] = field(default_factory=list)


@dataclass
class CanonicalFacts:
    """Aggregate root: the adjudicated authoritative facts for one session.

    This is the single unit that gets persisted (OpenViking) and injected (into
    both writers via WritingOptions). It is the shared source of truth that
    makes a novel run and a screenplay run — which happen separately — agree.
    """

    facts: list[CanonicalFact] = field(default_factory=list)
    unresolved: list[OpenConflict] = field(default_factory=list)
    session_id: str = ""
    lang: str = ""
    model: str = ""
    generated_at: str = ""
    schema_version: int = 1

    def to_dict(self) -> dict:
        from dataclasses import asdict
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CanonicalFacts":
        return cls(
            facts=[CanonicalFact(**f) for f in data.get("facts", [])],
            unresolved=[OpenConflict(**c) for c in data.get("unresolved", [])],
            session_id=data.get("session_id", ""),
            lang=data.get("lang", ""),
            model=data.get("model", ""),
            generated_at=data.get("generated_at", ""),
            schema_version=data.get("schema_version", 1),
        )

    def _facts_for(self, target_format: str) -> list[CanonicalFact]:
        """Facts whose scope applies to the given writer format."""
        return [f for f in self.facts if f.scope in ("all", target_format)]

    def render_block(self, target_format: str, is_zh: bool) -> str:
        """Render scope-filtered facts as a hard-constraint block for prompts.

        Returns "" when no in-scope facts exist, so callers inject nothing extra
        (back-compat). `rationale` is audit-only and never rendered.
        """
        facts = self._facts_for(target_format)
        if not facts:
            return ""
        lines: list[str] = []
        if is_zh:
            lines.append(
                "以下是经过仲裁的权威设定，绝对不可违背。"
                "无论场景日志如何叙述，你必须严格遵守，绝不能产生与之矛盾的内容："
            )
            for f in facts:
                line = f"- 关于【{f.topic}】：{f.question} 正确：{f.canonical_answer_zh}"
                if f.rejected_answers:
                    line += f"；禁止写成：{('、'.join(f.rejected_answers))}"
                lines.append(line)
        else:
            lines.append(
                "The following are adjudicated canonical facts. NEVER contradict "
                "them. Regardless of what the scene logs say, you MUST obey these "
                "and MUST NOT produce anything inconsistent:"
            )
            for f in facts:
                line = f"- On {f.topic}: {f.question} Correct: {f.canonical_answer_en}"
                if f.rejected_answers:
                    line += f"; NEVER write: {('; '.join(f.rejected_answers))}"
                lines.append(line)
        return "\n".join(lines)
