"""NarrativeWriter — facade that orchestrates the full narrative pipeline."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

from app.core.i18n import get_lang, Lang, t
from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.memory import MemoryManager
from app.services.plot_architect import PlotOutline, SceneSpec
from app.services.scene_engine.resolution import SceneArchive

from .canon_verifier import verify
from .chapter_planner import ChapterPlanner
from .cliche_scanner import scan
from .novel_writer import NovelWriter, _flatten_scenes
from .post_processor import PostProcessor
from .screenplay_writer import ScreenplayWriter
from .prop_lifecycle import build_prop_lifecycle_report
from .reader_sim import build_reader_sim_report
from .token_budget import BudgetReport
from .tension_scorer import build_tension_report
from .title_generator import TitleGenerator
from .types import ChapterPlan, ChapterSpec, WritingOptions, WrittenOutput, count_words


class NarrativeWriter:
    """Facade that orchestrates the full narrative pipeline.

    For novels:
      TitleGenerator -> ChapterPlanner -> NovelWriter (chapter-by-chapter)
      -> PostProcessor -> assembly with i18n
    For screenplays:
      ScreenplayWriter (per-scene) -> assembly with i18n

    Also handles export to file and format metadata queries.
    """

    def __init__(self, llm: LLMClient, memory: MemoryManager) -> None:
        self._llm = llm
        self._memory = memory
        self._title_gen = TitleGenerator(llm)
        self._planner = ChapterPlanner(llm)
        self._novel_writer = NovelWriter(llm)
        self._screenplay_writer = ScreenplayWriter(llm)
        self._post_processor = PostProcessor()

    async def convert(
        self,
        scene_archives: list[SceneArchive],
        characters: list[CharacterProfile],
        options: WritingOptions,
        plot_outline: PlotOutline | None = None,
        world_summary: str = "",
        selected_title_index: int = 0,
    ) -> WrittenOutput:
        """Convert scene archives to the requested format.

        plot_outline: required for novel chapter planning; optional otherwise.
        world_summary: used for title generation; can be empty string.
        selected_title_index: which title candidate to use (default: first).
        """
        if not scene_archives:
            raise ValueError("At least one scene archive is required")
        if not characters:
            raise ValueError("At least one character profile is required")
        if options.format not in ("novel", "screenplay"):
            raise ValueError(
                f"Unsupported format '{options.format}'. "
                "Use 'novel' or 'screenplay'."
            )

        # --- Step 1: Generate title candidates ---
        title_candidates = await self._title_gen.generate_titles(
            world_summary, characters, plot_outline
        )
        selected_title = (
            title_candidates[selected_title_index]
            if title_candidates and selected_title_index < len(title_candidates)
            else t("writer.default_title")
        )

        if options.format == "novel":
            result = await self._convert_novel(
                scene_archives=scene_archives,
                characters=characters,
                options=options,
                plot_outline=plot_outline,
                selected_title=selected_title,
                title_candidates=title_candidates,
            )
        else:
            result = await self._convert_screenplay(
                scene_archives=scene_archives,
                characters=characters,
                options=options,
                plot_outline=plot_outline,
                selected_title=selected_title,
                title_candidates=title_candidates,
            )

        return result

    async def _convert_novel(
        self,
        scene_archives: list[SceneArchive],
        characters: list[CharacterProfile],
        options: WritingOptions,
        plot_outline: PlotOutline | None,
        selected_title: str,
        title_candidates: list[str],
    ) -> WrittenOutput:
        """Full novel pipeline: plan chapters, write chapter by chapter, assemble."""
        scene_specs: dict[str, SceneSpec] = {}
        if plot_outline is not None:
            scene_specs = _flatten_scenes(plot_outline)

        # --- Step 2: Plan chapters ---
        if plot_outline is not None:
            chapter_plan = await self._planner.plan_chapters(plot_outline, characters)
        else:
            chapter_plan = self._fallback_chapter_plan(scene_archives)

        # --- Step 3: Write chapters ---
        budget_acc: list = []
        chapters = await self._novel_writer.write_chapters(
            chapter_plan=chapter_plan,
            scene_archives=scene_archives,
            characters=characters,
            options=options,
            scene_specs=scene_specs if scene_specs else None,
            budget_acc=budget_acc,
        )

        # --- Step 4: Post-process each chapter ---
        chapters = [self._post_processor.process(ch) for ch in chapters]

        # --- Step 5: Assemble ---
        content = self._assemble_novel(selected_title, chapter_plan, chapters)

        result = WrittenOutput(
            content=content,
            format="novel",
            word_count=count_words(content),
            scene_count=len(scene_archives),
            title=selected_title,
            title_candidates=title_candidates,
            export_formats=["md", "txt"],
        )
        # --- Step 6: Post-generation diagnostics (zero-LLM, synchronous) ---
        result.cliche_report = scan(result.content)
        if options.canonical_facts is not None:
            result.canon_report = verify(
                result.content, options.canonical_facts, "novel"
            )
        if options.score_tension:
            result.tension_report = build_tension_report(scene_archives, chapter_plan)
        if options.extract_props:
            result.prop_lifecycle_report = await build_prop_lifecycle_report(
                self._llm, result.content
            )
        if options.simulate_reader:
            result.reader_sim_report = await build_reader_sim_report(
                self._llm, result.content, chapter_plan
            )
        if budget_acc:
            result.budget_report = BudgetReport(
                per_chapter=budget_acc,
                any_over=any(cb.over_by > 0 for cb in budget_acc),
                total_tokens=sum(cb.total_tokens for cb in budget_acc),
            )
        return result

    async def _convert_screenplay(
        self,
        scene_archives: list[SceneArchive],
        characters: list[CharacterProfile],
        options: WritingOptions,
        plot_outline: PlotOutline | None,
        selected_title: str,
        title_candidates: list[str],
    ) -> WrittenOutput:
        """Screenplay pipeline: act planning, per-scene conversion, post-processing, assembly."""
        scene_specs: dict[str, SceneSpec] = {}
        if plot_outline is not None:
            scene_specs = _flatten_scenes(plot_outline)

        # Plan acts (reuse ChapterPlanner — chapters become acts in screenplay context)
        if plot_outline is not None:
            act_plan = await self._planner.plan_chapters(plot_outline, characters)
        else:
            act_plan = self._fallback_chapter_plan(scene_archives)

        output = await self._screenplay_writer.convert(
            scene_archives=scene_archives,
            characters=characters,
            options=options,
            act_plan=act_plan,
            title=selected_title,
            title_candidates=title_candidates,
            scene_specs=scene_specs if scene_specs else None,
        )

        # Post-process with screenplay-specific rules
        output.content = PostProcessor.normalize_screenplay(output.content, characters)
        output.word_count = count_words(output.content)

        # Post-generation diagnostics (zero-LLM, synchronous)
        output.cliche_report = scan(output.content)
        if options.canonical_facts is not None:
            output.canon_report = verify(
                output.content, options.canonical_facts, "screenplay"
            )

        return output

    # ------------------------------------------------------------------
    # Fallback: no plot outline
    # ------------------------------------------------------------------

    @staticmethod
    def _fallback_chapter_plan(
        scene_archives: list[SceneArchive],
    ) -> ChapterPlan:
        """Build a minimal chapter plan from archives when no plot outline exists.

        Groups every 3 scenes into one numbered chapter.
        """
        specs: list[ChapterSpec] = []
        chunk_size = 3
        lang = get_lang()

        for i in range(0, len(scene_archives), chunk_size):
            batch = scene_archives[i : i + chunk_size]
            chapter_num = i // chunk_size + 1
            scene_ids = [a.scene_id for a in batch]

            if lang == Lang.ZH:
                title = f"第{chapter_num}章"
            else:
                title = f"Chapter {chapter_num}"

            specs.append(
                ChapterSpec(
                    number=chapter_num,
                    title=title,
                    scene_ids=scene_ids,
                    summary="",
                )
            )

        if not specs:
            specs.append(
                ChapterSpec(
                    number=1,
                    title=t("writer.default_title"),
                    scene_ids=[],
                    summary="",
                )
            )

        return ChapterPlan(chapters=specs)

    # ------------------------------------------------------------------
    # Assembly
    # ------------------------------------------------------------------

    @staticmethod
    def _assemble_novel(
        title: str,
        chapter_plan: ChapterPlan,
        chapter_prose: list[str],
    ) -> str:
        """Combine chapter prose into a single markdown document.

        Title and chapter headings come from TitleGenerator and ChapterPlanner.
        All static text uses i18n t().
        """
        lang = get_lang()
        parts: list[str] = [f"# {title}\n"]

        for spec, prose in zip(chapter_plan.chapters, chapter_prose):
            if lang == Lang.ZH:
                heading = f"## 第{spec.number}章 {spec.title}"
            else:
                heading = f"## Chapter {spec.number}: {spec.title}"
            parts.append(f"\n{heading}\n\n{prose}")

        return "".join(parts)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export(
        self, output: WrittenOutput, fmt: str, filepath: str | Path
    ) -> None:
        """Write a WrittenOutput to disk in the requested export format.

        Supported format conversions:
          novel      -> md (Markdown, as-is)
          novel      -> txt (Plain text, stripped Markdown)
          screenplay -> txt (Plain text)
          screenplay -> fountain (Fountain format)
        """
        content = output.content
        ext = fmt.lower()

        if ext == "txt":
            if output.format == "novel":
                content = self._strip_markdown(content)
        elif ext == "fountain":
            if output.format != "screenplay":
                raise ValueError(
                    "Fountain export is only supported for screenplay format"
                )
            content = self._to_fountain(content)
        elif ext == "md":
            if output.format != "novel":
                raise ValueError(
                    "Markdown export is only supported for novel format"
                )
        else:
            raise ValueError(
                f"Unsupported export format '{fmt}'. "
                f"Supported: {', '.join(self._export_formats(output.format))}"
            )

        Path(filepath).write_text(content, encoding="utf-8")

    def export_to_temp(
        self, output: WrittenOutput, fmt: str
    ) -> str:
        """Export to a temporary file and return the file path."""
        suffix = f".{fmt}"
        with tempfile.NamedTemporaryFile(
            suffix=suffix, mode="w", encoding="utf-8", delete=False
        ) as f:
            self.export(output, fmt, f.name)
            return f.name

    @staticmethod
    def _export_formats(writing_format: str) -> list[str]:
        """Return list of export formats valid for the given writing format."""
        if writing_format == "novel":
            return ["md", "txt"]
        if writing_format == "screenplay":
            return ["txt", "fountain"]
        return []

    @staticmethod
    def supported_export_formats() -> dict[str, list[str]]:
        """Return mapping of writing format -> available export formats."""
        return {
            "novel": ["md", "txt"],
            "screenplay": ["txt", "fountain"],
        }

    # ------------------------------------------------------------------
    # Internal: format helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_markdown(text: str) -> str:
        """Remove Markdown formatting for plain-text export."""
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
        return text.strip()

    @staticmethod
    def _to_fountain(screenplay_text: str) -> str:
        """Convert basic screenplay text to Fountain format.

        Fountain is a plain-text markup language for screenplays.
        Since the screenplay output already uses standard conventions,
        this is primarily a normalization pass.
        """
        lines = screenplay_text.split("\n")
        fountain_lines: list[str] = []

        for line in lines:
            stripped = line.strip()

            if stripped.upper().startswith(("INT.", "EXT.", "INT/EXT.")):
                fountain_lines.append(stripped.upper())
                continue

            if stripped.isupper() and len(stripped) > 1 and stripped.strip("() ").isupper():
                fountain_lines.append(stripped)
                continue

            if stripped.startswith("(") and stripped.endswith(")"):
                fountain_lines.append(stripped)
                continue

            if not stripped:
                fountain_lines.append("")
                continue

            fountain_lines.append(stripped)

        return "\n".join(fountain_lines)
