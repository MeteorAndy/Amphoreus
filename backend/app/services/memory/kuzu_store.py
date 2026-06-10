from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import kuzu

from app.core.config import Settings

_NODE_LABELS = ("Character", "Location", "Faction", "Event")
_EDGE_LABELS = ("RELATES_TO", "BELONGS_TO", "LOCATED_AT", "CAUSED_BY")

_NODE_SCHEMA: dict[str, tuple[str, ...]] = {
    "Character": ("Character", "Character"),
    "Location": ("Location", "Location"),
    "Faction": ("Faction", "Faction"),
    "Event": ("Event", "Event"),
}

_EDGE_SCHEMA: dict[str, tuple[str, str]] = {
    "RELATES_TO": ("Character", "Character"),
    "BELONGS_TO": ("Character", "Faction"),
    "LOCATED_AT": ("Character", "Location"),
    "CAUSED_BY": ("Event", "Event"),
}

# Properties are stored as ONE serialized-JSON string column. Substring
# matching against that column (e.g. chapter invalidation) only works if the
# serializer and the fragment builder agree byte-for-byte, so both live here:
# create_node/create_edge serialize with _PROPS_SEPARATORS pinned (identical to
# json.dumps defaults today, but now explicit and auditable), and
# props_fragment() builds match fragments with the SAME separators + encoding.
_PROPS_SEPARATORS = (", ", ": ")


def props_fragment(key: str, value: str) -> str:
    """A substring guaranteed to appear in a properties column that was
    serialized by this module with {key: value}. The trailing quote from
    json.dumps(value) doubles as a delimiter, so "s1" never matches "s10"."""
    return (
        json.dumps(key, ensure_ascii=False)
        + ": "
        + json.dumps(value, ensure_ascii=False)
    )


@dataclass
class PathResult:
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    length: int


class KuzuStore:
    """Embedded graph database for character relationships and world structure."""

    def __init__(self, settings: Settings) -> None:
        db_dir: Path = settings.data_dir / "kuzu"
        db_dir.mkdir(parents=True, exist_ok=True)
        self._db_path: str = str(db_dir / "store.db")
        self._db: kuzu.Database | None = None
        self._conn: kuzu.Connection | None = None
        self._initialized: bool = False

    # ── Schema ─────────────────────────────────────────────────

    def ensure_schema(self) -> None:
        """Create node/rel tables if they do not exist."""
        if self._initialized:
            return
        self._db = kuzu.Database(self._db_path)
        self._conn = kuzu.Connection(self._db)

        for label in _NODE_SCHEMA:
            self._execute(
                f"CREATE NODE TABLE IF NOT EXISTS {label} "
                f"(name STRING, properties STRING, PRIMARY KEY (name))"
            )
        for label, (from_lbl, to_lbl) in _EDGE_SCHEMA.items():
            self._execute(
                f"CREATE REL TABLE IF NOT EXISTS {label} "
                f"(FROM {from_lbl} TO {to_lbl}, properties STRING)"
            )
        self._initialized = True

    # ── Node CRUD ──────────────────────────────────────────────

    def create_node(self, label: str, properties: dict[str, Any]) -> str:
        """Create a node and return its name (the primary key)."""
        name = properties.get("name", "")
        if not name:
            msg = f"'name' is required in properties for label '{label}'"
            raise ValueError(msg)

        props_json = json.dumps(properties, ensure_ascii=False,
                                separators=_PROPS_SEPARATORS)
        self._execute(
            f"MERGE (n:{label} {{name: $name}}) "
            f"ON CREATE SET n.properties = $props "
            f"ON MATCH SET n.properties = $props",
            {"name": name, "props": props_json},
        )
        return name

    def update_node(self, node_id: str, label: str, properties: dict[str, Any]) -> None:
        """Update a node's properties by name."""
        props_json = json.dumps(properties, ensure_ascii=False,
                                separators=_PROPS_SEPARATORS)
        self._execute(
            f"MATCH (n:{label}) WHERE n.name = $name "
            f"SET n.properties = $props",
            {"name": node_id, "props": props_json},
        )

    def delete_node(self, node_id: str) -> None:
        """Delete a node by name across all known labels (detaches edges)."""
        for label in _NODE_LABELS:
            self._execute(
                f"MATCH (n:{label}) WHERE n.name = $name DETACH DELETE n",
                {"name": node_id},
            )

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        """Return the first node matching *node_id* across all labels, or None."""
        for label in _NODE_LABELS:
            result = self._execute(
                f"MATCH (n:{label}) WHERE n.name = $name "
                f"RETURN n.name, n.properties, labels(n) AS lbl",
                {"name": node_id},
            )
            while result.has_next():
                row = result.get_next()
                props_raw: str = row[1]
                try:
                    props = json.loads(props_raw)
                except (json.JSONDecodeError, TypeError):
                    props = {}
                return {"name": row[0], "label": row[2][0] if row[2] else label, **props}
        return None

    # ── Edge CRUD ──────────────────────────────────────────────

    def create_edge(
        self,
        from_id: str,
        to_id: str,
        rel_type: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        """Create a directed edge from *from_id* to *to_id* with the given *rel_type*."""
        if rel_type not in _EDGE_SCHEMA:
            msg = f"Unknown rel_type '{rel_type}'. Valid: {', '.join(_EDGE_LABELS)}"
            raise ValueError(msg)

        src_label, dst_label = _EDGE_SCHEMA[rel_type]
        props = properties or {}
        props_json = json.dumps(props, ensure_ascii=False,
                                separators=_PROPS_SEPARATORS)

        self._execute(
            f"MATCH (a:{src_label}), (b:{dst_label}) "
            f"WHERE a.name = $from AND b.name = $to "
            f"CREATE (a)-[:{rel_type} {{properties: $props}}]->(b)",
            {"from": from_id, "to": to_id, "props": props_json},
        )

    def delete_edge(self, from_id: str, to_id: str, rel_type: str) -> None:
        """Delete all edges of *rel_type* between the two nodes."""
        if rel_type not in _EDGE_SCHEMA:
            return
        self._execute(
            f"MATCH (a)-[r:{rel_type}]->(b) "
            f"WHERE a.name = $from AND b.name = $to "
            f"DELETE r",
            {"from": from_id, "to": to_id},
        )

    # ── Query ──────────────────────────────────────────────────

    def query_paths(
        self, from_id: str, to_id: str, *, max_hops: int = 3
    ) -> list[PathResult]:
        """Find paths between two nodes using variable-length traversal."""
        # Kuzu does not support parameterised variable-length bounds, so
        # max_hops is injected directly. All other parameters use $placeholders.
        cypher = (
            f"MATCH p = (a)-[*1..{max_hops}]-(b) "
            "WHERE a.name = $from AND b.name = $to "
            "RETURN p LIMIT 20"
        )
        result = self._execute(cypher, {"from": from_id, "to": to_id})

        paths: list[PathResult] = []
        while result.has_next():
            row = result.get_next()
            path_data = row[0]  # the path object

            nodes_raw: list[dict[str, Any]] = path_data.get("_nodes", [])
            rels_raw: list[dict[str, Any]] = path_data.get("_rels", [])

            pruned_nodes = []
            for n in nodes_raw:
                pruned_nodes.append({
                    "name": n.get("name", ""),
                    "label": n.get("_label", ""),
                    "properties": n.get("properties", ""),
                })

            pruned_edges = []
            for r in rels_raw:
                pruned_edges.append({
                    "rel_type": r.get("_label", ""),
                    "from": r.get("_src", {}),
                    "to": r.get("_dst", {}),
                    "properties": r.get("properties", ""),
                })

            paths.append(
                PathResult(
                    nodes=pruned_nodes,
                    edges=pruned_edges,
                    length=len(pruned_edges),
                )
            )

        return paths

    def query_cypher(
        self, cypher: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute arbitrary Cypher and return results as a list of dicts."""
        result = self._execute(cypher, params or {})
        col_names: list[str] = result.get_column_names()
        rows: list[dict[str, Any]] = []
        while result.has_next():
            raw = result.get_next()
            row = {}
            for i, col in enumerate(col_names):
                val = raw[i]
                if isinstance(val, bytes):
                    val = val.decode("utf-8")
                row[col] = val
            rows.append(row)
        return rows

    # ── Internal ───────────────────────────────────────────────

    def _execute(self, cypher: str, params: dict[str, Any] | None = None) -> Any:
        if self._conn is None:
            raise RuntimeError("KuzuStore not initialized. Call ensure_schema() first.")
        return self._conn.execute(cypher, params or {})
