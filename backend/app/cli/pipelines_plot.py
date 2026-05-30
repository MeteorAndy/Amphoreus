"""Plot architecture and scene execution pipeline stages."""

from __future__ import annotations

from rich import box
from rich.prompt import Prompt
from rich.rule import Rule
from rich.table import Table

from app.cli.console import console
from app.cli.display import _display_outline, _progress
from app.cli.session import CliSession, _save_cli_session
from app.core.i18n import Lang, get_lang, t
from app.core.llm_client import LLMClient, LLMError, LLMErrorCode
from app.models.character import CharacterProfile
from app.services.memory import MemoryManager
from app.services.plot_architect import NarrativeStructure, PlotArchitect, PlotOutline
from app.services.scene_engine import SceneEngine
from app.services.scene_engine.resolution import SceneArchive
from app.services.scene_engine.types import EnvironmentUpdate
from app.services.world_builder import WorldState

STRUCTURE_LABELS: dict[NarrativeStructure, str] = {
    NarrativeStructure.THREE_ACT: "1. Three-Act Structure / 三幕结构",
    NarrativeStructure.HERO_JOURNEY: "2. Hero's Journey (12 Steps) / 英雄之旅",
    NarrativeStructure.SAVE_THE_CAT: "3. Save the Cat (15 Beats) / Save the Cat",
    NarrativeStructure.QI_CHENG_ZHUAN_HE: "4. Qi Cheng Zhuan He / 起承转合",
}


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
        p.add_task(description=f"[yellow]{generating}[/]")
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

        # Stream rounds in real-time; collect for archive
        try:
            round_count = 0
            env_update = None
            async for event in scene_engine.run_scene_stream(
                scene_spec=scene_spec, characters=scene_characters, max_rounds=30
            ):
                etype = event.get("type", "")
                if etype == "setup":
                    data = event.get("data", {})
                    loc_desc = data.get("location_description", "")[:200]
                    if loc_desc:
                        console.print(f"[dim italic]{loc_desc}[/]")
                elif etype == "environment":
                    env_update = event.get("data", {})
                    data = event.get("data", {})
                    atm = data.get("atmosphere", "")[:150]
                    if atm:
                        console.print(f"[dim italic]{atm}[/]")
                elif etype == "round":
                    data = event.get("data", {})
                    rn = data.get("round_num", "?")
                    actor = data.get("actor_name", "?")
                    dialogue = data.get("dialogue", "")
                    action = data.get("action", "")
                    emotion = data.get("emotion", "")
                    inner = data.get("inner_thought", "")

                    console.print(f"  [bold cyan][{rn}] {actor}[/] [dim]({emotion})[/]")
                    if dialogue:
                        console.print(f'    "[cyan]{dialogue[:200]}[/]"')
                    if action:
                        console.print(f"    [dim]* {action[:200]}[/]")
                    if inner:
                        console.print(f"    [dim]({inner[:150]})[/]")

                    round_count += 1
                    session.last_step = f"scene_{scene_spec.id}_round_{rn}"
                    _save_cli_session(session)
                elif etype == "complete":
                    archive = SceneArchive(
                        scene_id=scene_spec.id,
                        rounds=[],  # rounds collected live above, resolution handles persistence
                        final_environment=EnvironmentUpdate(
                            atmosphere=env_update.get("atmosphere", "") if env_update else "",
                            changes=[],
                            background_activity="",
                        ),
                        character_changes={},
                    )
                    completed_archives[scene_spec.id] = archive
                    session.completed_scene_ids.append(scene_spec.id)
                    _save_cli_session(session)
                    total_rounds = "共 {n} 轮" if get_lang() == Lang.ZH else "{n} rounds"
                    console.print(f"[dim]{total_rounds.format(n=round_count)}[/]")

        except LLMError as e:
            if e.code == LLMErrorCode.QUOTA_EXHAUSTED:
                quota_msg = "API 额度已用尽！" if get_lang() == Lang.ZH else "API quota exhausted!"
                saved_msg = "进度已保存。充值后重新运行 CLI 即可从中断处继续。" if get_lang() == Lang.ZH else "Progress saved. Recharge and re-run CLI to resume."
                console.print(f"\n[red bold]{quota_msg}[/]")
                console.print(f"[yellow]{saved_msg}[/]")
                console.print(f"[dim]DeepSeek: https://platform.deepseek.com/top_up[/]")
            else:
                err_msg = "LLM 错误" if get_lang() == Lang.ZH else "LLM Error"
                retry_msg = "进度已保存，稍后重试。" if get_lang() == Lang.ZH else "Progress saved. Retry later."
                console.print(f"\n[red]{err_msg} ({e.code.value}): {e}[/]")
                console.print(f"[yellow]{retry_msg}[/]")
            _save_cli_session(session)
            return completed_archives
        except Exception as e:
            failed = "场景执行失败" if get_lang() == Lang.ZH else "Scene execution failed"
            console.print(f"[red]{failed}: {e}[/]")
            _save_cli_session(session)
            continue

    console.print()
    done = f"场景完成！共 {len(completed_archives)} 个存档。" if get_lang() == Lang.ZH else f"Scene(s) complete! {len(completed_archives)} archive(s)."
    console.print(f"[green]{done}[/]")
    return completed_archives
