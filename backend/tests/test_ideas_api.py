"""Tests for the Ideas API (CRUD operations)."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_idea(test_client: AsyncClient):
    """Happy path: create a new idea returns 201 with correct fields."""
    response = await test_client.post(
        "/api/ideas",
        json={"title": "AI Cooking App", "description": "An AI-powered cooking assistant"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "AI Cooking App"
    assert data["slug"] == "ai-cooking-app"
    assert data["description"] == "An AI-powered cooking assistant"
    assert data["current_phase"] == "capture"
    assert data["status"] == "active"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_ideas_list(test_client: AsyncClient, sample_idea):
    """Happy path: GET /api/ideas returns list including the sample idea."""
    response = await test_client.get("/api/ideas")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    ids = [idea["id"] for idea in data]
    assert sample_idea.id in ids


@pytest.mark.asyncio
async def test_get_idea_by_id(test_client: AsyncClient, sample_idea):
    """Happy path: GET /api/ideas/{id} returns the idea with correct fields."""
    response = await test_client.get(f"/api/ideas/{sample_idea.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_idea.id
    assert data["title"] == "Test Idea"
    assert data["slug"] == "test-idea"


@pytest.mark.asyncio
async def test_get_idea_not_found(test_client: AsyncClient):
    """Edge case: GET /api/ideas/{nonexistent} returns 404."""
    response = await test_client.get("/api/ideas/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_idea(test_client: AsyncClient, sample_idea):
    """Happy path: PATCH /api/ideas/{id} updates title and description."""
    response = await test_client.patch(
        f"/api/ideas/{sample_idea.id}",
        json={"title": "Updated Idea", "description": "Updated description"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Idea"
    assert data["description"] == "Updated description"


@pytest.mark.asyncio
async def test_update_idea_partial(test_client: AsyncClient, sample_idea):
    """Edge case: PATCH with only title updates title but keeps description."""
    response = await test_client.patch(
        f"/api/ideas/{sample_idea.id}",
        json={"title": "Only Title Changed"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Only Title Changed"
    assert data["description"] == "A test idea for unit testing"


@pytest.mark.asyncio
async def test_delete_idea(test_client: AsyncClient, sample_idea):
    """Happy path: DELETE /api/ideas/{id} archives the idea (204)."""
    response = await test_client.delete(f"/api/ideas/{sample_idea.id}")
    assert response.status_code == 204

    # Verify idea is no longer in active list
    response = await test_client.get(f"/api/ideas/{sample_idea.id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_idea(test_client: AsyncClient):
    """Edge case: DELETE nonexistent idea returns 404."""
    response = await test_client.delete("/api/ideas/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_idea_empty_title(test_client: AsyncClient):
    """Edge case: create idea with empty title returns 422."""
    response = await test_client.post(
        "/api/ideas",
        json={"title": "", "description": "Some description"},
    )
    assert response.status_code == 422
