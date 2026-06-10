from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.narrative.aftermath_pipeline import ChapterAftermathPipeline
from app.services.narrative.canon_verifier import CanonReport, Violation
from app.services.narrative.foreshadowing import Foreshadowing, ForeshadowingRegistry
from app.services.narrative.narrative_debt import (
    NarrativeDebtItem,
    NarrativeDebtLedger,
    build_narrative_debt_ledger,
)
from app.services.narrative.prop_lifecycle import PropLifecycle, PropLifecycleReport
from app.services.narrative.reader_sim import DanglingThread, ReaderSimReport
from app.services.narrative.types import ChapterPlan, ChapterSpec, WritingOptions, WrittenOutput
from app.services.pipeline_orchestrator import PipelineOrchestrator


def _output() -> WrittenOutput:
    return WrittenOutput(content="prose", format="novel", word_count=1, scene_count=1)


def test_build_ledger_collects_open_debts_from_reports_and_registry():
    output = _output()
    output.prop_lifecycle_report = PropLifecycleReport(
        props=[
            PropLifecycle(
                object_name="the map",
                introduced_in_chapter=1,
                status="UNRESOLVED",
                use_count=0,
                mention_chapters=[1],
                last_chapter=1,
            ),
            PropLifecycle(
                object_name="the key",
                introduced_in_chapter=1,
                status="PAID_OFF",
                use_count=1,
                mention_chapters=[1, 2],
                last_chapter=2,
            ),
        ],
        unresolved=["the map"],
    )
    output.reader_sim_report = ReaderSimReport(
        dangling_threads=[DanglingThread("Who opened the vault?", 2, "high")]
    )
    output.canon_report = CanonReport(
        violations=[
            Violation("fact-1", "lineage", "contradiction", "high", "wrong father")
        ],
        checked=1,
        clean=False,
    )
    registry = ForeshadowingRegistry(
        [
            Foreshadowing(
                id="thread-1",
                planted_in_chapter=1,
                description="A bell rings under the lake.",
                importance="HIGH",
                status="PLANTED",
                suggested_resolve_chapter=3,
            )
        ]
    )

    ledger = build_narrative_debt_ledger(output, foreshadowing_registry=registry)

    by_id = {item.id: item for item in ledger.items}
    assert "prop:the map" in by_id
    assert "prop:the key" not in by_id
    assert "reader:2:Who opened the vault?" in by_id
    assert "canon:fact-1:contradiction" in by_id
    assert "foreshadowing:thread-1" in by_id
    assert all(item.status == "OPEN" for item in by_id.values())
    json.dumps(ledger.to_dict())


def test_ledger_roundtrip_and_marks_missing_seen_source_debt_resolved():
    prior = NarrativeDebtLedger(
        items=[
            NarrativeDebtItem(
                id="prop:the map",
                kind="prop_unresolved",
                description="Unresolved prop: the map",
                severity="medium",
                status="OPEN",
                source="prop_lifecycle",
                introduced_in_chapter=1,
            )
        ]
    )
    output = _output()
    output.prop_lifecycle_report = PropLifecycleReport(props=[], unresolved=[])

    ledger = build_narrative_debt_ledger(output, prior=prior)
    restored = NarrativeDebtLedger.from_dict(ledger.to_dict())

    assert restored.items[0].id == "prop:the map"
    assert restored.items[0].status == "RESOLVED"


@pytest.mark.asyncio
async def test_aftermath_attaches_narrative_debt_ledger():
    output = _output()
    output.prop_lifecycle_report = PropLifecycleReport(
        props=[
            PropLifecycle(
                object_name="the map",
                introduced_in_chapter=1,
                status="UNRESOLVED",
                use_count=0,
                mention_chapters=[1],
                last_chapter=1,
            )
        ],
        unresolved=["the map"],
    )
    pipeline = ChapterAftermathPipeline(AsyncMock())

    result = await pipeline.attach_novel_reports(
        output,
        scene_archives=[],
        chapter_plan=ChapterPlan(chapters=[ChapterSpec(1, "Open", [], "")]),
        options=WritingOptions(format="novel"),
        budget_acc=[],
    )

    assert result.narrative_debt_ledger is not None
    assert result.narrative_debt_ledger.open_count == 1


class _FakeOpenViking:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def write_entry(self, path, content, **kwargs) -> None:
        self.store[path] = content

    def read_entry(self, path):
        if path not in self.store:
            raise KeyError(path)
        return SimpleNamespace(l2=self.store[path])


class _FakeMemory:
    def __init__(self) -> None:
        self.openviking = _FakeOpenViking()


@pytest.mark.asyncio
async def test_writing_stage_persists_narrative_debt_ledger(monkeypatch):
    memory = _FakeMemory()
    orch = object.__new__(PipelineOrchestrator)
    orch._memory = memory
    orch._narrative_writer = SimpleNamespace(convert=AsyncMock())
    orch._aftermath = SimpleNamespace(persist_inferred_facts=AsyncMock())
    orch._load_artifact = PipelineOrchestrator._load_artifact.__get__(orch)
    orch._persist_artifact = PipelineOrchestrator._persist_artifact.__get__(orch)
    orch._save_state = PipelineOrchestrator._save_state.__get__(orch)
    orch._world_summary = PipelineOrchestrator._world_summary

    ledger = NarrativeDebtLedger(
        items=[
            NarrativeDebtItem(
                id="reader:1:q",
                kind="reader_dangling",
                description="Dangling reader question: q",
                severity="high",
                status="OPEN",
                source="reader_sim",
                introduced_in_chapter=1,
            )
        ]
    )
    output = _output()
    output.narrative_debt_ledger = ledger
    orch._narrative_writer.convert.return_value = output

    def _skip_task(coro):
        coro.close()
        return None

    monkeypatch.setattr("app.services.pipeline_stages.asyncio.create_task", _skip_task)

    state = {
        "archives": [],
        "characters": [],
        "outline": object(),
        "world_state": SimpleNamespace(rules=[], locations=[], factions=[], timeline=[]),
        "canonical_facts": None,
    }
    events = [
        event async for event in orch._stage_writing(
            SimpleNamespace(output_format="novel"),
            "sess",
            state,
        )
    ]

    saved = json.loads(memory.openviking.store["pipeline/sessions/sess/narrative_debt_ledger"])
    assert saved["open_count"] == 1
    assert events[-1].data["narrative_debt_ledger"]["open_count"] == 1


@pytest.mark.asyncio
async def test_writing_stage_merges_prior_narrative_debt_ledger(monkeypatch):
    memory = _FakeMemory()
    prior = NarrativeDebtLedger(
        items=[
            NarrativeDebtItem(
                id="prop:old map",
                kind="prop_unresolved",
                description="Unresolved prop: old map",
                severity="medium",
                status="OPEN",
                source="prop_lifecycle",
                introduced_in_chapter=1,
            )
        ]
    )
    memory.openviking.store[
        "pipeline/sessions/sess/narrative_debt_ledger"
    ] = json.dumps(prior.to_dict())

    orch = object.__new__(PipelineOrchestrator)
    orch._memory = memory
    orch._narrative_writer = SimpleNamespace(convert=AsyncMock())
    orch._aftermath = SimpleNamespace(persist_inferred_facts=AsyncMock())
    orch._load_artifact = PipelineOrchestrator._load_artifact.__get__(orch)
    orch._persist_artifact = PipelineOrchestrator._persist_artifact.__get__(orch)
    orch._save_state = PipelineOrchestrator._save_state.__get__(orch)
    orch._world_summary = PipelineOrchestrator._world_summary

    output = _output()
    output.prop_lifecycle_report = PropLifecycleReport(props=[], unresolved=[])
    output.narrative_debt_ledger = build_narrative_debt_ledger(output)
    orch._narrative_writer.convert.return_value = output

    def _skip_task(coro):
        coro.close()
        return None

    monkeypatch.setattr("app.services.pipeline_stages.asyncio.create_task", _skip_task)

    state = {
        "archives": [],
        "characters": [],
        "outline": object(),
        "world_state": SimpleNamespace(rules=[], locations=[], factions=[], timeline=[]),
        "canonical_facts": None,
    }
    events = [
        event async for event in orch._stage_writing(
            SimpleNamespace(output_format="novel"),
            "sess",
            state,
        )
    ]

    saved = json.loads(memory.openviking.store["pipeline/sessions/sess/narrative_debt_ledger"])
    assert saved["open_count"] == 0
    assert saved["items"][0]["id"] == "prop:old map"
    assert saved["items"][0]["status"] == "RESOLVED"
    assert events[-1].data["narrative_debt_ledger"]["items"][0]["status"] == "RESOLVED"
