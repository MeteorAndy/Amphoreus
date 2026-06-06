"""World, document, character, and relationship pipeline stages."""

from __future__ import annotations

from pathlib import Path

from rich import box
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.table import Table

from app.cli.console import console
from app.cli.display import _display_characters, _edit_character, _progress, _stage_progress
from app.cli.picker import pick, select
from app.cli.session import CliSession, _save_cli_session
from app.core.i18n import Lang, get_lang, t
from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.character_manager import CharacterManager
from app.services.document_parser import DocumentParser, ParsedDocument
from app.services.memory import MemoryManager
from app.services.relationship_builder import Relationship, RelationshipBuilder
from app.services.world_builder import WorldBuilder, WorldState, _auto_fill_instruction


async def _world_building_pipeline(
    llm: LLMClient, memory: MemoryManager, session: CliSession,
    seed_idea: str, auto: bool = False,
) -> WorldState:
    console.print(Rule(f"[bold cyan]{t('world.start')}[/]"))
    builder = WorldBuilder(llm, memory)

    stage_map = {"rules": 0, "locations": 1, "factions": 2, "timeline": 3, "done": 4}

    with _progress() as p:
        p.add_task(description=f"[yellow]{t('general.loading')}[/]")
        wb_session = await builder.start_new_world(seed_idea)

    session.world_session_id = wb_session.session_id

    stage_names: dict[str, str] = {
        "rules": t("world.rules"),
        "locations": t("world.locations"),
        "factions": t("world.factions"),
        "timeline": t("world.timeline"),
        "done": "Done" if get_lang() == Lang.EN else "完成",
    }

    auto_iterations = 0
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

        if auto:
            user_input = _auto_fill_instruction()
            auto_iterations += 1
            if auto_iterations > 12:
                break
            console.print(f"[dim]{t('world.autofilling')}[/]")
        else:
            res = pick(
                "",
                wb_session.suggestions,
                allow_auto=True,
                auto_label=t("picker.auto_stage"),
            )
            if res.kind == "auto":
                auto = True
                user_input = _auto_fill_instruction()
                console.print(f"[dim]{t('world.autofilling')}[/]")
            else:
                user_input = res.value

        with _progress() as p:
            p.add_task(description=f"[yellow]{t('general.loading')}[/]")
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


async def _choose_seed_idea(llm: LLMClient, memory: MemoryManager) -> str:
    """Brainstorm seed ideas and let the user pick, type their own, or skip."""
    builder = WorldBuilder(llm, memory)
    panel_title = "故事灵感" if get_lang() == Lang.ZH else "Story Spark"
    question = "你想写一个什么样的故事？" if get_lang() == Lang.ZH else "What kind of story do you want to write?"

    with _progress() as p:
        p.add_task(description=f"[yellow]{t('seed.brainstorming')}[/]")
        try:
            ideas = await builder.brainstorm_seed_ideas(count=5)
        except Exception:
            ideas = []

    console.print(Panel(Markdown(question), box=box.ROUNDED, title=f"[bold]{panel_title}[/]"))
    res = pick(t("seed.choose"), ideas, allow_custom=True, allow_auto=False)
    return res.value


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
        task = p.add_task(description=f"[yellow]{t('doc.parsing')}[/]")
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
        p.add_task(description=f"[yellow]{t('chars.generating')} ({char_count} {generating})[/]")
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
        labels = [c.name for c in characters] + ["✓ " + ("完成" if get_lang() == Lang.ZH else "Done")]
        sel = select(edit_prompt, labels, default_index=len(characters), divider_before=len(characters))
        if sel == len(characters):
            break

        await _edit_character(char_mgr, characters[sel])

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


async def _relationship_pipeline(
    llm: LLMClient, memory: MemoryManager,
    characters: list[CharacterProfile], world: WorldState,
) -> list[Relationship]:
    rels_section_title = "角色关系" if get_lang() == Lang.ZH else "Relationships"
    console.print(Rule(f"[bold cyan]{rels_section_title}[/]"))
    rel_builder = RelationshipBuilder(llm, memory)

    inferring = "正在推断角色关系..." if get_lang() == Lang.ZH else "Inferring character relationships..."
    with _progress() as p:
        p.add_task(description=f"[yellow]{inferring}[/]")
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
