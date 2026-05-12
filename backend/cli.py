#!/usr/bin/env python3
"""Amphoreus Story Engine — Interactive CLI.

Runs the full story engine pipeline end-to-end:

  1. Language selection (中文 / English)
  2. API key check (with prompt to configure if missing)
  3. Mode selection: new world / upload document / continue project
  4. World building (conversational LLM-guided)
  5. Character generation (with inline editing)
  6. Relationship inference
  7. Plot architecture (structure selection + outline)
  8. Scene execution (round-by-round display)
  9. Narrative writing (novel/screenplay conversion + file export)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from app.core.api_keys import KeyManager
from app.core.config import get_settings
from app.core.i18n import Lang, get_lang, set_lang, t
from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.character_manager import CharacterManager
from app.services.document_parser import DocumentParser, ParsedDocument
from app.services.memory import MemoryManager
from app.services.narrative_writer import NarrativeWriter, WritingOptions
from app.services.plot_architect import NarrativeStructure, PlotArchitect, PlotOutline, SceneSpec
from app.services.relationship_builder import Relationship, RelationshipBuilder
from app.services.scene_engine import SceneEngine
from app.services.scene_engine.resolution import SceneArchive
from app.services.story_guardian import GuardianResult, Severity, StoryGuardian, Verdict
from app.services.world_builder import WorldBuilder, WorldState

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------

console = Console()
OUTPUT_DIR = Path.home() / "amphoreus" / "output"
SESSION_DIR = Path.home() / ".amphoreus" / "cli-sessions"

STRUCTURE_LABELS: dict[NarrativeStructure, str] = {
    NarrativeStructure.THREE_ACT: "1. Three-Act Structure / 三幕结构",
    NarrativeStructure.HERO_JOURNEY: "2. Hero's Journey (12 Steps) / 英雄之旅",
    NarrativeStructure.SAVE_THE_CAT: "3. Save the Cat (15 Beats) / Save the Cat",
    NarrativeStructure.QI_CHENG_ZHUAN_HE: "4. Qi Cheng Zhuan He / 起承转合",
}


# ---------------------------------------------------------------------------
# Session persistence
# ---------------------------------------------------------------------------


@dataclass
class CliSession:
    session_id: str
    created_at: str
    updated_at: str
    seed_idea: str = ""
    world_session_id: str = ""
    current_stage: str = "rules"
    character_ids: list[str] = field(default_factory=list)
    plot_id: str = ""
    narrative_structure: str = "three_act"
    completed_scene_ids: list[str] = field(default_factory=list)
    output_path: str = ""
    last_step: str = ""


def _session_path(session_id: str) -> Path:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    return SESSION_DIR / f"{session_id}.json"


def _save_cli_session(session: CliSession) -> None:
    session.updated_at = datetime.now().isoformat()
    data = {
        "session_id": session.session_id,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "seed_idea": session.seed_idea,
        "world_session_id": session.world_session_id,
        "current_stage": session.current_stage,
        "character_ids": session.character_ids,
        "plot_id": session.plot_id,
        "narrative_structure": session.narrative_structure,
        "completed_scene_ids": session.completed_scene_ids,
        "output_path": session.output_path,
        "last_step": session.last_step,
    }
    _session_path(session.session_id).write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _load_cli_session(session_id: str) -> CliSession | None:
    path = _session_path(session_id)
    if not path.exists():
        return None
    try:
        return CliSession(**json.loads(path.read_text("utf-8")))
    except (json.JSONDecodeError, KeyError):
        return None


def _list_saved_sessions() -> list[CliSession]:
    if not SESSION_DIR.exists():
        return []
    sessions: list[CliSession] = []
    for f in sorted(SESSION_DIR.iterdir(), key=os.path.getmtime, reverse=True):
        if f.suffix == ".json":
            s = _load_cli_session(f.stem)
            if s is not None:
                sessions.append(s)
    return sessions


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    )


def _stage_progress(stage: str, completeness: float) -> str:
    bar_len = 20
    filled = int(completeness * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)
    stage_names: dict[str, str] = {
        "rules": t("world.rules") if get_lang() == Lang.EN else "规则",
        "locations": t("world.locations") if get_lang() == Lang.EN else "地点",
        "factions": t("world.factions") if get_lang() == Lang.EN else "势力",
        "timeline": t("world.timeline") if get_lang() == Lang.EN else "时间线",
        "done": "Done / 完成",
    }
    label = stage_names.get(stage, stage)
    return f"[bold]{t('world.stage')}:[/] {label} | {t('world.completeness')}: [{bar}] {int(completeness * 100)}%"


def _show_language_selection() -> None:
    """Let user choose language at startup."""
    console.print()
    console.print(Panel(
        "[bold cyan]Amphoreus Story Engine[/]\n"
        "[bold cyan]Amphoreus 故事引擎[/]\n\n"
        "[1] 简体中文\n"
        "[2] English",
        box=box.HEAVY,
    ))
    console.print()

    while True:
        choice = Prompt.ask(
            "Select language / 选择语言",
            default="1",
        )
        if choice == "1":
            set_lang(Lang.ZH)
            break
        elif choice == "2":
            set_lang(Lang.EN)
            break
        console.print("[red]Invalid / 无效选择[/]")


def _show_banner() -> None:
    lang = get_lang()
    if lang == Lang.ZH:
        title = Text("Amphoreus 故事引擎", style="bold cyan")
        subtitle = Text("AI 驱动的小说与剧本生成器\n", style="bold yellow")
    else:
        title = Text("Amphoreus Story Engine", style="bold cyan")
        subtitle = Text("AI-Powered Novel & Screenplay Generator\n", style="bold yellow")

    console.print(Panel(Columns([title, subtitle]), box=box.HEAVY, style="cyan"))
    console.print()


def _confirm_api_keys() -> None:
    """Check for API keys; prompt user if missing."""
    settings = get_settings()
    settings.load_from_user_config()
    key_manager = KeyManager(settings)

    needs_save = False

    if not key_manager.is_deepseek_configured():
        console.print(f"[yellow]{t('apikey.missing_deepseek')}[/]")
        key = Prompt.ask(t("apikey.enter"), password=True)
        if key.strip():
            key_manager.set_deepseek_key(key.strip())
            needs_save = True
            console.print(f"[green]✓[/]")
        else:
            console.print(f"[red]{t('general.error')}[/]")
            sys.exit(1)
    else:
        console.print(f"[green]DeepSeek {t('apikey.configured')}[/]")

    if not key_manager.is_volcengine_configured():
        console.print(f"[yellow]{t('apikey.missing_volcengine')}[/]")
        console.print("[dim]" + ("按回车跳过（OpenViking将使用降级方案）" if get_lang() == Lang.ZH else "Press Enter to skip (OpenViking will use fallback)") + "[/]")
        key = Prompt.ask(t("apikey.enter"), password=True, default="")
        if key.strip():
            key_manager.set_volcengine_key(key.strip())
            needs_save = True
            console.print(f"[green]✓[/]")
        else:
            console.print("[dim]" + ("已跳过" if get_lang() == Lang.ZH else "Skipped") + "[/]")
    else:
        console.print(f"[green]Volcengine {t('apikey.configured')}[/]")

    if needs_save:
        settings.save_user_config()


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------


async def _world_building_pipeline(
    llm: LLMClient, memory: MemoryManager, session: CliSession, seed_idea: str
) -> WorldState:
    console.print(Rule(f"[bold cyan]{t('world.start')}[/]"))
    builder = WorldBuilder(llm, memory)

    stage_map = {"rules": 0, "locations": 1, "factions": 2, "timeline": 3, "done": 4}

    with _progress() as p:
        p.add_item(description=f"[yellow]{t('general.loading')}[/]")
        wb_session = await builder.start_new_world(seed_idea)

    session.world_session_id = wb_session.session_id

    stage_names: dict[str, str] = {
        "rules": "规则" if get_lang() == Lang.ZH else "Rules",
        "locations": "地点" if get_lang() == Lang.ZH else "Locations",
        "factions": "势力" if get_lang() == Lang.ZH else "Factions",
        "timeline": "时间线" if get_lang() == Lang.ZH else "Timeline",
        "done": "完成" if get_lang() == Lang.ZH else "Done",
    }

    while wb_session.stage != "done":
        stage_name = stage_names.get(wb_session.stage, wb_session.stage)
        stage_num = stage_map.get(wb_session.stage, 0)
        total_stages = 4
        console.print(_stage_progress(wb_session.stage, wb_session.extracted_data.completeness))
        console.print(f"[dim]{t('world.stage')} {stage_num + 1}/{total_stages}: {stage_name}[/]")
        console.print()

        question_panel_title = "世界架构师" if get_lang() == Lang.ZH else "World Architect"
        md = Markdown(wb_session.next_question)
        console.print(Panel(md, box=box.ROUNDED, title=f"[bold]{question_panel_title}[/]"))

        answer_label = "你的回答" if get_lang() == Lang.ZH else "Your answer"
        user_input = Prompt.ask(f"[bold cyan]{answer_label}[/]")

        with _progress() as p:
            p.add_item(description=f"[yellow]{t('general.loading')}[/]")
            try:
                wb_session = await builder.continue_session(wb_session.session_id, user_input)
            except Exception as e:
                console.print(f"[red]{t('general.error')}: {e}[/]")
                continue

        session.current_stage = wb_session.stage
        _save_cli_session(session)

    console.print()
    console.print(f"[green]✓ {t('world.finalized')}[/]")
    console.print()

    return await builder.finalize_world(wb_session.session_id)


async def _upload_document_pipeline(llm: LLMClient) -> WorldState:
    console.print(Rule(f"[bold cyan]{t('doc.upload')}[/]"))
    parser = DocumentParser(llm)

    while True:
        prompt_text = "文档路径 (PDF/MD/TXT)" if get_lang() == Lang.ZH else "Document path (PDF/MD/TXT)"
        file_path = Prompt.ask(f"[bold cyan]{prompt_text}[/]")
        path = Path(file_path).expanduser()
        if not path.exists():
            not_found = "文件不存在" if get_lang() == Lang.ZH else "File not found"
            console.print(f"[red]{not_found}: {path}[/]")
            continue
        if path.suffix.lower() not in (".pdf", ".md", ".txt", ".markdown"):
            unsupported = "不支持的格式，请使用 PDF、.md 或 .txt" if get_lang() == Lang.ZH else "Unsupported format. Use PDF, .md, or .txt"
            console.print(f"[yellow]{unsupported}[/]")
            continue
        break

    with _progress() as p:
        task = p.add_item(description=f"[yellow]{t('doc.parsing')}[/]")
        try:
            parsed: ParsedDocument = await parser.parse(str(path))
        except Exception as e:
            console.print(f"[red]{t('general.error')}: {e}[/]")
            raise

    chars_found = "字符" if get_lang() == Lang.ZH else "characters"
    console.print(f"[green]{t('doc.parsed')}: {len(parsed.raw_text)} {chars_found}.[/]")
    ent_found = "实体引用" if get_lang() == Lang.ZH else "entity references"
    console.print(
        f"[dim]{len(parsed.extracted_world.rules)} rules / {len(parsed.extracted_world.locations)} locations / "
        f"{len(parsed.extracted_world.factions)} factions / {len(parsed.extracted_world.timeline)} timeline, "
        f"{len(parsed.entities)} {ent_found}.[/]"
    )
    console.print()
    return parsed.extracted_world


async def _character_generation_pipeline(
    llm: LLMClient, memory: MemoryManager, session: CliSession,
    world: WorldState, char_count: int = 5,
) -> list[CharacterProfile]:
    console.print(Rule(f"[bold cyan]{t('chars.title')}[/]"))
    char_mgr = CharacterManager(llm, memory)

    generating = "个角色生成中..." if get_lang() == Lang.ZH else "characters..."
    with _progress() as p:
        p.add_item(description=f"[yellow]{t('chars.generating')} ({char_count} {generating})[/]")
        try:
            characters = await char_mgr.generate_characters(world, count=char_count)
        except Exception as e:
            console.print(f"[red]{t('general.error')}: {e}[/]")
            return []

    if not characters:
        no_chars = "没有生成任何角色。" if get_lang() == Lang.ZH else "No characters were generated."
        console.print(f"[red]{no_chars}[/]")
        return []

    session.character_ids = [c.id for c in characters]
    _save_cli_session(session)

    role_map = {
        "protagonist": "主角" if get_lang() == Lang.ZH else "Protagonist",
        "antagonist": "反派" if get_lang() == Lang.ZH else "Antagonist",
        "supporting": "配角" if get_lang() == Lang.ZH else "Supporting",
        "deuteragonist": "第二主角" if get_lang() == Lang.ZH else "Deuteragonist",
        "minor": "次要" if get_lang() == Lang.ZH else "Minor",
    }
    await _display_characters(characters, role_map)

    # Editing loop
    while True:
        console.print()
        edit_prompt = "编辑角色？(输入编号编辑，回车继续)" if get_lang() == Lang.ZH else "Edit any character? (number to edit, Enter to continue)"
        edit_choice = Prompt.ask(f"[bold cyan]{edit_prompt}[/]", default="")
        if not edit_choice.strip():
            break

        try:
            idx = int(edit_choice) - 1
            if idx < 0 or idx >= len(characters):
                invalid = "无效选择" if get_lang() == Lang.ZH else "Invalid choice"
                console.print(f"[red]{invalid}[/]")
                continue
        except ValueError:
            invalid = "无效选择" if get_lang() == Lang.ZH else "Invalid choice"
            console.print(f"[red]{invalid}[/]")
            continue

        await _edit_character(char_mgr, characters[idx])

        characters = []
        for cid in session.character_ids:
            c = await char_mgr.get_character(cid)
            if c is not None:
                characters.append(c)
        await _display_characters(characters, role_map)

    finalized = "角色已确定！" if get_lang() == Lang.ZH else "Characters finalized!"
    console.print(f"[green]{finalized}[/]")
    console.print()
    return characters


async def _display_characters(characters: list[CharacterProfile], role_map: dict[str, str]) -> None:
    chars_title = "角色列表" if get_lang() == Lang.ZH else "Characters"
    table = Table(box=box.ROUNDED, title=chars_title)
    table.add_column("#", style="dim")
    table.add_column("Name" if get_lang() == Lang.ZH or True else "Name", style="cyan")
    table.add_column("Role" if get_lang() == Lang.ZH or True else "Role", style="magenta")
    core_desire_label = "核心欲望" if get_lang() == Lang.ZH else "Core Desire"
    deep_fear_label = "深层恐惧" if get_lang() == Lang.ZH else "Deep Fear"
    table.add_column(core_desire_label, style="yellow")
    table.add_column(deep_fear_label, style="red")

    for i, c in enumerate(characters, 1):
        table.add_row(
            str(i), c.name, role_map.get(c.role, c.role),
            c.core_desire[:60] + ("..." if len(c.core_desire) > 60 else ""),
            c.deep_fear[:60] + ("..." if len(c.deep_fear) > 60 else ""),
        )
    console.print(table)


async def _edit_character(char_mgr: CharacterManager, char: CharacterProfile) -> None:
    editing = f"编辑角色 {char.name}" if get_lang() == Lang.ZH else f"Editing {char.name}"
    console.print(f"\n[bold]{editing}[/]")

    core_desire_l = "核心欲望" if get_lang() == Lang.ZH else "Core Desire"
    deep_fear_l = "深层恐惧" if get_lang() == Lang.ZH else "Deep Fear"
    traits_l = "特质" if get_lang() == Lang.ZH else "Traits"
    voice_l = "语气范本" if get_lang() == Lang.ZH else "Voice"

    console.print(Panel(
        f"[cyan]Name/名:[/] {char.name}\n"
        f"[cyan]Role/角色:[/] {char.role}\n"
        f"[cyan]{core_desire_l}:[/] {char.core_desire}\n"
        f"[cyan]{deep_fear_l}:[/] {char.deep_fear}\n"
        f"[cyan]{traits_l}:[/] {', '.join(char.personality.core_traits)}\n"
        f"[cyan]{voice_l}:[/] {char.voice_sample[:80]}...\n",
        title=f"[bold]{char.name}[/]", box=box.ROUNDED,
    ))

    describe_changes = "描述你想要的修改" if get_lang() == Lang.ZH else "Describe the changes you want"
    feedback = Prompt.ask(f"[bold yellow]{describe_changes}[/]", default="")
    if not feedback.strip():
        skipped = "已跳过" if get_lang() == Lang.ZH else "Skipped"
        console.print(f"[dim]{skipped}[/]")
        return

    refining = f"正在优化 {char.name}..." if get_lang() == Lang.ZH else f"Refining {char.name}..."
    with _progress() as p:
        p.add_item(description=f"[yellow]{refining}[/]")
        try:
            updated = await char_mgr.refine_character(char.id, feedback)
            updated_l = "已更新" if get_lang() == Lang.ZH else "Updated"
            console.print(f"[green]{updated_l}: {updated.name}[/]")
        except Exception as e:
            failed = "优化失败" if get_lang() == Lang.ZH else "Refinement failed"
            console.print(f"[red]{failed}: {e}[/]")


async def _relationship_pipeline(
    llm: LLMClient, memory: MemoryManager,
    characters: list[CharacterProfile], world: WorldState,
) -> list[Relationship]:
    console.print(Rule("[bold cyan]Relationships / 角色关系[/]"))
    rel_builder = RelationshipBuilder(llm, memory)

    inferring = "正在推断角色关系..." if get_lang() == Lang.ZH else "Inferring character relationships..."
    with _progress() as p:
        p.add_item(description=f"[yellow]{inferring}[/]")
        try:
            relationships = await rel_builder.build_relationships(characters, world)
        except Exception as e:
            failed = "关系推断失败" if get_lang() == Lang.ZH else "Relationship inference failed"
            console.print(f"[red]{failed}: {e}[/]")
            return []

    if not relationships:
        none_found = "未推断出任何关系。" if get_lang() == Lang.ZH else "No relationships were inferred."
        console.print(f"[yellow]{none_found}[/]")
        return []

    rels_title = "关系图谱" if get_lang() == Lang.ZH else "Relationships"
    table = Table(box=box.SIMPLE, title=rels_title)
    from_l = "从" if get_lang() == Lang.ZH else "From"
    to_l = "到" if get_lang() == Lang.ZH else "To"
    type_l = "类型" if get_lang() == Lang.ZH else "Type"
    strength_l = "强度" if get_lang() == Lang.ZH else "Strength"
    desc_l = "描述" if get_lang() == Lang.ZH else "Description"
    table.add_column(from_l, style="cyan")
    table.add_column(to_l, style="cyan")
    table.add_column(type_l, style="magenta")
    table.add_column(strength_l, style="yellow")
    table.add_column(desc_l)

    for r in relationships[:20]:
        table.add_row(
            r.from_id[:20], r.to_id[:20], r.rel_type, f"{r.strength:.2f}",
            r.description[:60] + ("..." if len(r.description) > 60 else ""),
        )
    console.print(table)

    if len(relationships) > 20:
        more = f"... 还有 {len(relationships) - 20} 个关系" if get_lang() == Lang.ZH else f"... and {len(relationships) - 20} more"
        console.print(f"[dim]{more}[/]")

    console.print()
    return relationships


async def _plot_architecture_pipeline(
    llm: LLMClient, memory: MemoryManager, session: CliSession,
    world: WorldState, characters: list[CharacterProfile],
) -> PlotOutline:
    console.print(Rule(f"[bold cyan]{t('plot.title')}[/]"))
    plotter = PlotArchitect(llm, memory)

    available = "可用的叙事结构" if get_lang() == Lang.ZH else "Available narrative structures"
    console.print(f"[bold]{available}:[/]")
    structures = [
        NarrativeStructure.THREE_ACT,
        NarrativeStructure.HERO_JOURNEY,
        NarrativeStructure.SAVE_THE_CAT,
        NarrativeStructure.QI_CHENG_ZHUAN_HE,
    ]

    table = Table(box=box.SIMPLE)
    table.add_column("#", style="dim")
    structure_l = "结构" if get_lang() == Lang.ZH else "Structure"
    desc_l = "描述" if get_lang() == Lang.ZH else "Description"
    table.add_column(structure_l, style="cyan bold")
    table.add_column(desc_l)
    for i, s in enumerate(structures, 1):
        desc = plotter.get_structure_templates().get(s.value, "")
        table.add_row(str(i), STRUCTURE_LABELS.get(s, s.value), desc[:80] + "...")
    console.print(table)

    choose = "选择结构" if get_lang() == Lang.ZH else "Choose a structure"
    while True:
        choice = Prompt.ask(f"[bold cyan]{choose}[/]", default="1")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(structures):
                session.narrative_structure = structures[idx].value
                break
        except ValueError:
            pass
        invalid = "无效选择" if get_lang() == Lang.ZH else "Invalid choice"
        console.print(f"[red]{invalid}[/]")

    console.print()

    generating = "正在生成剧情大纲..." if get_lang() == Lang.ZH else "Generating plot outline..."
    with _progress() as p:
        p.add_item(description=f"[yellow]{generating}[/]")
        try:
            outline = await plotter.generate_plot(world, characters, structures[idx])
        except Exception as e:
            failed = "剧情生成失败" if get_lang() == Lang.ZH else "Plot generation failed"
            console.print(f"[red]{failed}: {e}[/]")
            outline = PlotOutline(structure=structures[idx])

    plot_id = plotter.save_plot(outline)
    session.plot_id = plot_id
    _save_cli_session(session)

    _display_outline(outline)
    console.print()
    return outline


def _display_outline(outline: PlotOutline) -> None:
    for act in outline.acts:
        tree = Tree(f"[bold cyan]{act.name}[/]", guide_style="dim")
        if act.description:
            tree.add(f"[dim]{act.description}[/]")

        for scene in act.scenes:
            scene_node = tree.add(f"[green]{scene.id}:[/] [bold]{scene.title}[/]")
            location_l = "地点" if get_lang() == Lang.ZH else "Location"
            scene_node.add(f"[dim]{location_l}:[/] {scene.location}")
            if scene.cast:
                cast_l = "角色" if get_lang() == Lang.ZH else "Cast"
                cast_text = ", ".join(scene.cast[:5])
                if len(scene.cast) > 5:
                    cast_text += "..."
                scene_node.add(f"[dim]{cast_l}:[/] {cast_text}")
            conflict_l = "冲突" if get_lang() == Lang.ZH else "Conflict"
            conflict_text = scene.conflict[:100] + ("..." if len(scene.conflict) > 100 else "")
            scene_node.add(f"[yellow]{conflict_l}:[/] {conflict_text}")

        console.print(tree)


async def _scene_execution_pipeline(
    llm: LLMClient, memory: MemoryManager, session: CliSession,
    outline: PlotOutline, characters: list[CharacterProfile],
) -> dict[str, SceneArchive]:
    console.print(Rule(f"[bold cyan]{t('scene.title')}[/]"))
    char_by_id = {c.id: c for c in characters}

    plotter = PlotArchitect(llm, memory)
    all_scenes = await plotter.generate_scene_specs(outline)

    if not all_scenes:
        no_scenes = "大纲中没有场景。" if get_lang() == Lang.ZH else "No scenes in the outline."
        console.print(f"[yellow]{no_scenes}[/]")
        return {}

    scenes_title = "场景列表" if get_lang() == Lang.ZH else "Scenes"
    table = Table(box=box.SIMPLE, title=scenes_title)
    table.add_column("#", style="dim")
    table.add_column("ID", style="cyan")
    title_l = "标题" if get_lang() == Lang.ZH else "Title"
    table.add_column(title_l, style="bold")
    location_l = "地点" if get_lang() == Lang.ZH else "Location"
    table.add_column(location_l)
    cast_l = "角色" if get_lang() == Lang.ZH else "Cast"
    table.add_column(cast_l)

    for i, s in enumerate(all_scenes, 1):
        cast_str = ", ".join(
            char_by_id[c].name if c in char_by_id else c for c in s.cast[:3]
        )
        if len(s.cast) > 3:
            cast_str += " ..."
        table.add_row(str(i), s.id, s.title, s.location, cast_str)
    console.print(table)

    scene_engine = SceneEngine(llm, memory)
    completed_archives: dict[str, SceneArchive] = {}

    run_which = "执行哪个场景？(编号, 'all'=全部, 回车=第一场)" if get_lang() == Lang.ZH else "Run which scene? (number, 'all', or Enter for first)"
    choice = Prompt.ask(f"[bold cyan]{run_which}[/]", default="1")

    if choice.lower() == "all":
        scenes_to_run = all_scenes
    elif choice.strip() == "":
        scenes_to_run = [all_scenes[0]] if all_scenes else []
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(all_scenes):
                scenes_to_run = [all_scenes[idx]]
            else:
                invalid = "无效选择" if get_lang() == Lang.ZH else "Invalid choice"
                console.print(f"[red]{invalid}[/]")
                return {}
        except ValueError:
            invalid = "无效选择" if get_lang() == Lang.ZH else "Invalid choice"
            console.print(f"[red]{invalid}[/]")
            return {}

    for scene_spec in scenes_to_run:
        console.print()
        console.print(Rule(f"[bold green]{scene_spec.title}[/]"))
        location_label = "地点" if get_lang() == Lang.ZH else "Location"
        console.print(f"[dim]{location_label}:[/] {scene_spec.location}")

        scene_characters = [char_by_id[cid] for cid in scene_spec.cast if cid in char_by_id]
        if not scene_characters:
            no_chars = "此场景无可用角色，跳过。" if get_lang() == Lang.ZH else "No available characters. Skipping."
            console.print(f"[yellow]{no_chars}[/]")
            continue

        chars_in_scene = "场景中的角色" if get_lang() == Lang.ZH else "Characters in scene"
        console.print(f"[dim]{chars_in_scene}: {', '.join(c.name for c in scene_characters)}[/]")
        console.print()

        try:
            archive = await scene_engine.run_scene(scene_spec=scene_spec, characters=scene_characters, max_rounds=30)
        except Exception as e:
            failed = "场景执行失败" if get_lang() == Lang.ZH else "Scene execution failed"
            console.print(f"[red]{failed}: {e}[/]")
            continue

        completed_archives[scene_spec.id] = archive
        session.completed_scene_ids.append(scene_spec.id)
        _save_cli_session(session)

        total_rounds = "共 {n} 轮" if get_lang() == Lang.ZH else "{n} rounds"
        console.print(f"[dim]{total_rounds.format(n=len(archive.rounds))}[/]")

    console.print()
    done = f"场景完成！共 {len(completed_archives)} 个存档。" if get_lang() == Lang.ZH else f"Scene(s) complete! {len(completed_archives)} archive(s)."
    console.print(f"[green]{done}[/]")
    return completed_archives


async def _narrative_writing_pipeline(
    llm: LLMClient, memory: MemoryManager, session: CliSession,
    characters: list[CharacterProfile], archives: dict[str, SceneArchive],
) -> str:
    console.print(Rule(f"[bold cyan]{t('writer.title')}[/]"))
    writer = NarrativeWriter(llm, memory)

    scene_archives = list(archives.values())
    if not scene_archives:
        no_archives = "没有场景存档可供写作。" if get_lang() == Lang.ZH else "No scene archives to write."
        console.print(f"[yellow]{no_archives}[/]")
        return ""

    title = session.seed_idea or "Untitled"
    short_title = title[:40] + ("..." if len(title) > 40 else "")

    options = WritingOptions(
        format="novel",
        narrative_voice="third_person_limited",
        enhance=True,
        chapter_title=short_title,
    )

    converting = "正在转换为小说格式..." if get_lang() == Lang.ZH else "Converting to novel format..."
    with _progress() as p:
        p.add_item(description=f"[yellow]{converting}[/]")
        try:
            output = await writer.convert(scene_archives, characters, options)
        except Exception as e:
            failed = "写作失败" if get_lang() == Lang.ZH else "Writing failed"
            console.print(f"[red]{failed}: {e}[/]")
            retrying = "重试中（不增强）..." if get_lang() == Lang.ZH else "Retrying without enhancement..."
            options.enhance = False
            try:
                output = await writer.convert(scene_archives, characters, options)
            except Exception as e2:
                still_failed = "仍然失败" if get_lang() == Lang.ZH else "Still failed"
                console.print(f"[red]{still_failed}: {e2}[/]")
                return ""

    complete = "写作完成！" if get_lang() == Lang.ZH else "Writing complete!"
    words = "字" if get_lang() == Lang.ZH else "words"
    scenes_label = "场" if get_lang() == Lang.ZH else "scenes"
    console.print(f"[green]{complete}[/] [dim]{output.word_count} {words}, {output.scene_count} {scenes_label}[/]")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)[:50]
    filename = f"{safe_name}_chapter_1.md"
    output_path = OUTPUT_DIR / filename

    writer.export(output, "md", str(output_path))
    session.output_path = str(output_path)
    _save_cli_session(session)

    saved_to = "已保存到" if get_lang() == Lang.ZH else "Saved to"
    console.print(f"[green]{saved_to}: {output_path}[/]")

    view_label = "查看输出？" if get_lang() == Lang.ZH else "View output?"
    view = Confirm.ask(f"[bold cyan]{view_label}[/]", default=False)
    if view:
        preview = output.content[:2000] + ("..." if len(output.content) > 2000 else "")
        preview_title = "章节预览" if get_lang() == Lang.ZH else "Chapter Preview"
        console.print(Panel(Markdown(preview), title=f"[bold]{preview_title}[/]", box=box.HEAVY))

    return str(output_path)


# ---------------------------------------------------------------------------
# Guardian intervention
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Mode selection
# ---------------------------------------------------------------------------


def _select_mode() -> str:
    console.print()
    console.print(f"[bold cyan]{t('mode.title')}:[/]")
    console.print(f"  [bold]1.[/] {t('mode.1')}")
    console.print(f"  [bold]2.[/] {t('mode.2')}")
    console.print(f"  [bold]3.[/] {t('mode.3')}")
    console.print(f"  [bold]q.[/] {t('mode.q')}")
    console.print()

    while True:
        choice = Prompt.ask(f"[bold cyan]Mode / 模式[/]", default="1")
        if choice in ("1", "2", "3", "q", "Q"):
            return choice
        invalid = "无效选择" if get_lang() == Lang.ZH else "Invalid choice"
        console.print(f"[red]{invalid}[/]")


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


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
        output_path = await _narrative_writing_pipeline(llm, memory, cli_session, characters, archives)
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


if __name__ == "__main__":
    main()
