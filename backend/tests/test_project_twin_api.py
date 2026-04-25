from __future__ import annotations

import pytest
from httpx import AsyncClient


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
    imported = await test_client.post(
        "/api/ideas/import/github",
        json={
            "installation_id": "12345",
            "repo_full_name": "cauld/indexed-app",
            "default_branch": "main",
        },
    )
    idea_id = imported.json()["idea"]["id"]

    claim_response = await test_client.post("/api/worker/claim", json={"worker_id": "win-worker-1"})
    assert claim_response.status_code == 200
    claim = claim_response.json()["claim"]
    assert claim["job"]["status"] == "claimed"

    job = claim["job"]
    heartbeat = await test_client.post(
        f"/api/worker/jobs/{job['id']}/heartbeat",
        json={"worker_id": "win-worker-1", "claim_token": job["claim_token"], "logs": "still alive"},
    )
    assert heartbeat.status_code == 200
    assert heartbeat.json()["job"]["status"] == "running"

    complete = await test_client.post(
        f"/api/worker/jobs/{job['id']}/complete",
        json={
            "worker_id": "win-worker-1",
            "claim_token": job["claim_token"],
            "logs": "indexed",
            "result": {
                "commit_sha": "abc123",
                "tests_passed": True,
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


@pytest.mark.asyncio
async def test_worker_fail_requeues_retryable_job(test_client: AsyncClient):
    await test_client.post(
        "/api/ideas/import/github",
        json={
            "installation_id": "12345",
            "repo_full_name": "cauld/failing-app",
            "default_branch": "main",
        },
    )
    claim = (await test_client.post("/api/worker/claim", json={"worker_id": "win-worker-1"})).json()["claim"]
    job = claim["job"]

    response = await test_client.post(
        f"/api/worker/jobs/{job['id']}/fail",
        json={
            "worker_id": "win-worker-1",
            "claim_token": job["claim_token"],
            "error": "machine went offline",
            "retryable": True,
        },
    )

    assert response.status_code == 200
    data = response.json()["job"]
    assert data["status"] == "failed_retryable"
    assert data["retry_count"] == 1
