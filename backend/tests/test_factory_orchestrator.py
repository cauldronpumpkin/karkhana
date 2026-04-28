"""Tests for factory run orchestration: phase advancement, state transitions, and failure handling."""
from __future__ import annotations

import pytest

from backend.app.repository import (
    Idea,
    InMemoryRepository,
    ProjectTwin,
    TemplatePack,
    set_repository,
    utcnow,
)
from backend.app.services.factory_orchestrator import FactoryOrchestratorService
from backend.app.services.factory_run import FactoryRunService


async def _seed_project_and_template(repo: InMemoryRepository):
    idea = Idea(title="Test Project", slug="test-project", description="test")
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

    template = TemplatePack(
        template_id="multi-phase-v1",
        version="1.0.0",
        channel="stable",
        display_name="Multi-Phase",
        description="",
        phases=[
            {"key": "scaffold", "label": "Scaffold"},
            {"key": "backend", "label": "Backend"},
            {"key": "frontend", "label": "Frontend"},
        ],
    )
    await repo.save_template_pack(template)

    return idea, project, template


async def _create_factory_run(repo: InMemoryRepository):
    idea, project, template = await _seed_project_and_template(repo)
    svc = FactoryRunService()
    result = await svc.create_factory_run(
        project_id=project.id,
        template_id=template.template_id,
    )
    return idea, project, template, result


@pytest.fixture
def repo():
    r = InMemoryRepository()
    set_repository(r)
    return r


@pytest.mark.asyncio
async def test_on_task_completed_advances_to_next_phase(repo):
    _, project, _, result = await _create_factory_run(repo)

    run_id = result["factory_run"]["id"]
    work_item_id = result["work_item"]["id"]

    work_item = await repo.get_work_item(work_item_id)
    work_item.status = "completed"
    work_item.result = {"summary": "Scaffold done", "tests_passed": True}
    await repo.save_work_item(work_item)

    orchestrator = FactoryOrchestratorService()
    orch_result = await orchestrator.on_task_completed(work_item_id)

    assert orch_result is not None
    assert orch_result["action"] == "phase_advanced"
    assert orch_result["next_phase"] == "backend"
    assert orch_result["work_item_id"] is not None

    phases = await repo.list_factory_phases(run_id)
    assert phases[0].status == "completed"
    assert phases[1].status == "running"
    assert phases[2].status == "pending"

    run = await repo.get_factory_run(run_id)
    assert run.status == "running"


@pytest.mark.asyncio
async def test_on_task_completed_sets_s3_output_uris(repo):
    _, project, _, result = await _create_factory_run(repo)

    run_id = result["factory_run"]["id"]
    work_item_id = result["work_item"]["id"]
    batch_id = result["first_batch"]["id"]
    phases = await repo.list_factory_phases(run_id)
    phase_id = phases[0].id

    work_item = await repo.get_work_item(work_item_id)
    work_item.status = "completed"
    work_item.result = {
        "summary": "Done",
        "tests_passed": True,
        "phase_artifacts": {"output_uri": "s3://custom-bucket/output.tgz"},
    }
    await repo.save_work_item(work_item)

    orchestrator = FactoryOrchestratorService()
    await orchestrator.on_task_completed(work_item_id)

    batch = await repo.get_factory_batch(batch_id)
    assert batch is not None
    assert batch.output_uri == "s3://custom-bucket/output.tgz"

    phase = await repo.get_factory_phase(run_id, phase_id)
    assert phase is not None
    assert phase.output_uri is not None
    assert phase.output_uri.startswith("s3://factory-artifacts/")

    verifications = await repo.list_verification_runs(batch_id)
    assert len(verifications) == 1
    assert verifications[0].status == "passed"
    assert verifications[0].result_uri is not None


@pytest.mark.asyncio
async def test_on_task_completed_completes_run_when_last_phase(repo):
    _, project, _, result = await _create_factory_run(repo)
    run_id = result["factory_run"]["id"]

    orchestrator = FactoryOrchestratorService()

    for i, expected_action in enumerate(["phase_advanced", "phase_advanced", "run_completed"]):
        phases = await repo.list_factory_phases(run_id)
        running_phase = next((p for p in phases if p.status == "running"), None)
        assert running_phase is not None, f"No running phase at step {i}"

        batches = await repo.list_factory_batches(running_phase.id)
        assert batches, f"No batches for phase {running_phase.phase_key}"
        work_item_id = batches[0].work_item_id

        work_item = await repo.get_work_item(work_item_id)
        assert work_item is not None
        work_item.status = "completed"
        work_item.result = {"summary": f"Phase {i + 1} done", "tests_passed": True}
        await repo.save_work_item(work_item)

        orch_result = await orchestrator.on_task_completed(work_item_id)
        assert orch_result is not None
        assert orch_result["action"] == expected_action

    run = await repo.get_factory_run(run_id)
    assert run.status == "completed"
    assert run.completed_at is not None
    assert run.tracking_manifest_uri is not None
    assert "manifest.json" in run.tracking_manifest_uri

    phases = await repo.list_factory_phases(run_id)
    assert all(p.status == "completed" for p in phases)


@pytest.mark.asyncio
async def test_on_task_failed_terminal_creates_repair(repo):
    _, project, _, result = await _create_factory_run(repo)

    run_id = result["factory_run"]["id"]
    work_item_id = result["work_item"]["id"]
    batch_id = result["first_batch"]["id"]

    work_item = await repo.get_work_item(work_item_id)
    work_item.status = "failed_terminal"
    work_item.error = "Build crashed"
    await repo.save_work_item(work_item)

    orchestrator = FactoryOrchestratorService()
    orch_result = await orchestrator.on_task_failed(work_item_id)

    assert orch_result is not None
    assert orch_result["action"] == "repair_created"
    assert orch_result["failure_classification"] == "ambiguous"

    run = await repo.get_factory_run(run_id)
    assert run.status == "running"

    from backend.app.repository import RepairTask
    repairs = await repo.list_repair_tasks(run_id)
    assert len(repairs) == 1
    assert repairs[0].status == "pending"

    verifications = await repo.list_verification_runs(batch_id)
    assert len(verifications) == 1
    assert verifications[0].status == "failed"

    verifications = await repo.list_verification_runs(result["first_batch"]["id"])
    assert len(verifications) == 1
    assert verifications[0].status == "failed"


@pytest.mark.asyncio
async def test_on_task_failed_retryable_is_noop(repo):
    _, project, _, result = await _create_factory_run(repo)

    run_id = result["factory_run"]["id"]
    work_item_id = result["work_item"]["id"]

    work_item = await repo.get_work_item(work_item_id)
    work_item.status = "failed_retryable"
    work_item.error = "Temporary issue"
    await repo.save_work_item(work_item)

    orchestrator = FactoryOrchestratorService()
    orch_result = await orchestrator.on_task_failed(work_item_id)

    assert orch_result is None

    run = await repo.get_factory_run(run_id)
    assert run.status == "running"


@pytest.mark.asyncio
async def test_on_task_completed_nonexistent_work_item_is_noop(repo):
    orchestrator = FactoryOrchestratorService()
    result = await orchestrator.on_task_completed("nonexistent-id")
    assert result is None


@pytest.mark.asyncio
async def test_on_task_completed_non_factory_job_is_noop(repo):
    from backend.app.repository import WorkItem

    item = WorkItem(
        idea_id="i1",
        project_id="p1",
        job_type="repo_index",
        payload={"reason": "test"},
    )
    item.status = "completed"
    await repo.save_work_item(item)

    orchestrator = FactoryOrchestratorService()
    result = await orchestrator.on_task_completed(item.id)
    assert result is None


@pytest.mark.asyncio
async def test_on_task_failed_non_factory_job_is_noop(repo):
    from backend.app.repository import WorkItem

    item = WorkItem(
        idea_id="i1",
        project_id="p1",
        job_type="repo_index",
        payload={"reason": "test"},
    )
    item.status = "failed_terminal"
    item.error = "broken"
    await repo.save_work_item(item)

    orchestrator = FactoryOrchestratorService()
    result = await orchestrator.on_task_failed(item.id)
    assert result is None


@pytest.mark.asyncio
async def test_on_task_completed_idempotent_for_completed_run(repo):
    _, project, _, result = await _create_factory_run(repo)
    run_id = result["factory_run"]["id"]

    run = await repo.get_factory_run(run_id)
    run.status = "completed"
    run.completed_at = utcnow()
    await repo.save_factory_run(run)

    work_item_id = result["work_item"]["id"]
    work_item = await repo.get_work_item(work_item_id)
    work_item.status = "completed"
    await repo.save_work_item(work_item)

    orchestrator = FactoryOrchestratorService()
    orch_result = await orchestrator.on_task_completed(work_item_id)
    assert orch_result is None


@pytest.mark.asyncio
async def test_is_factory_job():
    assert FactoryOrchestratorService.is_factory_job({"factory_run_id": "abc"}) is True
    assert FactoryOrchestratorService.is_factory_job({"other": "data"}) is False
    assert FactoryOrchestratorService.is_factory_job({}) is False
    assert FactoryOrchestratorService.is_factory_job(None) is False


@pytest.mark.asyncio
async def test_on_task_failed_sets_s3_failure_uri_on_batch(repo):
    _, project, _, result = await _create_factory_run(repo)
    run_id = result["factory_run"]["id"]
    work_item_id = result["work_item"]["id"]
    batch_id = result["first_batch"]["id"]

    work_item = await repo.get_work_item(work_item_id)
    work_item.status = "failed_terminal"
    work_item.error = "Crash"
    await repo.save_work_item(work_item)

    orchestrator = FactoryOrchestratorService()
    await orchestrator.on_task_failed(work_item_id)

    batch = await repo.get_factory_batch(batch_id)
    assert batch is not None
    assert batch.output_uri is not None
    assert "/failure" in batch.output_uri
    assert batch.output_uri.startswith("s3://")


@pytest.mark.asyncio
async def test_phase_advancement_enqueues_work_item_with_factory_payload(repo):
    _, project, _, result = await _create_factory_run(repo)
    run_id = result["factory_run"]["id"]
    work_item_id = result["work_item"]["id"]

    work_item = await repo.get_work_item(work_item_id)
    work_item.status = "completed"
    work_item.result = {"summary": "Done", "tests_passed": True}
    await repo.save_work_item(work_item)

    orchestrator = FactoryOrchestratorService()
    orch_result = await orchestrator.on_task_completed(work_item_id)

    next_work_item_id = orch_result["work_item_id"]
    next_item = await repo.get_work_item(next_work_item_id)
    assert next_item is not None
    assert next_item.job_type == "agent_branch_work"
    assert next_item.payload["factory_run_id"] == run_id
    assert next_item.payload["factory_phase_id"] is not None
    assert next_item.payload["factory_batch_id"] is not None
    assert next_item.payload["role"] == "worker"
    assert next_item.payload["role_prompt"].startswith("Role: Worker")
    assert next_item.payload["role_prompt_template"].startswith("Role: Worker")
    assert next_item.payload["role_output_schema"]["type"] == "object"
    assert next_item.payload["verifier_contract"]["role"] == "verifier"
    assert next_item.priority == 60
