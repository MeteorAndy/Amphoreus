"""InferredTriplesStore — persists extracted prose facts to the knowledge graph.

Writes InferredTriple records into KuzuStore (finally populating the
Event/Location/Faction node tables and their edges) and mirrors them to
OpenViking for text-search recall. All KuzuStore calls run inside
asyncio.to_thread: the embedded Kuzu Connection is synchronous and single-writer,
so calling it directly from a background asyncio task would block the event loop.

Chapter provenance is split across two layers so MERGE-overwrite on nodes never
corrupts it:

  Nodes (entity identity only):  name + source_type.
    create_node MERGEs by name; ON MATCH SET overwrites the entire properties
    JSON, so chapter_id CANNOT live here (ch1+ch5 entities lose ch1's entry).

  Edges (chapter-scoped facts):  carry chapter_id + confidence.
    Edges are CREATE, never MERGE — clean, append-only, per-chapter.

  Invalidation targets EDGES, not nodes.  When a chapter is rewritten we delete
  only the edges that chapter produced; entity nodes survive (they are useful
  knowledge and may be referenced across chapters). We also clean up orphan
  nodes — any endpoint whose only remaining edges were the ones we just deleted.

  source_type gating:  only 'chapter_inferred' edges are eligible for deletion;
  manual/bible edges (if they are ever written here) survive unconditionally.
"""

from __future__ import annotations

import asyncio
import json

from app.services.memory import MemoryManager

from .types_post_write import InferredTriple, _VALID_NODE_TYPES

_EDGE_LABELS = ("RELATES_TO", "BELONGS_TO", "LOCATED_AT", "CAUSED_BY")


class InferredTriplesStore:
    """Adapter writing InferredTriples to Kuzu + OpenViking. Stateless."""

    def __init__(self, memory: MemoryManager) -> None:
        self._memory = memory

    async def persist(self, triples: list[InferredTriple], chapter_id: str) -> None:
        if not triples:
            return
        await asyncio.to_thread(self._persist_sync, triples, chapter_id)
        self._mirror_to_openviking(triples, chapter_id)

    def _persist_sync(self, triples: list[InferredTriple], chapter_id: str) -> None:
        kuzu = self._memory.kuzu
        for t in triples:
            # Nodes: identity only (no chapter_id — MERGE overwrites it).
            kuzu.create_node(t.subject_type, {"name": t.subject,
                                              "source_type": t.source_type})
            kuzu.create_node(t.object_type, {"name": t.object_,
                                             "source_type": t.source_type})
            # Edges: carry chapter provenance + confidence.
            if t.edge_is_valid():
                kuzu.create_edge(
                    t.subject, t.object_, t.predicate,
                    {"chapter_id": chapter_id, "confidence": t.confidence,
                     "source_type": t.source_type},
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
        await asyncio.to_thread(self._invalidate_sync, chapter_id)
        try:
            self._memory.openviking.delete_entry(
                f"story/chapters/{chapter_id}/inferred_triples"
            )
        except Exception:
            pass

    def _invalidate_sync(self, chapter_id: str) -> None:
        """Delete only the EDGES contributed by *chapter_id*, not the entity nodes.

        Before the fix, we DETACH DELETE'd nodes whose properties CONTAINed
        the chapter_id fragment — but create_node MERGE-overwrites properties,
        so a ch1+ch5 entity only kept ch5's id: rewriting ch1 missed its
        edges, and rewriting ch5 deleted ch1's edges too.

        Now we target edges directly (each edge is CREATE, never MERGE, so its
        properties are per-chapter and append-only). The CONTAINS fragment
        matches the serialised chapter_id key-value pair in edge.properties.
        source_type gating ensures only 'chapter_inferred' edges are eligible.
        """
        kuzu = self._memory.kuzu
        # Serialised JSON key-value as a CONTAINS fragment.
        # json.dumps wraps strings in quotes, so for chapter_id="s1" we get
        #   "chapter_id":"s1"
        # We match that literal substring anywhere in edge.properties.
        frag = json.dumps("chapter_id") + ":" + json.dumps(chapter_id)
        for label in ("RELATES_TO", "BELONGS_TO", "LOCATED_AT", "CAUSED_BY"):
            kuzu.query_cypher(
                f"MATCH ()-[e:{label}]->() "
                "WHERE e.properties CONTAINS $frag "
                "DELETE e",
                {"frag": frag},
            )
