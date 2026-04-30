from __future__ import annotations

import pytest
from httpx import AsyncClient

from backend.app.repository import (
    CodeIndexArtifact,
    GitHubInstallation,
    Idea,
    InMemoryRepository,
    ProjectTwin,
    TemplateArtifact,
    TemplatePack,
    set_repository,
)


async def _approved_worker(test_client: AsyncClient):
    registered = await test_client.post(
        "/api/local-workers/register",
        json={
            "display_name": "Build Box",
            "machine_name": "WIN-BUILD-1",
            "platform": "Windows 11",
            "engine": "openclaude",
            "capabilities": ["repo_index", "agent_branch_work"],
            "config": {"autonomy": "branch_pr"},
        },
    )
    request_id = registered.json()["request"]["id"]
    approved = await test_client.post(f"/api/local-workers/requests/{request_id}/approve")
    return approved.json()["worker"], approved.json()["credentials"]


async def _seed_project_and_template(repo: InMemoryRepository) -> dict:
    idea = Idea(
        title="Project Twin Factory",
        slug="project-twin-factory",
        description="Project for factory run tracking testing",
        source_type="github_project",
    )
    await repo.create_idea(idea)

    await repo.save_github_installation(
        GitHubInstallation(installation_id="99", account_login="acme")
    )

    project = ProjectTwin(
        idea_id=idea.id,
        provider="github",
        installation_id="99",
        owner="acme",
        repo="factory-app",
        repo_full_name="acme/factory-app",
        repo_url="https://github.com/acme/factory-app",
        clone_url="https://github.com/acme/factory-app.git",
        default_branch="main",
        detected_stack=["python", "fastapi"],
        test_commands=["pytest backend/tests"],
    )
    await repo.save_project_twin(project)

    template = TemplatePack(
        template_id="factory-tracking-v1",
        version="3.1.4",
        channel="stable",
        display_name="Factory Tracking",
        description="Factory run tracking template",
        phases=[
            {"key": "scaffold", "label": "Project Scaffolding"},
            {"key": "backend", "label": "Backend API"},
        ],
        opencode_worker={
            "goal": "Build the factory-tracking sample",
            "verification_commands": ["pytest backend/tests", "graphify update ."],
        },
    )
    await repo.save_template_pack(template)
    await repo.save_template_artifact(TemplateArtifact(
        template_id=template.template_id,
        artifact_key="README.md",
        content_type="text/markdown",
        uri="s3://templates/factory-tracking-v1/README.md",
        content="# Factory Tracking",
    ))

    index = CodeIndexArtifact(
        project_id=project.id,
        idea_id=idea.id,
        commit_sha="abc123",
        file_inventory=[{"path": "backend/app/main.py", "size": 1200, "kind": "source"}],
        test_commands=["pytest backend/tests"],
        architecture_summary="FastAPI backend with DynamoDB storage",
    )
    await repo.put_code_index(index)

    return {"idea": idea, "project": project, "template": template}


@pytest.mark.asyncio
async def test_import_github_project_creates_idea_project_and_initial_job(test_client: AsyncClient):
    response = await test_client.post(
        "/api/ideas/import/github",
        json={
            "installation_id": "12345",
            "repo_full_name": "cauld/example-app",
            "default_branch": "main",
            "deploy_url": "https://example.test",
            "current_status": "Deployed but incomplete",
            "desired_outcome": "Finish production readiness",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["idea"]["source_type"] == "github_project"
    assert data["project"]["repo_full_name"] == "cauld/example-app"
    assert data["job"]["job_type"] == "repo_index"
    assert data["job"]["status"] == "queued"

    status = await test_client.get(f"/api/ideas/{data['idea']['id']}/project")
    assert status.status_code == 200
    assert status.json()["project"]["open_queue_count"] == 1


@pytest.mark.asyncio
async def test_worker_claim_heartbeat_complete_and_code_index(test_client: AsyncClient):
    worker, credentials = await _approved_worker(test_client)
    imported = await test_client.post(
        "/api/ideas/import/github",
        json={
            "installation_id": "12345",
            "repo_full_name": "cauld/indexed-app",
            "default_branch": "main",
        },
    )
    idea_id = imported.json()["idea"]["id"]

    claim_response = await test_client.post(
        "/api/worker/claim",
        json={"worker_id": worker["id"]},
        headers={"Authorization": f"Bearer {credentials['api_token']}"},
    )
    assert claim_response.status_code == 200
    claim = claim_response.json()["claim"]
    assert claim["job"]["status"] == "claimed"

    job = claim["job"]
    heartbeat = await test_client.post(
        f"/api/worker/jobs/{job['id']}/heartbeat",
        json={"worker_id": worker["id"], "claim_token": job["claim_token"], "logs": "still alive"},
        headers={"Authorization": f"Bearer {credentials['api_token']}"},
    )
    assert heartbeat.status_code == 200
    assert heartbeat.json()["job"]["status"] == "running"

    complete = await test_client.post(
        f"/api/worker/jobs/{job['id']}/complete",
        headers={"Authorization": f"Bearer {credentials['api_token']}"},
        json={
            "worker_id": worker["id"],
            "claim_token": job["claim_token"],
            "logs": "indexed",
            "result": {
                "commit_sha": "abc123",
                "tests_passed": True,
                "token_economy": {
                    "worker_run_id": "worker-run-001",
                    "provider": "openai",
                    "model": "gpt-5.4-mini",
                    "input_tokens_total": 100,
                    "input_tokens_cached": 25,
                    "output_tokens": 50,
                    "tool_calls_count": 2,
                    "files_read_count": 3,
                    "files_modified_count": 1,
                    "cost_estimate_usd": 0.75,
                },
                "code_index": {
                    "file_inventory": [{"path": "package.json", "size": 120, "kind": "manifest"}],
                    "manifests": [{"path": "package.json", "content": "{}"}],
                    "detected_stack": ["svelte"],
                    "test_commands": ["npm test"],
                    "architecture_summary": "# Codebase Dossier\n\nIndexed.",
                    "risks": ["No CI detected."],
                },
            },
        },
    )
    assert complete.status_code == 200
    assert complete.json()["job"]["status"] == "completed"

    status = (await test_client.get(f"/api/ideas/{idea_id}/project")).json()
    assert status["project"]["last_indexed_commit"] == "abc123"
    assert status["project"]["index_status"] == "indexed"
    assert status["project"]["detected_stack"] == ["svelte"]
    assert status["latest_index"]["commit_sha"] == "abc123"
    token_economy = complete.json()["job"]["result"]["token_economy"]
    assert token_economy["cache_hit_rate"] == 0.25
    assert token_economy["input_tokens_total"] == 100
    assert token_economy["duplicate_work_detected"] is False


@pytest.mark.asyncio
async def test_project_status_includes_factory_run_tracking(test_client: AsyncClient, db_session):
    repo = db_session.repo
    seed = await _seed_project_and_template(repo)
    project = seed["project"]
    idea = seed["idea"]
    template = seed["template"]

    create = await test_client.post(
        f"/api/projects/{project.id}/factory-runs",
        json={"template_id": template.template_id},
    )
    assert create.status_code == 201

    status = await test_client.get(f"/api/ideas/{idea.id}/project")
    assert status.status_code == 200
    data = status.json()
    assert len(data["factory_runs"]) == 1

    factory_run = data["factory_runs"][0]
    summary = factory_run["tracking_summary"]
    assert summary["template"]["template_id"] == template.template_id
    assert summary["template"]["template_version"] == template.version
    assert summary["phase_progress"]["total"] == 2
    assert summary["batch_progress"]["total"] == 1
    assert summary["last_indexed_commit"] == "abc123"
    assert summary["graphify_status"] in {"pending", "running", "updated", "missing"}
    assert summary["verification_state"]["status"] == "pending"
    assert summary["worker_queue_state"]["total_work_items"] >= 1


@pytest.mark.asyncio
async def test_build_next_actions_endpoint(test_client: AsyncClient, db_session):
    repo = db_session.repo
    idea = Idea(
        title="Next Action Idea",
        slug="next-action-idea",
        description="Testing next action endpoint",
        source_type="manual",
    )
    await repo.create_idea(idea)

    response = await test_client.get(f"/api/ideas/{idea.id}/build/next-actions")
    assert response.status_code == 200
    data = response.json()
    assert data["idea_id"] == idea.id
    assert data["next_actions"]
    assert data["next_actions"][0]["suggested_owner"] == "local-worker"


@pytest.mark.asyncio
async def test_worker_fail_requeues_retryable_job(test_client: AsyncClient):
    worker, credentials = await _approved_worker(test_client)
    await test_client.post(
        "/api/ideas/import/github",
        json={
            "installation_id": "12345",
            "repo_full_name": "cauld/failing-app",
            "default_branch": "main",
        },
    )
    claim = (
        await test_client.post(
            "/api/worker/claim",
            json={"worker_id": worker["id"]},
            headers={"Authorization": f"Bearer {credentials['api_token']}"},
        )
    ).json()["claim"]
    job = claim["job"]

    response = await test_client.post(
        f"/api/worker/jobs/{job['id']}/fail",
        headers={"Authorization": f"Bearer {credentials['api_token']}"},
        json={
            "worker_id": worker["id"],
            "claim_token": job["claim_token"],
            "error": "machine went offline",
            "retryable": True,
        },
    )

    assert response.status_code == 200
    data = response.json()["job"]
    assert data["status"] == "failed_retryable"
    assert data["retry_count"] == 1
