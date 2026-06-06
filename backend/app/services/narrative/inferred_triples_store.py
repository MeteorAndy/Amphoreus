"""InferredTriplesStore — persists extracted prose facts to the knowledge graph.

Writes InferredTriple records into KuzuStore (finally populating the
Event/Location/Faction node tables and their edges) and mirrors them to
OpenViking for text-search recall. All KuzuStore calls run inside
asyncio.to_thread: the embedded Kuzu Connection is synchronous and single-writer,
so calling it directly from a background asyncio task would block the event loop.

Chapter provenance lives in each node's properties JSON. Kuzu's Cypher dialect
has no JSON-path function, so invalidate_chapter() filters with a string
CONTAINS on the serialized properties column.
"""
from __future__ import annotations

import asyncio
import json

from app.services.memory import MemoryManager

from .types_post_write import InferredTriple, _VALID_NODE_TYPES


class InferredTriplesStore:
    """Adapter writing InferredTriples to Kuzu + OpenViking. Stateless."""

    def __init__(self, memory: MemoryManager) -> None:
        self._memory = memory

    async def persist(self, triples: list[InferredTriple], chapter_id: str) -> None:
        """Upsert each triple's endpoints as nodes and add the edge when legal.

        create_node is a MERGE upsert keyed on name, so repeated calls are safe.
        Edges are only written when the predicate + endpoint types form a valid
        schema row (triple.edge_is_valid). All Kuzu work is offloaded to a thread.
        """
        if not triples:
            return
        await asyncio.to_thread(self._persist_sync, triples, chapter_id)
        self._mirror_to_openviking(triples, chapter_id)

    def _persist_sync(self, triples: list[InferredTriple], chapter_id: str) -> None:
        kuzu = self._memory.kuzu
        for t in triples:
            props_s = {"name": t.subject, "chapter_id": chapter_id,
                       "source_type": t.source_type}
            props_o = {"name": t.object_, "chapter_id": chapter_id,
                       "source_type": t.source_type}
            kuzu.create_node(t.subject_type, props_s)
            kuzu.create_node(t.object_type, props_o)
            if t.edge_is_valid():
                kuzu.create_edge(
                    t.subject, t.object_, t.predicate,
                    {"chapter_id": chapter_id, "confidence": t.confidence},
                )

    def _mirror_to_openviking(
        self, triples: list[InferredTriple], chapter_id: str
    ) -> None:
        payload = json.dumps(
            {"chapter_id": chapter_id, "triples": [t.to_dict() for t in triples]},
            ensure_ascii=False,
        )
        self._memory.openviking.write_entry(
            f"story/chapters/{chapter_id}/inferred_triples",
            payload, l0="inferred_triples", l1=chapter_id,
        )

    async def invalidate_chapter(self, chapter_id: str) -> None:
        """Delete all inferred nodes (and their edges) planted by *chapter_id*.

        Used when a chapter is rewritten. Kuzu has no JSON-path function, so we
        match on a CONTAINS fragment of the serialized properties column.
        """
        await asyncio.to_thread(self._invalidate_sync, chapter_id)
        try:
            self._memory.openviking.delete_entry(
                f"story/chapters/{chapter_id}/inferred_triples"
            )
        except Exception:
            pass

    def _invalidate_sync(self, chapter_id: str) -> None:
        kuzu = self._memory.kuzu
        fragment = json.dumps({"chapter_id": chapter_id}, ensure_ascii=False)[1:-1]
        for label in _VALID_NODE_TYPES:
            kuzu.query_cypher(
                f"MATCH (n:{label}) WHERE n.properties CONTAINS $frag DETACH DELETE n",
                {"frag": fragment},
            )
