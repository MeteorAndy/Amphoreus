"""Post-processor — normalises prose text per language conventions."""

from __future__ import annotations

import re

from app.core.i18n import get_lang, Lang
from app.models.character import CharacterProfile


class PostProcessor:
    """Normalises prose text per language conventions.

    ZH: Chinese quotes, ellipsis, em-dash, paragraph spacing.
    EN: Standard English punctuation and spacing.
    """

    @staticmethod
    def process(text: str) -> str:
        """Apply language-appropriate normalisation to the given text."""
        if get_lang() == Lang.ZH:
            return PostProcessor._process_zh(text)
        return PostProcessor._process_en(text)

    @staticmethod
    def _process_zh(text: str) -> str:
        text = re.sub(r"\.{3,}", "……", text)
        text = re.sub(r"。{3,}", "……", text)
        text = re.sub(r"-{3,}", "——", text)
        text = re.sub(r"—{1,2}", "——", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _process_en(text: str) -> str:
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)
        return text.strip()

    # ------------------------------------------------------------------
    # Screenplay-specific normalisation
    # ------------------------------------------------------------------

    @staticmethod
    def _sanitize_screenplay_content(text: str) -> str:
        """Remove leaked formatting markers that the LLM should not have produced.

        Strips:
        - Lines starting with # (leaked markdown headings)
        - Standalone --- lines
        - Scene-end markers like （第一幕·场景一完）or "(End of Act 1, Scene 1)"
        - **bold** markers around character names (ZH mode only)
        """
        lines = text.split("\n")
        cleaned: list[str] = []

        for line in lines:
            stripped = line.strip()

            # Remove standalone markdown headings (lines starting with #),
            # but KEEP the very first line if it starts with "# " — that's the title added by code
            if stripped.startswith("#") and len(cleaned) > 0:
                continue

            # Remove standalone separator lines
            if re.match(r"^---+\s*$", stripped):
                continue

            # Remove scene-end markers like （第X幕·场景X完）or similar
            if re.search(
                r"[（(]\s*(第\d+幕|第\d+章|Act\s+\d+|Scene\s+\d+)[^）)]*[完终止][）)]\s*$",
                stripped,
            ):
                continue
            if re.search(
                r"[（(]\s*(End|结束|完)\s+of\s+", stripped, re.IGNORECASE
            ):
                continue

            # Remove **bold** markers around character names (ZH mode)
            if get_lang() == Lang.ZH:
                stripped = re.sub(r"\*\*(.+?)\*\*", r"\1", stripped)

            cleaned.append(stripped)

        return "\n".join(cleaned)

    @staticmethod
    def normalize_screenplay(text: str, characters: list[CharacterProfile]) -> str:
        """Apply screenplay-specific normalisations (headings, character names)."""
        text = PostProcessor._sanitize_screenplay_content(text)
        if get_lang() == Lang.ZH:
            text = PostProcessor._normalize_scene_headings_zh(text)
            text = PostProcessor._normalize_character_names(text, characters)
        else:
            text = PostProcessor._normalize_scene_headings_en(text)
        return text

    @staticmethod
    def _normalize_scene_headings_zh(text: str) -> str:
        """Normalise Chinese scene headings to [内景]/[外景] format."""
        text = re.sub(r'\[INT\.\]', '[内景]', text)
        text = re.sub(r'\[EXT\.\]', '[外景]', text)
        text = re.sub(r'\[INT/EXT\.\]', '[内景/外景]', text)
        text = re.sub(r'\[EXT/INT\.\]', '[外景/内景]', text)
        text = re.sub(r'(?<!\w)INT/EXT\.', '[内景/外景]', text)
        text = re.sub(r'(?<!\w)EXT/INT\.', '[外景/内景]', text)
        text = re.sub(r'(?<!\w)INT\.', '[内景]', text)
        text = re.sub(r'(?<!\w)EXT\.', '[外景]', text)
        text = re.sub(r'内景\.', '[内景]', text)
        text = re.sub(r'外景\.', '[外景]', text)
        text = re.sub(r'^(外景|内景)\s', r'[\1] ', text, flags=re.MULTILINE)
        return text

    @staticmethod
    def _normalize_scene_headings_en(text: str) -> str:
        """Normalise English scene headings to [INT.]/[EXT.] format."""
        for prefix in ('INT/EXT.', 'EXT/INT.', 'INT.', 'EXT.'):
            text = re.sub(
                rf'(?<!\w){re.escape(prefix)}(?!\])',
                f'[{prefix}]',
                text,
            )
        text = re.sub(r'\[\[(.*?)\]\]', r'[\1]', text)
        return text

    @staticmethod
    def _normalize_character_names(text: str, characters: list[CharacterProfile]) -> str:
        """Revert ALL CAPS English names to original form (ZH mode only)."""
        if get_lang() != Lang.ZH:
            return text
        for char in characters:
            if not char.name:
                continue
            upper_name = char.name.upper()
            if upper_name == char.name:
                continue
            text = re.sub(
                rf'(?<!\w){re.escape(upper_name)}(?!\w)',
                char.name,
                text,
            )
        return text
