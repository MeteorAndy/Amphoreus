from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from app.core.i18n import get_lang, Lang
from app.core.llm_client import LLMClient
from app.models.character import CharacterProfile
from app.services.memory import MemoryManager
from app.services.world_builder import WorldState

_RELATIONSHIP_SYSTEM_PROMPT_EN = """\
You are analyzing character relationships for a story world. Given the following \
world context and character profiles, infer the most likely relationships between \
these characters.

For each relationship, determine:
- from_id: the source character ID
- to_id: the target character ID
- rel_type: one of ALLY, RIVAL, ENEMY, FAMILY, MENTOR, ROMANTIC, UNKNOWN
- strength: 0.0 to 1.0 indicating how strong the relationship is
- description: a brief description of the relationship
- established_event: what event or circumstance established this relationship

You MUST respond ONLY with valid JSON in this exact format:
{"relationships": [{"from_id": "...", "to_id": "...", "rel_type": "ALLY", \
"strength": 0.0, "description": "...", "established_event": "..."}]}"""

_RELATIONSHIP_SYSTEM_PROMPT_ZH = """\
你正在分析一个故事世界中的人物关系。根据给定的世界背景和角色档案，推断这些角色之间最可能存在的关系。

每个关系需要确定：
- from_id: 源角色 ID
- to_id: 目标角色 ID
- rel_type: 关系类型，可选 ALLY（盟友）、RIVAL（竞争对手）、ENEMY（敌人）、FAMILY（家族）、MENTOR（师徒）、ROMANTIC（恋情）、UNKNOWN（未知）
- strength: 0.0 到 1.0，表示关系强度
- description: 关系描述（使用简体中文）
- established_event: 建立此关系的事件或情境（使用简体中文）

重要提示：
- description 和 established_event 必须使用简体中文
- from_id、to_id、rel_type、strength 保持英文/数值
- 关系描述要具体而生动，反映角色之间真实的情感纽带

你必须严格按照以下 JSON 格式回复，且只回复 JSON：
{"relationships": [{"from_id": "...", "to_id": "...", "rel_type": "ALLY", \
"strength": 0.0, "description": "...", "established_event": "..."}]}"""


def _get_relationship_prompt() -> str:
    return _RELATIONSHIP_SYSTEM_PROMPT_ZH if get_lang() == Lang.ZH else _RELATIONSHIP_SYSTEM_PROMPT_EN

_RELATES_TO = "RELATES_TO"


@dataclass
class Relationship:
    from_id: str
    to_id: str
    rel_type: str  # ALLY, RIVAL, ENEMY, FAMILY, MENTOR, ROMANTIC, UNKNOWN
    strength: float  # 0-1
    description: str
    established_event: str  # what event established this relationship


@dataclass
class PathStep:
    from_id: str
    to_id: str
    rel_type: str
    description: str


@dataclass
class NetworkGraph:
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)


class RelationshipBuilder:
    """Infers and manages character relationships using Kuzu graph."""

    def __init__(self, llm_client: LLMClient, memory_manager: MemoryManager) -> None:
        self._llm = llm_client
        self._ov = memory_manager.openviking
        self._kuzu = memory_manager.kuzu

    async def build_relationships(
        self, characters: list[CharacterProfile], world: WorldState
    ) -> list[Relationship]:
        """Infer relationships between characters using the LLM and store in Kuzu."""
        if len(characters) < 2:
            return []

        prompt = self._build_relationship_prompt(characters, world)
        result = await self._llm.chat_json(prompt)

        raw_relationships: list[dict[str, Any]] = result.get("relationships", [])
        relationships: list[Relationship] = []

        for raw in raw_relationships:
            rel = self._parse_relationship(raw)
            relationships.append(rel)
            self._store_relationship(rel)

        return relationships

    async def update_relationship(
        self, from_id: str, to_id: str, changes: dict[str, Any]
    ) -> None:
        """Update properties on an existing RELATES_TO edge."""
        # Read existing edge properties via Cypher
        rows = self._kuzu.query_cypher(
            "MATCH (a:Character {name: $from})-[r:RELATES_TO]->(b:Character {name: $to}) "
            "RETURN r.properties",
            {"from": from_id, "to": to_id},
        )
        if not rows:
            return

        props_raw: str = rows[0].get("r.properties", "{}")
        try:
            current_props: dict[str, Any] = json.loads(props_raw)
        except (json.JSONDecodeError, TypeError):
            current_props = {}

        current_props.update(changes)

        # Delete and recreate the edge with merged properties
        self._kuzu.delete_edge(from_id, to_id, _RELATES_TO)
        self._kuzu.create_edge(from_id, to_id, _RELATES_TO, current_props)

    async def get_relationship_path(
        self, from_id: str, to_id: str
    ) -> list[PathStep]:
        """Find the shortest path between two characters in the relationship graph."""
        paths = self._kuzu.query_paths(from_id, to_id, max_hops=5)
        if not paths:
            return []

        # Return the first (shortest) path
        path = paths[0]
        steps: list[PathStep] = []

        for edge in path.edges:
            edge_props_raw: str = edge.get("properties", "{}")
            try:
                edge_props: dict[str, Any] = json.loads(edge_props_raw)
            except (json.JSONDecodeError, TypeError):
                edge_props = {}

            src: Any = edge.get("from", {})
            dst: Any = edge.get("to", {})

            steps.append(
                PathStep(
                    from_id=src.get("name", "") if isinstance(src, dict) else str(src),
                    to_id=dst.get("name", "") if isinstance(dst, dict) else str(dst),
                    rel_type=edge.get("rel_type", ""),
                    description=edge_props.get("description", ""),
                )
            )

        return steps

    async def get_character_network(
        self, char_id: str, depth: int = 2
    ) -> NetworkGraph:
        """Get the subgraph of characters connected to *char_id* within *depth* hops."""
        rows = self._kuzu.query_cypher(
            "MATCH (c:Character {name: $name}) "
            "OPTIONAL MATCH (c)-[r:RELATES_TO]-(n:Character) "
            "RETURN n.name AS name, n.properties AS props, "
            "  r.properties AS rel_props",
            {"name": char_id},
        )

        seen_nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []

        for row in rows:
            node_name: str = row.get("name", "")
            if not node_name:
                continue

            if node_name not in seen_nodes:
                props_raw: str = row.get("props", "{}")
                try:
                    node_props: dict[str, Any] = json.loads(props_raw)
                except (json.JSONDecodeError, TypeError):
                    node_props = {}
                seen_nodes[node_name] = node_props

            rel_props_raw: str = row.get("rel_props", "{}")
            try:
                rel_props: dict[str, Any] = json.loads(rel_props_raw)
            except (json.JSONDecodeError, TypeError):
                rel_props = {}

            edges.append(
                {
                    "from": char_id,
                    "to": node_name,
                    **rel_props,
                }
            )

        return NetworkGraph(
            nodes=[
                {"name": nid, **props} for nid, props in seen_nodes.items()
            ],
            edges=edges,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_relationship_prompt(
        self, characters: list[CharacterProfile], world: WorldState
    ) -> list[dict[str, str]]:
        world_desc = json.dumps(
            {
                "rules": world.rules,
                "locations": world.locations,
                "factions": world.factions,
                "timeline": world.timeline,
            },
            indent=2,
            ensure_ascii=False,
        )

        char_summaries = [
            {
                "id": c.id,
                "name": c.name,
                "role": c.role,
                "core_desire": c.core_desire,
                "core_traits": c.personality.core_traits,
            }
            for c in characters
        ]

        return [
            {"role": "system", "content": _get_relationship_prompt()},
            {
                "role": "user",
                "content": (
                    f"World context:\n{world_desc}\n\n"
                    f"Characters:\n{json.dumps(char_summaries, indent=2, ensure_ascii=False)}\n\n"
                    f"Infer relationships for these {len(characters)} characters."
                ),
            },
        ]

    def _parse_relationship(self, raw: dict[str, Any]) -> Relationship:
        return Relationship(
            from_id=raw.get("from_id", ""),
            to_id=raw.get("to_id", ""),
            rel_type=raw.get("rel_type", "UNKNOWN"),
            strength=float(raw.get("strength", 0.5)),
            description=raw.get("description", ""),
            established_event=raw.get("established_event", ""),
        )

    def _store_relationship(self, rel: Relationship) -> None:
        """Persist a single relationship as a Kuzu RELATES_TO edge."""
        props: dict[str, Any] = {
            "rel_type": rel.rel_type,
            "strength": rel.strength,
            "description": rel.description,
            "established_event": rel.established_event,
        }

        try:
            self._kuzu.create_edge(
                rel.from_id,
                rel.to_id,
                _RELATES_TO,
                props,
            )
        except Exception:
            # Nodes may not exist yet; skip silently
            pass
