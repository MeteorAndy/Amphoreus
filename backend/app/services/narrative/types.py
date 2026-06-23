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
    # Optional relationship-trend analysis (T2-⑧): when True, the novel writer
    # attaches a zero-LLM RelationshipTrendReport (per-pair sentiment series +
    # IMPROVING/DETERIORATING/VOLATILE/STABLE trend). Off by default; novel-only.
    analyze_relationship_trends: bool = False
    # Optional token-budget accounting/allocation. By default it only estimates
    # per-section prompt cost and attaches a BudgetReport; when
    # TokenBudgetConfig.apply_trimming is explicitly true, the novel writer may
    # drop/trim lower-priority context before the LLM call. Off by default;
    # novel-only. String-annotated to avoid a cycle.
    token_budget: "TokenBudgetConfig | None" = None
    # Optional entity event sourcing (T3-⑥): when True, the novel writer derives
    # a read-only CharacterEventHistory (auditable event stream) from scene
    # archives. Off by default; novel-only. Zero write-path change.
    track_entity_events: bool = False
    # Optional graph-inference channel (T3-④): when True, the writer runs a few
    # deterministic read-only Cypher rules over the Kuzu graph and attaches a
    # GraphInferenceReport (co-faction / co-location / indirect-cause facts).
    # Off by default; novel-only. Never writes to the graph.
    enable_graph_inference: bool = False
    # Optional AI-slop adaptive pattern detection (T3-③): when True, the writer
    # attaches a report of THIS novel's recurring cliche tics. Report-only —
    # never mutates cliche_scanner._RULES. Off by default; novel-only.
    learn_adaptive_patterns: bool = False


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
    # Logic-plausibility audit (T1-⑧). Unlike cliche/canon/repeats which are
    # string-level zero-LLM checks, this is one LLM call per chapter that catches
    # *reasonableness* failures (implausible identity props, motivation gaps,
    # causal breaks). Default ON because it is the only diagnostic that can catch
    # the class of bug dogfood acceptance surfaced. Disabled callers set False.
    logic_enabled: bool = True
    logic_max_issues: int = 8
    # Real-world fact checking via Tavily (T1-⑨). One LLM call extracts
    # checkable real-world claims (weapon years, medical history, geography),
    # then N Tavily searches + one verdict LLM call classify each as
    # confirmed/contradiction/unverifiable. Only contradictions trigger a
    # rewrite. No-ops silently when no TAVILY_API_KEY is configured, so this
    # flag being True costs nothing without a key.
    fact_check_enabled: bool = True
    fact_check_max_queries: int = 5


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
    # Relationship-trend diagnostics (T2-⑧). Populated by the novel writer when
    # WritingOptions.analyze_relationship_trends is set. String-annotated to
    # avoid a cycle.
    relationship_trend_report: "RelationshipTrendReport | None" = None
    # Token-budget accounting/allocation. Populated by the novel writer when
    # WritingOptions.token_budget is enabled. String-annotated to avoid a cycle.
    budget_report: "BudgetReport | None" = None
    # Entity event sourcing (T3-⑥). Read-only CharacterEventHistory derived from
    # scene archives when WritingOptions.track_entity_events is set. String-
    # annotated to avoid a cycle.
    entity_event_report: "CharacterEventHistory | None" = None
    # Graph-inference diagnostics (T3-④). Read-only Cypher-derived structural
    # facts when WritingOptions.enable_graph_inference is set. String-annotated.
    graph_inference_report: "GraphInferenceReport | None" = None
    # Adaptive-pattern diagnostics (T3-③). Recurring cliche tics for this novel
    # when WritingOptions.learn_adaptive_patterns is set. Report-only.
    adaptive_pattern_report: "AdaptivePatternReport | None" = None
    # Persistent narrative-debt ledger. Populated after post-write diagnostics
    # from unresolved props, reader dangling threads, canon notes, and planted
    # foreshadowing. String-annotated to avoid a cycle.
    narrative_debt_ledger: "NarrativeDebtLedger | None" = None


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
