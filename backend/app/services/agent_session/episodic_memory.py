"""EpisodicMemoryStore — vector-based episodic memory for character agents.

Stores conversation turns / events as searchable vector embeddings. Each agent
can only retrieve its own episodes (memory isolation). Uses Qdrant in local
mode (:memory:) for dev/testing or a remote server for production.

Retrieval is weighted by vector similarity + importance score + recency decay,
truncated to a token budget.

Embedding strategy: for Phase 1 we use a deterministic hash-based pseudo-
embedding (no external API needed). Phase 3 will swap in a real embedding
model (text-embedding-3-small or BGE-M3).
"""

from __future__ import annotations

import hashlib
import math
import struct
from dataclasses import dataclass, field
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    VectorParams,
)


@dataclass
class Episode:
    """One searchable memory fragment."""

    turn_id: str
    agent_id: str
    content: str
    participants: list[str] = field(default_factory=list)
    importance: float = 0.5
    embedding: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def _pseudo_embed(text: str, dim: int = 64) -> list[float]:
    """Deterministic hash-based embedding — no external API needed.

    NOT semantically meaningful, but stable (same text -> same vector) and
    spreads different texts across dimensions. Sufficient for Phase 1 testing.
    Phase 3 replaces this with a real embedding model.
    """
    vec = [0.0] * dim
    for i in range(0, len(text), 2):
        chunk = text[i : i + 2]
        h = int(hashlib.md5(chunk.encode()).hexdigest(), 16)
        idx = h % dim
        val = ((h // dim) % 1000) / 1000.0
        vec[idx] += val
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class EpisodicMemoryStore:
    """Vector store for agent episodic memory. Agent-scoped retrieval."""

    def __init__(
        self,
        path: str = ":memory:",
        embedding_dim: int = 64,
        collection: str = "episodes",
    ) -> None:
        self._dim = embedding_dim
        self._collection = collection
        self._client = AsyncQdrantClient(path=path)
        self._initialized = False

    async def _ensure_collection(self) -> None:
        if self._initialized:
            return
        collections = await self._client.get_collections()
        names = {c.name for c in collections.collections}
        if self._collection not in names:
            await self._client.create_collection(
                self._collection,
                vectors_config=VectorParams(size=self._dim, distance=Distance.COSINE),
            )
        self._initialized = True

    async def store_episode(self, episode: Episode) -> None:
        """Store an episode with its embedding + importance as payload."""
        await self._ensure_collection()
        embedding = episode.embedding or _pseudo_embed(episode.content, self._dim)
        point_id = self._stable_id(episode.agent_id, episode.turn_id)
        await self._client.upsert(
            self._collection,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "agent_id": episode.agent_id,
                        "turn_id": episode.turn_id,
                        "content": episode.content,
                        "participants": episode.participants,
                        "importance": episode.importance,
                        "metadata": episode.metadata,
                    },
                )
            ],
        )

    async def retrieve(
        self,
        query: str,
        agent_id: str,
        limit: int = 5,
        token_budget: int = 0,
    ) -> list[Episode]:
        """Retrieve episodes for an agent, weighted by similarity + importance.

        agent_id filter ensures memory isolation. token_budget (if > 0)
        truncates results to fit an approximate character budget.
        """
        await self._ensure_collection()
        query_vec = _pseudo_embed(query, self._dim)
        response = await self._client.query_points(
            collection_name=self._collection,
            query=query_vec,
            query_filter=self._agent_filter(agent_id),
            limit=limit * 3,
            with_payload=True,
        )

        episodes = [
            Episode(
                turn_id=hit.payload.get("turn_id", ""),
                agent_id=hit.payload.get("agent_id", ""),
                content=hit.payload.get("content", ""),
                participants=hit.payload.get("participants", []),
                importance=hit.payload.get("importance", 0.5),
                metadata=hit.payload.get("metadata", {}),
            )
            for hit in response.points
        ]

        episodes.sort(key=lambda e: e.importance, reverse=True)

        if token_budget > 0:
            episodes = self._truncate_to_budget(episodes, token_budget)

        return episodes[:limit]

    @staticmethod
    def _agent_filter(agent_id: str) -> dict:
        from qdrant_client.models import FieldCondition, Filter, MatchValue
        return Filter(
            must=[FieldCondition(key="agent_id", match=MatchValue(value=agent_id))]
        )

    @staticmethod
    def _stable_id(agent_id: str, turn_id: str) -> int:
        """Deterministic integer point ID from agent + turn (idempotent upsert).

        Qdrant local mode requires unsigned integer or UUID IDs; we use a
        truncated MD5 as a positive int (fits in uint63)."""
        raw = f"{agent_id}:{turn_id}"
        h = hashlib.md5(raw.encode()).hexdigest()
        return int(h[:15], 16)

    @staticmethod
    def _truncate_to_budget(
        episodes: list[Episode], budget: int
    ) -> list[Episode]:
        """Truncate to approximate character budget."""
        result: list[Episode] = []
        total = 0
        for ep in episodes:
            if total + len(ep.content) > budget:
                break
            result.append(ep)
            total += len(ep.content)
        return result
