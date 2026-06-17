"""Persistence + resume mixin for the pipeline orchestrator.

Holds the data-plane I/O (state machine flags, per-stage artifacts) and the
cross-process resume logic (_hydrate_state, partial scene archives). Mixed
into PipelineOrchestrator; relies on self._memory being set by __init__.
"""

from __future__ import annotations

import json
from typing import Any

from app.services.narrative.types import CanonicalFacts
from app.services.narrative import canon_persistence as cp
from app.services.scene_engine.resolution import SceneArchive


class _PersistenceMixin:
    """Session state + artifact persistence. Requires self._memory."""

    async def _load_state(self, session_id: str) -> dict[str, Any]:
        try:
            entry = self._memory.openviking.read_entry(f"pipeline/sessions/{session_id}/state")
            return json.loads(entry.l2)
        except Exception:
            return {}

    async def _save_state(self, session_id: str, state: dict[str, Any]) -> None:
        # Pre-reset STASH (T3-②): when enabled, snapshot the live state +
        # artifacts to a side-channel namespace BEFORE this overwrite, so a
        # rerun can never lose prior work. Opt-in; no-op when disabled.
        if getattr(self, "_stash_enabled", False) and getattr(self, "_stash", None) is not None:
            self._stash.stash(
                session_id,
                stage=str(state.get("current_stage", "")),
                reason="pre-save",
            )
        serializable = {
            k: v for k, v in state.items()
            if k in ("world_done", "characters_done", "relationships_done",
                     "plot_done", "scenes_done", "canon_done", "writing_done",
                     "current_stage", "progress")
        }
        self._memory.openviking.write_entry(
            f"pipeline/sessions/{session_id}/state",
            json.dumps(serializable),
            l0="pipeline_state",
            l1=session_id,
        )

    # --- Artifact persistence (data plane; survives cross-process resume) ---

    def _persist_artifact(self, session_id: str, name: str, payload: dict) -> None:
        self._memory.openviking.write_entry(
            f"pipeline/sessions/{session_id}/{name}",
            json.dumps(payload, ensure_ascii=False),
            l0="pipeline_artifact",
            l1=session_id,
        )

    def _load_artifact(self, session_id: str, name: str) -> dict | None:
        try:
            entry = self._memory.openviking.read_entry(
                f"pipeline/sessions/{session_id}/{name}"
            )
            return json.loads(entry.l2)
        except Exception:
            return None

    # --- Stash pass-throughs (T3-②); self._stash set by PipelineOrchestrator ---

    def list_stashes(self, session_id: str) -> list:
        return self._stash.list_stashes(session_id)

    def peek_stash(self, session_id: str, stash_id: str) -> dict:
        return self._stash.peek(session_id, stash_id)

    def restore_stash(self, session_id: str, stash_id: str) -> None:
        self._stash.restore(session_id, stash_id)

    def drop_stash(self, session_id: str, stash_id: str) -> None:
        self._stash.drop(session_id, stash_id)

    def _load_partial_archives(self, session_id: str) -> list[SceneArchive]:
        """Reload scene archives a prior (crashed) run persisted, in order.

        Scenes run sequentially and are persisted as a growing prefix, so the
        returned list is exactly the scenes completed before the crash. Returns
        [] on a fresh run. Used by _stage_scenes (T2-②) to resume by skipping
        the first len() scenes. A corrupt trailing item truncates the prefix
        (rather than dropping a middle scene) so resume stays contiguous."""
        d = self._load_artifact(session_id, "archives")
        if not d:
            return []
        result: list[SceneArchive] = []
        for item in d.get("items", []):
            try:
                result.append(cp.archive_from_dict(item))
            except Exception:
                # Stop at the first undecodable item: the prefix up to here is
                # trustworthy; anything after re-runs (safe, at worst redundant).
                break
        return result

    def _persist_archives_list(
        self, session_id: str, archives: list[SceneArchive]
    ) -> None:
        """Persist the archives completed so far as an ordered prefix.

        Written after every scene so a later crash never discards completed
        work. Same {"items": [...]} shape _hydrate_state already expects."""
        self._persist_artifact(
            session_id, "archives",
            {"items": [cp.archive_to_dict(a) for a in archives]},
        )

    def _hydrate_state(self, session_id: str, state: dict[str, Any]) -> None:
        """Rebuild in-memory data objects from persisted artifacts on resume.

        _save_state persists only boolean flags, so a fresh process resuming at
        CANON/WRITING would KeyError on archives/characters/outline/world_state.
        Re-load whatever the completed stages should have produced.
        """
        if state.get("world_done") and "world_state" not in state:
            d = self._load_artifact(session_id, "world_state")
            if d is not None:
                state["world_state"] = cp.world_state_from_dict(d)

        if state.get("characters_done") and "characters" not in state:
            d = self._load_artifact(session_id, "characters")
            if d is not None:
                state["characters"] = [cp.character_from_dict(c) for c in d.get("items", [])]

        if state.get("plot_done") and "outline" not in state:
            d = self._load_artifact(session_id, "outline")
            if d is not None:
                state["outline"] = cp.outline_from_dict(d)

        if state.get("scenes_done") and "archives" not in state:
            d = self._load_artifact(session_id, "archives")
            if d is not None:
                state["archives"] = [cp.archive_from_dict(a) for a in d.get("items", [])]

        if state.get("canon_done") and "canonical_facts" not in state:
            d = self._load_artifact(session_id, "canonical_facts")
            if d is not None:
                state["canonical_facts"] = CanonicalFacts.from_dict(d)
