from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.llm_client import LLMClient
from app.services.world_builder import WorldState

_DOC_SYSTEM_PROMPT = """\
You are a world document analyzer. Given the following text from a story or world-building document, \
extract all structured world-building information.

Return JSON in this exact format:
{
  "rules": [{"name": "...", "category": "...", "description": "...", "l0": "...", "l1": "..."}],
  "locations": [{"name": "...", "type": "...", "description": "...", "l0": "...", "l1": "..."}],
  "factions": [{"name": "...", "type": "...", "description": "...", "l0": "...", "l1": "..."}],
  "timeline": [{"name": "...", "era": "...", "description": "...", "l0": "...", "l1": "..."}],
  "characters": [{"name": "...", "role": "...", "description": "...", "affiliations": ["..."]}]
}

Only include information explicitly stated or strongly implied in the text. \
If no information is found for a category, return an empty array.\
"""


@dataclass
class ParsedDocument:
    """Result of parsing a document through the LLM."""

    raw_text: str
    extracted_world: WorldState = field(default_factory=WorldState)
    entities: list[dict[str, Any]] = field(default_factory=list)


class DocumentParser:
    """Parse uploaded documents and extract world/character data via LLM.

    Supports: PDF (via PyMuPDF), Markdown, and plain text.
    Large documents are split into chunks (max 50K chars each) to stay within
    context limits.
    """

    _CHUNK_SIZE = 50_000

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client

    @staticmethod
    def supported_formats() -> list[str]:
        return ["pdf", "md", "txt"]

    async def parse(self, file_path: str) -> ParsedDocument:
        """Read *file_path* and extract structured world data."""
        raw_text = self._read_file(file_path)

        if len(raw_text) > self._CHUNK_SIZE:
            return await self._parse_large(raw_text)
        return await self._parse_single(raw_text)

    # ---- LLM extraction ----

    async def _parse_single(self, text: str) -> ParsedDocument:
        result = await self._extract_chunk(text)
        return ParsedDocument(
            raw_text=text,
            extracted_world=WorldState(
                rules=result.get("rules", []),
                locations=result.get("locations", []),
                factions=result.get("factions", []),
                timeline=result.get("timeline", []),
            ),
            entities=result.get("characters", []),
        )

    async def _parse_large(self, text: str) -> ParsedDocument:
        chunks = [
            text[i : i + self._CHUNK_SIZE]
            for i in range(0, len(text), self._CHUNK_SIZE)
        ]
        combined = WorldState()
        all_entities: list[dict[str, Any]] = []

        for chunk in chunks:
            result = await self._extract_chunk(chunk)
            _merge_into(combined, result)
            all_entities.extend(result.get("characters", []))

        return ParsedDocument(
            raw_text=text,
            extracted_world=combined,
            entities=all_entities,
        )

    async def _extract_chunk(self, text: str) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": _DOC_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ]
        return await self._llm.chat_json(messages)

    # ---- file I/O ----

    @staticmethod
    def _read_file(file_path: str) -> str:
        ext = file_path.rsplit(".", 1)[-1].lower()
        if ext == "pdf":
            return DocumentParser._read_pdf(file_path)
        return DocumentParser._read_text(file_path)

    @staticmethod
    def _read_pdf(file_path: str) -> str:
        import fitz

        doc = fitz.open(file_path)
        parts = [page.get_text() for page in doc]
        doc.close()
        return "\n".join(parts)

    @staticmethod
    def _read_text(file_path: str) -> str:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            return f.read()


def _merge_into(target: WorldState, source: dict[str, Any]) -> None:
    """Merge world data from a parsed dict into an existing WorldState (dedup by name)."""
    for key in ("rules", "locations", "factions", "timeline"):
        existing = getattr(target, key)
        seen = {e.get("name") for e in existing if e.get("name")}
        for item in source.get(key, []):
            if item.get("name") and item["name"] not in seen:
                existing.append(item)
                seen.add(item["name"])
