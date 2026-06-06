"""Screenplay writer — converts scene logs to standard screenplay format with act structure."""

from __future__ import annotations

import re

from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.plot_architect import SceneSpec
from app.services.scene_engine.resolution import SceneArchive

from .prompts import (
    _get_screenplay_system_prompt,
    _get_screenplay_enhance_prompt,
)
from .foreshadowing import render_foreshadowing_block
from .types import ChapterPlan, WritingOptions, WrittenOutput, count_words


class ScreenplayWriter:
    """Converts scene logs to standard screenplay format with act structure.

    ZH scene headings use [内景]/[外景]; EN uses [INT.]/[EXT.].
    Acts and scene numbers are applied during assembly (not by the LLM).
    """

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def convert(
        self,
        scene_archives: list[SceneArchive],
        characters: list[CharacterProfile],
        options: WritingOptions,
        act_plan: ChapterPlan,
        title: str,
        title_candidates: list[str],
        scene_specs: dict[str, SceneSpec] | None = None,
    ) -> WrittenOutput:
        """Convert scene archives to screenplay-format text with act structure."""
        char_by_id = {c.id: c for c in characters}
        char_names = "、".join(c.name for c in characters if c.name)
        scene_pages: dict[str, str] = {}
        from app.core.i18n import Lang, get_lang
        lang = get_lang()
        canon_block = ""
        if options.canonical_facts is not None:
            canon_block = options.canonical_facts.render_block("screenplay", lang == Lang.ZH)

        # Screenplay is generated per-scene in a single pass; act_spec.number is
        # not in scope here, so the T0 block is computed once using the first
        # planned act/chapter number as the representative reference point.
        rep_chapter = act_plan.chapters[0].number if act_plan.chapters else 1
        foreshadowing_block = render_foreshadowing_block(
            options.foreshadowing_registry, rep_chapter, lang == Lang.ZH
        )

        for archive in scene_archives:
            location = ""
            if scene_specs and archive.scene_id in scene_specs:
                location = scene_specs[archive.scene_id].location
            scene_log = self._format_scene_log(archive, char_by_id, location)
            formatted = await self._generate_screenplay(
                scene_log, char_names, canon_block, foreshadowing_block
            )
            formatted = self._strip_thinking_tags(formatted)
            if options.enhance:
                formatted = await self._enhance_screenplay(formatted, canon_block)
            formatted = self._ensure_slug_line(formatted, location, lang)
            scene_pages[archive.scene_id] = formatted

        content = self._assemble_screenplay(
            title=title,
            scene_pages=scene_pages,
            act_plan=act_plan,
        )

        return WrittenOutput(
            content=content,
            format="screenplay",
            word_count=count_words(content),
            scene_count=len(scene_archives),
            title=title,
            title_candidates=title_candidates,
            export_formats=["txt", "fountain"],
        )

    # ------------------------------------------------------------------
    # Internal: LLM calls
    # ------------------------------------------------------------------

    async def _generate_screenplay(
        self, scene_log: str, character_names: str = "", canon_block: str = "",
        foreshadowing_block: str = "",
    ) -> str:
        """Send a scene log to the LLM and return screenplay-format text."""
        from app.core.i18n import Lang, get_lang
        messages: list[dict[str, str]] = [
            {"role": "system", "content": _get_screenplay_system_prompt()},
        ]
        if canon_block:
            messages.append({"role": "system", "content": canon_block})
        if foreshadowing_block:
            messages.append({"role": "system", "content": foreshadowing_block})
        if get_lang() == Lang.ZH:
            name_rule = (
                f"场景中的角色名称为：{character_names}。"
                "你必须使用这些中文名称，绝对不能写成拼音或英文大写。"
            ) if character_names else "你必须使用简体中文角色名，绝对不能写成拼音或英文大写。"
            messages.append({"role": "user", "content": name_rule})
        messages.append({"role": "user", "content": scene_log})
        return await self._llm.chat(messages)

    async def _enhance_screenplay(self, text: str, canon_block: str = "") -> str:
        """Second-pass LLM call for formatting consistency."""
        messages: list[dict[str, str]] = [
            {"role": "system", "content": _get_screenplay_enhance_prompt()},
        ]
        if canon_block:
            messages.append({"role": "system", "content": canon_block})
        messages.append({"role": "user", "content": text})
        return await self._llm.chat(messages)

    @staticmethod
    def _has_slug_line(text: str) -> bool:
        """True if the scene page already opens with a [内景]/[外景]/INT/EXT heading."""
        for line in text.lstrip().split("\n"):
            s = line.strip()
            if not s:
                continue
            return bool(re.match(r"^\[?(内景|外景|内景/外景|外景/内景|INT|EXT)", s, re.I))
        return False

    @staticmethod
    def _ensure_slug_line(text: str, location: str, lang) -> str:
        """Prepend a fallback scene heading when the LLM omitted one.

        Guarantees every scene page has a slug line (review found a scene with
        none). Uses the scene spec's location; time-of-day is unknown here, so a
        neutral default is used rather than inventing one.
        """
        if ScreenplayWriter._has_slug_line(text):
            return text
        from app.core.i18n import Lang
        loc = (location or "").strip()
        if lang == Lang.ZH:
            loc = loc or "未指定地点"
            heading = f"[内景] {loc} - 日"
        else:
            loc = loc or "UNSPECIFIED"
            heading = f"[INT.] {loc} - DAY"
        return f"{heading}\n\n{text.lstrip()}"

    @staticmethod
    def _strip_thinking_tags(text: str) -> str:
        """Remove <构思> / <thinking> tags from LLM screenplay output."""
        cleaned = re.sub(r'<构思>.*?</构思>', '', text, flags=re.DOTALL)
        cleaned = re.sub(r'<thinking>.*?</thinking>', '', cleaned, flags=re.DOTALL)
        return cleaned.strip()

    # ------------------------------------------------------------------
    # Internal: formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _format_scene_log(
        archive: SceneArchive,
        char_by_id: dict[str, CharacterProfile],
        location: str = "",
    ) -> str:
        """Format scene rounds into a readable log for screenplay conversion."""
        lines: list[str] = []
        lines.append(f"Scene: {archive.scene_id}")
        if location:
            lines.append(f"Location: {location}")
        lines.append(f"Atmosphere: {archive.final_environment.atmosphere}")
        if archive.final_environment.background_activity:
            lines.append(
                f"Background: {archive.final_environment.background_activity}"
            )
        lines.append("")

        for entry in archive.rounds:
            lines.append(f"Character: {entry.actor_name}")
            if entry.dialogue:
                lines.append(f'Says: "{entry.dialogue}"')
            if entry.action:
                lines.append(f"Does: {entry.action}")
            if entry.inner_thought:
                lines.append(f"[内心] {entry.actor_name}心想：{entry.inner_thought}")
            if entry.emotion:
                lines.append(f"Emotion: {entry.emotion}")
            for reaction in entry.reactions:
                lines.append(
                    f"  {reaction.reactor_name} reacts: {reaction.visible_reaction}"
                )
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _assemble_screenplay(
        title: str,
        scene_pages: dict[str, str],
        act_plan: ChapterPlan,
    ) -> str:
        """Combine formatted scenes into full screenplay with markdown structure.

        Uses the same markdown hierarchy as the novel output:
        # Title → ## Act → ### Scene
        """
        from app.core.i18n import Lang, get_lang
        lang = get_lang()
        parts: list[str] = [f"# {title}", ""]

        global_scene_num = 1

        for act_spec in act_plan.chapters:
            # Skip acts where none of their scene_ids have content
            act_scenes = [sid for sid in act_spec.scene_ids if sid in scene_pages]
            if not act_scenes:
                continue

            if lang == Lang.ZH:
                parts.append(f"## 第{act_spec.number}幕 {act_spec.title}")
            else:
                parts.append(f"## Act {act_spec.number}: {act_spec.title}")
            parts.append("")

            for scene_id in act_scenes:
                scene_text = scene_pages.get(scene_id)
                if scene_text is None:
                    continue

                if lang == Lang.ZH:
                    parts.append(f"### 第{global_scene_num}场")
                else:
                    parts.append(f"### Scene {global_scene_num}")
                parts.append("")
                parts.append(scene_text)
                parts.append("")
                global_scene_num += 1

        return "\n".join(parts)
