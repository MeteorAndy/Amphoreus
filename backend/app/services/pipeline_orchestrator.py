"""Autonomous story-generation pipeline orchestrator.

Thin composition layer: the run loop lives here; the seven stage methods come
from _StagesMixin and the persistence/resume helpers from _PersistenceMixin.
Public names (PipelineConfig, PipelineEvent, PipelineStage, _STAGE_SEVERITY)
are re-exported here so existing imports of this module keep working.
"""

from __future__ import annotations

import uuid
from typing import Any, AsyncIterator

from app.core.circuit_breaker import CircuitBreaker
from app.core.i18n import set_lang, Lang
from app.core.llm_client import LLMClient, LLMError, LLMErrorCode
from app.services.character_manager import CharacterManager
from app.services.memory import MemoryManager
from app.services.narrative import NarrativeWriter
from app.services.narrative.aftermath_pipeline import ChapterAftermathPipeline
from app.services.narrative.canon_adjudicator import CanonAdjudicator
from app.services.plot_architect import PlotArchitect
from app.services.relationship_builder import RelationshipBuilder
from app.services.scene_engine import SceneEngine
from app.services.world_builder import WorldBuilder
from app.services.pipeline_persistence import _PersistenceMixin
from app.services.pipeline_stash import StashStore
from app.services.pipeline_stages import _StagesMixin
from app.services.pipeline_types import (  # re-exported for consumers
    PipelineConfig,
    PipelineEvent,
    PipelineStage,
    _STAGE_SEVERITY,
    _STRUCTURE_MAP,
    _AUTO_ANSWER_PROMPT_ZH,
    _AUTO_ANSWER_PROMPT_EN,
)

__all__ = [
    "PipelineOrchestrator",
    "PipelineConfig",
    "PipelineEvent",
    "PipelineStage",
    "_STAGE_SEVERITY",
]


class PipelineOrchestrator(_StagesMixin, _PersistenceMixin):
    """Runs the full story generation pipeline autonomously."""

    def __init__(self, llm: LLMClient, memory: MemoryManager,
                 *, stash_enabled: bool = False) -> None:
        self._llm = llm
        self._memory = memory
        self._world_builder = WorldBuilder(llm, memory)
        self._char_manager = CharacterManager(llm, memory)
        self._rel_builder = RelationshipBuilder(llm, memory)
        self._plot_architect = PlotArchitect(llm, memory)
        self._scene_engine = SceneEngine(llm, memory)
        self._narrative_writer = NarrativeWriter(llm, memory)
        self._canon_adjudicator = CanonAdjudicator(llm)
        self._aftermath = ChapterAftermathPipeline(llm, memory=memory)
        self._breaker = CircuitBreaker()
        # T3-② pre-reset STASH — opt-in; off by default so _save_state is a no-op
        # change and resume is untouched.
        self._stash_enabled = stash_enabled
        self._stash = StashStore(memory.openviking)

    def run(self, config: PipelineConfig) -> AsyncIterator[PipelineEvent]:
        """Execute the full pipeline, yielding events as progress is made."""
        return self._run_pipeline(config)

    async def _run_pipeline(self, config: PipelineConfig) -> AsyncIterator[PipelineEvent]:
        lang = Lang.ZH if config.lang == "zh" else Lang.EN
        set_lang(lang)

        session_id = config.session_id or str(uuid.uuid4())
        state = await self._load_state(session_id)
        self._hydrate_state(session_id, state)

        stage_status: dict[str, str] = {}
        try:
            for stage, done_key in (
                (PipelineStage.WORLD, "world_done"),
                (PipelineStage.CHARACTERS, "characters_done"),
                (PipelineStage.RELATIONSHIPS, "relationships_done"),
                (PipelineStage.PLOT, "plot_done"),
                (PipelineStage.SCENES, "scenes_done"),
                (PipelineStage.CANON, "canon_done"),
                (PipelineStage.WRITING, "writing_done"),
            ):
                if stage == PipelineStage.CANON and not config.adjudicate:
                    continue
                if state.get(done_key):
                    stage_status[stage.value] = "skipped"
                    continue
                if _STAGE_SEVERITY[stage] == "optional":
                    try:
                        async for event in self._drive_stage(stage, config, session_id, state):
                            yield event
                        stage_status[stage.value] = "ok"
                    except LLMError as exc:
                        yield PipelineEvent(
                            stage=stage, type="warning",
                            data={"code": exc.code, "message": str(exc)},
                            progress=state.get("progress", 0.0),
                            session_id=session_id,
                        )
                        stage_status[stage.value] = f"degraded: {exc.code.value}"
                else:
                    async for event in self._drive_stage(stage, config, session_id, state):
                        yield event
                    stage_status[stage.value] = "ok"

            yield PipelineEvent(
                stage=PipelineStage.DONE,
                type="completed",
                data={"session_id": session_id, "stage_status": stage_status},
                progress=1.0,
                session_id=session_id,
            )

        except LLMError as exc:
            if exc.code == LLMErrorCode.BREAKER_OPEN:
                yield PipelineEvent(
                    stage=state.get("current_stage", PipelineStage.WORLD),
                    type="error",
                    data={"code": "BREAKER_OPEN", "message": "breaker tripped — resume later"},
                    progress=state.get("progress", 0.0),
                    session_id=session_id,
                )
            else:
                yield PipelineEvent(
                    stage=state.get("current_stage", PipelineStage.WORLD),
                    type="error",
                    data={"code": exc.code, "message": str(exc)},
                    progress=state.get("progress", 0.0),
                    session_id=session_id,
                )
