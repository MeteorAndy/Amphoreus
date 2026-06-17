"""Tests for T3-②: pre-reset STASH (git-like worldline, first slice).

Side-channel copy of a session's state + artifacts into a _stash/ namespace
before any destructive overwrite, so a rerun never loses prior work. Opt-in
(stash_enabled); never auto-rollback; resume path untouched.

Uses an in-memory openviking double (the resume_canon test pattern) — exercises
the real read/write/delete logic faithfully without the hanging integration suite.

    uv run pytest tests/test_pipeline_stash.py -v
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.pipeline_stash import StashStore, StashRef
from app.services.pipeline_persistence import _PersistenceMixin


class _FakeOV:
    def __init__(self):
        self.store: dict[str, str] = {}

    def write_entry(self, path, content, *, l0, l1):
        self.store[path] = content

    def read_entry(self, path):
        if path not in self.store:
            raise KeyError(path)
        return SimpleNamespace(l2=self.store[path])

    def delete_entry(self, path):
        self.store.pop(path, None)


def _orch(ov):
    o = object.__new__(_PersistenceMixin)
    o._memory = MagicMock()
    o._memory.openviking = ov
    o._stash_enabled = False
    o._stash = StashStore(ov)
    return o


def _seed(ov, session_id):
    ov.write_entry(f"pipeline/sessions/{session_id}/state",
                   json.dumps({"progress": 0.4, "world_done": True}),
                   l0="pipeline_state", l1=session_id)
    ov.write_entry(f"pipeline/sessions/{session_id}/outline",
                   json.dumps({"acts": []}), l0="pipeline_artifact", l1=session_id)


# --- stash copies, original untouched ------------------------------------

def test_stash_copies_state_and_artifacts_original_untouched():
    ov = _FakeOV()
    _seed(ov, "s1")
    store = StashStore(ov)
    ref = store.stash("s1", stage="plot", reason="rerun")

    assert ref.artifact_names  # captured something
    # originals still readable & unchanged
    assert json.loads(ov.read_entry("pipeline/sessions/s1/state").l2)["world_done"] is True
    assert "pipeline/sessions/s1/_stash" in ref.artifact_names[0] or ref.stash_id
    # stash copy exists for state
    stashed = ov.read_entry(f"pipeline/sessions/s1/_stash/{ref.stash_id}/state").l2
    assert json.loads(stashed)["world_done"] is True


def test_stash_then_overwrite_original_stash_intact():
    ov = _FakeOV()
    _seed(ov, "s1")
    store = StashStore(ov)
    ref = store.stash("s1", stage="plot", reason="rerun")

    # simulate a destructive rerun overwriting live state
    ov.write_entry("pipeline/sessions/s1/state",
                   json.dumps({"progress": 0.0}), l0="pipeline_state", l1="s1")

    # stash copy still holds the OLD state
    stashed = json.loads(ov.read_entry(f"pipeline/sessions/s1/_stash/{ref.stash_id}/state").l2)
    assert stashed["world_done"] is True


# --- list / restore / drop ------------------------------------------------

def test_list_stashes_chronological():
    ov = _FakeOV()
    _seed(ov, "s1")
    store = StashStore(ov)
    r1 = store.stash("s1", stage="plot", reason="a")
    r2 = store.stash("s1", stage="scenes", reason="b")
    refs = store.list_stashes("s1")
    assert [r.stash_id for r in refs] == [r1.stash_id, r2.stash_id]


def test_restore_overwrites_live_state():
    ov = _FakeOV()
    _seed(ov, "s1")
    store = StashStore(ov)
    ref = store.stash("s1", stage="plot", reason="rerun")
    ov.write_entry("pipeline/sessions/s1/state",
                   json.dumps({"progress": 0.0}), l0="pipeline_state", l1="s1")

    store.restore("s1", ref.stash_id)

    restored = json.loads(ov.read_entry("pipeline/sessions/s1/state").l2)
    assert restored["world_done"] is True  # back to the stashed value


def test_drop_removes_stash_namespace_and_index():
    ov = _FakeOV()
    _seed(ov, "s1")
    store = StashStore(ov)
    ref = store.stash("s1", stage="plot", reason="x")
    assert store.list_stashes("s1")

    store.drop("s1", ref.stash_id)

    assert store.list_stashes("s1") == []
    assert f"pipeline/sessions/s1/_stash/{ref.stash_id}/state" not in ov.store


# --- mixin hook is opt-in -------------------------------------------------

@pytest.mark.asyncio
async def test_stash_hook_only_fires_when_enabled():
    ov = _FakeOV()
    _seed(ov, "s1")
    orch_off = _orch(ov)
    await orch_off._save_state("s1", {"progress": 0.5, "world_done": True})
    assert orch_off.list_stashes("s1") == []  # nothing stashed when disabled

    orch_on = _orch(ov)
    orch_on._stash_enabled = True
    await orch_on._save_state("s1", {"progress": 0.5, "world_done": True})
    assert len(orch_on.list_stashes("s1")) == 1  # stashed before overwrite
