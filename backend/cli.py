#!/usr/bin/env python3
"""TheWorld Story Engine — Interactive CLI (Phase 9: Self-Dogfooding).

Runs the full story engine pipeline end-to-end:

  1. API key check (with prompt to configure if missing)
  2. Mode selection: new world / upload document / continue project
  3. World building (conversational LLM-guided)
  4. Character generation (with inline editing)
  5. Relationship inference
  6. Plot architecture (structure selection + outline)
  7. Scene execution (round-by-round display)
  8. Narrative writing (novel conversion + file export)

All services use the DI pattern: LLMClient + MemoryManager injected at construction.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

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
OUTPUT_DIR = Path.home() / "the-world" / "output"
SESSION_DIR = Path.home() / ".the-world" / "cli-sessions"

STRUCTURE_LABELS: dict[NarrativeStructure, str] = {
    NarrativeStructure.THREE_ACT: "1. Three-Act Structure",
    NarrativeStructure.HERO_JOURNEY: "2. Hero's Journey (12 Steps)",
    NarrativeStructure.SAVE_THE_CAT: "3. Save the Cat (15 Beats)",
    NarrativeStructure.QI_CHENG_ZHUAN_HE: "4. Qi Cheng Zhuan He (Eastern 4-Part)",
}

STAGE_LABELS: dict[str, str] = {
    "rules": "Rules",
    "locations": "Locations",
    "factions": "Factions",
    "timeline": "Timeline",
    "done": "Complete",
}


# ---------------------------------------------------------------------------
# Session persistence
# ---------------------------------------------------------------------------


@dataclass
class CliSession:
    """Tracks CLI pipeline state between steps and across runs."""

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
    last_step: str = ""  # which pipeline step was last completed


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
    path = _session_path(session.session_id)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_cli_session(session_id: str) -> CliSession | None:
    path = _session_path(session_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text("utf-8"))
        return CliSession(**data)
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


def _delete_cli_session(session_id: str) -> None:
    path = _session_path(session_id)
    if path.exists():
        path.unlink()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _progress() -> Progress:
    """Create a standard progress bar for LLM operations."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    )


def _stage_progress(stage: str, completeness: float) -> str:
    """Show a stage indicator with completeness bar in text."""
    bar_len = 20
    filled = int(completeness * bar_len)
    bar = "#" * filled + "-" * (bar_len - filled)
    label = STAGE_LABELS.get(stage, stage)
    return f"[bold]Stage:[/] {label} | Completeness: [{bar}] {int(completeness * 100)}%"


def _show_banner() -> None:
    """Display the welcome banner."""
    banner_text = Text(
        r"""
  _______ _    _ ______ _   _  _____  ______ _____   _____ _   _ ____
 |__   __| |  | |  ____| \ | |/ ____||  ____|  __ \ / ____| \ | |  _ \
    | |  | |__| | |__  |  \| | |  __ | |__  | |__) | |  __|  \| | |_) |
    | |  |  __  |  __| | . ` | | |_ ||  __| |  _  /| | |_ | . ` |  _ <
    | |  | |  | | |____| |\  | |__| || |____| | \ \| |__| | |\  | |_) |
    |_|  |_|  |_|______|_| \_|\_____||______|_|  \_\\_____|_| \_|____/
        """,
        style="bold cyan",
    )
    subtitle = Text("AI-Powered Novel Generator\n", style="bold yellow")
    console.print(Panel(Columns([banner_text, subtitle]), box=box.HEAVY, style="cyan"))
    console.print()


def _confirm_api_key() -> None:
    """Check for DeepSeek API key; prompt user if missing."""
    settings = get_settings()
    settings.load_from_user_config()
    key_manager = KeyManager(settings)

    if key_manager.is_deepseek_configured():
        console.print("[green]API key found.[/]")
        return

    console.print("[yellow]No DeepSeek API key configured.[/]")
    console.print(
        "The story engine requires a DeepSeek API key "
        "(deepseek-v4-flash model)."
    )
    key = Prompt.ask(
        "Enter your DeepSeek API key",
        password=True,
    )
    if key.strip():
        key_manager.set_deepseek_key(key.strip())
        console.print("[green]API key saved![/]")
    else:
        console.print("[red]No key entered. Exiting.[/]")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------


async def _world_building_pipeline(
    llm: LLMClient, memory: MemoryManager, session: CliSession, seed_idea: str
) -> WorldState:
    """Run the world-building conversation loop.

    Returns the final WorldState once all stages are complete.
    """
    console.print(Rule("[bold cyan]WORLD BUILDING[/]"))
    builder = WorldBuilder(llm, memory)

    stage_map = {"rules": 0, "locations": 1, "factions": 2, "timeline": 3, "done": 4}

    with _progress() as p:
        p.add_item(description="[yellow]Initializing world...[/]")
        wb_session = await builder.start_new_world(seed_idea)

    session.world_session_id = wb_session.session_id

    while wb_session.stage != "done":
        stage_name = STAGE_LABELS.get(wb_session.stage, wb_session.stage)
        stage_num = stage_map.get(wb_session.stage, 0)
        total_stages = 4
        console.print(
            _stage_progress(
                wb_session.stage, wb_session.extracted_data.completeness
            )
        )
        console.print(
            f"[dim]Stage {stage_num + 1}/{total_stages}: {stage_name}[/]"
        )
        console.print()

        # Display the LLM's question
        md = Markdown(wb_session.next_question)
        console.print(Panel(md, box=box.ROUNDED, title="[bold]World Architect[/]"))

        # Get user response
        user_input = Prompt.ask("[bold cyan]Your answer[/]")

        with _progress() as p:
            p.add_item(description="[yellow]Processing...[/]")
            try:
                wb_session = await builder.continue_session(
                    wb_session.session_id, user_input
                )
            except Exception as e:
                console.print(f"[red]Error: {e}[/]")
                console.print("[yellow]Let me retry...[/]")
                continue

        # Update CLI session stage
        session.current_stage = wb_session.stage
        _save_cli_session(session)

    console.print()
    console.print("[green]World building complete![/]")
    console.print()

    # Finalize and return the world state
    world = await builder.finalize_world(wb_session.session_id)
    return world


async def _upload_document_pipeline(llm: LLMClient) -> WorldState:
    """Parse an uploaded world document."""
    console.print(Rule("[bold cyan]DOCUMENT UPLOAD[/]"))
    parser = DocumentParser(llm)

    while True:
        file_path = Prompt.ask(
            "[bold cyan]Path to world document[/] (PDF, Markdown, or text file)"
        )
        path = Path(file_path).expanduser()
        if not path.exists():
            console.print(f"[red]File not found: {path}[/]")
            continue
        if path.suffix.lower() not in (".pdf", ".md", ".txt", ".markdown"):
            console.print(
                "[yellow]Unsupported format. Use PDF, .md, or .txt[/]"
            )
            continue
        break

    with _progress() as p:
        task = p.add_item(description="[yellow]Parsing document...[/]")
        try:
            parsed: ParsedDocument = await parser.parse(str(path))
        except Exception as e:
            console.print(f"[red]Error parsing document: {e}[/]")
            raise

    console.print(f"[green]Parsed {len(parsed.raw_text)} characters.[/]")
    console.print(f"[dim]Found {len(parsed.extracted_world.rules)} rules, "
                  f"{len(parsed.extracted_world.locations)} locations, "
                  f"{len(parsed.extracted_world.factions)} factions, "
                  f"{len(parsed.extracted_world.timeline)} timeline entries.[/]")

    if parsed.entities:
        console.print(f"[dim]Detected {len(parsed.entities)} character references.[/]")

    console.print()
    return parsed.extracted_world


async def _character_generation_pipeline(
    llm: LLMClient,
    memory: MemoryManager,
    session: CliSession,
    world: WorldState,
    char_count: int = 5,
) -> list[CharacterProfile]:
    """Generate characters and allow editing."""
    console.print(Rule("[bold cyan]CHARACTER GENERATION[/]"))
    char_mgr = CharacterManager(llm, memory)

    with _progress() as p:
        p.add_item(description=f"[yellow]Generating {char_count} characters...[/]")
        try:
            characters = await char_mgr.generate_characters(world, count=char_count)
        except Exception as e:
            console.print(f"[red]Character generation failed: {e}[/]")
            console.print("[yellow]Retrying...[/]")
            try:
                characters = await char_mgr.generate_characters(world, count=char_count)
            except Exception as e2:
                console.print(f"[red]Still failed: {e2}[/]")
                return []

    if not characters:
        console.print("[red]No characters were generated.[/]")
        return []

    session.character_ids = [c.id for c in characters]
    _save_cli_session(session)

    # Display character table
    await _display_characters(characters)

    # Editing loop
    while True:
        console.print()
        edit_choice = Prompt.ask(
            "[bold cyan]Edit any character?[/] (number to edit, "
            "[dim]Enter[/] to continue)",
            default="",
        )
        if not edit_choice.strip():
            break

        try:
            idx = int(edit_choice) - 1
            if idx < 0 or idx >= len(characters):
                console.print("[red]Invalid choice.[/]")
                continue
        except ValueError:
            console.print("[red]Invalid choice.[/]")
            continue

        char = characters[idx]
        await _edit_character(char_mgr, char)

        # Refresh display
        characters = []
        for cid in session.character_ids:
            c = await char_mgr.get_character(cid)
            if c is not None:
                characters.append(c)
        await _display_characters(characters)

    console.print("[green]Characters finalized![/]")
    console.print()
    return characters


async def _display_characters(characters: list[CharacterProfile]) -> None:
    """Display character table."""
    table = Table(box=box.ROUNDED, title="Characters")
    table.add_column("#", style="dim")
    table.add_column("Name", style="cyan")
    table.add_column("Role", style="magenta")
    table.add_column("Core Desire", style="yellow")
    table.add_column("Deep Fear", style="red")

    for i, c in enumerate(characters, 1):
        table.add_row(
            str(i),
            c.name,
            c.role.capitalize(),
            c.core_desire[:60] + ("..." if len(c.core_desire) > 60 else ""),
            c.deep_fear[:60] + ("..." if len(c.deep_fear) > 60 else ""),
        )
    console.print(table)


async def _edit_character(
    char_mgr: CharacterManager, char: CharacterProfile
) -> None:
    """Edit a single character's properties via LLM refinement."""
    console.print(f"\n[bold]Editing: {char.name}[/]")

    # Show current details
    console.print(Panel(
        f"[cyan]Name:[/] {char.name}\n"
        f"[cyan]Role:[/] {char.role}\n"
        f"[cyan]Core Desire:[/] {char.core_desire}\n"
        f"[cyan]Deep Fear:[/] {char.deep_fear}\n"
        f"[cyan]Traits:[/] {', '.join(char.personality.core_traits)}\n"
        f"[cyan]Voice:[/] {char.voice_sample[:80]}...\n",
        title=f"[bold]{char.name}[/]",
        box=box.ROUNDED,
    ))

    feedback = Prompt.ask(
        "[bold yellow]Describe the changes you want[/]",
        default="",
    )
    if not feedback.strip():
        console.print("[dim]Skipped.[/]")
        return

    with _progress() as p:
        p.add_item(description=f"[yellow]Refining {char.name}...[/]")
        try:
            updated = await char_mgr.refine_character(char.id, feedback)
            console.print(f"[green]Updated:[/] {updated.name}")
        except Exception as e:
            console.print(f"[red]Refinement failed: {e}[/]")


async def _relationship_pipeline(
    llm: LLMClient,
    memory: MemoryManager,
    characters: list[CharacterProfile],
    world: WorldState,
) -> list[Relationship]:
    """Build relationships between characters."""
    console.print(Rule("[bold cyan]RELATIONSHIP INFERENCE[/]"))
    rel_builder = RelationshipBuilder(llm, memory)

    with _progress() as p:
        p.add_item(description="[yellow]Inferring character relationships...[/]")
        try:
            relationships = await rel_builder.build_relationships(characters, world)
        except Exception as e:
            console.print(f"[red]Relationship inference failed: {e}[/]")
            return []

    if not relationships:
        console.print("[yellow]No relationships were inferred.[/]")
    else:
        table = Table(box=box.SIMPLE, title="Relationships")
        table.add_column("From", style="cyan")
        table.add_column("To", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Strength", style="yellow")
        table.add_column("Description")

        for r in relationships[:20]:  # cap display
            strength_str = f"{r.strength:.2f}"
            table.add_row(
                r.from_id[:20], r.to_id[:20], r.rel_type, strength_str,
                r.description[:60] + ("..." if len(r.description) > 60 else ""),
            )
        console.print(table)

        if len(relationships) > 20:
            console.print(f"[dim]... and {len(relationships) - 20} more.[/]")

    console.print()
    return relationships


async def _plot_architecture_pipeline(
    llm: LLMClient,
    memory: MemoryManager,
    session: CliSession,
    world: WorldState,
    characters: list[CharacterProfile],
) -> PlotOutline:
    """Generate a plot outline using a chosen narrative structure."""
    console.print(Rule("[bold cyan]PLOT ARCHITECTURE[/]"))
    plotter = PlotArchitect(llm, memory)

    # Show available structures
    console.print("[bold]Available narrative structures:[/]")
    structures = [
        NarrativeStructure.THREE_ACT,
        NarrativeStructure.HERO_JOURNEY,
        NarrativeStructure.SAVE_THE_CAT,
        NarrativeStructure.QI_CHENG_ZHUAN_HE,
    ]

    table = Table(box=box.SIMPLE)
    table.add_column("#", style="dim")
    table.add_column("Structure", style="cyan bold")
    table.add_column("Description")
    for i, s in enumerate(structures, 1):
        desc = plotter.get_structure_templates().get(s.value, "")
        table.add_row(str(i), STRUCTURE_LABELS.get(s, s.value), desc[:80] + "...")
    console.print(table)

    # Pick structure
    while True:
        choice = Prompt.ask(
            "[bold cyan]Choose a structure[/]",
            default="1",
        )
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(structures):
                console.print("[red]Invalid choice.[/]")
                continue
            selected_structure = structures[idx]
            session.narrative_structure = selected_structure.value
            break
        except ValueError:
            console.print("[red]Please enter a number.[/]")

    console.print()

    # Generate the outline
    with _progress() as p:
        p.add_item(description="[yellow]Generating plot outline...[/]")
        try:
            outline = await plotter.generate_plot(
                world, characters, selected_structure
            )
        except Exception as e:
            console.print(f"[red]Plot generation failed: {e}[/]")
            console.print("[yellow]Retrying once...[/]")
            try:
                outline = await plotter.generate_plot(
                    world, characters, selected_structure
                )
            except Exception as e2:
                console.print(f"[red]Still failed: {e2}[/]")
                # Create empty outline to allow continued flow
                outline = PlotOutline(structure=selected_structure)

    # Save plot
    plot_id = plotter.save_plot(outline)
    session.plot_id = plot_id
    _save_cli_session(session)

    # Display the outline
    _display_outline(outline)

    console.print()
    return outline


def _display_outline(outline: PlotOutline) -> None:
    """Display plot outline with acts and scenes."""
    for act in outline.acts:
        act_pct = max(1, 100 // max(len(outline.acts), 1))
        tree = Tree(
            f"[bold cyan]{act.name}[/] ([yellow]~{act_pct}%[/])",
            guide_style="dim",
        )
        if act.description:
            tree.add(f"[dim]{act.description}[/]")

        for scene in act.scenes:
            scene_node = tree.add(
                f"[green]Scene {scene.id}:[/] [bold]{scene.title}[/]"
            )
            scene_node.add(f"[dim]Location:[/] {scene.location}")
            if scene.cast:
                scene_node.add(
                    f"[dim]Cast:[/] {', '.join(scene.cast[:5])}"
                    + ("..." if len(scene.cast) > 5 else "")
                )
            conflict_text = scene.conflict[:100] + ("..." if len(scene.conflict) > 100 else "")
            scene_node.add(f"[yellow]Conflict:[/] {conflict_text}")

        console.print(tree)


async def _scene_execution_pipeline(
    llm: LLMClient,
    memory: MemoryManager,
    session: CliSession,
    outline: PlotOutline,
    characters: list[CharacterProfile],
) -> dict[str, SceneArchive]:
    """Execute scenes interactively."""
    console.print(Rule("[bold cyan]SCENE EXECUTION[/]"))
    char_by_id = {c.id: c for c in characters}

    # Flatten all scenes
    plotter = PlotArchitect(llm, memory)
    all_scenes = await plotter.generate_scene_specs(outline)

    if not all_scenes:
        console.print("[yellow]No scenes in the outline.[/]")
        return {}

    # Show scene list
    table = Table(box=box.SIMPLE, title="Scenes")
    table.add_column("#", style="dim")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="bold")
    table.add_column("Location")
    table.add_column("Cast")

    for i, s in enumerate(all_scenes, 1):
        cast_str = ", ".join(
            char_by_id[c].name if c in char_by_id else c
            for c in s.cast[:3]
        )
        if len(s.cast) > 3:
            cast_str += " ..."
        table.add_row(str(i), s.id, s.title, s.location, cast_str)
    console.print(table)

    # Track completed scenes
    scene_engine = SceneEngine(llm, memory)
    completed_archives: dict[str, SceneArchive] = {}

    # Determine which scenes to run
    scenes_to_run: list[SceneSpec] = []
    while True:
        choice = Prompt.ask(
            "[bold cyan]Run which scene?[/] (number, [dim]'all'[/], or "
            "[dim]Enter[/] for scene 1)",
            default="1",
        )
        if choice.lower() == "all":
            scenes_to_run = all_scenes
            break
        elif choice.strip() == "":
            scenes_to_run = [all_scenes[0]] if all_scenes else []
            break
        else:
            try:
                idx = int(choice) - 1
                if idx < 0 or idx >= len(all_scenes):
                    console.print("[red]Invalid choice.[/]")
                    continue
                scenes_to_run = [all_scenes[idx]]
                break
            except ValueError:
                console.print("[red]Invalid choice.[/]")
                continue

    if not scenes_to_run:
        return completed_archives

    for scene_spec in scenes_to_run:
        console.print()
        console.print(Rule(f"[bold green]Scene: {scene_spec.title}[/]"))
        console.print(f"[dim]Location:[/] {scene_spec.location}")

        # Determine cast character profiles
        scene_characters = [
            char_by_id[cid] for cid in scene_spec.cast if cid in char_by_id
        ]
        if not scene_characters:
            console.print("[yellow]No available characters for this scene. Skipping.[/]")
            continue

        console.print(f"[dim]Characters in scene:[/] "
                      f"{', '.join(c.name for c in scene_characters)}")
        console.print()

        # Run the scene
        try:
            archive = await scene_engine.run_scene(
                scene_spec=scene_spec,
                characters=scene_characters,
                max_rounds=30,
            )
        except Exception as e:
            console.print(f"[red]Scene execution failed: {e}[/]")
            console.print("[yellow]Retrying...[/]")
            try:
                archive = await scene_engine.run_scene(
                    scene_spec=scene_spec,
                    characters=scene_characters,
                    max_rounds=30,
                )
            except Exception as e2:
                console.print(f"[red]Still failed: {e2}[/]")
                continue

        completed_archives[scene_spec.id] = archive
        session.completed_scene_ids.append(scene_spec.id)
        _save_cli_session(session)

        # Display the scene results
        _display_scene_rounds(archive, char_by_id)

        # Check if user wants to continue
        if scene_spec != scenes_to_run[-1]:
            cont = Confirm.ask("[bold cyan]Continue to next scene?[/]", default=True)
            if not cont:
                break

    console.print()
    if completed_archives:
        console.print(f"[green]Scene(s) complete! {len(completed_archives)} archive(s).[/]")
    else:
        console.print("[yellow]No scenes were executed.[/]")
    return completed_archives


def _display_scene_rounds(
    archive: SceneArchive, char_by_id: dict[str, CharacterProfile]
) -> None:
    """Display each round of a completed scene."""
    console.print(f"\n[dim]Scene completed: {len(archive.rounds)} rounds[/]")

    for entry in archive.rounds:
        console.print()
        # Round header
        console.print(
            Panel(
                f"[bold]{entry.actor_name}[/] "
                f"([italic]{entry.emotion}[/])",
                box=box.MINIMAL,
                border_style="blue",
            )
        )

        if entry.dialogue:
            console.print(f'  "{entry.dialogue}"')
        if entry.action:
            console.print(f"  [dim]Action:[/] {entry.action}")
        if entry.inner_thought:
            console.print(f"  [dim]({entry.inner_thought})[/]")

        # Reactions
        for reaction in entry.reactions:
            reactor_name = char_by_id[reaction.reactor_id].name if reaction.reactor_id in char_by_id else reaction.reactor_name
            console.print(
                f"  [dim]{reactor_name}:[/] {reaction.visible_reaction}"
            )
            if reaction.inner_thought:
                console.print(
                    f"    [dim]({reaction.inner_thought})[/]"
                )


async def _narrative_writing_pipeline(
    llm: LLMClient,
    memory: MemoryManager,
    session: CliSession,
    characters: list[CharacterProfile],
    archives: dict[str, SceneArchive],
) -> str:
    """Convert scene archives to novel format and export."""
    console.print(Rule("[bold cyan]NARRATIVE WRITING[/]"))
    writer = NarrativeWriter(llm, memory)

    scene_archives = list(archives.values())
    if not scene_archives:
        console.print("[yellow]No scene archives to write.[/]")
        return ""

    # Generate a chapter title from the seed idea
    title = session.seed_idea or "Generated Narrative"
    short_title = title[:40] + ("..." if len(title) > 40 else "")

    options = WritingOptions(
        format="novel",
        narrative_voice="third_person_limited",
        enhance=True,
        chapter_title=short_title,
    )

    with _progress() as p:
        p.add_item(description="[yellow]Converting to novel format...[/]")
        try:
            output = await writer.convert(scene_archives, characters, options)
        except Exception as e:
            console.print(f"[red]Writing failed: {e}[/]")
            console.print("[yellow]Retrying without enhancement...[/]")
            options.enhance = False
            try:
                output = await writer.convert(scene_archives, characters, options)
            except Exception as e2:
                console.print(f"[red]Writing still failed: {e2}[/]")
                return ""

    console.print(f"[green]Writing complete![/]")
    console.print(f"[dim]Word count: {output.word_count}, "
                  f"Scenes: {output.scene_count}[/]")

    # Export to file
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)[:50]
    filename = f"{safe_name}_第1章.md"
    output_path = OUTPUT_DIR / filename

    writer.export(output, "md", str(output_path))
    session.output_path = str(output_path)
    _save_cli_session(session)

    console.print(f"[green]Output saved to: {output_path}[/]")

    # Preview option
    view = Confirm.ask("[bold cyan]View output?[/]", default=False)
    if view:
        content = output.content
        preview = content[:2000] + ("..." if len(content) > 2000 else "")
        console.print(Panel(
            Markdown(preview),
            title="[bold]Chapter Preview[/]",
            box=box.HEAVY,
        ))

    return str(output_path)


# ---------------------------------------------------------------------------
# Guardian intervention
# ---------------------------------------------------------------------------


async def _guardian_check(
    guardian: StoryGuardian,
    proposed_change: str,
    affected_characters: list[str],
    world_id: str | None = None,
) -> bool:
    """Run a proposed change through the Story Guardian.

    Returns True if the change should proceed (approved or overridden),
    False if rejected by CRITICAL issues.
    """
    console.print("[yellow]Checking through Story Guardian...[/]")

    try:
        result: GuardianResult = await guardian.evaluate(
            proposed_plot=proposed_change,
            affected_characters=affected_characters,
            world_id=world_id,
        )
    except Exception as e:
        console.print(f"[yellow]Guardian check failed (non-critical): {e}[/]")
        return True

    if result.verdict == Verdict.APPROVED:
        console.print("[green]Guardian: Approved with no issues.[/]")
        return True

    # Display issues
    table = Table(box=box.SIMPLE, title="Guardian Review")
    table.add_column("Severity", style="bold")
    table.add_column("Dimension")
    table.add_column("Description")
    table.add_column("Suggestion")

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
        console.print("[red bold]PROPOSAL REJECTED: Critical issues found.[/]")
        if result.can_override:
            return Confirm.ask(
                "[bold yellow]Override and proceed anyway?[/]", default=False
            )
        return False

    if result.verdict == Verdict.WARNING:
        console.print("[yellow]Proposal has warnings.[/]")
        return Confirm.ask(
            "[bold yellow]Proceed with warnings?[/]", default=True
        )

    return True


# ---------------------------------------------------------------------------
# Mode selection
# ---------------------------------------------------------------------------


def _select_mode() -> str:
    """Show the main menu and return the selected mode."""
    console.print()
    console.print("[bold cyan]Select mode:[/]")
    console.print("  [bold]1.[/] Build a new world from an idea")
    console.print("  [bold]2.[/] Upload existing world document")
    console.print("  [bold]3.[/] Continue existing project")
    console.print("  [bold]q.[/] Quit")
    console.print()

    while True:
        choice = Prompt.ask("[bold cyan]Mode[/]", default="1")
        if choice in ("1", "2", "3", "q", "Q"):
            return choice
        console.print("[red]Invalid choice.[/]")


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


async def async_main() -> None:
    """Main CLI entry point — orchestrates the entire pipeline."""
    _show_banner()

    # ── API key check ─────────────────────────────────────────────
    _confirm_api_key()

    # Initialize core services
    settings = get_settings()
    llm = LLMClient()
    memory = MemoryManager(settings)
    await memory.initialize()

    # ── Mode selection ────────────────────────────────────────────
    mode = _select_mode()

    if mode in ("q", "Q"):
        console.print("[yellow]Goodbye![/]")
        return

    # Create a new CLI session
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
        seed_idea = Prompt.ask(
            "[bold cyan]Enter your story idea[/] (one sentence)"
        )
        cli_session.seed_idea = seed_idea
        _save_cli_session(cli_session)

        world = await _world_building_pipeline(
            llm, memory, cli_session, seed_idea
        )

    # ── Mode 2: Upload document ───────────────────────────────────
    elif mode == "2":
        try:
            world = await _upload_document_pipeline(llm)
        except Exception as e:
            console.print(f"[red]Document parsing failed: {e}[/]")
            console.print("[yellow]Falling back to idea-based world building.[/]")
            seed_idea = Prompt.ask(
                "[bold cyan]Enter your story idea[/] (one sentence)"
            )
            cli_session.seed_idea = seed_idea
            _save_cli_session(cli_session)
            world = await _world_building_pipeline(
                llm, memory, cli_session, seed_idea
            )

    # ── Mode 3: Continue project ──────────────────────────────────
    elif mode == "3":
        saved = _list_saved_sessions()
        if not saved:
            console.print("[yellow]No saved sessions found.[/]")
            seed_idea = Prompt.ask(
                "[bold cyan]Enter your story idea[/] (one sentence)"
            )
            cli_session.seed_idea = seed_idea
            _save_cli_session(cli_session)
            world = await _world_building_pipeline(
                llm, memory, cli_session, seed_idea
            )
        else:
            # Let user pick a session
            console.print("[bold cyan]Saved sessions:[/]")
            for i, s in enumerate(saved, 1):
                console.print(
                    f"  {i}. {s.seed_idea[:60] or 'Unknown'} "
                    f"[dim]({s.updated_at[:19]})[/]"
                )
            console.print()

            while True:
                choice = Prompt.ask(
                    "[bold cyan]Pick a session[/] (number, or [dim]'n'[/] for new)",
                    default="1",
                )
                if choice.lower() == "n":
                    seed_idea = Prompt.ask(
                        "[bold cyan]Enter your story idea[/] (one sentence)"
                    )
                    cli_session.seed_idea = seed_idea
                    _save_cli_session(cli_session)
                    world = await _world_building_pipeline(
                        llm, memory, cli_session, seed_idea
                    )
                    break
                try:
                    idx = int(choice) - 1
                    if idx < 0 or idx >= len(saved):
                        console.print("[red]Invalid choice.[/]")
                        continue
                    existing = saved[idx]
                    cli_session = existing

                    # Restore world state
                    builder = WorldBuilder(llm, memory)
                    if cli_session.world_session_id:
                        world = await builder.finalize_world(
                            cli_session.world_session_id
                        )
                        # Reload characters
                        char_mgr = CharacterManager(llm, memory)
                        for cid in cli_session.character_ids:
                            c = await char_mgr.get_character(cid)
                            if c is not None:
                                characters.append(c)
                    break
                except ValueError:
                    console.print("[red]Invalid choice.[/]")

    # Guard: world must be initialized
    if world is None:
        console.print("[red]World state is empty. Cannot proceed.[/]")
        return

    # ── Character generation ──────────────────────────────────────
    if not characters:
        characters = await _character_generation_pipeline(
            llm, memory, cli_session, world
        )

    if not characters:
        console.print("[red]No characters available. Cannot proceed.[/]")
        return

    # ── Relationship inference ────────────────────────────────────
    relationships = await _relationship_pipeline(
        llm, memory, characters, world
    )

    # ── Plot architecture ─────────────────────────────────────────
    outline = await _plot_architecture_pipeline(
        llm, memory, cli_session, world, characters
    )

    if not outline.acts:
        console.print("[red]Plot outline is empty. Cannot proceed.[/]")
        return

    # ── Scene execution ───────────────────────────────────────────
    archives = await _scene_execution_pipeline(
        llm, memory, cli_session, outline, characters
    )

    # ── Narrative writing ─────────────────────────────────────────
    if archives:
        output_path = await _narrative_writing_pipeline(
            llm, memory, cli_session, characters, archives
        )
    else:
        console.print("[yellow]No scenes completed. Skipping narrative writing.[/]")
        output_path = ""

    cli_session.last_step = "complete"
    _save_cli_session(cli_session)

    # ── Final summary ─────────────────────────────────────────────
    console.print()
    console.print(Rule("[bold green]PIPELINE COMPLETE[/]"))
    summary = Table(box=box.HEAVY, title="Session Summary")
    summary.add_column("Metric", style="bold cyan")
    summary.add_column("Value")
    summary.add_row("Seed Idea", cli_session.seed_idea[:60] + ("..." if len(cli_session.seed_idea) > 60 else ""))
    summary.add_row("Characters", str(len(characters)))
    summary.add_row("Relationships", str(len(relationships)))
    summary.add_row("Acts", str(len(outline.acts)))
    summary.add_row("Scenes Executed", str(len(archives)))
    summary.add_row("Output", str(output_path) if output_path else "N/A")
    summary.add_row("Session ID", cli_session.session_id[:8] + "...")
    console.print(summary)
    console.print()

    # Cleanup
    await memory.close()


def main() -> None:
    """Entry point executed from `uv run python cli.py`."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user. Goodbye![/]")
        sys.exit(0)
    except Exception as exc:
        console.print(f"\n[red bold]Unexpected error:[/] {exc}")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
