"""Tests for the Research service."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.app.services.research import ResearchService
from backend.app.services.file_manager import FileManager


@pytest.mark.asyncio
async def test_create_research_task(db_session, sample_idea, temp_dir):
    """Happy path: create_research_task creates task and saves prompt."""
    fm = FileManager(base_dir=temp_dir)
    with patch.object(ResearchService, "__init__", lambda self, **kw: None):
        service = ResearchService()
        service.file_manager = fm
        service.llm_service = _mock_llm('{"topic": "Market", "prompt": "Research the market"}')

        task_id = await service.create_research_task(
            idea_id=sample_idea.id,
            prompt="Research the market size",
            topic="Market Size",
        )
        assert task_id is not None
        assert len(task_id) > 0


@pytest.mark.asyncio
async def test_upload_research_result(db_session, sample_idea, temp_dir):
    """Happy path: upload_research_result saves file and updates task status."""
    fm = FileManager(base_dir=temp_dir)
    with patch.object(ResearchService, "__init__", lambda self, **kw: None):
        service = ResearchService()
        service.file_manager = fm
        service.llm_service = _mock_llm("")

        task_id = await service.create_research_task(
            idea_id=sample_idea.id,
            prompt="Research prompt",
            topic="Test Topic",
        )

        result_path = await service.upload_research_result(
            idea_id=sample_idea.id,
            task_id=task_id,
            content="# Research Results\n\nSome findings here.",
        )
        assert result_path is not None


@pytest.mark.asyncio
async def test_upload_research_result_task_not_found(db_session, sample_idea, temp_dir):
    """Edge case: upload_research_result raises ValueError for nonexistent task."""
    fm = FileManager(base_dir=temp_dir)
    with patch.object(ResearchService, "__init__", lambda self, **kw: None):
        service = ResearchService()
        service.file_manager = fm
        service.llm_service = _mock_llm("")

        with pytest.raises(ValueError, match="not found"):
            await service.upload_research_result(
                idea_id=sample_idea.id,
                task_id="nonexistent-task-id",
                content="Some content",
            )


@pytest.mark.asyncio
async def test_integrate_research(db_session, sample_idea, temp_dir):
    """Happy path: integrate_research reads result and returns summary."""
    fm = FileManager(base_dir=temp_dir)
    with patch.object(ResearchService, "__init__", lambda self, **kw: None):
        service = ResearchService()
        service.file_manager = fm
        service.llm_service = _mock_llm("Mock integration summary")

        task_id = await service.create_research_task(
            idea_id=sample_idea.id,
            prompt="Research prompt",
            topic="Test Topic",
        )

        await service.upload_research_result(
            idea_id=sample_idea.id,
            task_id=task_id,
            content="# Research\n\nKey finding: market is growing.",
        )

        result = await service.integrate_research(
            idea_id=sample_idea.id,
            task_id=task_id,
        )
        assert "summary" in result
        assert "task_id" in result


@pytest.mark.asyncio
async def test_integrate_research_incomplete_task(db_session, sample_idea, temp_dir):
    """Edge case: integrate_research raises ValueError for incomplete task."""
    fm = FileManager(base_dir=temp_dir)
    with patch.object(ResearchService, "__init__", lambda self, **kw: None):
        service = ResearchService()
        service.file_manager = fm
        service.llm_service = _mock_llm("")

        task_id = await service.create_research_task(
            idea_id=sample_idea.id,
            prompt="Research prompt",
            topic="Test Topic",
        )

        with pytest.raises(ValueError, match="not completed"):
            await service.integrate_research(
                idea_id=sample_idea.id,
                task_id=task_id,
            )


@pytest.mark.asyncio
async def test_get_pending_tasks(db_session, sample_idea, temp_dir):
    """Happy path: get_pending_tasks returns pending tasks."""
    fm = FileManager(base_dir=temp_dir)
    with patch.object(ResearchService, "__init__", lambda self, **kw: None):
        service = ResearchService()
        service.file_manager = fm
        service.llm_service = _mock_llm("")

        await service.create_research_task(
            idea_id=sample_idea.id,
            prompt="Pending research",
            topic="Pending Topic",
        )

        tasks = await service.get_pending_tasks(sample_idea.id)
        assert isinstance(tasks, list)
        assert len(tasks) >= 1
        assert tasks[0]["status"] == "pending"


@pytest.mark.asyncio
async def test_get_completed_tasks(db_session, sample_idea, temp_dir):
    """Happy path: get_completed_tasks returns completed tasks."""
    fm = FileManager(base_dir=temp_dir)
    with patch.object(ResearchService, "__init__", lambda self, **kw: None):
        service = ResearchService()
        service.file_manager = fm
        service.llm_service = _mock_llm("")

        task_id = await service.create_research_task(
            idea_id=sample_idea.id,
            prompt="Completed research",
            topic="Completed Topic",
        )
        await service.upload_research_result(
            idea_id=sample_idea.id,
            task_id=task_id,
            content="Done",
        )

        tasks = await service.get_completed_tasks(sample_idea.id)
        assert isinstance(tasks, list)
        assert len(tasks) >= 1
        assert tasks[0]["status"] == "completed"


def _mock_llm(response: str):
    """Create a mock LLM service."""
    from backend.tests.conftest import MockLLMService
    return MockLLMService(responses={"": response})
