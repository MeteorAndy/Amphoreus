"""TDD tests for Project Management API.

Written BEFORE implementation (RED phase).
Defines expected behavior of /api/projects endpoints.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import create_app


@pytest.fixture
def app(tmp_path, monkeypatch):
    """Create app with storage redirected to tmp_path."""
    monkeypatch.setenv("THE_WORLD_PROJECTS_DIR", str(tmp_path / "projects"))
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------------------
# POST /api/projects — create
# ---------------------------------------------------------------------------


async def test_create_project_returns_id_name_created_at(client):
    """Creating a project returns id, name, and created_at."""
    resp = await client.post(
        "/api/projects",
        json={"name": "My Epic Story", "seed_idea": "A dragon learns to code"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["name"] == "My Epic Story"
    assert "created_at" in data


async def test_create_project_without_name_returns_422(client):
    """POST /api/projects without name should return 422."""
    resp = await client.post("/api/projects", json={"seed_idea": "something"})
    assert resp.status_code == 422


async def test_create_project_without_seed_idea_returns_422(client):
    """POST /api/projects without seed_idea should return 422."""
    resp = await client.post("/api/projects", json={"name": "My Story"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/projects — list
# ---------------------------------------------------------------------------


async def test_list_projects_returns_empty_initially(client):
    """GET /api/projects returns empty list when no projects exist."""
    resp = await client.get("/api/projects")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {"projects": []}


async def test_list_projects_includes_created_project(client):
    """GET /api/projects includes a project after it is created."""
    await client.post(
        "/api/projects",
        json={"name": "Story Alpha", "seed_idea": "A wizard in space"},
    )
    resp = await client.get("/api/projects")
    assert resp.status_code == 200
    projects = resp.json()["projects"]
    assert len(projects) == 1
    p = projects[0]
    assert p["name"] == "Story Alpha"
    assert "id" in p
    assert "created_at" in p
    assert "updated_at" in p
    assert "last_stage" in p


# ---------------------------------------------------------------------------
# GET /api/projects/{id} — load
# ---------------------------------------------------------------------------


async def test_get_project_returns_full_state(client):
    """GET /api/projects/{id} returns full project state."""
    create_resp = await client.post(
        "/api/projects",
        json={"name": "Deep Dive", "seed_idea": "Underwater civilization"},
    )
    project_id = create_resp.json()["id"]

    resp = await client.get(f"/api/projects/{project_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == project_id
    assert data["name"] == "Deep Dive"
    assert data["seed_idea"] == "Underwater civilization"
    assert data["last_stage"] == "idle"
    assert data["world_state"] is None
    assert data["characters"] is None
    assert data["plot_outline"] is None


async def test_get_nonexistent_project_returns_404(client):
    """GET /api/projects/{id} for unknown id returns 404."""
    resp = await client.get("/api/projects/nonexistent-id")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/projects/{id} — update
# ---------------------------------------------------------------------------


async def test_update_project_saves_fields(client):
    """PUT /api/projects/{id} updates specified fields."""
    create_resp = await client.post(
        "/api/projects",
        json={"name": "Draft Story", "seed_idea": "A time traveler"},
    )
    project_id = create_resp.json()["id"]

    update_resp = await client.put(
        f"/api/projects/{project_id}",
        json={"last_stage": "world", "world_state": {"rules": ["magic exists"]}},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["last_stage"] == "world"
    assert data["world_state"] == {"rules": ["magic exists"]}
    assert data["name"] == "Draft Story"  # unchanged


async def test_update_project_updates_updated_at(client):
    """PUT /api/projects/{id} updates the updated_at timestamp."""
    create_resp = await client.post(
        "/api/projects",
        json={"name": "Timestamp Test", "seed_idea": "A clock story"},
    )
    project_id = create_resp.json()["id"]
    original_updated_at = create_resp.json()["created_at"]

    import asyncio
    await asyncio.sleep(0.01)  # ensure time advances

    update_resp = await client.put(
        f"/api/projects/{project_id}",
        json={"last_stage": "characters"},
    )
    assert update_resp.json()["updated_at"] >= original_updated_at


async def test_update_nonexistent_project_returns_404(client):
    """PUT /api/projects/{id} for unknown id returns 404."""
    resp = await client.put("/api/projects/ghost-id", json={"last_stage": "world"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/projects/{id}
# ---------------------------------------------------------------------------


async def test_delete_project_removes_it(client):
    """DELETE /api/projects/{id} removes the project."""
    create_resp = await client.post(
        "/api/projects",
        json={"name": "Doomed Story", "seed_idea": "A story that ends"},
    )
    project_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/projects/{project_id}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/projects/{project_id}")
    assert get_resp.status_code == 404


async def test_delete_project_removes_from_list(client):
    """DELETE /api/projects/{id} removes project from list."""
    create_resp = await client.post(
        "/api/projects",
        json={"name": "Gone Story", "seed_idea": "Vanishes"},
    )
    project_id = create_resp.json()["id"]

    await client.delete(f"/api/projects/{project_id}")

    list_resp = await client.get("/api/projects")
    projects = list_resp.json()["projects"]
    assert all(p["id"] != project_id for p in projects)


async def test_delete_nonexistent_project_returns_404(client):
    """DELETE /api/projects/{id} for unknown id returns 404."""
    resp = await client.delete("/api/projects/phantom-id")
    assert resp.status_code == 404
