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
    def find_repeated_fragments(text: str, min_len: int = 8) -> list[tuple[str, int]]:
        """Surface verbatim-repeated clauses/sentences across the whole text.

        The review found copy-pasted descriptive *clauses* recurring across
        chapters (e.g. "像干涸的血迹", "像一头锁定猎物的瘦狼") — embedded inside
        larger sentences, so splitting on sentence terminators alone misses them.
        This splits on clause boundaries (commas, semicolons, enumeration commas)
        as well as sentence terminators, and returns (fragment, count) for every
        clause of >= min_len chars appearing more than once, most-repeated first.
        Diagnostic only — not auto-applied to content; callers log/inspect it.
        """
        frags = re.split(r"[。！？!?，、；;,\n]+", text)
        counts: dict[str, int] = {}
        for f in frags:
            s = f.strip().strip("“”\"'…—— ")
            if len(s) >= min_len:
                counts[s] = counts.get(s, 0) + 1
        repeats = [(s, n) for s, n in counts.items() if n > 1]
        repeats.sort(key=lambda x: (-x[1], -len(x[0])))
        return repeats

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
            text = PostProcessor._normalize_dialogue_zh(text, characters)
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

    @staticmethod
    def _normalize_dialogue_zh(
        text: str, characters: list[CharacterProfile]
    ) -> str:
        """Unify ZH screenplay dialogue + voice-over markup into one system.

        - Inline "角色：对白" (known character) -> name line + dialogue line.
        - All OS variants (角色：（OS）/ 角色（OS）：/（OS）角色：/（角色OS）)
          -> "角色（OS）" name line + content line.
        - "（旁白）…" -> "旁白（VO）" name line + content line.
        Conservative: only splits cues whose prefix is a known character name,
        so action lines containing colons are left untouched. Idempotent.
        """
        names = sorted((c.name for c in characters if c.name), key=len, reverse=True)
        if not names:
            return text
        nm = "(" + "|".join(re.escape(n) for n in names) + ")"
        co = r"[：:]"
        os_ = r"(?:O\.?S\.?|画外音)"
        lp, rp = r"[（(]", r"[）)]"
        out: list[str] = []

        def emit(name: str, content: str) -> None:
            out.append(name)
            if content.strip():
                out.append(content.strip())

        for raw in text.split("\n"):
            s = raw.strip()
            if not s:
                out.append(raw)
                continue
            # （OS）角色：内容  ->  角色（OS） + 内容
            m = re.match(rf'^{lp}\s*{os_}\s*{rp}\s*{nm}\s*{co}?\s*(.*)$', s, re.I)
            if m:
                emit(f"{m.group(1)}（OS）", m.group(2)); continue
            # 角色（OS）：内容  (also matches bare "角色（OS）" -> empty content)
            m = re.match(rf'^{nm}\s*{lp}\s*{os_}\s*{rp}\s*{co}?\s*(.*)$', s, re.I)
            if m:
                emit(f"{m.group(1)}（OS）", m.group(2)); continue
            # 角色：（OS）内容
            m = re.match(rf'^{nm}\s*{co}\s*{lp}\s*{os_}\s*{rp}\s*(.*)$', s, re.I)
            if m:
                emit(f"{m.group(1)}（OS）", m.group(2)); continue
            # （角色OS）内容  (name inside the parens)
            m = re.match(rf'^{lp}\s*{nm}\s*{os_}\s*{rp}\s*(.*)$', s, re.I)
            if m:
                emit(f"{m.group(1)}（OS）", m.group(2)); continue
            # （旁白）内容  ->  旁白（VO） + 内容
            m = re.match(rf'^{lp}\s*旁白\s*{rp}\s*{co}?\s*(.*)$', s)
            if m:
                emit("旁白（VO）", m.group(1)); continue
            # inline 角色：对白  ->  角色 + 对白 (bare "角色" line won't match: colon required)
            m = re.match(rf'^{nm}\s*{co}\s*(.+)$', s)
            if m:
                emit(m.group(1), m.group(2)); continue
            out.append(raw)
        return "\n".join(out)
