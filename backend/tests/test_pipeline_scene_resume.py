"""T2-②: per-scene incremental persistence + resume-by-skip in _stage_scenes."""
from __future__ import annotations

import pytest

from app.services.pipeline_orchestrator import PipelineOrchestrator
from app.services.scene_engine.resolution import SceneArchive
from app.services.scene_engine.types import EnvironmentUpdate


class _FakeOpenViking:
    """In-memory OpenViking — survives across orchestrator instances."""

    def __init__(self):
        self.store: dict[str, str] = {}
        self.writes = 0

    def write_entry(self, path, content, **kwargs):
        self.store[path] = content
        self.writes += 1

    def read_entry(self, path):
        if path not in self.store:
            raise KeyError(path)
        from types import SimpleNamespace
        return SimpleNamespace(l2=self.store[path])


class _FakeMemory:
    def __init__(self, ov):
        self.openviking = ov


def _orch(memory):
    orch = object.__new__(PipelineOrchestrator)
    orch._memory = memory
    return orch


def _archive(scene_id: str) -> SceneArchive:
    return SceneArchive(
        scene_id=scene_id,
        rounds=[],
        final_environment=EnvironmentUpdate(
            atmosphere=f"atmo-{scene_id}", changes=[], background_activity=""
        ),
        character_changes={},
    )


def test_partial_archives_empty_on_fresh_run():
    orch = _orch(_FakeMemory(_FakeOpenViking()))
    assert orch._load_partial_archives("sess") == []


def test_incremental_persist_then_reload_cross_process():
    # Process A persists scenes 1-2 (crash before 3).
    ov = _FakeOpenViking()
    orchA = _orch(_FakeMemory(ov))
    orchA._persist_archives_list("sess", [_archive("s1"), _archive("s2")])

    # Process B resumes: reloads exactly the 2 completed scenes, in order.
    orchB = _orch(_FakeMemory(ov))
    reload = orchB._load_partial_archives("sess")
    assert [a.scene_id for a in reload] == ["s1", "s2"]


def test_persist_preserves_prefix_order():
    ov = _FakeOpenViking()
    orch = _orch(_FakeMemory(ov))
    orch._persist_archives_list("sess", [_archive("s1"), _archive("s2"), _archive("s3")])
    import json
    stored = json.loads(ov.store["pipeline/sessions/sess/archives"])
    assert [item["scene_id"] for item in stored["items"]] == ["s1", "s2", "s3"]


def test_corrupt_trailing_item_truncates_prefix():
    # A corrupt item must not drop a *middle* scene — resume stays contiguous.
    ov = _FakeOpenViking()
    orch = _orch(_FakeMemory(ov))
    orch._persist_archives_list("sess", [_archive("s1"), _archive("s2")])
    import json
    blob = json.loads(ov.store["pipeline/sessions/sess/archives"])
    blob["items"].append({"garbage": True})  # corrupt trailing entry
    ov.store["pipeline/sessions/sess/archives"] = json.dumps(blob)
    reload = orch._load_partial_archives("sess")
    assert [a.scene_id for a in reload] == ["s1", "s2"]

