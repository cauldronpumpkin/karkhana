"""Tests for WorkflowEngine state transitions and AGENTS.md artifact versioning."""
from __future__ import annotations

import pytest

from backend.app.repository import (
    BLOCKED_STATUS,
    FactoryBatch,
    FactoryPhase,
    FactoryRun,
    Idea,
    InMemoryRepository,
    ProjectTwin,
    RepairTask,
    TemplateArtifact,
    TemplatePack,
    VerificationRun,
    WorkItem,
    set_repository,
    utcnow,
)
from backend.app.services.agents_md_artifact import AgentsMdArtifactService
from backend.app.services.workflow_engine import SqsDdbWorkflowEngine


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
    engine = SqsDdbWorkflowEngine(repo=repo)
    result = await engine.start_factory_run(
        project_id=project.id,
        template_id=template.template_id,
    )
    return idea, project, template, result


@pytest.fixture
def repo():
    r = InMemoryRepository()
    set_repository(r)
    return r


# ------------------------------------------------------------------
# WorkflowEngine transitions
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_engine_start_factory_run_creates_run_and_phases(repo):
    _, project, template, result = await _create_factory_run(repo)

    assert result["factory_run"]["status"] == "running"
    assert len(result["phases"]) == 3
    assert result["first_batch"] is not None
    assert result["work_item"] is not None


@pytest.mark.asyncio
async def test_engine_on_task_completed_advances_phase(repo):
    _, project, _, result = await _create_factory_run(repo)
    run_id = result["factory_run"]["id"]
    work_item_id = result["work_item"]["id"]

    work_item = await repo.get_work_item(work_item_id)
    work_item.status = "completed"
    work_item.result = {"summary": "Scaffold done", "tests_passed": True}
    await repo.save_work_item(work_item)

    engine = SqsDdbWorkflowEngine(repo=repo)
    orch_result = await engine.on_task_completed(work_item_id)

    assert orch_result is not None
    assert orch_result["action"] == "phase_advanced"
    assert orch_result["next_phase"] == "backend"

    phases = await repo.list_factory_phases(run_id)
    assert phases[0].status == "completed"
    assert phases[1].status == "running"
    assert phases[2].status == "pending"


@pytest.mark.asyncio
async def test_engine_on_task_completed_completes_run(repo):
    _, project, _, result = await _create_factory_run(repo)
    run_id = result["factory_run"]["id"]

    engine = SqsDdbWorkflowEngine(repo=repo)

    for expected_action in ["phase_advanced", "phase_advanced", "run_completed"]:
        phases = await repo.list_factory_phases(run_id)
        running_phase = next((p for p in phases if p.status == "running"), None)
        assert running_phase is not None

        batches = await repo.list_factory_batches(running_phase.id)
        work_item_id = batches[0].work_item_id

        work_item = await repo.get_work_item(work_item_id)
        work_item.status = "completed"
        work_item.result = {"summary": "done", "tests_passed": True}
        await repo.save_work_item(work_item)

        orch_result = await engine.on_task_completed(work_item_id)
        assert orch_result["action"] == expected_action

    run = await repo.get_factory_run(run_id)
    assert run.status == "completed"
    assert run.completed_at is not None


@pytest.mark.asyncio
async def test_engine_on_task_failed_blocks_after_max_repairs(repo):
    from backend.app.config import settings

    original_max = settings.max_repair_attempts_per_task
    settings.max_repair_attempts_per_task = 1
    try:
        _, project, _, result = await _create_factory_run(repo)
        run_id = result["factory_run"]["id"]
        work_item_id = result["work_item"]["id"]

        work_item = await repo.get_work_item(work_item_id)
        work_item.status = "failed_terminal"
        work_item.error = "Build crashed"
        await repo.save_work_item(work_item)

        engine = SqsDdbWorkflowEngine(repo=repo)
        orch_result = await engine.on_task_failed(work_item_id)

        assert orch_result is not None
        assert orch_result["action"] == "repair_created"

        # Simulate repair also failing
        repairs = await repo.list_repair_tasks(run_id)
        assert len(repairs) == 1
        repair_item = await repo.get_work_item(repairs[0].work_item_id)
        repair_item.status = "failed_terminal"
        repair_item.error = "Repair failed"
        await repo.save_work_item(repair_item)

        # Trigger failure on the repair work item (it also has factory_run_id in payload)
        orch_result2 = await engine.on_task_failed(repair_item.id)
        # The repair work item is a factory job, so it will try to create another repair
        # After max attempts, it should block
        run = await repo.get_factory_run(run_id)
        assert run.status == BLOCKED_STATUS
    finally:
        settings.max_repair_attempts_per_task = original_max


@pytest.mark.asyncio
async def test_engine_mark_blocked(repo):
    _, project, _, result = await _create_factory_run(repo)
    run_id = result["factory_run"]["id"]

    engine = SqsDdbWorkflowEngine(repo=repo)
    res = await engine.mark_blocked(run_id, "security violation")

    assert res["action"] == "blocked"
    assert res["reason"] == "security violation"

    run = await repo.get_factory_run(run_id)
    assert run.status == BLOCKED_STATUS


@pytest.mark.asyncio
async def test_engine_mark_complete(repo):
    _, project, _, result = await _create_factory_run(repo)
    run_id = result["factory_run"]["id"]

    engine = SqsDdbWorkflowEngine(repo=repo)
    res = await engine.mark_complete(run_id)

    assert res["action"] == "run_completed"

    run = await repo.get_factory_run(run_id)
    assert run.status == "completed"
    assert run.completed_at is not None


@pytest.mark.asyncio
async def test_engine_pause_and_resume_after_approval(repo):
    _, project, _, result = await _create_factory_run(repo)
    run_id = result["factory_run"]["id"]
    work_item_id = result["work_item"]["id"]

    work_item = await repo.get_work_item(work_item_id)
    work_item.status = "completed"
    work_item.result = {"summary": "done", "tests_passed": True}
    await repo.save_work_item(work_item)

    engine = SqsDdbWorkflowEngine(repo=repo)

    # Force pause by setting autonomy to suggest_only so can_auto_advance_phase returns False
    run = await repo.get_factory_run(run_id)
    run.config["autonomy_level"] = "suggest_only"
    await repo.save_factory_run(run)

    orch_result = await engine.on_task_completed(work_item_id)
    assert orch_result["action"] == "awaiting_approval"

    run = await repo.get_factory_run(run_id)
    assert run.status == "awaiting_approval"

    # Resume
    resume_result = await engine.resume_after_approval(run_id)
    assert resume_result["action"] == "phase_advanced"

    run = await repo.get_factory_run(run_id)
    assert run.status == "running"


@pytest.mark.asyncio
async def test_engine_record_worker_event(repo):
    engine = SqsDdbWorkflowEngine(repo=repo)
    event = await engine.record_worker_event("worker-1", "heartbeat", {"cpu": 10})

    assert event.worker_id == "worker-1"
    assert event.event_type == "heartbeat"
    assert event.payload == {"cpu": 10}

    events = await repo.list_worker_events("worker-1")
    assert len(events) == 1


@pytest.mark.asyncio
async def test_engine_request_verification_passed(repo):
    idea, project, template, result = await _create_factory_run(repo)
    run_id = result["factory_run"]["id"]
    batch_id = result["first_batch"]["id"]

    engine = SqsDdbWorkflowEngine(repo=repo)
    res = await engine.request_verification(
        run_id,
        batch_id,
        {"tests_passed": True, "summary": "All good"},
    )
    assert res["action"] == "verification_passed"

    verifications = await repo.list_verification_runs(batch_id)
    assert len(verifications) == 1
    assert verifications[0].status == "passed"


@pytest.mark.asyncio
async def test_engine_request_repair_creates_task(repo):
    idea, project, template, result = await _create_factory_run(repo)
    run_id = result["factory_run"]["id"]
    batch_id = result["first_batch"]["id"]

    engine = SqsDdbWorkflowEngine(repo=repo)
    res = await engine.request_repair(run_id, batch_id, "test failure")
    assert res["action"] == "repair_created"

    repairs = await repo.list_repair_tasks(run_id)
    assert len(repairs) == 1
    assert repairs[0].status == "pending"


@pytest.mark.asyncio
async def test_engine_enqueue_next_batch_directly(repo):
    idea, project, template, result = await _create_factory_run(repo)
    run_id = result["factory_run"]["id"]
    work_item_id = result["work_item"]["id"]

    # Complete first phase
    work_item = await repo.get_work_item(work_item_id)
    work_item.status = "completed"
    work_item.result = {"summary": "done", "tests_passed": True}
    await repo.save_work_item(work_item)

    phases = await repo.list_factory_phases(run_id)
    first_phase = phases[0]
    first_phase.status = "completed"
    first_phase.completed_at = utcnow()
    await repo.save_factory_phase(first_phase)

    next_phase = phases[1]

    engine = SqsDdbWorkflowEngine(repo=repo)
    res = await engine.enqueue_next_batch(run_id, next_phase.id)

    assert res["action"] == "phase_advanced"
    assert res["next_phase"] == "backend"

    batch = await repo.list_factory_batches(next_phase.id)
    assert len(batch) == 1
    assert batch[0].work_item_id is not None


# ------------------------------------------------------------------
# AGENTS.md Artifact versioning
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_agents_md_import_and_retrieve(repo):
    svc = AgentsMdArtifactService(repo=repo)
    artifact = await svc.import_from_disk(template_id="tpl-1", version="1.0.0")

    assert artifact.template_id == "tpl-1"
    assert artifact.artifact_key == "AGENTS.md"
    assert artifact.version == "1.0.0"
    assert artifact.content_type == "text/markdown"
    assert "graphify" in artifact.content.lower() or artifact.content == ""

    fetched = await svc.get_artifact("tpl-1")
    assert fetched is not None
    assert fetched.version == "1.0.0"


@pytest.mark.asyncio
async def test_agents_md_versioning(repo):
    svc = AgentsMdArtifactService(repo=repo)
    await svc.import_from_disk(template_id="tpl-2", version="1.0.0")
    await svc.import_from_disk(template_id="tpl-2", version="1.1.0")

    versions = await svc.list_versions("tpl-2")
    assert len(versions) == 2
    assert versions[0]["version"] == "1.1.0"
    assert versions[1]["version"] == "1.0.0"

    specific = await svc.get_artifact("tpl-2", version="1.0.0")
    assert specific is not None
    assert specific.version == "1.0.0"

    latest = await svc.get_artifact("tpl-2")
    assert latest is not None
    assert latest.version == "1.1.0"


@pytest.mark.asyncio
async def test_agents_md_contract_reference(repo):
    svc = AgentsMdArtifactService(repo=repo)
    await svc.import_from_disk(template_id="tpl-3", version="2.0.0")

    ref = await svc.get_reference_for_contract("tpl-3")
    assert ref is not None
    assert ref["key"] == "AGENTS.md"
    assert ref["version"] == "2.0.0"
    assert ref["content_type"] == "text/markdown"
    assert "uri" in ref


@pytest.mark.asyncio
async def test_agents_md_missing_returns_none(repo):
    svc = AgentsMdArtifactService(repo=repo)
    fetched = await svc.get_artifact("nonexistent-template")
    assert fetched is None

    ref = await svc.get_reference_for_contract("nonexistent-template")
    assert ref is None

    versions = await svc.list_versions("nonexistent-template")
    assert versions == []
