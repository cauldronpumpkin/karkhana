"""Tests for the Chat API (REST endpoints; WebSocket tested via REST history)."""
from __future__ import annotations

from unittest.mock import patch, AsyncMock

import pytest
from httpx import AsyncClient

from backend.app.models.message import Message


@pytest.mark.asyncio
async def test_get_chat_history_empty(test_client: AsyncClient, sample_idea):
    """Happy path: GET chat history for idea with no messages returns empty list."""
    response = await test_client.get(f"/api/ideas/{sample_idea.id}/chat/history")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_get_chat_history_with_messages(test_client: AsyncClient, sample_idea, db_session):
    """Happy path: GET chat history returns messages in order."""
    msg1 = Message(
        id="msg-1",
        idea_id=sample_idea.id,
        role="user",
        content="Hello",
    )
    msg2 = Message(
        id="msg-2",
        idea_id=sample_idea.id,
        role="assistant",
        content="Hi there!",
    )
    db_session.add_all([msg1, msg2])
    await db_session.commit()

    response = await test_client.get(f"/api/ideas/{sample_idea.id}/chat/history")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["role"] == "user"
    assert data[0]["content"] == "Hello"
    assert data[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_get_chat_history_idea_not_found(test_client: AsyncClient):
    """Edge case: GET chat history for nonexistent idea returns 404."""
    response = await test_client.get("/api/ideas/nonexistent-id/chat/history")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_send_chat_message_success(test_client: AsyncClient, sample_idea):
    """Happy path: POST chat message returns assistant response."""
    async def mock_stream(*args, **kwargs):
        for chunk in "Mock assistant response".split(" "):
            yield chunk + " "

    with patch("backend.app.routers.chat.llm_service") as mock_llm:
        mock_llm.chat_completion = mock_stream

        response = await test_client.post(
            f"/api/ideas/{sample_idea.id}/chat/message",
            json={"message": "Hello there"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "message_id" in data
        assert data["content"] == "Mock assistant response "


@pytest.mark.asyncio
async def test_send_chat_message_idea_not_found(test_client: AsyncClient):
    """Edge case: POST chat message for nonexistent idea returns 404."""
    response = await test_client.post(
        "/api/ideas/nonexistent-id/chat/message",
        json={"message": "Hello"},
    )
    assert response.status_code == 404
