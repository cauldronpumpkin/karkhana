"""Tests for the Build Handoff service."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from backend.app.repository import ProjectTwin
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


@pytest.mark.asyncio
async def test_get_next_actions(db_session, sample_idea, temp_dir):
    fm = FileManager(base_dir=temp_dir)
    with patch.object(BuildHandoffService, "__init__", lambda self, **kw: None):
        service = BuildHandoffService()
        service.llm = _mock_llm_sync("")
        service.fm = fm
        service.memory = _stateful_mock_memory()
        service.scoring = _mock_scoring_service()

        result = await service.get_next_actions(sample_idea.id)
        assert result["idea_id"] == sample_idea.id
        assert result["status_summary"]["current_step"] == BUILD_STEPS[0]
        assert result["next_actions"]
        assert result["next_actions"][0]["priority"] == 1
        assert "codex_prompt" in result["next_actions"][0]
        assert result["next_actions"][0]["engine"] == "opencode"
        assert result["next_actions"][0]["opencode_prompt"] == result["next_actions"][0]["codex_prompt"]
        assert result["next_actions"][0]["opencode_command"].startswith("opencode run")


@pytest.mark.asyncio
async def test_get_next_actions_handles_missing_project_twin(db_session, sample_idea, temp_dir):
    fm = FileManager(base_dir=temp_dir)
    with patch.object(BuildHandoffService, "__init__", lambda self, **kw: None):
        service = BuildHandoffService()
        service.llm = _mock_llm_sync("")
        service.fm = fm
        service.memory = _stateful_mock_memory()
        service.scoring = _mock_scoring_service()

        result = await service.get_next_actions(sample_idea.id)
        assert result["status_summary"]["project_attached"] is False
        assert any(action["title"] == "Link the idea to a project twin" for action in result["next_actions"])


@pytest.mark.asyncio
async def test_codex_prompt_uses_plausible_context_files(db_session, sample_idea, temp_dir):
    fm = FileManager(base_dir=temp_dir)
    with patch.object(BuildHandoffService, "__init__", lambda self, **kw: None):
        service = BuildHandoffService()
        service.llm = _mock_llm_sync("")
        service.fm = fm
        service.memory = _stateful_mock_memory()
        service.scoring = _mock_scoring_service()

        result = await service.get_next_actions(sample_idea.id)
        prompt = result["next_actions"][0]["codex_prompt"]
        context_files = _extract_context_files(prompt)
        repo_root = Path(__file__).resolve().parents[2]

        assert "graphify-out/GRAPH_REPORT.md" in context_files
        assert "backend/app/services/build_handoff.py" in context_files
        assert "backend/app/routers/build.py" in context_files
        assert "backend/app/services/project_twin.py" in context_files
        assert "frontend/src/lib/components/ProjectTwin/ProjectTwinView.svelte" in context_files
        assert "frontend/src/lib/api.js" in context_files
        assert "backend/app/routers/project_twin.py" not in context_files
        assert "backend/app/routers/workers.py" not in context_files

        for path in context_files:
            assert (repo_root / path).exists(), f"Missing context file: {path}"


@pytest.mark.asyncio
async def test_codex_prompt_includes_project_twin_context_files(db_session, sample_idea, temp_dir):
    repo = db_session.repo
    await repo.save_project_twin(
        ProjectTwin(
            idea_id=sample_idea.id,
            provider="github",
            installation_id="inst-1",
            owner="acme",
            repo="factory-app",
            repo_full_name="acme/factory-app",
            repo_url="https://github.com/acme/factory-app",
            clone_url="https://github.com/acme/factory-app.git",
            default_branch="main",
        )
    )

    fm = FileManager(base_dir=temp_dir)
    with patch.object(BuildHandoffService, "__init__", lambda self, **kw: None):
        service = BuildHandoffService()
        service.llm = _mock_llm_sync("")
        service.fm = fm
        service.memory = _stateful_mock_memory()
        service.scoring = _mock_scoring_service()

        result = await service.get_next_actions(sample_idea.id)
        prompt = result["next_actions"][0]["codex_prompt"]
        context_files = _extract_context_files(prompt)

        assert "backend/app/routers/projects.py" in context_files
        assert "backend/app/routers/worker.py" in context_files
        assert "backend/app/routers/project_twin.py" not in context_files
        assert "backend/app/routers/workers.py" not in context_files


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


def _extract_context_files(prompt: str) -> list[str]:
    lines = prompt.splitlines()
    start = lines.index("Context files to inspect:") + 1
    end = lines.index("Constraints:")
    return [line.removeprefix("- ").strip() for line in lines[start:end]]
