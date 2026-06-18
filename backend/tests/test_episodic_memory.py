"""Tests for EpisodicMemoryStore (Phase 1).

Uses Qdrant local mode (:memory:) — no server needed.
"""

from __future__ import annotations

import pytest

from app.services.agent_session.episodic_memory import (
    Episode,
    EpisodicMemoryStore,
)


def _store() -> EpisodicMemoryStore:
    return EpisodicMemoryStore(":memory:", embedding_dim=64)


def _episode(
    agent_id: str = "a1",
    content: str = "陈漠在锈铁镇遇到了铁颅",
    importance: float = 0.8,
    turn_id: str = "t1",
) -> Episode:
    return Episode(
        turn_id=turn_id,
        agent_id=agent_id,
        content=content,
        participants=["a1", "a2"],
        importance=importance,
    )


# --- Episode model ---

def test_episode_defaults():
    e = Episode(turn_id="t1", agent_id="a1", content="hello")
    assert e.participants == []
    assert e.importance == 0.5
    assert e.embedding is None


# --- store + retrieve ---

@pytest.mark.asyncio
async def test_store_and_retrieve():
    store = _store()
    await store.store_episode(_episode(content="铁颅威胁陈漠交出水"))
    results = await store.retrieve("铁颅做了什么", "a1", limit=1)
    assert len(results) >= 1
    assert "铁颅" in results[0].content


@pytest.mark.asyncio
async def test_retrieve_filters_by_agent():
    store = _store()
    await store.store_episode(_episode(agent_id="a1", content="陈漠的秘密"))
    await store.store_episode(_episode(agent_id="a2", content="铁颅的计划"))
    # a1 should only see its own episodes
    results_a1 = await store.retrieve("秘密", "a1", limit=5)
    assert all(r.agent_id == "a1" for r in results_a1)
    results_a2 = await store.retrieve("计划", "a2", limit=5)
    assert all(r.agent_id == "a2" for r in results_a2)


@pytest.mark.asyncio
async def test_retrieve_empty_store():
    store = _store()
    results = await store.retrieve("anything", "a1")
    assert results == []


@pytest.mark.asyncio
async def test_importance_weighting():
    store = _store()
    # Store a high-importance and low-importance episode with similar content
    await store.store_episode(_episode(
        content="陈漠找到了翡翠眼绿洲的位置",
        importance=0.95, turn_id="t1",
    ))
    await store.store_episode(_episode(
        content="陈漠找到了一块普通的石头",
        importance=0.1, turn_id="t2",
    ))
    # Searching for "找到了" should rank the high-importance one first
    results = await store.retrieve("陈漠找到了", "a1", limit=2)
    assert len(results) >= 2
    assert results[0].importance >= results[1].importance


@pytest.mark.asyncio
async def test_token_budget_truncation():
    store = _store()
    for i in range(10):
        await store.store_episode(_episode(
            content=f"事件编号{i}：" + "很长的内容" * 20,
            importance=0.5 + i * 0.05,
            turn_id=f"t{i}",
        ))
    # Small budget should truncate
    results = await store.retrieve("事件", "a1", token_budget=100)
    total_chars = sum(len(r.content) for r in results)
    assert total_chars <= 200  # roughly bounded
