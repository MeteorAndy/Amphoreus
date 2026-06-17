"""Unified post-write aftermath pipeline.

This module owns work that happens after prose/screenplay text is assembled:
diagnostic reports attached to `WrittenOutput`, and best-effort persistence of
facts inferred from finished prose.
"""

from __future__ import annotations

from app.core.llm_client import LLMClient
from app.services.memory import MemoryManager
from app.services.scene_engine.resolution import SceneArchive

from .canon_verifier import verify
from .cliche_scanner import scan
from .entity_events import build_entity_event_history
from .graph_inference import GraphInferenceEngine
from .inferred_triples_store import InferredTriplesStore
from .narrative_debt import build_narrative_debt_ledger
from .prop_lifecycle import build_prop_lifecycle_report
from .prose_fact_extractor import ProseFactExtractor
from .reader_sim import build_reader_sim_report
from .relationship_trend import build_relationship_trend_report
from .tension_scorer import build_tension_report
from .token_budget import BudgetReport, ChapterBudget
from .types import ChapterPlan, WritingOptions, WrittenOutput


class ChapterAftermathPipeline:
    """Attach post-write diagnostics and persist inferred facts."""

    def __init__(
        self,
        llm: LLMClient,
        *,
        memory: MemoryManager | None = None,
        fact_extractor: ProseFactExtractor | None = None,
        triples_store: InferredTriplesStore | None = None,
    ) -> None:
        self._llm = llm
        self._fact_extractor = fact_extractor or ProseFactExtractor(llm)
        self._memory = memory
        self._triples_store = triples_store
        if self._triples_store is None and memory is not None:
            self._triples_store = InferredTriplesStore(memory)

    async def attach_novel_reports(
        self,
        output: WrittenOutput,
        *,
        scene_archives: list[SceneArchive],
        chapter_plan: ChapterPlan,
        options: WritingOptions,
        budget_acc: list[ChapterBudget],
    ) -> WrittenOutput:
        """Populate all novel post-write reports on `output`."""
        output.cliche_report = scan(output.content)
        if options.canonical_facts is not None:
            output.canon_report = verify(output.content, options.canonical_facts, "novel")
        if options.score_tension:
            output.tension_report = build_tension_report(scene_archives, chapter_plan)
        if options.analyze_relationship_trends:
            output.relationship_trend_report = build_relationship_trend_report(
                scene_archives, chapter_plan
            )
        if options.track_entity_events:
            output.entity_event_report = build_entity_event_history(
                scene_archives, chapter_plan
            )
        if options.enable_graph_inference and self._memory is not None:
            # Read-only pass over the accumulated Kuzu graph. NOTE: this run's
            # just-extracted triples are persisted by a background task after
            # the completed event, so the report reflects the graph as it stood
            # at write time (prior runs' facts); it never writes to the graph.
            output.graph_inference_report = GraphInferenceEngine(
                self._memory.kuzu
            ).run()
        if options.extract_props:
            output.prop_lifecycle_report = await build_prop_lifecycle_report(
                self._llm, output.content
            )
        if options.simulate_reader:
            output.reader_sim_report = await build_reader_sim_report(
                self._llm, output.content, chapter_plan
            )
        if budget_acc:
            output.budget_report = BudgetReport(
                per_chapter=budget_acc,
                any_over=any(cb.over_by > 0 for cb in budget_acc),
                total_tokens=sum(cb.total_tokens for cb in budget_acc),
            )
        output.narrative_debt_ledger = build_narrative_debt_ledger(
            output, foreshadowing_registry=options.foreshadowing_registry
        )
        return output

    def attach_screenplay_reports(
        self,
        output: WrittenOutput,
        *,
        options: WritingOptions,
    ) -> WrittenOutput:
        """Populate screenplay post-write reports on `output`."""
        output.cliche_report = scan(output.content)
        if options.canonical_facts is not None:
            output.canon_report = verify(
                output.content, options.canonical_facts, "screenplay"
            )
        output.narrative_debt_ledger = build_narrative_debt_ledger(output)
        return output

    async def persist_inferred_facts(self, chapter_id: str, content: str) -> None:
        """Extract finished-prose facts and persist them best-effort."""
        if self._triples_store is None:
            return
        try:
            triples = await self._fact_extractor.extract(content, chapter_id)
            if triples:
                await self._triples_store.persist(triples, chapter_id)
        except Exception:
            pass
