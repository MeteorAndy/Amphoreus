from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncIterator
from enum import Enum

from app.core.i18n import set_lang, Lang
from app.core.llm_client import LLMClient, LLMError
from app.models.character import CharacterProfile
from app.services.character_manager import CharacterManager
from app.services.memory import MemoryManager
from app.services.narrative import NarrativeWriter, WritingOptions
from app.services.narrative.canon_adjudicator import CanonAdjudicator
from app.services.narrative.types import CanonicalFacts
from app.services.narrative import canon_persistence as cp
from app.services.plot_architect import NarrativeStructure, PlotArchitect, PlotOutline
from app.services.relationship_builder import RelationshipBuilder
from app.services.scene_engine import SceneEngine
from app.services.scene_engine.resolution import SceneArchive
from app.services.world_builder import WorldBuilder, WorldBuilderSession, WorldState


class PipelineStage(str, Enum):
    WORLD = "world"
    CHARACTERS = "characters"
    RELATIONSHIPS = "relationships"
    PLOT = "plot"
    SCENES = "scenes"
    CANON = "canon"
    WRITING = "writing"
    DONE = "done"


@dataclass
class PipelineConfig:
    seed_idea: str
    lang: str = "zh"
    character_count: int = 5
    narrative_structure: str = "three_act"
    output_format: str = "novel"
    max_rounds_per_scene: int = 15
    auto_refine: bool = True
    adjudicate: bool = True  # run the CANON stage to lock cross-product facts
    session_id: str | None = None


@dataclass
class PipelineEvent:
    stage: str
    type: str
    data: dict[str, Any] = field(default_factory=dict)
    progress: float = 0.0
    session_id: str = ""


_STRUCTURE_MAP: dict[str, NarrativeStructure] = {
    "three_act": NarrativeStructure.THREE_ACT,
    "hero_journey": NarrativeStructure.HERO_JOURNEY,
    "save_the_cat": NarrativeStructure.SAVE_THE_CAT,
    "qi_cheng_zhuan_he": NarrativeStructure.QI_CHENG_ZHUAN_HE,
}

_AUTO_ANSWER_PROMPT_ZH = """\
你是一个创意写作助手，正在帮助构建一个故事世界。
根据以下种子创意，为世界构建问题提供一个富有创意、详细的回答。
你的回答应该扩展种子创意，增加具体细节，使世界更加丰富生动。
直接回答问题，不要解释你在做什么。回答长度适中（2-4句话）。"""

_AUTO_ANSWER_PROMPT_EN = """\
You are a creative writing assistant helping to build a story world.
Based on the seed idea below, provide a creative and detailed answer to the world-building question.
Your answer should expand on the seed idea, adding specific details to make the world richer.
Answer the question directly without explaining what you are doing. Keep answers moderate length (2-4 sentences)."""


class PipelineOrchestrator:
    """Runs the full story generation pipeline autonomously."""

    def __init__(self, llm: LLMClient, memory: MemoryManager) -> None:
        self._llm = llm
        self._memory = memory
        self._world_builder = WorldBuilder(llm, memory)
        self._char_manager = CharacterManager(llm, memory)
        self._rel_builder = RelationshipBuilder(llm, memory)
        self._plot_architect = PlotArchitect(llm, memory)
        self._scene_engine = SceneEngine(llm, memory)
        self._narrative_writer = NarrativeWriter(llm, memory)
        self._canon_adjudicator = CanonAdjudicator(llm)

    def run(self, config: PipelineConfig) -> AsyncIterator[PipelineEvent]:
        """Execute the full pipeline, yielding events as progress is made."""
        return self._run_pipeline(config)

    async def _run_pipeline(self, config: PipelineConfig) -> AsyncIterator[PipelineEvent]:
        lang = Lang.ZH if config.lang == "zh" else Lang.EN
        set_lang(lang)

        session_id = config.session_id or str(uuid.uuid4())
        state = await self._load_state(session_id)
        self._hydrate_state(session_id, state)

        try:
            if not state.get("world_done"):
                async for event in self._stage_world(config, session_id, state):
                    yield event

            if not state.get("characters_done"):
                async for event in self._stage_characters(config, session_id, state):
                    yield event

            if not state.get("relationships_done"):
                async for event in self._stage_relationships(config, session_id, state):
                    yield event

            if not state.get("plot_done"):
                async for event in self._stage_plot(config, session_id, state):
                    yield event

            if not state.get("scenes_done"):
                async for event in self._stage_scenes(config, session_id, state):
                    yield event

            if config.adjudicate and not state.get("canon_done"):
                async for event in self._stage_canon(config, session_id, state):
                    yield event

            if not state.get("writing_done"):
                async for event in self._stage_writing(config, session_id, state):
                    yield event

            yield PipelineEvent(
                stage=PipelineStage.DONE,
                type="completed",
                data={"session_id": session_id},
                progress=1.0,
                session_id=session_id,
            )

        except LLMError as exc:
            yield PipelineEvent(
                stage=state.get("current_stage", PipelineStage.WORLD),
                type="error",
                data={"code": exc.code, "message": str(exc)},
                progress=state.get("progress", 0.0),
                session_id=session_id,
            )

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
        archives: list[SceneArchive] = []

        for idx, scene_spec in enumerate(all_scenes):
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
            archives.append(archive)
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

        state["archives"] = archives
        state["scenes_done"] = True
        state["progress"] = 0.75
        self._persist_artifact(
            session_id, "archives", {"items": [cp.archive_to_dict(a) for a in archives]}
        )
        await self._save_state(session_id, state)

        yield PipelineEvent(
            stage=PipelineStage.SCENES,
            type="completed",
            data={"scenes_completed": len(archives)},
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
        options = WritingOptions(
            format=config.output_format,
            canonical_facts=state.get("canonical_facts"),
        )

        output: WrittenOutput = await self._narrative_writer.convert(
            scene_archives=archives,
            characters=characters,
            options=options,
            plot_outline=outline,
            world_summary=world_summary,
            selected_title_index=0,
        )

        state["output"] = output
        state["writing_done"] = True
        state["progress"] = 1.0
        await self._save_state(session_id, state)

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
            },
            progress=1.0,
            session_id=session_id,
        )

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

    async def _load_state(self, session_id: str) -> dict[str, Any]:
        try:
            entry = self._memory.openviking.read_entry(f"pipeline/sessions/{session_id}/state")
            return json.loads(entry.l2)
        except Exception:
            return {}

    async def _save_state(self, session_id: str, state: dict[str, Any]) -> None:
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
