"""Pre-reset STASH — git-like worldline, first slice (T3-②).

A side-channel copy of a session's live state + artifacts into a ``_stash/``
namespace before any destructive overwrite, so a pipeline rerun can never lose
prior work. Implemented as a manifest-indexed set of openviking entries (no scan
primitive needed — OpenViking exposes only read/write/delete by path).

Opt-in: the orchestrator stashes only when ``stash_enabled``. Restore is NEVER
automatic — resume/rollback stay explicit caller actions. The stash namespace
(``pipeline/sessions/{id}/_stash/...``) never collides with live artifact names.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

# Live artifact names to capture. "state" is the pipeline_state entry; the rest
# are pipeline_artifact entries written by the stages.
_LIVE_NAMES = ("state", "archives", "outline", "characters", "world_state", "canonical_facts")
_LIVE_L0 = {"state": "pipeline_state"}
_STASH_L0 = "pipeline_stash"


@dataclass
class StashRef:
    """Manifest entry for one stashed snapshot."""

    stash_id: str
    session_id: str
    stage: str
    reason: str
    created_at: float
    artifact_names: list[str] = field(default_factory=list)


class StashStore:
    """Stash/list/peek/restore/drop over an openviking-like store."""

    def __init__(self, openviking: Any) -> None:
        self._ov = openviking

    # --- paths ------------------------------------------------------------

    @staticmethod
    def _live(session_id: str, name: str) -> str:
        return f"pipeline/sessions/{session_id}/{name}"

    @staticmethod
    def _stash_path(session_id: str, stash_id: str, name: str) -> str:
        return f"pipeline/sessions/{session_id}/_stash/{stash_id}/{name}"

    @staticmethod
    def _index_path(session_id: str) -> str:
        return f"pipeline/sessions/{session_id}/_stash/_index"

    # --- index ------------------------------------------------------------

    def _read_index(self, session_id: str) -> list[StashRef]:
        try:
            raw = self._ov.read_entry(self._index_path(session_id)).l2
            data = json.loads(raw)
        except Exception:
            return []
        out: list[StashRef] = []
        for row in data:
            try:
                out.append(StashRef(**row))
            except Exception:
                continue
        return out

    def _write_index(self, session_id: str, refs: list[StashRef]) -> None:
        self._ov.write_entry(
            self._index_path(session_id),
            json.dumps([asdict(r) for r in refs], ensure_ascii=False),
            l0=_STASH_L0, l1=session_id,
        )

    def _find(self, session_id: str, stash_id: str) -> StashRef:
        for r in self._read_index(session_id):
            if r.stash_id == stash_id:
                return r
        raise KeyError(stash_id)

    # --- public API -------------------------------------------------------

    def stash(
        self, session_id: str, *, stage: str, reason: str,
        names: tuple[str, ...] | None = None,
    ) -> StashRef:
        """Copy the live state + artifacts into a fresh stash namespace."""
        stash_id = uuid.uuid4().hex[:12]
        captured: list[str] = []
        for name in (names or _LIVE_NAMES):
            try:
                entry = self._ov.read_entry(self._live(session_id, name))
            except Exception:
                continue
            self._ov.write_entry(
                self._stash_path(session_id, stash_id, name), entry.l2,
                l0=_STASH_L0, l1=session_id,
            )
            captured.append(name)
        ref = StashRef(
            stash_id=stash_id, session_id=session_id, stage=stage, reason=reason,
            created_at=time.time(), artifact_names=captured,
        )
        refs = self._read_index(session_id) + [ref]
        self._write_index(session_id, refs)
        return ref

    def list_stashes(self, session_id: str) -> list[StashRef]:
        return sorted(self._read_index(session_id), key=lambda r: r.created_at)

    def peek(self, session_id: str, stash_id: str) -> dict[str, Any]:
        """Read-only view of a stash's payloads (name -> parsed JSON)."""
        ref = self._find(session_id, stash_id)
        out: dict[str, Any] = {}
        for name in ref.artifact_names:
            try:
                out[name] = json.loads(
                    self._ov.read_entry(self._stash_path(session_id, stash_id, name)).l2
                )
            except Exception:
                continue
        return out

    def restore(self, session_id: str, stash_id: str) -> None:
        """Overwrite the live state + artifacts with the stash's payloads."""
        ref = self._find(session_id, stash_id)
        for name in ref.artifact_names:
            try:
                entry = self._ov.read_entry(self._stash_path(session_id, stash_id, name))
            except Exception:
                continue
            self._ov.write_entry(
                self._live(session_id, name), entry.l2,
                l0=_LIVE_L0.get(name, "pipeline_artifact"), l1=session_id,
            )

    def drop(self, session_id: str, stash_id: str) -> None:
        """Remove a stash's payloads + its index entry (live data untouched)."""
        ref = self._find(session_id, stash_id)
        for name in ref.artifact_names:
            self._ov.delete_entry(self._stash_path(session_id, stash_id, name))
        refs = [r for r in self._read_index(session_id) if r.stash_id != stash_id]
        self._write_index(session_id, refs)
