"""InferredTriplesStore — persists extracted prose facts to the knowledge graph.

Writes InferredTriple records into KuzuStore (finally populating the
Event/Location/Faction node tables and their edges) and mirrors them to
OpenViking for text-search recall. All KuzuStore calls run inside
asyncio.to_thread: the embedded Kuzu Connection is synchronous and single-writer,
so calling it directly from a background asyncio task would block the event loop.

Chapter provenance is split across two layers so MERGE-overwrite on nodes never
corrupts it:

  Nodes (entity identity only):  name + source_type.
    We only create a node if that label/name does not already exist, because
    KuzuStore.create_node MERGEs by name and overwrites the entire properties
    JSON. chapter_id CANNOT live here (ch1+ch5 entities lose ch1's entry), and
    post-write extraction must not clobber character/world nodes created by
    earlier pipeline stages.

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

from .types_post_write import InferredTriple


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
            # Nodes: identity only (no chapter_id). Avoid overwriting core
            # character/world nodes that earlier pipeline stages already own.
            self._ensure_node(t.subject_type, t.subject, t.source_type)
            self._ensure_node(t.object_type, t.object_, t.source_type)
            # Edges: carry chapter provenance + confidence.
            if t.edge_is_valid():
                kuzu.create_edge(
                    t.subject, t.object_, t.predicate,
                    {"chapter_id": chapter_id, "confidence": t.confidence,
                     "source_type": t.source_type},
                )

    def _ensure_node(self, label: str, name: str, source_type: str) -> None:
        rows = self._memory.kuzu.query_cypher(
            f"MATCH (n:{label}) WHERE n.name = $name RETURN n.name AS name LIMIT 1",
            {"name": name},
        )
        if rows:
            return
        self._memory.kuzu.create_node(label, {"name": name, "source_type": source_type})

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
        """Delete the chapter_inferred EDGES contributed by *chapter_id*, then
        remove endpoint nodes left with zero edges (true orphans).

        Matching: both fragments come from kuzu_store.props_fragment, which
        shares the exact separators/encoding the serializer pins — a hand-built
        fragment previously diverged on a colon-space and silently matched
        nothing. The fragment's trailing quote is the delimiter that keeps
        "s1" from matching "s10"; ensure_ascii=False keeps ZH chapter ids
        matching their raw-UTF-8 storage.

        source_type gating is structural: every WHERE also requires the
        chapter_inferred fragment, so manual/bible edges are untouchable.

        Orphan cleanup is ENDPOINT-SCOPED, never a global sweep: only nodes
        that were endpoints of the just-deleted edges are candidates, only if
        their remaining degree across all rel tables is zero, and only if the
        node itself was created as chapter_inferred. Core character/world nodes
        created by earlier stages survive even when temporarily edge-less.
        """
        from app.services.memory.kuzu_store import _EDGE_SCHEMA, props_fragment

        kuzu = self._memory.kuzu
        params = {
            "ch": props_fragment("chapter_id", chapter_id),
            "src": props_fragment("source_type", "chapter_inferred"),
        }

        # 1) Collect endpoints of the doomed edges (orphan candidates), then
        # 2) delete those edges — per label, gated on BOTH fragments.
        candidates: set[tuple[str, str]] = set()
        for label, (from_lbl, to_lbl) in _EDGE_SCHEMA.items():
            rows = kuzu.query_cypher(
                f"MATCH (a:{from_lbl})-[e:{label}]->(b:{to_lbl}) "
                "WHERE e.properties CONTAINS $ch AND e.properties CONTAINS $src "
                "RETURN DISTINCT a.name AS a_name, b.name AS b_name",
                params,
            )
            for r in rows:
                candidates.add((from_lbl, r["a_name"]))
                candidates.add((to_lbl, r["b_name"]))
            kuzu.query_cypher(
                f"MATCH (:{from_lbl})-[e:{label}]->(:{to_lbl}) "
                "WHERE e.properties CONTAINS $ch AND e.properties CONTAINS $src "
                "DELETE e",
                params,
            )

        # 3) Remove candidates whose total degree is now zero.
        for node_label, name in candidates:
            degree_rows = kuzu.query_cypher(
                f"MATCH (n:{node_label})-[e]-() WHERE n.name = $name "
                "RETURN count(e) AS degree",
                {"name": name},
            )
            degree = degree_rows[0]["degree"] if degree_rows else 0
            props_rows = kuzu.query_cypher(
                f"MATCH (n:{node_label}) WHERE n.name = $name "
                "RETURN n.properties AS properties",
                {"name": name},
            )
            node_props = {}
            if props_rows:
                try:
                    node_props = json.loads(props_rows[0]["properties"])
                except (json.JSONDecodeError, TypeError):
                    node_props = {}
            if degree == 0 and node_props.get("source_type") == "chapter_inferred":
                kuzu.query_cypher(
                    f"MATCH (n:{node_label}) WHERE n.name = $name DELETE n",
                    {"name": name},
                )
