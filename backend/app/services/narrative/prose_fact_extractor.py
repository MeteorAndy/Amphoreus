"""ProseFactExtractor — LLM-backed S/P/O triple extraction from finished prose.

Reads a rendered chapter back and emits InferredTriple records for the facts
the prose explicitly asserts. Stateless. Degrades to an empty list on any LLM
or parse error so a post-write background task never surfaces an exception.
"""
from __future__ import annotations

from app.core.i18n import get_lang, Lang
from app.core.llm_client import LLMClient, LLMError

from .prompts import _get_prose_fact_extractor_prompt
from .types_post_write import InferredTriple, _VALID_NODE_TYPES


class ProseFactExtractor:
    """Extracts knowledge-graph triples from prose via a single LLM call."""

    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    async def extract(self, prose: str, chapter_id: str) -> list[InferredTriple]:
        """Return triples explicitly asserted by *prose*. Never raises.

        Malformed payloads, LLM errors, and individual bad rows are dropped
        silently; the worst case is an empty list.
        """
        if not prose or not prose.strip():
            return []

        messages = [
            {"role": "system", "content": _get_prose_fact_extractor_prompt()},
            {"role": "user", "content": prose},
        ]
        try:
            payload = await self._llm.chat_json(messages, temperature=0.1)
        except (LLMError, Exception):
            return []

        rows = payload.get("triples") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            return []

        triples: list[InferredTriple] = []
        seen: set[tuple[str, str, str]] = set()
        for row in rows:
            triple = self._parse_row(row, chapter_id)
            if triple is None:
                continue
            key = (triple.subject, triple.predicate, triple.object_)
            if key in seen:
                continue
            seen.add(key)
            triples.append(triple)
        return triples

    @staticmethod
    def _parse_row(row: object, chapter_id: str) -> InferredTriple | None:
        """Coerce one raw JSON row into an InferredTriple, or None if unusable."""
        if not isinstance(row, dict):
            return None
        subject = str(row.get("subject", "")).strip()
        obj = str(row.get("object", row.get("object_", ""))).strip()
        predicate = str(row.get("predicate", "")).strip()
        if not subject or not obj or not predicate:
            return None
        s_type = str(row.get("subject_type", "Event")).strip() or "Event"
        o_type = str(row.get("object_type", "Event")).strip() or "Event"
        if s_type not in _VALID_NODE_TYPES or o_type not in _VALID_NODE_TYPES:
            return None
        try:
            confidence = float(row.get("confidence", 0.9))
        except (TypeError, ValueError):
            confidence = 0.9
        return InferredTriple(
            subject=subject, predicate=predicate, object_=obj,
            subject_type=s_type, object_type=o_type,
            chapter_id=chapter_id, confidence=confidence,
        )
