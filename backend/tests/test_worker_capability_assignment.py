from __future__ import annotations

import pytest

from backend.app.repository import (
    DynamoDBRepository,
    Idea,
    InMemoryRepository,
    ProjectTwin,
    TemplatePack,
    WorkItem,
    get_repository,
    set_repository,
    utcnow,
)
from backend.app.services import project_twin as project_twin_module
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


async def _seed_project(repo):
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
    return idea.id, project.id


async def _seed_work_item(repo, *,
    autonomy_level: str = "autonomous_development",
    job_type: str = "agent_branch_work",
    project_id: str | None = None,
    set_autonomy: bool = True,
    ledger_policy: str = "none",
    ledger_path: str | None = None,
    verification_commands: list[str] | None = None,
    test_commands: list[str] | None = None,
) -> str:
    if not project_id:
        _, project_id = await _seed_project(repo)

    payload: dict[str, object] = {
        "factory_run_id": "run-001",
    }
    if verification_commands is not None:
        payload["verification_commands"] = verification_commands
    elif test_commands is not None:
        payload["test_commands"] = test_commands
    else:
        payload["verification_commands"] = ["graphify update ."]
    if set_autonomy:
        payload["autonomy_level"] = autonomy_level
    item = WorkItem(
        idea_id="idea-001",
        project_id=project_id,
        job_type=job_type,
        payload=payload,
        status="queued",
        ledger_policy=ledger_policy,
        ledger_path=ledger_path,
    )
    await repo.enqueue_work_item(item)
    return item.id


class TestWorkItemLedgerFields:
    def test_legacy_work_item_defaults_to_no_ledger_policy(self):
        item = WorkItem(
            idea_id="idea-001",
            project_id="project-001",
            job_type="agent_branch_work",
        )
        assert item.ledger_policy == "none"
        assert item.ledger_path is None

    def test_legacy_ddb_hydration_defaults_to_no_ledger_policy(self):
        repo = DynamoDBRepository.__new__(DynamoDBRepository)
        item = repo._work_item({
            "id": "job-001",
            "idea_id": "idea-001",
            "project_id": "project-001",
            "job_type": "agent_branch_work",
            "created_at": utcnow().isoformat(),
            "updated_at": utcnow().isoformat(),
        })
        assert item.ledger_policy == "none"
        assert item.ledger_path is None

    def test_invalid_ledger_policy_rejected(self):
        with pytest.raises(ValueError, match="Invalid ledger_policy"):
            WorkItem(
                idea_id="idea-001",
                project_id="project-001",
                job_type="agent_branch_work",
                ledger_policy="sometimes",
            )

    def test_non_none_ledger_policy_requires_path(self):
        with pytest.raises(ValueError, match="ledger_path is required"):
            WorkItem(
                idea_id="idea-001",
                project_id="project-001",
                job_type="agent_branch_work",
                ledger_policy="required",
            )

    @pytest.mark.parametrize("ledger_path", ["../run.md", "karkhana-runs/../run.md", "/tmp/run.md", "C:/tmp/run.md"])
    def test_ledger_path_rejects_traversal_and_absolute_paths(self, ledger_path):
        with pytest.raises(ValueError, match="ledger_path"):
            WorkItem(
                idea_id="idea-001",
                project_id="project-001",
                job_type="agent_branch_work",
                ledger_policy="required",
                ledger_path=ledger_path,
            )


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


class TestVerificationCommandNormalization:
    @pytest.mark.asyncio
    async def test_enqueue_job_normalizes_legacy_test_commands(self, repo):
        idea_id, project_id = await _seed_project(repo)

        class _NullPublisher:
            async def send_job_available(self, *_args, **_kwargs):
                return None

        svc = ProjectTwinService(sqs_publisher=_NullPublisher())
        job = await svc.enqueue_job(
            idea_id=idea_id,
            project_id=project_id,
            job_type="agent_branch_work",
            payload={
                "factory_run_id": "run-legacy",
                "test_commands": ["python -m pytest", "graphify update ."],
                "autonomy_level": "suggest_only",
            },
            idempotency_key="legacy-enqueue",
        )

        stored = await repo.get_work_item(job.id)
        assert stored is not None
        assert stored.payload["verification_commands"] == ["python -m pytest", "graphify update ."]
        assert "test_commands" not in stored.payload

    @pytest.mark.asyncio
    async def test_claim_job_normalizes_legacy_test_commands(self, repo):
        await _seed_work_item(
            repo,
            autonomy_level="suggest_only",
            test_commands=["python -m pytest", "graphify update ."],
        )
        svc = ProjectTwinService()
        result = await svc.claim_job(
            worker_id="worker-normalize",
            capabilities=["agent_branch_work", "repo_index"],
        )
        assert result is not None
        job = result["job"]
        assert job["verification_commands"] == ["python -m pytest", "graphify update ."]

        stored = await repo.get_work_item(job["id"])
        assert stored is not None
        assert stored.payload["verification_commands"] == ["python -m pytest", "graphify update ."]
        assert "test_commands" not in stored.payload


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
        work_item_id = await _seed_work_item(
            repo,
            autonomy_level="suggest_only",
            verification_commands=["graphify update ."],
        )
        svc = ProjectTwinService()
        result = await svc.claim_job(
            worker_id="worker-001",
            capabilities=["agent_branch_work", "repo_index"],
        )
        assert result is not None
        job_id = result["job"]["id"]
        claim_token = result["job"]["claim_token"]
        await svc.complete_job(
            job_id=job_id,
            claim_token=claim_token,
            worker_id="worker-001",
            result={
                "summary": "Done",
                "tests_passed": True,
                "graphify_updated": False,
                "verification_results": [
                    {"command": "graphify update .", "status": "passed"},
                ],
            },
        )
        completed = await repo.get_work_item(job_id)
        assert completed is not None
        assert completed.status == "completed"
        assert "graphify update" in (completed.logs or "").lower()

    @pytest.mark.asyncio
    async def test_high_autonomy_without_graphify_fails_terminal(self, repo):
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
            result={
                "summary": "Done",
                "tests_passed": True,
                "graphify_updated": False,
                "verification_results": [
                    {"command": "graphify update .", "status": "passed"},
                ],
            },
        )
        completed = await repo.get_work_item(job_id)
        assert completed is not None
        assert completed.status == "failed_terminal"
        assert "graphify update" in (completed.error or "").lower()

    @pytest.mark.asyncio
    async def test_high_autonomy_without_verification_evidence_fails_terminal(self, repo):
        await _seed_work_item(
            repo,
            autonomy_level="autonomous_development",
            verification_commands=["python -m pytest", "graphify update ."],
        )
        svc = ProjectTwinService()
        result = await svc.claim_job(
            worker_id="worker-002",
            capabilities=_full_capabilities(),
        )
        assert result is not None
        job_id = result["job"]["id"]
        claim_token = result["job"]["claim_token"]
        await svc.complete_job(
            job_id=job_id,
            claim_token=claim_token,
            worker_id="worker-002",
            result={"summary": "Done", "tests_passed": True, "graphify_updated": True},
        )
        completed = await repo.get_work_item(job_id)
        assert completed is not None
        assert completed.status == "failed_terminal"
        assert "verification evidence" in (completed.error or "").lower()

    @pytest.mark.parametrize("status", ["failed", "timed_out", "blocked"])
    @pytest.mark.asyncio
    async def test_high_autonomy_fails_terminal_on_bad_verification_status(self, repo, status):
        await _seed_work_item(
            repo,
            autonomy_level="autonomous_development",
            verification_commands=["python -m pytest", "graphify update ."],
        )
        svc = ProjectTwinService()
        result = await svc.claim_job(
            worker_id="worker-003",
            capabilities=_full_capabilities(),
        )
        assert result is not None
        job_id = result["job"]["id"]
        claim_token = result["job"]["claim_token"]
        await svc.complete_job(
            job_id=job_id,
            claim_token=claim_token,
            worker_id="worker-003",
            result={
                "summary": "Done",
                "tests_passed": False if status == "failed" else True,
                "graphify_updated": True,
                "verification_results": [
                    {"command": "python -m pytest", "status": status},
                    {"command": "graphify update .", "status": "passed"},
                ],
            },
        )
        completed = await repo.get_work_item(job_id)
        assert completed is not None
        assert completed.status == "failed_terminal"
        assert status in (completed.error or "").lower()


class TestLedgerCompletionEnforcement:
    @pytest.mark.asyncio
    async def test_required_missing_ledger_update_completes_with_warning(self, repo):
        await _seed_work_item(
            repo,
            autonomy_level="suggest_only",
            ledger_policy="required",
            ledger_path="karkhana-runs/run-001.md",
        )
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
            result={
                "summary": "Done",
                "tests_passed": True,
                "graphify_updated": True,
                "verification_results": [
                    {"command": "graphify update .", "status": "passed"},
                ],
            },
        )

        completed = await repo.get_work_item(job_id)
        assert completed is not None
        assert completed.status == "completed"
        assert "ledger must be updated" in (completed.logs or "")

    @pytest.mark.asyncio
    async def test_strict_missing_ledger_update_fails_terminal(self, repo):
        await _seed_work_item(
            repo,
            autonomy_level="autonomous_development",
            ledger_policy="strict",
            ledger_path="karkhana-runs/run-001.md",
            verification_commands=["graphify update ."],
        )
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
            result={
                "summary": "Done",
                "tests_passed": True,
                "graphify_updated": True,
                "verification_results": [
                    {"command": "graphify update .", "status": "passed"},
                ],
            },
        )

        completed = await repo.get_work_item(job_id)
        assert completed is not None
        assert completed.status == "failed_terminal"
        assert "ledger must be updated" in (completed.error or "")

    @pytest.mark.asyncio
    async def test_successful_completion_records_ledger_update_fields(self, repo):
        await _seed_work_item(
            repo,
            autonomy_level="autonomous_development",
            ledger_policy="strict",
            ledger_path="karkhana-runs/run-001.md",
            verification_commands=["graphify update ."],
        )
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
            result={
                "summary": "Done",
                "tests_passed": True,
                "graphify_updated": True,
                "verification_results": [
                    {"command": "graphify update .", "status": "passed"},
                ],
                "ledger_updated": True,
                "ledger_sections_updated": ["Codex runs", "Risks"],
            },
        )

        completed = await repo.get_work_item(job_id)
        assert completed is not None
        assert completed.status == "completed"
        assert completed.result["ledger_updated"] is True
        assert completed.result["ledger_sections_updated"] == ["Codex runs", "Risks"]


class TestGraphifyCompletionSuccess:

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
            result={
                "summary": "Done",
                "tests_passed": True,
                "graphify_updated": True,
                "verification_results": [
                    {"command": "graphify update .", "status": "passed"},
                ],
            },
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


class TestDraftPullRequestCompletion:
    @pytest.mark.asyncio
    async def test_high_autonomy_completion_creates_draft_pull_request(self, repo, monkeypatch):
        await _seed_work_item(
            repo,
            autonomy_level="autonomous_development",
            verification_commands=["graphify update ."],
        )
        fake_service = _FakeGitHubAppService(
            response={
                "html_url": "https://github.com/acme/app/pull/42",
                "url": "https://api.github.com/repos/acme/app/pulls/42",
                "number": 42,
                "state": "open",
                "draft": True,
            }
        )
        monkeypatch.setattr(project_twin_module, "GitHubAppService", lambda: fake_service)

        svc = ProjectTwinService()
        claim = await svc.claim_job(
            worker_id="worker-001",
            capabilities=_full_capabilities(),
        )
        assert claim is not None
        job_id = claim["job"]["id"]
        claim_token = claim["job"]["claim_token"]

        completed = await svc.complete_job(
            job_id=job_id,
            claim_token=claim_token,
            worker_id="worker-001",
            result={
                "summary": "Done",
                "tests_passed": True,
                "graphify_updated": True,
                "verification_results": [
                    {"command": "graphify update .", "status": "passed"},
                ],
                "commit_sha": "abc123",
                "commit_message": "Ship the fix",
                "branch_name": "feature/job-1",
            },
        )

        assert completed["status"] == "completed"
        draft_pr = completed["result"]["draft_pr"]
        assert draft_pr["html_url"] == "https://github.com/acme/app/pull/42"
        assert draft_pr["head_branch"] == "feature/job-1"
        assert draft_pr["base_branch"] == "main"
        assert draft_pr["title"] == "Ship the fix"
        assert "Human approval required before merge." in draft_pr["body"]
        assert "Verification summary:" in draft_pr["body"]
        assert "Graphify status:" in draft_pr["body"]
        assert "Logs note:" in draft_pr["body"]
        assert fake_service.calls == [
            {
                "installation_id": "inst-1",
                "owner": "acme",
                "repo_name": "app",
                "title": "Ship the fix",
                "head_branch": "feature/job-1",
                "base_branch": "main",
                "body": draft_pr["body"],
            }
        ]

    @pytest.mark.asyncio
    async def test_draft_pull_request_failure_marks_job_terminal(self, repo, monkeypatch):
        await _seed_work_item(
            repo,
            autonomy_level="autonomous_development",
            verification_commands=["graphify update ."],
        )
        fake_service = _FakeGitHubAppService(error=RuntimeError("boom"))
        monkeypatch.setattr(project_twin_module, "GitHubAppService", lambda: fake_service)

        svc = ProjectTwinService()
        claim = await svc.claim_job(
            worker_id="worker-002",
            capabilities=_full_capabilities(),
        )
        assert claim is not None
        job_id = claim["job"]["id"]
        claim_token = claim["job"]["claim_token"]

        completed = await svc.complete_job(
            job_id=job_id,
            claim_token=claim_token,
            worker_id="worker-002",
            result={
                "summary": "Done",
                "tests_passed": True,
                "graphify_updated": True,
                "verification_results": [
                    {"command": "graphify update .", "status": "passed"},
                ],
                "commit_sha": "abc123",
                "commit_message": "Ship the fix",
                "branch_name": "feature/job-2",
            },
        )

        assert completed["status"] == "failed_terminal"
        assert "Draft pull request creation failed: boom" in (completed["error"] or "")
        stored = await repo.get_work_item(job_id)
        assert stored is not None
        assert stored.status == "failed_terminal"
        assert "Draft pull request creation failed: boom" in (stored.error or "")
        assert await repo.list_project_commits(stored.idea_id) == []

    @pytest.mark.asyncio
    @pytest.mark.parametrize("autonomy_level,job_type", [
        ("suggest_only", "agent_branch_work"),
        ("autonomous_development", "repo_index"),
    ])
    async def test_suggest_only_and_repo_index_skip_draft_pull_request(
        self,
        repo,
        monkeypatch,
        autonomy_level,
        job_type,
    ):
        await _seed_work_item(
            repo,
            autonomy_level=autonomy_level,
            job_type=job_type,
            verification_commands=["graphify update ."],
        )
        fake_service = _FakeGitHubAppService(
            response={
                "html_url": "https://github.com/acme/app/pull/42",
                "url": "https://api.github.com/repos/acme/app/pulls/42",
                "number": 42,
                "state": "open",
                "draft": True,
            }
        )
        monkeypatch.setattr(project_twin_module, "GitHubAppService", lambda: fake_service)

        svc = ProjectTwinService()
        claim = await svc.claim_job(
            worker_id="worker-003",
            capabilities=_full_capabilities(),
        )
        assert claim is not None
        job_id = claim["job"]["id"]
        claim_token = claim["job"]["claim_token"]

        completed = await svc.complete_job(
            job_id=job_id,
            claim_token=claim_token,
            worker_id="worker-003",
            result={
                "summary": "Done",
                "tests_passed": True,
                "graphify_updated": True,
                "verification_results": [
                    {"command": "graphify update .", "status": "passed"},
                ],
                "commit_sha": "abc123",
                "branch_name": "feature/job-3",
            },
        )

        assert completed["status"] == "completed"
        assert "draft_pr" not in (completed["result"] or {})
        assert fake_service.calls == []


class _FakeGitHubAppService:
    def __init__(self, *, response: dict | None = None, error: Exception | None = None) -> None:
        self.response = response or {}
        self.error = error
        self.calls: list[dict[str, object]] = []

    async def create_draft_pull_request(
        self,
        *,
        installation_id: str,
        owner: str,
        repo_name: str,
        title: str,
        head_branch: str,
        base_branch: str,
        body: str = "",
    ) -> dict[str, object]:
        self.calls.append(
            {
                "installation_id": installation_id,
                "owner": owner,
                "repo_name": repo_name,
                "title": title,
                "head_branch": head_branch,
                "base_branch": base_branch,
                "body": body,
            }
        )
        if self.error is not None:
            raise self.error
        return self.response
