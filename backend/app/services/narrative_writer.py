"""Narrative Writer — convert scene logs to novel or screenplay format.

Public types:
  - WritingOptions, WrittenOutput
  - NovelWriter (scene logs → literary prose)
  - ScreenplayWriter (scene logs → screenplay format)
  - NarrativeWriter (facade dispatching to the correct writer)

DI: LLMClient + MemoryManager injected at construction.
"""

from __future__ import annotations

import json
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.memory import MemoryManager
from app.services.scene_engine.resolution import SceneArchive
from app.services.scene_engine.types import EnvironmentUpdate, Reaction, RoundEntry

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class WritingOptions:
    """Configuration for the narrative conversion process."""

    format: str  # "novel" or "screenplay"
    narrative_voice: str = "third_person_limited"
    enhance: bool = False
    chapter_title: str | None = None


@dataclass
class WrittenOutput:
    """Result of a narrative conversion."""

    content: str
    format: str
    word_count: int
    scene_count: int
    export_formats: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

_NOVEL_SYSTEM_PROMPT_TEMPLATE = """\
You are a literary novelist. Transform the following scene log into vivid narrative prose.
Narrative voice: {voice}.
Include sensory details, internal monologue, and descriptive passages.
Preserve all dialogue and key actions exactly as recorded.
Write in paragraphs with proper literary pacing. Do NOT add any meta-commentary."""

_NOVEL_ENHANCE_PROMPT = """\
Review the narrative above and enhance it for:
1. Pacing — vary sentence length and structure for rhythm
2. Sensory richness — deepen the sensory experience (sights, sounds, smells, textures)
3. Dialogue polish — ensure dialogue sounds natural and distinct per character

Rewrite the passage below with these improvements. Return ONLY the rewritten prose, no explanations."""

_SCREENPLAY_SYSTEM_PROMPT = """\
Convert this scene log to standard screenplay format.
Formatting rules:
- [INT./EXT.] LOCATION - TIME for each scene heading
- Action descriptions in present tense, in paragraph form
- CHARACTER NAME in ALL CAPS, centered above dialogue
- (parenthetical) for tone/action within dialogue when needed
- Double-space between scene headings, action blocks, and dialogue blocks

Preserve all dialogue and key actions exactly as recorded. Do NOT add meta-commentary."""

_SCREENPLAY_ENHANCE_PROMPT = """\
Review the screenplay above for formatting consistency and quality:

1. Verify all scene headings use correct INT./EXT. notation
2. Ensure character names are properly formatted in ALL CAPS
3. Check action descriptions are in present tense
4. Fix any formatting inconsistencies
5. Ensure proper spacing between elements

Return ONLY the corrected screenplay, no explanations."""

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


# ---------------------------------------------------------------------------
# Novel writer
# ---------------------------------------------------------------------------


class NovelWriter:
    """Converts scene logs to novel-style literary prose.

    One responsibility: take scene archives + character profiles + options
    and produce novel-format narrative text via LLM calls.
    """

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def convert(
        self,
        scene_archives: list[SceneArchive],
        characters: list[CharacterProfile],
        options: WritingOptions,
    ) -> WrittenOutput:
        """Convert scene archives to novel-format prose."""
        char_by_id = {c.id: c for c in characters}
        chapters: list[str] = []

        for archive in scene_archives:
            scene_log = self._format_scene_log(archive, char_by_id)
            scene_prose = await self._generate_novel_prose(scene_log, options)
            if options.enhance:
                scene_prose = await self._enhance_prose(scene_prose)
            chapters.append(scene_prose)

        content = self._assemble_novel(chapters, options.chapter_title)

        return WrittenOutput(
            content=content,
            format="novel",
            word_count=len(content.split()),
            scene_count=len(scene_archives),
            export_formats=["md", "txt"],
        )

    # ------------------------------------------------------------------
    # Internal: LLM calls
    # ------------------------------------------------------------------

    async def _generate_novel_prose(
        self, scene_log: str, options: WritingOptions
    ) -> str:
        """Send a scene log to the LLM and return narrative prose."""
        voice_label = options.narrative_voice.replace("_", " ")
        system_prompt = _NOVEL_SYSTEM_PROMPT_TEMPLATE.format(voice=voice_label)

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": scene_log},
        ]
        return await self._llm.chat(messages)

    async def _enhance_prose(self, prose: str) -> str:
        """Second-pass LLM call for pacing, sensory depth, and dialogue polish."""
        messages: list[dict[str, str]] = [
            {"role": "system", "content": _NOVEL_ENHANCE_PROMPT},
            {"role": "user", "content": prose},
        ]
        return await self._llm.chat(messages)

    # ------------------------------------------------------------------
    # Internal: formatting
    # ------------------------------------------------------------------

    def _format_scene_log(
        self,
        archive: SceneArchive,
        char_by_id: dict[str, CharacterProfile],
    ) -> str:
        """Format scene rounds + atmosphere into a readable log for the LLM."""
        lines: list[str] = []
        lines.append(f"Scene: {archive.scene_id}")
        lines.append(f"Atmosphere: {archive.final_environment.atmosphere}")
        if archive.final_environment.background_activity:
            lines.append(
                f"Background: {archive.final_environment.background_activity}"
            )
        lines.append("")

        for entry in archive.rounds:
            lines.append(f"--- Round {entry.round_num} ---")
            lines.append(f"Actor: {entry.actor_name}")

            if entry.dialogue:
                lines.append(f'Dialogue: "{entry.dialogue}"')
            if entry.action:
                lines.append(f"Action: {entry.action}")
            if entry.inner_thought:
                lines.append(f"Inner thought: {entry.inner_thought}")
            if entry.emotion:
                lines.append(f"Emotion: {entry.emotion}")

            for reaction in entry.reactions:
                lines.append(
                    f"  {reaction.reactor_name} reacts: "
                    f"{reaction.visible_reaction}"
                )
                if reaction.inner_thought:
                    lines.append(
                        f"    ({reaction.reactor_name} thinks: "
                        f"{reaction.inner_thought})"
                    )
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _assemble_novel(
        chapters: list[str], title: str | None
    ) -> str:
        """Combine chapter prose into a single markdown document."""
        title_text = title or "Generated Narrative"
        parts: list[str] = [f"# {title_text}\n"]

        for i, chapter_prose in enumerate(chapters, 1):
            label = f"Chapter {i}" if len(chapters) > 1 else "Part I"
            parts.append(f"\n## {label}\n\n{chapter_prose}")

        return "".join(parts)


# ---------------------------------------------------------------------------
# Screenplay writer
# ---------------------------------------------------------------------------


class ScreenplayWriter:
    """Converts scene logs to standard screenplay format.

    One responsibility: take scene archives + character profiles + options
    and produce screenplay-format text via LLM calls.
    """

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def convert(
        self,
        scene_archives: list[SceneArchive],
        characters: list[CharacterProfile],
        options: WritingOptions,
    ) -> WrittenOutput:
        """Convert scene archives to screenplay-format text."""
        char_by_id = {c.id: c for c in characters}
        pages: list[str] = []

        for archive in scene_archives:
            scene_log = self._format_scene_log(archive, char_by_id)
            formatted_scene = await self._generate_screenplay(scene_log)
            if options.enhance:
                formatted_scene = await self._enhance_screenplay(
                    formatted_scene
                )
            pages.append(formatted_scene)

        content = self._assemble_screenplay(pages)

        return WrittenOutput(
            content=content,
            format="screenplay",
            word_count=len(content.split()),
            scene_count=len(scene_archives),
            export_formats=["txt", "fountain"],
        )

    # ------------------------------------------------------------------
    # Internal: LLM calls
    # ------------------------------------------------------------------

    async def _generate_screenplay(self, scene_log: str) -> str:
        """Send a scene log to the LLM and return screenplay-format text."""
        messages: list[dict[str, str]] = [
            {"role": "system", "content": _SCREENPLAY_SYSTEM_PROMPT},
            {"role": "user", "content": scene_log},
        ]
        return await self._llm.chat(messages)

    async def _enhance_screenplay(self, text: str) -> str:
        """Second-pass LLM call for formatting consistency."""
        messages: list[dict[str, str]] = [
            {"role": "system", "content": _SCREENPLAY_ENHANCE_PROMPT},
            {"role": "user", "content": text},
        ]
        return await self._llm.chat(messages)

    # ------------------------------------------------------------------
    # Internal: formatting
    # ------------------------------------------------------------------

    def _format_scene_log(
        self,
        archive: SceneArchive,
        char_by_id: dict[str, CharacterProfile],
    ) -> str:
        """Format scene rounds into a readable log for screenplay conversion."""
        lines: list[str] = []
        lines.append(f"Scene: {archive.scene_id}")
        lines.append(f"Atmosphere: {archive.final_environment.atmosphere}")
        if archive.final_environment.background_activity:
            lines.append(
                f"Background: {archive.final_environment.background_activity}"
            )
        lines.append("")

        for entry in archive.rounds:
            lines.append(f"--- Round {entry.round_num} ---")
            lines.append(f"Character: {entry.actor_name}")

            if entry.dialogue:
                lines.append(f'Says: "{entry.dialogue}"')
            if entry.action:
                lines.append(f"Does: {entry.action}")
            if entry.inner_thought:
                lines.append(f"Thinks: {entry.inner_thought}")
            if entry.emotion:
                lines.append(f"Emotion: {entry.emotion}")

            for reaction in entry.reactions:
                lines.append(
                    f"  {reaction.reactor_name} reacts: "
                    f"{reaction.visible_reaction}"
                )
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _assemble_screenplay(pages: list[str]) -> str:
        """Combine formatted scenes into a full screenplay document."""
        title = "SCREENPLAY"
        parts: list[str] = [
            title,
            "=" * len(title),
            "",
        ]
        for page in pages:
            parts.append(page)
            parts.append("")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Facade
# ---------------------------------------------------------------------------


class NarrativeWriter:
    """Facade that dispatches to NovelWriter or ScreenplayWriter by format.

    Also handles export to file and format metadata queries.
    """

    def __init__(self, llm: LLMClient, memory: MemoryManager) -> None:
        self._llm = llm
        self._memory = memory
        self._novel_writer = NovelWriter(llm)
        self._screenplay_writer = ScreenplayWriter(llm)

    async def convert(
        self,
        scene_archives: list[SceneArchive],
        characters: list[CharacterProfile],
        options: WritingOptions,
    ) -> WrittenOutput:
        """Convert scene archives to the requested format."""
        if not scene_archives:
            raise ValueError("At least one scene archive is required")
        if not characters:
            raise ValueError("At least one character profile is required")
        if options.format not in ("novel", "screenplay"):
            raise ValueError(
                f"Unsupported format '{options.format}'. "
                "Use 'novel' or 'screenplay'."
            )

        writer = (
            self._novel_writer
            if options.format == "novel"
            else self._screenplay_writer
        )
        return await writer.convert(scene_archives, characters, options)

    def export(
        self, output: WrittenOutput, fmt: str, filepath: str | Path
    ) -> None:
        """Write a WrittenOutput to disk in the requested export format.

        Supported format conversions:
          novel      → md (Markdown, as-is)
          novel      → txt (Plain text, stripped Markdown)
          screenplay → txt (Plain text)
          screenplay → fountain (Fountain format)
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
            # content is already markdown; pass through
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
        """Return mapping of writing format → available export formats."""
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
        # Remove ATX headings
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
        # Remove bold/italic markers
        text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
        # Remove link formatting but keep link text
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        # Remove horizontal rules
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

            # Scene headings should start with INT. or EXT.
            if stripped.upper().startswith(("INT.", "EXT.", "INT/EXT.")):
                fountain_lines.append(stripped.upper())
                continue

            # Character names in ALL CAPS followed by dialogue
            if stripped.isupper() and len(stripped) > 1 and stripped.strip("() ").isupper():
                # Could be a character name — preserve
                fountain_lines.append(stripped)
                continue

            # Parentheticals
            if stripped.startswith("(") and stripped.endswith(")"):
                fountain_lines.append(stripped)
                continue

            # Preserve blank lines (scene breaks)
            if not stripped:
                fountain_lines.append("")
                continue

            # Action / description — pass through
            fountain_lines.append(stripped)

        return "\n".join(fountain_lines)
