"""Narrative writing and guardian-check pipeline stages."""

from __future__ import annotations

from pathlib import Path

from rich import box
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.table import Table

from app.cli.console import console
from app.cli.display import _chapter_word_count_target, _format_world_summary, _progress
from app.cli.session import CliSession, _save_cli_session
from app.core.i18n import Lang, get_lang, t
from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.memory import MemoryManager
from app.services.narrative_writer import (
    NarrativeWriter, WritingOptions, WrittenOutput,
    TitleGenerator, ChapterPlanner, NovelWriter, PostProcessor,
)
from app.services.plot_architect import PlotOutline, SceneSpec
from app.services.scene_engine.resolution import SceneArchive
from app.services.story_guardian import GuardianResult, Severity, StoryGuardian, Verdict
from app.services.world_builder import WorldState

OUTPUT_DIR = Path.home() / "amphoreus" / "output"


async def _narrative_writing_pipeline(
    llm: LLMClient, memory: MemoryManager, session: CliSession,
    characters: list[CharacterProfile], archives: dict[str, SceneArchive],
    outline: PlotOutline | None = None, world: WorldState | None = None,
) -> str:
    """Narrative writing pipeline with title selection, chapter plan display,
    and chapter-by-chapter writing progress."""
    console.print(Rule(f"[bold cyan]{t('writer.title')}[/]"))

    scene_archives = list(archives.values())
    if not scene_archives:
        console.print(f"[yellow]{t('writer.no_archives')}[/]")
        return ""

    lang = get_lang()
    world_summary = _format_world_summary(world)

    # ------------------------------------------------------------------
    # Step 1 — Title generation
    # ------------------------------------------------------------------
    console.print()
    with _progress() as p:
        p.add_task(description=f"[yellow]{t('writer.generating_titles')}[/]")
        tg = TitleGenerator(llm)
        title_candidates = await tg.generate_titles(world_summary, characters, outline)

    if not title_candidates:
        title_candidates = [session.seed_idea or t("writer.default_title")]

    # ------------------------------------------------------------------
    # Step 2 — Title selection
    # ------------------------------------------------------------------
    console.print()
    header = "书名候选" if lang == Lang.ZH else "Title Candidates"
    console.print(f"[bold cyan]{header}[/]")

    title_table = Table(box=box.SIMPLE)
    title_table.add_column("#", style="dim")
    title_table.add_column("书名" if lang == Lang.ZH else "Title", style="bold")
    for i, candidate in enumerate(title_candidates, 1):
        title_table.add_row(str(i), candidate)
    console.print(title_table)
    console.print()

    while True:
        choice = Prompt.ask(
            f"[bold cyan]{t('writer.select_title')}[/]", default="1"
        )
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(title_candidates):
                selected_title = title_candidates[idx]
                break
        except ValueError:
            pass
        invalid = "无效选择" if lang == Lang.ZH else "Invalid choice"
        console.print(f"[red]{invalid}[/]")

    selected_label = "已选择" if lang == Lang.ZH else "Selected"
    console.print(f"[green]✓ {selected_label}: {selected_title}[/]")

    # ------------------------------------------------------------------
    # Step 3 — Chapter planning
    # ------------------------------------------------------------------
    console.print()
    with _progress() as p:
        p.add_task(description=f"[yellow]{t('writer.planning_chapters')}[/]")
        cp = ChapterPlanner(llm)
        if outline is not None:
            chapter_plan = await cp.plan_chapters(outline, characters)
        else:
            chapter_plan = NarrativeWriter._fallback_chapter_plan(scene_archives)

    if chapter_plan.chapters:
        console.print()
        plan_table = Table(
            box=box.ROUNDED,
            title=t("writer.chapter_plan"),
        )
        ch_col = "章节" if lang == Lang.ZH else "Chapter"
        title_col = "标题" if lang == Lang.ZH else "Title"
        scenes_col = "场景数" if lang == Lang.ZH else "Scenes"
        summary_col = "概述" if lang == Lang.ZH else "Summary"
        plan_table.add_column(ch_col, style="cyan bold")
        plan_table.add_column(title_col, style="bold")
        plan_table.add_column(scenes_col, style="yellow")
        plan_table.add_column(summary_col, style="dim")

        for ch in chapter_plan.chapters:
            plan_table.add_row(
                str(ch.number),
                ch.title,
                str(len(ch.scene_ids)),
                ch.summary[:80] + ("..." if len(ch.summary) > 80 else ""),
            )
        console.print(plan_table)
        console.print()

    # ------------------------------------------------------------------
    # Step 4 — Chapter-by-chapter writing with per-chapter progress
    # ------------------------------------------------------------------
    options = WritingOptions(
        format="novel",
        narrative_voice="third_person_limited",
        enhance=True,
        chapter_title=selected_title,
    )

    scene_specs: dict[str, SceneSpec] = {}
    if outline is not None:
        for act in outline.acts:
            for scene in act.scenes:
                scene_specs[scene.id] = scene

    novel_writer = NovelWriter(llm)
    post_processor = PostProcessor()
    archive_by_id = {a.scene_id: a for a in scene_archives}
    char_by_id = {c.id: c for c in characters}
    written_chapters: list[str] = []

    for i, spec in enumerate(chapter_plan.chapters):
        if lang == Lang.ZH:
            progress_label = f"正在写作 第{spec.number}章 {spec.title}..."
        else:
            progress_label = f"Writing Chapter {spec.number}: {spec.title}..."

        with _progress() as p:
            p.add_task(description=f"[yellow]{progress_label}[/]")

            scene_logs = NovelWriter._build_chapter_scene_logs(
                spec, archive_by_id, char_by_id,
                scene_specs if scene_specs else None,
            )

            prev_summary = chapter_plan.chapters[i - 1].summary if i > 0 else ""
            next_summary = (
                chapter_plan.chapters[i + 1].summary
                if i < len(chapter_plan.chapters) - 1
                else ""
            )

            word_count_target = _chapter_word_count_target(chapter_plan.is_short_story)

            try:
                chapter_prose = await novel_writer._generate_chapter(
                    spec=spec,
                    scene_logs=scene_logs,
                    prev_summary=prev_summary,
                    next_summary=next_summary,
                    word_count_target=word_count_target,
                    options=options,
                )
                if options.enhance:
                    chapter_prose = await novel_writer._enhance_prose(chapter_prose)
            except Exception as e:
                err_msg = "章节写作失败" if lang == Lang.ZH else "Chapter writing failed"
                console.print(f"[red]{err_msg}: {e}[/]")
                if not options.enhance:
                    continue
                # Retry without enhancement
                retry_msg = "重试中..." if lang == Lang.ZH else "Retrying..."
                console.print(f"[dim]{retry_msg}[/]")
                fallback_opts = WritingOptions(
                    format=options.format,
                    narrative_voice=options.narrative_voice,
                    enhance=False,
                    chapter_title=options.chapter_title,
                )
                try:
                    chapter_prose = await novel_writer._generate_chapter(
                        spec=spec,
                        scene_logs=scene_logs,
                        prev_summary=prev_summary,
                        next_summary=next_summary,
                        word_count_target=word_count_target,
                        options=fallback_opts,
                    )
                except Exception as e2:
                    still_failed = "仍然失败" if lang == Lang.ZH else "Still failed"
                    console.print(f"[red]{still_failed}: {e2}[/]")
                    continue

        chapter_prose = post_processor.process(chapter_prose)
        written_chapters.append(chapter_prose)

    if not written_chapters:
        none_written = "没有写出任何章节。" if lang == Lang.ZH else "No chapters were written."
        console.print(f"[red]{none_written}[/]")
        return ""

    # ------------------------------------------------------------------
    # Step 5 — Assemble, display, export
    # ------------------------------------------------------------------
    content = NarrativeWriter._assemble_novel(
        selected_title, chapter_plan, written_chapters,
    )

    total_words = sum(len(p.split()) for p in written_chapters)

    output = WrittenOutput(
        content=content,
        format="novel",
        word_count=total_words,
        scene_count=len(scene_archives),
        title=selected_title,
        title_candidates=title_candidates,
        export_formats=["md", "txt"],
    )

    complete = "写作完成！" if lang == Lang.ZH else "Writing complete!"
    words_label = "字" if lang == Lang.ZH else "words"
    scenes_label = "场" if lang == Lang.ZH else "scenes"
    console.print(
        f"[green]{complete}[/] [dim]{output.word_count} {words_label}, "
        f"{output.scene_count} {scenes_label}[/]"
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in selected_title)[:50]
    filename = f"{safe_name}.md"
    output_path = OUTPUT_DIR / filename

    export_writer = NarrativeWriter(llm, memory)
    export_writer.export(output, "md", str(output_path))
    session.output_path = str(output_path)
    _save_cli_session(session)

    saved_to = "已保存到" if lang == Lang.ZH else "Saved to"
    console.print(f"[green]{saved_to}: {output_path}[/]")

    view_label = "查看输出？" if lang == Lang.ZH else "View output?"
    view = Confirm.ask(f"[bold cyan]{view_label}[/]", default=False)
    if view:
        preview = output.content[:2000] + ("..." if len(output.content) > 2000 else "")
        preview_title = "章节预览" if lang == Lang.ZH else "Chapter Preview"
        console.print(Panel(Markdown(preview), title=f"[bold]{preview_title}[/]", box=box.HEAVY))

    return str(output_path)


async def _guardian_check(
    guardian: StoryGuardian, proposed_change: str,
    affected_characters: list[str], world_id: str | None = None,
) -> bool:
    checking = "正在通过故事守护者检查..." if get_lang() == Lang.ZH else "Checking through Story Guardian..."
    console.print(f"[yellow]{checking}[/]")

    try:
        result: GuardianResult = await guardian.evaluate(
            proposed_plot=proposed_change, affected_characters=affected_characters, world_id=world_id,
        )
    except Exception as e:
        failed = "守护者检查失败（非致命）" if get_lang() == Lang.ZH else "Guardian check failed (non-critical)"
        console.print(f"[yellow]{failed}: {e}[/]")
        return True

    if result.verdict == Verdict.APPROVED:
        approved = "守护者：已批准，无问题。" if get_lang() == Lang.ZH else "Guardian: Approved with no issues."
        console.print(f"[green]{approved}[/]")
        return True

    review_title = "守护者审查" if get_lang() == Lang.ZH else "Guardian Review"
    table = Table(box=box.SIMPLE, title=review_title)
    severity_l = "严重度" if get_lang() == Lang.ZH else "Severity"
    dimension_l = "维度" if get_lang() == Lang.ZH else "Dimension"
    desc_l = "描述" if get_lang() == Lang.ZH else "Description"
    suggestion_l = "建议" if get_lang() == Lang.ZH else "Suggestion"
    table.add_column(severity_l, style="bold")
    table.add_column(dimension_l)
    table.add_column(desc_l)
    table.add_column(suggestion_l)

    for issue in result.issues:
        severity_style = {
            Severity.CRITICAL: "red bold",
            Severity.WARNING: "yellow bold",
            Severity.SUGGESTION: "dim",
        }.get(issue.severity, "white")

        table.add_row(
            f"[{severity_style}]{issue.severity.value.upper()}[/]",
            issue.dimension,
            issue.description[:80] + ("..." if len(issue.description) > 80 else ""),
            issue.suggestion[:60] + ("..." if len(issue.suggestion) > 60 else ""),
        )
    console.print(table)

    if result.verdict == Verdict.REJECTED:
        rejected = "提案被拒绝：发现严重问题。" if get_lang() == Lang.ZH else "PROPOSAL REJECTED: Critical issues found."
        console.print(f"[red bold]{rejected}[/]")
        if result.can_override:
            override_label = "强制继续？" if get_lang() == Lang.ZH else "Override and proceed anyway?"
            return Confirm.ask(f"[bold yellow]{override_label}[/]", default=False)
        return False

    if result.verdict == Verdict.WARNING:
        warning_label = "提案有警告。继续？" if get_lang() == Lang.ZH else "Proposal has warnings. Proceed?"
        console.print("[yellow]⚠[/]")
        return Confirm.ask(f"[bold yellow]{warning_label}[/]", default=True)

    return True
