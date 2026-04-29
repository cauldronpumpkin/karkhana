from __future__ import annotations

import pytest
from httpx import AsyncClient

from backend.app.repository import (
    CodeIndexArtifact,
    FactoryBatch,
    FactoryPhase,
    FactoryRun,
    GitHubInstallation,
    Idea,
    InMemoryRepository,
    LocalWorker,
    ProjectTwin,
    RepairTask,
    ReviewPacket,
    TemplateArtifact,
    TemplatePack,
    VerificationRun,
    WorkItem,
    set_repository,
    utcnow,
)


async def _seed_project_and_template(repo: InMemoryRepository) -> dict:
    idea = Idea(
        title="Review Test",
        slug="review-test",
        description="Project for review packet testing",
        source_type="github_project",
    )
    await repo.create_idea(idea)

    await repo.save_github_installation(
        GitHubInstallation(installation_id="100", account_login="testorg")
    )

    project = ProjectTwin(
        idea_id=idea.id,
        provider="github",
        installation_id="100",
        owner="testorg",
        repo="review-app",
        repo_full_name="testorg/review-app",
        repo_url="https://github.com/testorg/review-app",
        clone_url="https://github.com/testorg/review-app.git",
        default_branch="main",
        detected_stack=["python", "fastapi"],
        test_commands=["pytest backend/tests"],
    )
    await repo.save_project_twin(project)

    template = TemplatePack(
        template_id="test-template-v1",
        version="1.0.0",
        channel="stable",
        display_name="Test Template",
        description="Template for review packet tests",
        phases=[
            {"key": "build", "label": "Build Phase"},
        ],
        quality_gates=[],
        constraints=[],
        opencode_worker={
            "goal": "Build the application",
            "deliverables": ["Working implementation"],
            "verification_commands": ["pytest backend/tests"],
        },
    )
    await repo.save_template_pack(template)

    await repo.save_template_artifact(TemplateArtifact(
        template_id="test-template-v1",
        artifact_key="AGENTS.md",
        content_type="text/markdown",
        uri="s3://templates/test-template-v1/AGENTS.md",
        content="# Standards",
    ))

    index = CodeIndexArtifact(
        project_id=project.id,
        idea_id=idea.id,
        commit_sha="abc123",
        file_inventory=[
            {"path": "backend/app/main.py", "size": 1200, "kind": "source"},
        ],
        test_commands=["pytest backend/tests"],
    )
    await repo.put_code_index(index)

    return {"idea": idea, "project": project, "template": template, "index": index}


async def _seed_factory_run_with_data(repo: InMemoryRepository) -> dict:
    seed = await _seed_project_and_template(repo)
    project = seed["project"]

    factory_run = FactoryRun(
        idea_id=project.idea_id,
        template_id="test-template-v1",
        status="running",
        config={
            "autonomy_level": "autonomous_development",
            "template_version": "1.0.0",
            "goal": "Build the review app",
        },
    )
    await repo.create_factory_run(factory_run)

    phase = FactoryPhase(
        factory_run_id=factory_run.id,
        phase_key="build",
        phase_order=1,
        status="running",
    )
    await repo.save_factory_phase(phase)

    batch = FactoryBatch(
        factory_phase_id=phase.id,
        factory_run_id=factory_run.id,
        batch_key="build-batch-1",
        status="completed",
        worker_id=None,
        work_item_id=None,
    )
    await repo.save_factory_batch(batch)

    work_item = WorkItem(
        idea_id=project.idea_id,
        project_id=project.id,
        job_type="agent_branch_work",
        status="completed",
        payload={
            "branch": "factory/abc12345/build",
            "factory_run_id": factory_run.id,
            "factory_phase_id": phase.id,
            "factory_batch_id": batch.id,
        },
        result={
            "tests_passed": True,
            "files_modified": ["backend/app/main.py", "backend/app/new_module.py"],
            "summary": "All tests passed",
            "graphify_updated": True,
        },
    )
    await repo.enqueue_work_item(work_item)
    batch.work_item_id = work_item.id
    await repo.save_factory_batch(batch)

    verification = VerificationRun(
        factory_batch_id=batch.id,
        factory_run_id=factory_run.id,
        verification_type="post_task",
        status="passed",
        result_summary="All verification commands passed.",
        changed_files=["backend/app/main.py", "backend/app/new_module.py"],
        completed_at=utcnow(),
    )
    await repo.save_verification_run(verification)

    return {**seed, "factory_run": factory_run, "phase": phase, "batch": batch, "work_item": work_item}


@pytest.mark.asyncio
async def test_create_review_packet(test_client: AsyncClient, db_session):
    repo = db_session.repo
    data = await _seed_factory_run_with_data(repo)
    factory_run = data["factory_run"]

    response = await test_client.post(f"/api/factory-runs/{factory_run.id}/review-packet")
    assert response.status_code == 201
    packet = response.json()

    assert packet["run_id"] == factory_run.id
    assert packet["wait_window_state"] == "awaiting_review"
    assert packet["status"] == "running"
    assert packet["promise"] == "Build the review app"
    assert packet["branch_name"] == "factory/abc12345/build"
    assert packet["autonomy_level"] == "autonomous_development"
    assert packet["template_id"] == "test-template-v1"
    assert packet["blast_radius"]["impact_score"] in ("low", "medium", "high")
    assert isinstance(packet["blast_radius"]["impacted_files"], list)
    assert packet["safety_net_results"]["tests_passed"] is True
    assert packet["safety_net_results"]["template_id"] == factory_run.template_id
    assert packet["safety_net_results"]["verification_expectations"]
    assert packet["safety_net_results"]["path_guardrails"]
    assert isinstance(packet["execution_trace"]["entries"], list)
    assert isinstance(packet["changed_files"], list)
    assert packet["evaluator_verdict"]["verdict"] in ("pass", "conditional_pass", "fail")
    assert packet["evaluator_verdict"]["source"] == "deterministic_placeholder"
    assert "review_packet_created" in str(packet["telemetry_events"])
    assert "approve" in packet["allowed_actions"]
    assert packet["decision_gates"]["template_id"] == factory_run.template_id
    assert packet["decision_gates"]["guardrail_pass"] is True
    assert packet["created_at"] is not None


@pytest.mark.asyncio
async def test_create_review_packet_idempotent(test_client: AsyncClient, db_session):
    repo = db_session.repo
    data = await _seed_factory_run_with_data(repo)
    factory_run = data["factory_run"]

    r1 = await test_client.post(f"/api/factory-runs/{factory_run.id}/review-packet")
    assert r1.status_code == 201
    r2 = await test_client.post(f"/api/factory-runs/{factory_run.id}/review-packet")
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]


@pytest.mark.asyncio
async def test_create_review_packet_run_not_found(test_client: AsyncClient, db_session):
    response = await test_client.post("/api/factory-runs/nonexistent/review-packet")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_review_packet(test_client: AsyncClient, db_session):
    repo = db_session.repo
    data = await _seed_factory_run_with_data(repo)
    factory_run = data["factory_run"]

    await test_client.post(f"/api/factory-runs/{factory_run.id}/review-packet")
    response = await test_client.get(f"/api/factory-runs/{factory_run.id}/review-packet")
    assert response.status_code == 200
    packet = response.json()
    assert packet["run_id"] == factory_run.id
    assert packet["run_status"] == "running"


@pytest.mark.asyncio
async def test_get_review_packet_not_found(test_client: AsyncClient, db_session):
    response = await test_client.get("/api/factory-runs/nonexistent/review-packet")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_review_packets(test_client: AsyncClient, db_session):
    repo = db_session.repo
    data1 = await _seed_factory_run_with_data(repo)

    response = await test_client.get("/api/review-packets")
    assert response.status_code == 200
    result = response.json()
    assert "review_packets" in result
    assert len(result["review_packets"]) == 0

    await test_client.post(f"/api/factory-runs/{data1['factory_run'].id}/review-packet")

    response = await test_client.get("/api/review-packets")
    assert response.status_code == 200
    assert len(response.json()["review_packets"]) == 1


@pytest.mark.asyncio
async def test_list_review_packets_with_filter(test_client: AsyncClient, db_session):
    repo = db_session.repo
    data = await _seed_factory_run_with_data(repo)
    fr = data["factory_run"]

    await test_client.post(f"/api/factory-runs/{fr.id}/review-packet")

    response = await test_client.get("/api/review-packets?filter=active")
    assert response.status_code == 200
    assert len(response.json()["review_packets"]) == 1

    response = await test_client.get("/api/review-packets?filter=complete")
    assert response.status_code == 200
    assert len(response.json()["review_packets"]) == 0


@pytest.mark.asyncio
async def test_submit_intervention_approve(test_client: AsyncClient, db_session):
    repo = db_session.repo
    data = await _seed_factory_run_with_data(repo)
    fr = data["factory_run"]

    await test_client.post(f"/api/factory-runs/{fr.id}/review-packet")

    response = await test_client.post(
        f"/api/factory-runs/{fr.id}/review-packet/intervene",
        json={"action": "approve", "rationale": "Looks good"},
    )
    assert response.status_code == 200
    packet = response.json()
    assert packet["wait_window_state"] == "approved"
    assert packet["resolved_at"] is not None

    updated_run = await repo.get_factory_run(fr.id)
    assert updated_run.status == "approved"


@pytest.mark.asyncio
async def test_submit_intervention_reject_requires_rationale(test_client: AsyncClient, db_session):
    repo = db_session.repo
    data = await _seed_factory_run_with_data(repo)
    fr = data["factory_run"]

    await test_client.post(f"/api/factory-runs/{fr.id}/review-packet")

    response = await test_client.post(
        f"/api/factory-runs/{fr.id}/review-packet/intervene",
        json={"action": "reject"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_submit_intervention_reject_with_rationale(test_client: AsyncClient, db_session):
    repo = db_session.repo
    data = await _seed_factory_run_with_data(repo)
    fr = data["factory_run"]

    await test_client.post(f"/api/factory-runs/{fr.id}/review-packet")

    response = await test_client.post(
        f"/api/factory-runs/{fr.id}/review-packet/intervene",
        json={"action": "reject", "rationale": "Security vulnerability detected"},
    )
    assert response.status_code == 200
    packet = response.json()
    assert packet["wait_window_state"] == "rejected"
    assert packet["resolved_at"] is not None


@pytest.mark.asyncio
async def test_submit_intervention_request_changes(test_client: AsyncClient, db_session):
    repo = db_session.repo
    data = await _seed_factory_run_with_data(repo)
    fr = data["factory_run"]

    await test_client.post(f"/api/factory-runs/{fr.id}/review-packet")

    response = await test_client.post(
        f"/api/factory-runs/{fr.id}/review-packet/intervene",
        json={"action": "request_changes", "rationale": "Need more tests"},
    )
    assert response.status_code == 200
    packet = response.json()
    assert packet["wait_window_state"] == "modification_requested"


@pytest.mark.asyncio
async def test_submit_intervention_pause(test_client: AsyncClient, db_session):
    repo = db_session.repo
    data = await _seed_factory_run_with_data(repo)
    fr = data["factory_run"]

    await test_client.post(f"/api/factory-runs/{fr.id}/review-packet")

    response = await test_client.post(
        f"/api/factory-runs/{fr.id}/review-packet/intervene",
        json={"action": "pause"},
    )
    assert response.status_code == 200
    packet = response.json()
    assert packet["wait_window_state"] == "paused"


@pytest.mark.asyncio
async def test_submit_intervention_invalid_transition(test_client: AsyncClient, db_session):
    repo = db_session.repo
    data = await _seed_factory_run_with_data(repo)
    fr = data["factory_run"]

    await test_client.post(f"/api/factory-runs/{fr.id}/review-packet")

    await test_client.post(
        f"/api/factory-runs/{fr.id}/review-packet/intervene",
        json={"action": "approve", "rationale": "ok"},
    )

    response = await test_client.post(
        f"/api/factory-runs/{fr.id}/review-packet/intervene",
        json={"action": "approve"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_submit_intervention_unknown_action(test_client: AsyncClient, db_session):
    repo = db_session.repo
    data = await _seed_factory_run_with_data(repo)
    fr = data["factory_run"]

    await test_client.post(f"/api/factory-runs/{fr.id}/review-packet")

    response = await test_client.post(
        f"/api/factory-runs/{fr.id}/review-packet/intervene",
        json={"action": "explode"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_start_wait_window(test_client: AsyncClient, db_session):
    repo = db_session.repo
    data = await _seed_factory_run_with_data(repo)
    fr = data["factory_run"]

    await test_client.post(f"/api/factory-runs/{fr.id}/review-packet")

    response = await test_client.post(
        f"/api/factory-runs/{fr.id}/review-packet/start-wait-window",
        json={},
    )
    assert response.status_code == 200
    packet = response.json()
    assert packet["wait_window_state"] == "wait_window"
    assert packet["wait_window_started_at"] is not None
    assert packet["expires_at"] is not None


@pytest.mark.asyncio
async def test_record_expiry_transition(test_client: AsyncClient, db_session):
    repo = db_session.repo
    data = await _seed_factory_run_with_data(repo)
    fr = data["factory_run"]

    await test_client.post(f"/api/factory-runs/{fr.id}/review-packet")
    await test_client.post(f"/api/factory-runs/{fr.id}/review-packet/start-wait-window", json={})

    response = await test_client.post(
        f"/api/factory-runs/{fr.id}/review-packet/record-expiry",
    )
    assert response.status_code == 200
    packet = response.json()
    assert packet["wait_window_state"] == "no_objection_recorded"

    response = await test_client.post(
        f"/api/factory-runs/{fr.id}/review-packet/intervene",
        json={"action": "continue_after_no_objection"},
    )
    assert response.status_code == 200
    assert response.json()["wait_window_state"] == "ready_to_continue"


@pytest.mark.asyncio
async def test_record_expiry_invalid_state(test_client: AsyncClient, db_session):
    repo = db_session.repo
    data = await _seed_factory_run_with_data(repo)
    fr = data["factory_run"]

    await test_client.post(f"/api/factory-runs/{fr.id}/review-packet")
    await test_client.post(
        f"/api/factory-runs/{fr.id}/review-packet/intervene",
        json={"action": "approve", "rationale": "ok"},
    )

    response = await test_client.post(
        f"/api/factory-runs/{fr.id}/review-packet/record-expiry",
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_review_packet_with_worker_metadata(test_client: AsyncClient, db_session):
    repo = db_session.repo
    data = await _seed_factory_run_with_data(repo)
    fr = data["factory_run"]
    batch = data["batch"]

    worker = LocalWorker(
        display_name="Dev Machine",
        machine_name="dev-laptop",
        platform="windows",
        status="approved",
    )
    await repo.save_local_worker(worker)
    batch.worker_id = worker.id
    await repo.save_factory_batch(batch)

    response = await test_client.post(f"/api/factory-runs/{fr.id}/review-packet")
    assert response.status_code == 201
    packet = response.json()
    assert packet["worker_id"] == worker.id
    assert packet["worker_display_name"] == "Dev Machine"
    assert packet["worker_machine_name"] == "dev-laptop"


@pytest.mark.asyncio
async def test_review_packet_with_verification_failures(test_client: AsyncClient, db_session):
    repo = db_session.repo
    data = await _seed_factory_run_with_data(repo)
    fr = data["factory_run"]
    batch = data["batch"]

    failed_v = VerificationRun(
        factory_batch_id=batch.id,
        factory_run_id=fr.id,
        verification_type="post_task",
        status="failed",
        result_summary="2 tests failed",
        failure_classification="test",
        changed_files=["backend/app/main.py"],
        command_output="FAILED test_something",
        completed_at=utcnow(),
    )
    await repo.save_verification_run(failed_v)

    repair = RepairTask(
        factory_run_id=fr.id,
        factory_batch_id=batch.id,
        failure_classification="test",
        status="pending",
        attempt_number=1,
        changed_files=["backend/app/main.py"],
    )
    await repo.save_repair_task(repair)

    response = await test_client.post(f"/api/factory-runs/{fr.id}/review-packet")
    assert response.status_code == 201
    packet = response.json()
    assert packet["safety_net_results"]["tests_passed"] is False
    assert packet["safety_net_results"]["repair_loop_triggered"] is True
    assert packet["safety_net_results"]["repair_count"] == 1
    assert packet["evaluator_verdict"]["verdict"] == "fail"
    assert packet["blast_radius"]["impacted_files"] == ["backend/app/main.py", "backend/app/new_module.py"]


@pytest.mark.asyncio
async def test_pause_resume_cycle(test_client: AsyncClient, db_session):
    repo = db_session.repo
    data = await _seed_factory_run_with_data(repo)
    fr = data["factory_run"]

    await test_client.post(f"/api/factory-runs/{fr.id}/review-packet")

    r = await test_client.post(
        f"/api/factory-runs/{fr.id}/review-packet/intervene",
        json={"action": "pause"},
    )
    assert r.status_code == 200
    assert r.json()["wait_window_state"] == "paused"

    r = await test_client.post(
        f"/api/factory-runs/{fr.id}/review-packet/start-wait-window",
        json={},
    )
    assert r.status_code == 200
    assert r.json()["wait_window_state"] == "wait_window"

    r = await test_client.post(
        f"/api/factory-runs/{fr.id}/review-packet/intervene",
        json={"action": "approve", "rationale": "Resuming with approval"},
    )
    assert r.status_code == 200
    assert r.json()["wait_window_state"] == "approved"


@pytest.mark.asyncio
async def test_intervention_packet_not_found(test_client: AsyncClient, db_session):
    response = await test_client.post(
        "/api/factory-runs/nonexistent/review-packet/intervene",
        json={"action": "approve"},
    )
    assert response.status_code == 404
