"""CLI orchestration entry point."""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import datetime

from rich import box
from rich.prompt import Prompt
from rich.rule import Rule
from rich.table import Table

from app.cli.console import console
from app.cli.display import (
    _confirm_api_keys, _select_mode, _show_banner, _show_language_selection,
)
from app.cli.pipelines_plot import _plot_architecture_pipeline, _scene_execution_pipeline
from app.cli.pipelines_story import _narrative_writing_pipeline
from app.cli.pipelines_world import (
    _character_generation_pipeline, _relationship_pipeline,
    _upload_document_pipeline, _world_building_pipeline,
)
from app.cli.session import CliSession, _list_saved_sessions, _save_cli_session
from app.core.config import get_settings
from app.core.i18n import Lang, get_lang, t
from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.character_manager import CharacterManager
from app.services.memory import MemoryManager
from app.services.world_builder import WorldBuilder, WorldState


async def async_main() -> None:
    _show_language_selection()
    _show_banner()
    _confirm_api_keys()

    settings = get_settings()
    llm = LLMClient()
    memory = MemoryManager(settings)
    await memory.initialize()

    mode = _select_mode()
    if mode in ("q", "Q"):
        console.print(f"[yellow]{t('general.goodbye')}[/]")
        return

    cli_session = CliSession(
        session_id=str(uuid.uuid4()),
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
    )

    world: WorldState | None = None
    characters: list[CharacterProfile] = []

    # ── Mode 1: World building ────────────────────────────────────
    if mode == "1":
        console.print()
        idea_prompt = "输入你的故事 idea（一句话）" if get_lang() == Lang.ZH else "Enter your story idea (one sentence)"
        seed_idea = Prompt.ask(f"[bold cyan]{idea_prompt}[/]")
        cli_session.seed_idea = seed_idea
        _save_cli_session(cli_session)
        world = await _world_building_pipeline(llm, memory, cli_session, seed_idea)

    # ── Mode 2: Upload document ───────────────────────────────────
    elif mode == "2":
        try:
            world = await _upload_document_pipeline(llm)
        except Exception:
            fallback = "回退到基于 idea 的世界构建。" if get_lang() == Lang.ZH else "Falling back to idea-based world building."
            console.print(f"[yellow]{fallback}[/]")
            idea_prompt = "输入你的故事 idea（一句话）" if get_lang() == Lang.ZH else "Enter your story idea (one sentence)"
            seed_idea = Prompt.ask(f"[bold cyan]{idea_prompt}[/]")
            cli_session.seed_idea = seed_idea
            _save_cli_session(cli_session)
            world = await _world_building_pipeline(llm, memory, cli_session, seed_idea)

    # ── Mode 3: Continue project ──────────────────────────────────
    elif mode == "3":
        saved = _list_saved_sessions()
        if not saved:
            no_sessions = "没有可恢复的会话，开始新建。" if get_lang() == Lang.ZH else "No saved sessions. Starting new."
            console.print(f"[yellow]{no_sessions}[/]")
            idea_prompt = "输入你的故事 idea（一句话）" if get_lang() == Lang.ZH else "Enter your story idea (one sentence)"
            seed_idea = Prompt.ask(f"[bold cyan]{idea_prompt}[/]")
            cli_session.seed_idea = seed_idea
            _save_cli_session(cli_session)
            world = await _world_building_pipeline(llm, memory, cli_session, seed_idea)
        else:
            saved_sessions = "已保存的会话" if get_lang() == Lang.ZH else "Saved sessions"
            console.print(f"[bold cyan]{saved_sessions}:[/]")
            for i, s in enumerate(saved, 1):
                idea = s.seed_idea[:60] or "Unknown"
                console.print(f"  {i}. {idea} [dim]({s.updated_at[:19]})[/]")
            console.print()

            pick = "选择一个会话（编号，或 'n' 新建）" if get_lang() == Lang.ZH else "Pick a session (number, or 'n' for new)"
            choice = Prompt.ask(f"[bold cyan]{pick}[/]", default="1")
            if choice.lower() == "n":
                idea_prompt = "输入你的故事 idea（一句话）" if get_lang() == Lang.ZH else "Enter your story idea (one sentence)"
                seed_idea = Prompt.ask(f"[bold cyan]{idea_prompt}[/]")
                cli_session.seed_idea = seed_idea
                _save_cli_session(cli_session)
                world = await _world_building_pipeline(llm, memory, cli_session, seed_idea)
            else:
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(saved):
                        cli_session = saved[idx]
                        builder = WorldBuilder(llm, memory)
                        if cli_session.world_session_id:
                            world = await builder.finalize_world(cli_session.world_session_id)
                            char_mgr = CharacterManager(llm, memory)
                            for cid in cli_session.character_ids:
                                c = await char_mgr.get_character(cid)
                                if c is not None:
                                    characters.append(c)
                except ValueError:
                    invalid = "无效选择" if get_lang() == Lang.ZH else "Invalid choice"
                    console.print(f"[red]{invalid}[/]")
                    return

    if world is None:
        no_world = "世界状态为空，无法继续。" if get_lang() == Lang.ZH else "World state is empty. Cannot proceed."
        console.print(f"[red]{no_world}[/]")
        return

    # ── Character generation ──────────────────────────────────────
    if not characters:
        characters = await _character_generation_pipeline(llm, memory, cli_session, world)
    if not characters:
        no_chars = "无可用角色，无法继续。" if get_lang() == Lang.ZH else "No characters available. Cannot proceed."
        console.print(f"[red]{no_chars}[/]")
        return

    # ── Relationships ─────────────────────────────────────────────
    relationships = await _relationship_pipeline(llm, memory, characters, world)

    # ── Plot ──────────────────────────────────────────────────────
    outline = await _plot_architecture_pipeline(llm, memory, cli_session, world, characters)
    if not outline.acts:
        no_plot = "剧情大纲为空，无法继续。" if get_lang() == Lang.ZH else "Plot outline is empty. Cannot proceed."
        console.print(f"[red]{no_plot}[/]")
        return

    # ── Scene execution ───────────────────────────────────────────
    archives = await _scene_execution_pipeline(llm, memory, cli_session, outline, characters)

    # ── Narrative writing ─────────────────────────────────────────
    if archives:
        output_path = await _narrative_writing_pipeline(
                llm, memory, cli_session, characters, archives,
                outline=outline, world=world,
            )
    else:
        output_path = ""

    cli_session.last_step = "complete"
    _save_cli_session(cli_session)

    # ── Final summary ─────────────────────────────────────────────
    console.print()
    complete_l = "管道完成" if get_lang() == Lang.ZH else "PIPELINE COMPLETE"
    console.print(Rule(f"[bold green]{complete_l}[/]"))
    summary_title = "会话摘要" if get_lang() == Lang.ZH else "Session Summary"
    summary = Table(box=box.HEAVY, title=summary_title)
    metric_l = "指标" if get_lang() == Lang.ZH else "Metric"
    value_l = "值" if get_lang() == Lang.ZH else "Value"
    summary.add_column(metric_l, style="bold cyan")
    summary.add_column(value_l)
    seed_l = "种子 Idea" if get_lang() == Lang.ZH else "Seed Idea"
    chars_l = "角色" if get_lang() == Lang.ZH else "Characters"
    rels_l = "关系" if get_lang() == Lang.ZH else "Relationships"
    acts_l = "幕" if get_lang() == Lang.ZH else "Acts"
    scenes_done = "已执行场景" if get_lang() == Lang.ZH else "Scenes Executed"
    output_l = "输出" if get_lang() == Lang.ZH else "Output"
    session_l = "会话 ID" if get_lang() == Lang.ZH else "Session ID"
    summary.add_row(seed_l, cli_session.seed_idea[:60] + ("..." if len(cli_session.seed_idea) > 60 else ""))
    summary.add_row(chars_l, str(len(characters)))
    summary.add_row(rels_l, str(len(relationships)))
    summary.add_row(acts_l, str(len(outline.acts)))
    summary.add_row(scenes_done, str(len(archives)))
    summary.add_row(output_l, str(output_path) if output_path else "N/A")
    summary.add_row(session_l, cli_session.session_id[:8] + "...")
    console.print(summary)
    console.print()

    await memory.close()


def main() -> None:
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        interrupted = "用户中断。再见！" if get_lang() == Lang.ZH else "Interrupted by user. Goodbye!"
        console.print(f"\n[yellow]{interrupted}[/]")
        sys.exit(0)
    except Exception as exc:
        console.print(f"\n[red bold]Error:[/] {exc}")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)
