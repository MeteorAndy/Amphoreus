"""TDD tests for Pipeline API endpoint.

These tests are written BEFORE the implementation (RED phase).
They define the expected behavior of POST /api/pipeline/run.
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
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
async def test_pipeline_run_returns_sse_stream(client):
    """Pipeline endpoint should return SSE content type."""
    response = await client.post(
        "/api/pipeline/run",
        json={"seed_idea": "A story about a robot"},
        headers={"Accept": "text/event-stream"},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_pipeline_run_requires_seed_idea(client):
    """Pipeline endpoint should reject requests without seed_idea."""
    response = await client.post("/api/pipeline/run", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_pipeline_run_accepts_full_config(client):
    """Pipeline endpoint should accept all config fields."""
    response = await client.post(
        "/api/pipeline/run",
        json={
            "seed_idea": "A cyberpunk story",
            "lang": "en",
            "character_count": 3,
            "narrative_structure": "hero_journey",
            "output_format": "screenplay",
            "max_rounds_per_scene": 10,
            "auto_refine": False,
        },
    )
    assert response.status_code == 200
