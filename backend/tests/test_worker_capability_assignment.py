from __future__ import annotations

import pytest

from backend.app.repository import (
    Idea,
    InMemoryRepository,
    ProjectTwin,
    TemplatePack,
    WorkItem,
    get_repository,
    set_repository,
    utcnow,
)
from backend.app.services.project_twin import ProjectTwinService


@pytest.fixture
def repo():
    r = InMemoryRepository()
    set_repository(r)
    return r


def _full_capabilities():
    return [
        "permission_guard",
        "circuit_breaker",
        "litellm_proxy",
        "diff_api",
        "verification_runner",
        "graphify_update",
        "repo_index",
        "agent_branch_work",
    ]


async def _seed_work_item(repo, *,
    autonomy_level: str = "autonomous_development",
    job_type: str = "agent_branch_work",
    project_id: str | None = None,
    set_autonomy: bool = True,
) -> str:
    if not project_id:
        idea = Idea(title="Capability Test", slug="cap-test", description="test")
        await repo.create_idea(idea)
        project = ProjectTwin(
            idea_id=idea.id,
            provider="github",
            installation_id="inst-1",
            owner="acme",
            repo="app",
            repo_full_name="acme/app",
            repo_url="https://github.com/acme/app",
            clone_url="https://github.com/acme/app.git",
            default_branch="main",
        )
        await repo.save_project_twin(project)
        project_id = project.id

    payload: dict = {
        "factory_run_id": "run-001",
        "verification_commands": ["graphify update ."],
    }
    if set_autonomy:
        payload["autonomy_level"] = autonomy_level
    item = WorkItem(
        idea_id="idea-001",
        project_id=project_id,
        job_type=job_type,
        payload=payload,
        status="queued",
    )
    await repo.enqueue_work_item(item)
    return item.id


class TestClaimJobAssignmentValidation:
    @pytest.mark.asyncio
    async def test_worker_with_full_capabilities_can_claim_high_autonomy_job(self, repo):
        work_item_id = await _seed_work_item(repo, autonomy_level="autonomous_development")
        svc = ProjectTwinService()
        result = await svc.claim_job(
            worker_id="worker-001",
            capabilities=_full_capabilities(),
        )
        assert result is not None
        assert result["job"]["id"] == work_item_id

    @pytest.mark.asyncio
    async def test_worker_missing_capabilities_rejected_for_high_autonomy(self, repo):
        await _seed_work_item(repo, autonomy_level="autonomous_development")
        svc = ProjectTwinService()
        result = await svc.claim_job(
            worker_id="worker-002",
            capabilities=["repo_index", "agent_branch_work"],
        )
        assert result is None
        items = await repo.list_work_items()
        failed_items = [wi for wi in items if wi.status == "failed_terminal"]
        assert len(failed_items) == 1, f"Expected 1 failed item, got {len(failed_items)}: {[wi.status for wi in items]}"
        failed_item = failed_items[0]
        assert "permission_guard" in failed_item.error
        assert "autonomous_development" in failed_item.error

    @pytest.mark.asyncio
    async def test_worker_without_capabilities_rejected_for_full_autopilot(self, repo):
        await _seed_work_item(repo, autonomy_level="full_autopilot")
        svc = ProjectTwinService()
        result = await svc.claim_job(
            worker_id="worker-003",
            capabilities=["repo_index"],
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_worker_limited_capabilities_allowed_for_suggest_only(self, repo):
        await _seed_work_item(repo, autonomy_level="suggest_only")
        svc = ProjectTwinService()
        result = await svc.claim_job(
            worker_id="worker-004",
            capabilities=["agent_branch_work", "repo_index"],
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_repo_index_job_without_autonomy_skips_capability_check(self, repo):
        work_item_id = await _seed_work_item(
            repo, job_type="repo_index", set_autonomy=False,
        )
        svc = ProjectTwinService()
        result = await svc.claim_job(
            worker_id="worker-005",
            capabilities=["repo_index"],
        )
        assert result is not None
        assert result["job"]["id"] == work_item_id


class TestEngineCapabilityConstants:
    def test_open_code_server_required_capabilities(self):
        from backend.app.services.autonomy import OPENCODE_SERVER_REQUIRED_CAPABILITIES
        expected = {
            "permission_guard",
            "circuit_breaker",
            "litellm_proxy",
            "diff_api",
            "verification_runner",
            "graphify_update",
        }
        assert OPENCODE_SERVER_REQUIRED_CAPABILITIES == expected

    def test_high_autonomy_levels(self):
        from backend.app.services.autonomy import HIGH_AUTONOMY_LEVELS
        assert "autonomous_development" in HIGH_AUTONOMY_LEVELS
        assert "full_autopilot" in HIGH_AUTONOMY_LEVELS
        assert "suggest_only" not in HIGH_AUTONOMY_LEVELS

    def test_limited_engines(self):
        from backend.app.services.autonomy import LIMITED_ENGINES
        assert "opencode" in LIMITED_ENGINES
        assert "openclaude" in LIMITED_ENGINES
        assert "codex" in LIMITED_ENGINES


class TestGraphifyEnforcement:
    @pytest.mark.asyncio
    async def test_complete_job_without_graphify_logs_warning(self, repo):
        work_item_id = await _seed_work_item(repo, autonomy_level="autonomous_development")
        svc = ProjectTwinService()
        result = await svc.claim_job(
            worker_id="worker-001",
            capabilities=_full_capabilities(),
        )
        assert result is not None
        job_id = result["job"]["id"]
        claim_token = result["job"]["claim_token"]
        await svc.complete_job(
            job_id=job_id,
            claim_token=claim_token,
            worker_id="worker-001",
            result={"summary": "Done", "tests_passed": True, "graphify_updated": False},
        )
        completed = await repo.get_work_item(job_id)
        assert completed is not None
        assert completed.status == "completed"
        assert "graphify update" in (completed.logs or "").lower()

    @pytest.mark.asyncio
    async def test_complete_job_with_graphify_no_warning(self, repo):
        work_item_id = await _seed_work_item(repo, autonomy_level="autonomous_development")
        svc = ProjectTwinService()
        result = await svc.claim_job(
            worker_id="worker-001",
            capabilities=_full_capabilities(),
        )
        assert result is not None
        job_id = result["job"]["id"]
        claim_token = result["job"]["claim_token"]
        await svc.complete_job(
            job_id=job_id,
            claim_token=claim_token,
            worker_id="worker-001",
            result={"summary": "Done", "tests_passed": True, "graphify_updated": True},
        )
        completed = await repo.get_work_item(job_id)
        assert completed is not None
        assert completed.status == "completed"
        assert "graphify" not in (completed.logs or "")

    @pytest.mark.asyncio
    async def test_repo_index_job_skips_graphify_check(self, repo):
        work_item_id = await _seed_work_item(
            repo, autonomy_level="autonomous_development", job_type="repo_index",
        )
        svc = ProjectTwinService()
        result = await svc.claim_job(
            worker_id="worker-001",
            capabilities=_full_capabilities(),
        )
        assert result is not None, "claim_job should succeed with full capabilities"
        job_id = result["job"]["id"]
        claim_token = result["job"]["claim_token"]
        await svc.complete_job(
            job_id=job_id,
            claim_token=claim_token,
            worker_id="worker-001",
            result={"commit_sha": "abc123"},
        )
        completed = await repo.get_work_item(job_id)
        assert completed is not None
        assert completed.status == "completed"
