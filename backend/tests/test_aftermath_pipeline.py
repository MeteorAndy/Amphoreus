from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services.narrative.aftermath_pipeline import ChapterAftermathPipeline
from app.services.narrative.token_budget import BudgetSection, ChapterBudget
from app.services.narrative.types import (
    CanonicalFact,
    CanonicalFacts,
    ChapterPlan,
    ChapterSpec,
    WritingOptions,
    WrittenOutput,
)
from app.services.narrative.types_post_write import InferredTriple


def _canon() -> CanonicalFacts:
    return CanonicalFacts(
        facts=[
            CanonicalFact(
                id="f-1",
                topic="family_truth",
                question="Who wrote the book?",
                canonical_answer_zh="Mother",
                canonical_answer_en="Mother",
                rejected_answers=["Father wrote the book"],
                scope="all",
            )
        ]
    )


def _budget() -> ChapterBudget:
    return ChapterBudget(
        chapter_number=1,
        sections=[BudgetSection("system", "baseline", 10)],
        total_tokens=10,
        budget_tokens=100,
        over_by=0,
    )


@pytest.mark.asyncio
async def test_attach_novel_reports_populates_sync_diagnostics_and_budget():
    output = WrittenOutput(
        content="Father wrote the book. Time stood still.",
        format="novel",
        word_count=7,
        scene_count=1,
    )
    plan = ChapterPlan(chapters=[ChapterSpec(1, "Open", ["s1"], "summary")])

    result = await ChapterAftermathPipeline(AsyncMock()).attach_novel_reports(
        output,
        scene_archives=[],
        chapter_plan=plan,
        options=WritingOptions(format="novel", canonical_facts=_canon()),
        budget_acc=[_budget()],
    )

    assert result is output
    assert result.cliche_report is not None
    assert result.canon_report is not None
    assert result.canon_report.violations
    assert result.budget_report is not None
    assert result.budget_report.total_tokens == 10


def test_attach_screenplay_reports_uses_screenplay_canon_mode():
    output = WrittenOutput(
        content="Father wrote the book.",
        format="screenplay",
        word_count=4,
        scene_count=1,
    )

    result = ChapterAftermathPipeline(AsyncMock()).attach_screenplay_reports(
        output,
        options=WritingOptions(format="screenplay", canonical_facts=_canon()),
    )

    assert result is output
    assert result.cliche_report is not None
    assert result.canon_report is not None
    assert result.canon_report.violations


@pytest.mark.asyncio
async def test_persist_inferred_facts_persists_extracted_triples():
    triple = InferredTriple(
        subject="A",
        predicate="RELATES_TO",
        object_="B",
        subject_type="Character",
        object_type="Character",
        chapter_id="ch1",
    )
    extractor = AsyncMock()
    extractor.extract = AsyncMock(return_value=[triple])
    store = AsyncMock()
    store.persist = AsyncMock()

    await ChapterAftermathPipeline(
        AsyncMock(), fact_extractor=extractor, triples_store=store
    ).persist_inferred_facts("ch1", "A met B.")

    extractor.extract.assert_awaited_once_with("A met B.", "ch1")
    store.persist.assert_awaited_once_with([triple], "ch1")


@pytest.mark.asyncio
async def test_persist_inferred_facts_swallows_extractor_and_store_errors():
    extractor = AsyncMock()
    extractor.extract = AsyncMock(side_effect=RuntimeError("boom"))
    store = AsyncMock()

    await ChapterAftermathPipeline(
        AsyncMock(), fact_extractor=extractor, triples_store=store
    ).persist_inferred_facts("ch1", "A met B.")

    store.persist.assert_not_called()

    extractor.extract = AsyncMock(return_value=[object()])
    store.persist = AsyncMock(side_effect=RuntimeError("boom"))

    await ChapterAftermathPipeline(
        AsyncMock(), fact_extractor=extractor, triples_store=store
    ).persist_inferred_facts("ch1", "A met B.")
