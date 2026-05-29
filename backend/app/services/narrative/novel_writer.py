"""Novel writer — converts scene logs to literary prose chapter by chapter."""

from __future__ import annotations

import json
import re
from typing import Any

from app.core.i18n import get_lang, Lang
from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.memory import MemoryManager
from app.services.plot_architect import PlotOutline, SceneSpec
from app.services.scene_engine.resolution import SceneArchive
from app.services.scene_engine.types import EnvironmentUpdate, Reaction, RoundEntry

from .prompts import (
    _get_chapter_write_system_prompt,
    _get_chapter_write_target,
    _get_chapter_write_short_target,
    _get_novel_enhance_prompt,
)
from .types import ChapterPlan, ChapterSpec, WritingOptions


# ---------------------------------------------------------------------------
# Archive parsing helpers
# ---------------------------------------------------------------------------


def _parse_archive_json(l2_content: str) -> SceneArchive:
    """Reconstruct a SceneArchive dataclass from stored JSON."""
    data: dict[str, Any] = json.loads(l2_content)

    rounds: list[RoundEntry] = [
        RoundEntry(
            round_num=r["round_num"],
            actor_id=r["actor_id"],
            actor_name=r["actor_name"],
            dialogue=r.get("dialogue", ""),
            action=r.get("action", ""),
            inner_thought=r.get("inner_thought", ""),
            emotion=r.get("emotion", ""),
            reactions=[
                Reaction(
                    reactor_id=rx["reactor_id"],
                    reactor_name=rx["reactor_name"],
                    visible_reaction=rx.get("visible_reaction", ""),
                    inner_thought=rx.get("inner_thought", ""),
                )
                for rx in r.get("reactions", [])
            ],
        )
        for r in data.get("rounds", [])
    ]

    fe_data = data.get("final_environment", {})
    final_environment = EnvironmentUpdate(
        atmosphere=fe_data.get("atmosphere", ""),
        changes=fe_data.get("changes", []),
        background_activity=fe_data.get("background_activity", ""),
    )

    return SceneArchive(
        scene_id=data["scene_id"],
        rounds=rounds,
        final_environment=final_environment,
        character_changes=data.get("character_changes", {}),
    )


def _load_scene_archive(memory: MemoryManager, scene_id: str) -> SceneArchive:
    """Load a single scene archive from OpenViking and return a SceneArchive."""
    entry = memory.openviking.read_entry(f"story/scenes/{scene_id}")
    return _parse_archive_json(entry.l2)


def _flatten_scenes(outline: PlotOutline) -> dict[str, SceneSpec]:
    """Flatten all SceneSpecs from a PlotOutline into a scene_id -> SceneSpec map."""
    result: dict[str, SceneSpec] = {}
    for act in outline.acts:
        for scene in act.scenes:
            result[scene.id] = scene
    return result


def _extract_chapter_story(raw: str) -> str:
    """Extract content between <story>...</story> tags from an LLM chapter response.

    Falls back to the full response with any <thinking>/<思考> blocks removed.
    """
    story_match = re.search(r"<story>(.*?)</story>", raw, re.DOTALL)
    if story_match:
        return story_match.group(1).strip()
    cleaned = re.sub(r"<thinking>.*?</thinking>", "", raw, flags=re.DOTALL)
    cleaned = re.sub(r"<思考>.*?</思考>", "", cleaned, flags=re.DOTALL)
    return cleaned.strip()


# ---------------------------------------------------------------------------
# Novel writer
# ---------------------------------------------------------------------------


class NovelWriter:
    """Writes novel-format prose chapter by chapter via LLM.

    Each chapter call receives its scene logs, chapter plan metadata, and
    adjacent chapter summaries for transition context.
    """

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def write_chapters(
        self,
        chapter_plan: ChapterPlan,
        scene_archives: list[SceneArchive],
        characters: list[CharacterProfile],
        options: WritingOptions,
        scene_specs: dict[str, SceneSpec] | None = None,
    ) -> list[str]:
        """Write each chapter as prose.  Returns one string per chapter."""
        char_by_id = {c.id: c for c in characters}
        archive_by_id = {a.scene_id: a for a in scene_archives}
        chapters: list[str] = []

        for i, spec in enumerate(chapter_plan.chapters):
            scene_logs = self._build_chapter_scene_logs(
                spec, archive_by_id, char_by_id, scene_specs
            )

            prev_summary = chapter_plan.chapters[i - 1].summary if i > 0 else ""
            next_summary = (
                chapter_plan.chapters[i + 1].summary
                if i < len(chapter_plan.chapters) - 1
                else ""
            )

            word_count_target = (
                _get_chapter_write_short_target()
                if chapter_plan.is_short_story
                else _get_chapter_write_target()
            )

            chapter_prose = await self._generate_chapter(
                spec=spec,
                scene_logs=scene_logs,
                prev_summary=prev_summary,
                next_summary=next_summary,
                word_count_target=word_count_target,
                options=options,
            )

            if options.enhance:
                chapter_prose = await self._enhance_prose(chapter_prose)

            chapters.append(chapter_prose)

        return chapters

    # ------------------------------------------------------------------
    # Internal: chapter LLM call
    # ------------------------------------------------------------------

    async def _generate_chapter(
        self,
        spec: ChapterSpec,
        scene_logs: str,
        prev_summary: str,
        next_summary: str,
        word_count_target: str,
        options: WritingOptions,
    ) -> str:
        """Send a chapter prompt to the LLM and return the prose."""
        voice_label = options.narrative_voice.replace("_", " ")
        system_prompt = _get_chapter_write_system_prompt().format(voice=voice_label)

        lang = get_lang()
        if lang == Lang.ZH:
            user_prompt = (
                f"## 章节信息\n\n"
                f"标题：第{spec.number}章 {spec.title}\n"
                f"概述：{spec.summary}\n"
                f"目标字数：{word_count_target}\n\n"
                f"上一章概述：{prev_summary if prev_summary else '（无）'}\n"
                f"下一章概述：{next_summary if next_summary else '（无）'}\n\n"
                f"## 场景日志\n\n{scene_logs}\n\n"
                f"请写出完整的章节正文。"
            )
        else:
            user_prompt = (
                f"## Chapter Info\n\n"
                f"Title: Chapter {spec.number}: {spec.title}\n"
                f"Summary: {spec.summary}\n"
                f"Target word count: {word_count_target}\n\n"
                f"Previous chapter summary: {prev_summary if prev_summary else '(none)'}\n"
                f"Next chapter summary: {next_summary if next_summary else '(none)'}\n\n"
                f"## Scene Logs\n\n{scene_logs}\n\n"
                f"Write the complete chapter."
            )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        raw = await self._llm.chat(messages)
        return _extract_chapter_story(raw)

    async def _enhance_prose(self, prose: str) -> str:
        """Second-pass LLM call for pacing, sensory depth, and dialogue polish."""
        messages: list[dict[str, str]] = [
            {"role": "system", "content": _get_novel_enhance_prompt()},
            {"role": "user", "content": prose},
        ]
        return await self._llm.chat(messages)

    # ------------------------------------------------------------------
    # Internal: scene log formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _build_chapter_scene_logs(
        spec: ChapterSpec,
        archive_by_id: dict[str, SceneArchive],
        char_by_id: dict[str, CharacterProfile],
        scene_specs: dict[str, SceneSpec] | None,
    ) -> str:
        """Build combined scene logs for a chapter."""
        all_lines: list[str] = []

        for scene_id in spec.scene_ids:
            archive = archive_by_id.get(scene_id)
            if archive is None:
                all_lines.append(f"## Scene: {scene_id} [no archive data]")
                all_lines.append("")
                continue

            sspec = scene_specs.get(scene_id) if scene_specs else None
            if sspec:
                all_lines.append(f"## Scene: {scene_id} - {sspec.title}")
                all_lines.append(f"Location: {sspec.location}")
            else:
                all_lines.append(f"## Scene: {scene_id}")
            all_lines.append(f"Atmosphere: {archive.final_environment.atmosphere}")
            if archive.final_environment.background_activity:
                all_lines.append(
                    f"Background: {archive.final_environment.background_activity}"
                )
            all_lines.append("")

            for entry in archive.rounds:
                all_lines.append(f"--- Round {entry.round_num} ---")
                all_lines.append(f"Actor: {entry.actor_name}")
                if entry.dialogue:
                    all_lines.append(f'Dialogue: "{entry.dialogue}"')
                if entry.action:
                    all_lines.append(f"Action: {entry.action}")
                if entry.inner_thought:
                    all_lines.append(f"Inner thought: {entry.inner_thought}")
                if entry.emotion:
                    all_lines.append(f"Emotion: {entry.emotion}")
                for reaction in entry.reactions:
                    all_lines.append(
                        f"  {reaction.reactor_name} reacts: {reaction.visible_reaction}"
                    )
                    if reaction.inner_thought:
                        all_lines.append(
                            f"    ({reaction.reactor_name} thinks: {reaction.inner_thought})"
                        )
                all_lines.append("")

        return "\n".join(all_lines)
