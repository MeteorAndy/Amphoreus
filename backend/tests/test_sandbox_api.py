"""TDD tests for Sandbox Observation Mode API.

Written BEFORE implementation (RED phase).
Defines expected behavior of /api/sandbox/* endpoints.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_sandbox_start_returns_session_id(client):
    r = await client.post("/api/sandbox/start", json={"world_id": "w1", "character_ids": ["c1", "c2"]})
    assert r.status_code == 200
    data = r.json()
    assert "session_id" in data
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_sandbox_start_requires_world_id(client):
    r = await client.post("/api/sandbox/start", json={"character_ids": ["c1"]})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_sandbox_inject_valid_session(client):
    r1 = await client.post("/api/sandbox/start", json={"world_id": "w1", "character_ids": ["c1"]})
    sid = r1.json()["session_id"]
    r2 = await client.post("/api/sandbox/inject", json={"session_id": sid, "event": "A storm arrives"})
    assert r2.status_code == 200
    assert r2.json()["ok"] is True


@pytest.mark.asyncio
async def test_sandbox_inject_invalid_session(client):
    r = await client.post("/api/sandbox/inject", json={"session_id": "nonexistent", "event": "test"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_sandbox_stop(client):
    r1 = await client.post("/api/sandbox/start", json={"world_id": "w1", "character_ids": ["c1"]})
    sid = r1.json()["session_id"]
    r2 = await client.post("/api/sandbox/stop", json={"session_id": sid})
    assert r2.status_code == 200
    assert r2.json()["ok"] is True
    assert "rounds" in r2.json()


@pytest.mark.asyncio
async def test_sandbox_feed_returns_sse(client):
    r1 = await client.post("/api/sandbox/start", json={"world_id": "w1", "character_ids": ["c1"]})
    sid = r1.json()["session_id"]
    r = await client.get(f"/api/sandbox/{sid}/feed")
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]
