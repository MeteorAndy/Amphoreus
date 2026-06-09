"""Pipeline stage methods, mixed into PipelineOrchestrator.

Each _stage_* method is an async generator yielding PipelineEvent. They read
and mutate the shared `state` dict and call persistence helpers provided by
_PersistenceMixin. Split out of pipeline_orchestrator.py to keep each module
under the project line limit.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

from app.models.character import CharacterProfile
from app.services.narrative import WritingOptions
from app.services.narrative import canon_persistence as cp
from app.services.plot_architect import NarrativeStructure, PlotOutline
from app.services.scene_engine.resolution import SceneArchive
from app.services.world_builder import WorldBuilderSession, WorldState
from app.services.pipeline_types import (
    PipelineConfig,
    PipelineEvent,
    PipelineStage,
    _AUTO_ANSWER_PROMPT_EN,
    _AUTO_ANSWER_PROMPT_ZH,
    _STRUCTURE_MAP,
)


class _StagesMixin:
    """The seven pipeline stages + their helpers. Requires self._llm and the
    service objects set by PipelineOrchestrator.__init__, plus persistence
    helpers from the sibling mixin."""

    async def _drive_stage(
        self, stage: PipelineStage, config: PipelineConfig,
        session_id: str, state: dict[str, Any],
    ) -> AsyncIterator[PipelineEvent]:
        """Dispatch the correct stage method. Thin — just a switch."""
        _stages = {
            PipelineStage.WORLD: self._stage_world,
            PipelineStage.CHARACTERS: self._stage_characters,
            PipelineStage.RELATIONSHIPS: self._stage_relationships,
            PipelineStage.PLOT: self._stage_plot,
            PipelineStage.SCENES: self._stage_scenes,
            PipelineStage.CANON: self._stage_canon,
            PipelineStage.WRITING: self._stage_writing,
        }
        async for event in _stages[stage](config, session_id, state):
            yield event

    async def _stage_world(
        self, config: PipelineConfig, session_id: str, state: dict[str, Any]
    ) -> AsyncIterator[PipelineEvent]:
        state["current_stage"] = PipelineStage.WORLD
        yield PipelineEvent(
            stage=PipelineStage.WORLD, type="started", progress=0.0, session_id=session_id
        )

        wb_session: WorldBuilderSession = await self._world_builder.start_new_world(config.seed_idea)
        iteration = 0
        max_iterations = 12

        while wb_session.stage != "done" and wb_session.extracted_data.completeness < 0.8:
            if iteration >= max_iterations:
                break
            auto_answer = await self._auto_answer(
                config.seed_idea, wb_session.next_question, config.lang
            )
            wb_session = await self._world_builder.continue_session(wb_session.session_id, auto_answer)
            iteration += 1
            progress = 0.0 + (0.15 * min(iteration / max_iterations, 1.0))
            yield PipelineEvent(
                stage=PipelineStage.WORLD,
                type="progress",
                data={"question": wb_session.next_question, "completeness": wb_session.extracted_data.completeness},
                progress=progress,
                session_id=session_id,
            )

        world_state = await self._world_builder.finalize_world(wb_session.session_id)
        state["world_state"] = world_state
        state["world_done"] = True
        state["progress"] = 0.15
        self._persist_artifact(session_id, "world_state", cp.world_state_to_dict(world_state))
        await self._save_state(session_id, state)

        yield PipelineEvent(
            stage=PipelineStage.WORLD,
            type="completed",
            data={
                "rules_count": len(world_state.rules),
                "locations_count": len(world_state.locations),
                "factions_count": len(world_state.factions),
                "completeness": world_state.completeness,
            },
            progress=0.15,
            session_id=session_id,
        )

    async def _stage_characters(
        self, config: PipelineConfig, session_id: str, state: dict[str, Any]
    ) -> AsyncIterator[PipelineEvent]:
        state["current_stage"] = PipelineStage.CHARACTERS
        yield PipelineEvent(
            stage=PipelineStage.CHARACTERS, type="started", progress=0.15, session_id=session_id
        )

        world_state: WorldState = state["world_state"]
        characters = await self._char_manager.generate_characters(world_state, config.character_count)

        if config.auto_refine:
            refined: list[CharacterProfile] = []
            for char in characters:
                updated = await self._char_manager.refine_character(
                    char.id, "Make this character more nuanced and complex"
                )
                refined.append(updated)
            characters = refined

        state["characters"] = characters
        state["characters_done"] = True
        state["progress"] = 0.25
        self._persist_artifact(
            session_id, "characters", {"items": [cp.character_to_dict(c) for c in characters]}
        )
        await self._save_state(session_id, state)

        yield PipelineEvent(
            stage=PipelineStage.CHARACTERS,
            type="completed",
            data={"count": len(characters), "names": [c.name for c in characters]},
            progress=0.25,
            session_id=session_id,
        )

    async def _stage_relationships(
        self, config: PipelineConfig, session_id: str, state: dict[str, Any]
    ) -> AsyncIterator[PipelineEvent]:
        state["current_stage"] = PipelineStage.RELATIONSHIPS
        yield PipelineEvent(
            stage=PipelineStage.RELATIONSHIPS, type="started", progress=0.25, session_id=session_id
        )

        characters: list[CharacterProfile] = state["characters"]
        world_state: WorldState = state["world_state"]
        relationships = await self._rel_builder.build_relationships(characters, world_state)

        state["relationships"] = relationships
        state["relationships_done"] = True
        state["progress"] = 0.30
        await self._save_state(session_id, state)

        yield PipelineEvent(
            stage=PipelineStage.RELATIONSHIPS,
            type="completed",
            data={"count": len(relationships)},
            progress=0.30,
            session_id=session_id,
        )

    async def _stage_plot(
        self, config: PipelineConfig, session_id: str, state: dict[str, Any]
    ) -> AsyncIterator[PipelineEvent]:
        state["current_stage"] = PipelineStage.PLOT
        yield PipelineEvent(
            stage=PipelineStage.PLOT, type="started", progress=0.30, session_id=session_id
        )

        world_state: WorldState = state["world_state"]
        characters: list[CharacterProfile] = state["characters"]
        structure = _STRUCTURE_MAP.get(config.narrative_structure, NarrativeStructure.THREE_ACT)
        outline = await self._plot_architect.generate_plot(world_state, characters, structure)

        state["outline"] = outline
        state["plot_done"] = True
        state["progress"] = 0.40
        self._persist_artifact(session_id, "outline", cp.outline_to_dict(outline))
        await self._save_state(session_id, state)

        scene_count = sum(len(act.scenes) for act in outline.acts)
        yield PipelineEvent(
            stage=PipelineStage.PLOT,
            type="completed",
            data={"acts": len(outline.acts), "scenes": scene_count, "structure": structure.value},
            progress=0.40,
            session_id=session_id,
        )

    async def _stage_scenes(
        self, config: PipelineConfig, session_id: str, state: dict[str, Any]
    ) -> AsyncIterator[PipelineEvent]:
        state["current_stage"] = PipelineStage.SCENES
        yield PipelineEvent(
            stage=PipelineStage.SCENES, type="started", progress=0.40, session_id=session_id
        )

        outline: PlotOutline = state["outline"]
        characters: list[CharacterProfile] = state["characters"]
        all_scenes = [scene for act in outline.acts for scene in act.scenes]
        total = len(all_scenes)

        # Resume support (T2-②): reload scenes already archived by a prior run
        # that crashed mid-stage. Scenes run sequentially, so the persisted list
        # is always a contiguous prefix — resume = skip the first len(done).
        # Keyed by POSITION, not scene_id: SceneSpec.id is LLM-generated and not
        # guaranteed unique, so an id-keyed dict could drop or mis-skip a scene.
        done: list[SceneArchive] = self._load_partial_archives(session_id)
        resume_from = len(done)

        for idx, scene_spec in enumerate(all_scenes):
            if idx < resume_from:
                # Already produced in an earlier (crashed) run — don't re-run.
                yield PipelineEvent(
                    stage=PipelineStage.SCENES,
                    type="progress",
                    data={"scene_id": scene_spec.id, "title": scene_spec.title,
                          "index": idx, "total": total, "cached": True},
                    progress=0.40 + (0.35 * (idx + 1) / max(total, 1)),
                    session_id=session_id,
                )
                continue

            scene_progress_start = 0.40 + (0.35 * idx / max(total, 1))
            yield PipelineEvent(
                stage=PipelineStage.SCENES,
                type="progress",
                data={"scene_id": scene_spec.id, "title": scene_spec.title, "index": idx, "total": total},
                progress=scene_progress_start,
                session_id=session_id,
            )

            cast_chars = [c for c in characters if c.id in scene_spec.cast] or characters
            archive = await self._scene_engine.run_scene(
                scene_spec, cast_chars, config.max_rounds_per_scene
            )
            done.append(archive)
            # Persist incrementally so a crash on a later scene never discards
            # work already done. The list is the canonical prefix run so far.
            self._persist_archives_list(session_id, done)
            yield PipelineEvent(
                stage=PipelineStage.SCENES,
                type="progress",
                data={
                    "scene_id": scene_spec.id,
                    "title": scene_spec.title,
                    "rounds": len(archive.rounds),
                    "index": idx,
                    "total": total,
                },
                progress=0.40 + (0.35 * (idx + 1) / max(total, 1)),
                session_id=session_id,
            )

        state["archives"] = done
        state["scenes_done"] = True
        state["progress"] = 0.75
        self._persist_archives_list(session_id, done)
        await self._save_state(session_id, state)

        yield PipelineEvent(
            stage=PipelineStage.SCENES,
            type="completed",
            data={"scenes_completed": len(done)},
            progress=0.75,
            session_id=session_id,
        )

    async def _stage_canon(
        self, config: PipelineConfig, session_id: str, state: dict[str, Any]
    ) -> AsyncIterator[PipelineEvent]:
        """Adjudicate load-bearing facts the source leaves silent, so the novel
        and screenplay runs (separate runs) share one locked truth."""
        state["current_stage"] = PipelineStage.CANON
        yield PipelineEvent(
            stage=PipelineStage.CANON, type="started", progress=0.75, session_id=session_id
        )

        archives: list[SceneArchive] = state["archives"]
        characters: list[CharacterProfile] = state["characters"]
        outline: PlotOutline | None = state.get("outline")
        world_state: WorldState = state["world_state"]

        facts = await self._canon_adjudicator.adjudicate(
            archives=archives,
            outline=outline,
            characters=characters,
            world_summary=self._world_summary(world_state),
            session_id=session_id,
        )

        state["canonical_facts"] = facts
        state["canon_done"] = True
        state["progress"] = 0.78
        self._persist_artifact(session_id, "canonical_facts", facts.to_dict())
        await self._save_state(session_id, state)

        yield PipelineEvent(
            stage=PipelineStage.CANON,
            type="completed",
            data={
                "facts_locked": len(facts.facts),
                "unresolved": len(facts.unresolved),
            },
            progress=0.78,
            session_id=session_id,
        )

    async def _stage_writing(
        self, config: PipelineConfig, session_id: str, state: dict[str, Any]
    ) -> AsyncIterator[PipelineEvent]:
        state["current_stage"] = PipelineStage.WRITING
        yield PipelineEvent(
            stage=PipelineStage.WRITING, type="started", progress=0.78, session_id=session_id
        )

        archives: list[SceneArchive] = state["archives"]
        characters: list[CharacterProfile] = state["characters"]
        outline: PlotOutline = state["outline"]
        world_state: WorldState = state["world_state"]

        world_summary = self._world_summary(world_state)

        # Rehydrate the foreshadowing registry from its artifact (empty if none
        # persisted yet). Single from_dict — the writers apply TTL downgrade in
        # place, so we persist the updated state back after writing.
        reg_dict = self._load_artifact(session_id, "foreshadowing_registry")
        registry = cp.registry_from_dict(reg_dict) if reg_dict else None

        options = WritingOptions(
            format=config.output_format,
            canonical_facts=state.get("canonical_facts"),
            foreshadowing_registry=registry,
            score_tension=True,
            extract_props=True,
        )

        output: WrittenOutput = await self._narrative_writer.convert(
            scene_archives=archives,
            characters=characters,
            options=options,
            plot_outline=outline,
            world_summary=world_summary,
            selected_title_index=0,
        )

        if registry is not None:
            self._persist_artifact(
                session_id, "foreshadowing_registry", cp.registry_to_dict(registry)
            )

        state["output"] = output
        state["writing_done"] = True
        state["progress"] = 1.0
        await self._save_state(session_id, state)

        # Fire-and-forget: extract S/P/O facts from the finished prose and
        # persist them to the knowledge graph. This is a SEPARATE channel from
        # the synchronous cliche/canon diagnostics (which ride the event below)
        # — it must not block or delay the completed event. chapter_id = the
        # session_id for the single-output MVP.
        asyncio.create_task(
            self._post_write_background(session_id, output.content)
        )

        yield PipelineEvent(
            stage=PipelineStage.WRITING,
            type="completed",
            data={
                "title": output.title,
                "word_count": output.word_count,
                "format": output.format,
                "title_candidates": output.title_candidates,
                "content": output.content,
                "cliche_report": (
                    output.cliche_report.to_dict() if output.cliche_report else {}
                ),
                "canon_report": (
                    output.canon_report.to_dict() if output.canon_report else {}
                ),
                "tension_report": (
                    output.tension_report.to_dict() if output.tension_report else {}
                ),
                "prop_lifecycle_report": (
                    output.prop_lifecycle_report.to_dict()
                    if output.prop_lifecycle_report
                    else {}
                ),
            },
            progress=1.0,
            session_id=session_id,
        )

    async def _post_write_background(self, session_id: str, content: str) -> None:
        """Extract S/P/O facts from finished prose and persist to the graph.

        Best-effort and fully isolated: any failure is swallowed so a background
        task can never crash the event loop or surface to the user. chapter_id is
        the session_id for the single-output MVP.
        """
        try:
            triples = await self._fact_extractor.extract(content, session_id)
            if triples:
                await self._triples_store.persist(triples, session_id)
        except Exception:
            pass

    async def _auto_answer(self, seed_idea: str, question: str, lang: str) -> str:
        system_prompt = _AUTO_ANSWER_PROMPT_ZH if lang == "zh" else _AUTO_ANSWER_PROMPT_EN
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Seed idea: {seed_idea}\n\nQuestion: {question}",
            },
        ]
        result = await self._llm.chat(messages, temperature=0.8)
        return result if isinstance(result, str) else str(result)

    @staticmethod
    def _world_summary(world: WorldState) -> str:
        parts: list[str] = []
        if world.rules:
            parts.append("Rules: " + ", ".join(r.get("name", "") for r in world.rules[:3]))
        if world.locations:
            parts.append("Locations: " + ", ".join(l.get("name", "") for l in world.locations[:3]))
        if world.factions:
            parts.append("Factions: " + ", ".join(f.get("name", "") for f in world.factions[:3]))
        if world.timeline:
            parts.append("Timeline: " + ", ".join(t.get("name", "") for t in world.timeline[:3]))
        return "; ".join(parts)
