"""Tests for the Memory service."""
from __future__ import annotations

import pytest

from backend.app.services.memory import MemoryService


@pytest.mark.asyncio
async def test_set_memory_creates_new(db_session, sample_idea):
    """Happy path: set_memory creates a new memory entry."""
    service = MemoryService()
    memory = await service.set_memory(
        key="test_key",
        value="test_value",
        category="note",
        idea_id=sample_idea.id,
    )
    assert memory.key == "test_key"
    assert memory.value == "test_value"
    assert memory.category == "note"
    assert memory.idea_id == sample_idea.id


@pytest.mark.asyncio
async def test_set_memory_updates_existing(db_session, sample_idea):
    """Happy path: set_memory updates an existing entry with same key."""
    service = MemoryService()
    await service.set_memory(
        key="update_key",
        value="original",
        category="note",
        idea_id=sample_idea.id,
    )
    memory = await service.set_memory(
        key="update_key",
        value="updated",
        category="issue",
        idea_id=sample_idea.id,
    )
    assert memory.value == "updated"
    assert memory.category == "issue"


@pytest.mark.asyncio
async def test_set_memory_invalid_category(db_session, sample_idea):
    """Edge case: set_memory raises ValueError for invalid category."""
    service = MemoryService()
    with pytest.raises(ValueError, match="Invalid category"):
        await service.set_memory(
            key="bad_key",
            value="test",
            category="invalid_category",
            idea_id=sample_idea.id,
        )


@pytest.mark.asyncio
async def test_get_memory(db_session, sample_idea):
    """Happy path: get_memory returns the correct entry."""
    service = MemoryService()
    await service.set_memory(
        key="get_key",
        value="get_value",
        category="note",
        idea_id=sample_idea.id,
    )
    memory = await service.get_memory(key="get_key", idea_id=sample_idea.id)
    assert memory is not None
    assert memory.value == "get_value"


@pytest.mark.asyncio
async def test_get_memory_not_found(db_session, sample_idea):
    """Edge case: get_memory returns None for nonexistent key."""
    service = MemoryService()
    memory = await service.get_memory(key="nonexistent", idea_id=sample_idea.id)
    assert memory is None


@pytest.mark.asyncio
async def test_get_all_memory(db_session, sample_idea):
    """Happy path: get_all_memory returns all entries for an idea."""
    service = MemoryService()
    await service.set_memory(key="key1", value="val1", category="note", idea_id=sample_idea.id)
    await service.set_memory(key="key2", value="val2", category="issue", idea_id=sample_idea.id)

    memories = await service.get_all_memory(idea_id=sample_idea.id)
    assert len(memories) == 2


@pytest.mark.asyncio
async def test_get_all_memory_global(db_session):
    """Happy path: get_all_memory returns global entries when idea_id=None."""
    service = MemoryService()
    await service.set_memory(key="global_key", value="global_val", category="note", idea_id=None)

    memories = await service.get_all_memory(idea_id=None)
    assert len(memories) >= 1
    keys = [m.key for m in memories]
    assert "global_key" in keys


@pytest.mark.asyncio
async def test_delete_memory(db_session, sample_idea):
    """Happy path: delete_memory removes an entry."""
    service = MemoryService()
    await service.set_memory(key="delete_key", value="to_delete", category="note", idea_id=sample_idea.id)

    deleted = await service.delete_memory(key="delete_key", idea_id=sample_idea.id)
    assert deleted is True

    memory = await service.get_memory(key="delete_key", idea_id=sample_idea.id)
    assert memory is None


@pytest.mark.asyncio
async def test_delete_memory_not_found(db_session, sample_idea):
    """Edge case: delete_memory returns False for nonexistent key."""
    service = MemoryService()
    deleted = await service.delete_memory(key="nonexistent", idea_id=sample_idea.id)
    assert deleted is False


@pytest.mark.asyncio
async def test_get_by_category(db_session, sample_idea):
    """Happy path: get_by_category returns entries matching category."""
    service = MemoryService()
    await service.set_memory(key="issue1", value="bug found", category="issue", idea_id=sample_idea.id)
    await service.set_memory(key="note1", value="some note", category="note", idea_id=sample_idea.id)

    issues = await service.get_by_category(category="issue", idea_id=sample_idea.id)
    assert len(issues) == 1
    assert issues[0].key == "issue1"


@pytest.mark.asyncio
async def test_get_context_for_idea(db_session, sample_idea):
    """Happy path: get_context_for_idea returns formatted text."""
    service = MemoryService()
    await service.set_memory(key="ctx_key", value="ctx_value", category="note", idea_id=sample_idea.id)

    context = await service.get_context_for_idea(sample_idea.id)
    assert "Project Memory" in context
    assert "ctx_key" in context
    assert "ctx_value" in context


@pytest.mark.asyncio
async def test_get_context_for_idea_empty(db_session, sample_idea):
    """Edge case: get_context_for_idea returns empty string when no memories."""
    service = MemoryService()
    context = await service.get_context_for_idea(sample_idea.id)
    assert context == ""
