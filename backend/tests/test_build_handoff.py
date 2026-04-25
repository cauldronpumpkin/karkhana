"""Tests for the Build Handoff service."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.app.services.build_handoff import BUILD_STEPS, BuildHandoffService
from backend.app.services.file_manager import FileManager


@pytest.mark.asyncio
async def test_generate_prometheus_prompt(db_session, sample_idea, temp_dir):
    """Happy path: generate_prometheus_prompt returns prompt with context."""
    fm = FileManager(base_dir=temp_dir)
    with patch.object(BuildHandoffService, "__init__", lambda self, **kw: None):
        service = BuildHandoffService()
        service.llm = _mock_llm_sync("# Prometheus planning prompt")
        service.fm = fm
        service.memory = _stateful_mock_memory()
        service.scoring = _mock_scoring_service()

        result = await service.generate_prometheus_prompt(sample_idea.id)
        assert result["idea_id"] == sample_idea.id
        assert result["prompt"] == "# Prometheus planning prompt"
        assert "context_summary" in result


@pytest.mark.asyncio
async def test_generate_prometheus_prompt_idea_not_found():
    """Edge case: generate_prometheus_prompt raises ValueError for nonexistent idea."""
    with patch.object(BuildHandoffService, "__init__", lambda self, **kw: None):
        service = BuildHandoffService()
        service.llm = _mock_llm_sync("")
        service.fm = FileManager()
        service.memory = _stateful_mock_memory()
        service.scoring = _mock_scoring_service()

        with pytest.raises(ValueError, match="Idea not found"):
            await service.generate_prometheus_prompt("nonexistent-id")


@pytest.mark.asyncio
async def test_generate_step_prompts(db_session, sample_idea, temp_dir):
    """Happy path: generate_step_prompts returns prompts for all build steps."""
    fm = FileManager(base_dir=temp_dir)
    with patch.object(BuildHandoffService, "__init__", lambda self, **kw: None):
        service = BuildHandoffService()
        service.llm = _mock_llm_sync("Step prompt content")
        service.fm = fm
        service.memory = _stateful_mock_memory()
        service.scoring = _mock_scoring_service()

        result = await service.generate_step_prompts(sample_idea.id)
        assert result["idea_id"] == sample_idea.id
        assert result["total_steps"] == len(BUILD_STEPS)
        assert len(result["steps"]) == len(BUILD_STEPS)


@pytest.mark.asyncio
async def test_get_current_build_state(db_session, sample_idea, temp_dir):
    """Happy path: get_current_build_state returns initial state."""
    fm = FileManager(base_dir=temp_dir)
    with patch.object(BuildHandoffService, "__init__", lambda self, **kw: None):
        service = BuildHandoffService()
        service.llm = _mock_llm_sync("")
        service.fm = fm
        service.memory = _stateful_mock_memory()
        service.scoring = _mock_scoring_service()

        state = await service.get_current_build_state(sample_idea.id)
        assert state["idea_id"] == sample_idea.id
        assert state["current_step"] == BUILD_STEPS[0]
        assert state["completed_steps"] == []
        assert state["total_steps"] == len(BUILD_STEPS)


@pytest.mark.asyncio
async def test_mark_step_complete(db_session, sample_idea, temp_dir):
    """Happy path: mark_step_complete advances to next step."""
    fm = FileManager(base_dir=temp_dir)
    with patch.object(BuildHandoffService, "__init__", lambda self, **kw: None):
        service = BuildHandoffService()
        service.llm = _mock_llm_sync("Next step prompt")
        service.fm = fm
        service.memory = _stateful_mock_memory()
        service.scoring = _mock_scoring_service()

        result = await service.mark_step_complete(sample_idea.id, BUILD_STEPS[0])
        assert result["completed_step"] == BUILD_STEPS[0]
        assert result["next_step"] == BUILD_STEPS[1]
        assert result["is_complete"] is False


@pytest.mark.asyncio
async def test_mark_step_complete_invalid_step(db_session, sample_idea, temp_dir):
    """Edge case: mark_step_complete raises ValueError for invalid step."""
    fm = FileManager(base_dir=temp_dir)
    with patch.object(BuildHandoffService, "__init__", lambda self, **kw: None):
        service = BuildHandoffService()
        service.llm = _mock_llm_sync("")
        service.fm = fm
        service.memory = _stateful_mock_memory()
        service.scoring = _mock_scoring_service()

        with pytest.raises(ValueError, match="Invalid step"):
            await service.mark_step_complete(sample_idea.id, "invalid_step")


@pytest.mark.asyncio
async def test_mark_step_complete_last_step(db_session, sample_idea, temp_dir):
    """Edge case: marking last step complete sets is_complete=True."""
    fm = FileManager(base_dir=temp_dir)
    memory = _stateful_mock_memory()
    with patch.object(BuildHandoffService, "__init__", lambda self, **kw: None):
        service = BuildHandoffService()
        service.llm = _mock_llm_sync("")
        service.fm = fm
        service.memory = memory
        service.scoring = _mock_scoring_service()

        # Mark all steps complete
        for step in BUILD_STEPS[:-1]:
            await service.mark_step_complete(sample_idea.id, step)

        result = await service.mark_step_complete(sample_idea.id, BUILD_STEPS[-1])
        assert result["is_complete"] is True
        assert result["next_step"] is None


def _mock_llm_sync(response: str):
    """Create a mock LLM service."""
    from backend.tests.conftest import MockLLMService
    return MockLLMService(responses={"": response})


def _stateful_mock_memory():
    """Create a stateful mock memory service that actually stores data."""
    from unittest.mock import AsyncMock
    from datetime import datetime, timezone
    from uuid import uuid4

    store: dict[tuple[str, str | None], dict] = {}

    async def set_memory(key, value, category, idea_id=None):
        mem = {
            "id": str(uuid4()),
            "key": key,
            "value": value,
            "category": category,
            "idea_id": idea_id,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        store[(key, idea_id)] = mem
        return type("MockMemory", (), mem)()

    async def get_memory(key, idea_id=None):
        mem = store.get((key, idea_id))
        if mem is None:
            return None
        return type("MockMemory", (), mem)()

    async def get_all_memory(idea_id=None):
        return [type("MockMemory", (), v)() for k, v in store.items() if k[1] == idea_id]

    async def get_context_for_idea(idea_id):
        return ""

    async def delete_memory(key, idea_id=None):
        return store.pop((key, idea_id), None) is not None

    async def get_by_category(category, idea_id=None):
        return [type("MockMemory", (), v)() for k, v in store.items() if v["category"] == category and k[1] == idea_id]

    mock = AsyncMock()
    mock.set_memory = set_memory
    mock.get_memory = get_memory
    mock.get_all_memory = get_all_memory
    mock.get_context_for_idea = get_context_for_idea
    mock.delete_memory = delete_memory
    mock.get_by_category = get_by_category
    return mock


def _mock_memory_service():
    """Create a mock memory service."""
    from unittest.mock import AsyncMock
    mock = AsyncMock()
    mock.set_memory = AsyncMock(return_value=None)
    mock.get_memory = AsyncMock(return_value=None)
    mock.get_all_memory = AsyncMock(return_value=[])
    mock.get_context_for_idea = AsyncMock(return_value="")
    mock.delete_memory = AsyncMock(return_value=False)
    mock.get_by_category = AsyncMock(return_value=[])
    return mock


def _mock_scoring_service():
    """Create a mock scoring service."""
    from unittest.mock import AsyncMock
    mock = AsyncMock()
    mock.get_scores = AsyncMock(return_value=[])
    return mock
