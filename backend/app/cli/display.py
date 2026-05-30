"""Rich presentation helpers for the CLI."""

from __future__ import annotations

import sys

from rich import box
from rich.columns import Columns
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from app.cli.console import console
from app.core.api_keys import KeyManager
from app.core.config import get_settings
from app.core.i18n import Lang, get_lang, set_lang, t
from app.models.character import CharacterProfile
from app.services.character_manager import CharacterManager
from app.services.plot_architect import PlotOutline
from app.services.world_builder import WorldState


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
        "rules": t("world.rules"),
        "locations": t("world.locations"),
        "factions": t("world.factions"),
        "timeline": t("world.timeline"),
        "done": "Done" if get_lang() == Lang.EN else "完成",
    }
    label = stage_names.get(stage, stage)
    return f"[bold]{t('world.stage')}:[/] {label} | {t('world.completeness')}: [{bar}] {int(completeness * 100)}%"


def _format_world_summary(world: WorldState | None) -> str:
    """Format a WorldState into a compact summary string for title generation."""
    if world is None:
        return ""
    parts: list[str] = []
    fields = [
        ("Rules", world.rules),
        ("Locations", world.locations),
        ("Factions", world.factions),
        ("Timeline", world.timeline),
    ]
    for label, items in fields:
        if not items:
            continue
        summaries: list[str] = []
        for item in items[:5]:
            if isinstance(item, dict):
                summaries.append(
                    str(item.get("name", item.get("title", item.get("event", ""))))[:60]
                )
            else:
                summaries.append(str(item)[:60])
        parts.append(f"{label} ({len(items)}): {'; '.join(summaries)}")
    return "\n".join(parts)


def _chapter_word_count_target(is_short_story: bool) -> str:
    """Return the word-count target string suitable for the chapter prompt."""
    if get_lang() == Lang.ZH:
        return "800-1500字" if is_short_story else "2500-4000字"
    return "800-1500 words" if is_short_story else "2000-3500 words"


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
        p.add_task(description=f"[yellow]{refining}[/]")
        try:
            updated = await char_mgr.refine_character(char.id, feedback)
            updated_l = "已更新" if get_lang() == Lang.ZH else "Updated"
            console.print(f"[green]{updated_l}: {updated.name}[/]")
        except Exception as e:
            failed = "优化失败" if get_lang() == Lang.ZH else "Refinement failed"
            console.print(f"[red]{failed}: {e}[/]")


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
