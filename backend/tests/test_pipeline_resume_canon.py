"""Integration tests for the CANON stage: persistence, resume, cross-run sharing."""
from __future__ import annotations

import json

import pytest

from app.services.narrative.types import CanonicalFact, CanonicalFacts
from app.services.pipeline_orchestrator import PipelineOrchestrator


class _FakeOpenViking:
    """In-memory OpenViking — survives across orchestrator instances (= processes)."""

    def __init__(self):
        self.store: dict[str, str] = {}

    def write_entry(self, path, content, **kwargs):
        self.store[path] = content

    def read_entry(self, path):
        if path not in self.store:
            raise KeyError(path)
        from types import SimpleNamespace
        return SimpleNamespace(l2=self.store[path])


class _FakeMemory:
    def __init__(self, ov):
        self.openviking = ov


def _orch(memory):
    # Bypass the heavy __init__ (which builds CharacterManager/kuzu etc.) —
    # these tests exercise only the persistence/hydration helpers, which need
    # just _memory.
    orch = object.__new__(PipelineOrchestrator)
    orch._memory = memory
    return orch


def _sample_facts():
    return CanonicalFacts(facts=[CanonicalFact(
        id="ft-1", topic="family_truth", question="谁?",
        canonical_answer_zh="母亲，第97页", canonical_answer_en="Mother, p97",
        scope="all",
    )], session_id="sess")


def test_canon_done_in_save_state_whitelist():
    ov = _FakeOpenViking()
    orch = _orch(_FakeMemory(ov))
    import asyncio
    asyncio.run(orch._save_state("sess", {
        "canon_done": True, "scenes_done": True, "progress": 0.78,
        "current_stage": "canon", "archives": ["should not persist"],
    }))
    saved = json.loads(ov.store["pipeline/sessions/sess/state"])
    assert saved["canon_done"] is True
    assert "archives" not in saved  # thin state machine preserved


def test_hydrate_reloads_canonical_facts_cross_process():
    ov = _FakeOpenViking()
    # Process A: persist canon artifact + flag.
    _orch(_FakeMemory(ov))._persist_artifact("sess", "canonical_facts", _sample_facts().to_dict())

    # Process B (fresh orchestrator, empty memory state) resumes.
    state = {"canon_done": True}
    _orch(_FakeMemory(ov))._hydrate_state("sess", state)
    assert "canonical_facts" in state
    cf = state["canonical_facts"]
    assert cf.facts[0].canonical_answer_zh == "母亲，第97页"


def test_hydrate_no_keyerror_when_artifact_missing():
    # canon_done flag set but artifact absent — hydrate must not raise.
    state = {"canon_done": True, "scenes_done": True}
    _orch(_FakeMemory(_FakeOpenViking()))._hydrate_state("sess", state)
    assert "canonical_facts" not in state  # silently skipped, no crash


def test_both_runs_read_same_persisted_facts():
    """A novel run and a screenplay run (separate orchestrators) hydrate the
    identical canonical_facts — the root fix for cross-product divergence."""
    ov = _FakeOpenViking()
    _orch(_FakeMemory(ov))._persist_artifact("sess", "canonical_facts", _sample_facts().to_dict())

    novel_state = {"canon_done": True}
    screenplay_state = {"canon_done": True}
    _orch(_FakeMemory(ov))._hydrate_state("sess", novel_state)
    _orch(_FakeMemory(ov))._hydrate_state("sess", screenplay_state)

    assert novel_state["canonical_facts"].to_dict() == screenplay_state["canonical_facts"].to_dict()
