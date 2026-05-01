from __future__ import annotations

import json
from datetime import timedelta

import pytest
from httpx import AsyncClient

from backend.app.config import settings
from backend.app.repository import get_repository, utcnow


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
    pairing_token = registered.json()["pairing_token"]
    approved = await test_client.post(f"/api/local-workers/requests/{request_id}/approve")
    return request_id, pairing_token, approved.json()["worker"], approved.json()["credentials"]


@pytest.mark.asyncio
async def test_register_approve_deny_revoke_and_rotate_worker(test_client: AsyncClient):
    denied = await test_client.post(
        "/api/local-workers/register",
        json={"machine_name": "LAPTOP-DENY", "platform": "Windows", "engine": "openclaude"},
    )
    deny_response = await test_client.post(
        f"/api/local-workers/requests/{denied.json()['request']['id']}/deny",
        json={"reason": "not this machine"},
    )
    assert deny_response.status_code == 200
    assert deny_response.json()["request"]["status"] == "denied"

    request_id, pairing_token, worker, credentials = await _approved_worker(test_client)
    assert worker["status"] == "approved"
    assert credentials["api_token"]
    assert credentials["command_queue_url"] == ""

    registration = await test_client.get(f"/api/local-workers/registrations/{request_id}")
    assert registration.json()["credentials"]["api_token"] is None

    installer_registration = await test_client.get(f"/api/local-workers/registrations/{request_id}?pairing_token={pairing_token}")
    assert installer_registration.json()["credentials"]["api_token"]

    rotated = await test_client.post(f"/api/local-workers/{worker['id']}/rotate-credentials")
    assert rotated.status_code == 200
    assert rotated.json()["credentials"]["api_token"]

    revoked = await test_client.post(f"/api/local-workers/{worker['id']}/revoke")
    assert revoked.status_code == 200
    assert revoked.json()["worker"]["status"] == "revoked"


@pytest.mark.asyncio
async def test_worker_event_completes_existing_work_item(test_client: AsyncClient):
    _, _, worker, credentials = await _approved_worker(test_client)
    imported = await test_client.post(
        "/api/ideas/import/github",
        json={"installation_id": "12345", "repo_full_name": "cauld/sqs-app", "default_branch": "main"},
    )
    idea_id = imported.json()["idea"]["id"]

    claim = (
        await test_client.post(
            "/api/worker/claim",
            json={"worker_id": worker["id"], "capabilities": ["repo_index"]},
            headers={"Authorization": f"Bearer {credentials['api_token']}"},
        )
    ).json()["claim"]

    event = await test_client.post(
        f"/api/local-workers/{worker['id']}/events",
        headers={"Authorization": f"Bearer {credentials['api_token']}"},
        json={
            "type": "job_completed",
            "payload": {
                "work_item_id": claim["job"]["id"],
                "claim_token": claim["job"]["claim_token"],
                            "result": {"commit_sha": "def456", "tests_passed": True, "code_index": {"detected_stack": ["python"]}},
                            "logs": "completed through event queue",
                            "branch_name": "factory/job-1/fix",
                        },
                    },
                )
    assert event.status_code == 200

    status = (await test_client.get(f"/api/ideas/{idea_id}/project")).json()
    assert status["project"]["last_indexed_commit"] == "def456"
    assert status["jobs"][0]["status"] == "completed"
    assert status["jobs"][0]["branch_name"] == "factory/job-1/fix"


@pytest.mark.asyncio
async def test_revoked_and_expired_workers_cannot_submit_events(test_client: AsyncClient):
    _, _, worker, credentials = await _approved_worker(test_client)

    await test_client.post(f"/api/local-workers/{worker['id']}/revoke")
    revoked_event = await test_client.post(
        f"/api/local-workers/{worker['id']}/events",
        headers={"Authorization": f"Bearer {credentials['api_token']}"},
        json={"type": "heartbeat", "payload": {}},
    )
    assert revoked_event.status_code == 401

    _, _, active_worker, active_credentials = await _approved_worker(test_client)
    lease = await get_repository().get_worker_credential_lease(active_worker["id"])
    lease.expires_at = utcnow() - timedelta(seconds=1)
    await get_repository().save_worker_credential_lease(lease)

    expired_event = await test_client.post(
        f"/api/local-workers/{active_worker['id']}/events",
        headers={"Authorization": f"Bearer {active_credentials['api_token']}"},
        json={"type": "heartbeat", "payload": {}},
    )
    assert expired_event.status_code == 401


@pytest.mark.asyncio
async def test_sqs_records_fail_retryable_job(test_client: AsyncClient):
    _, _, worker, credentials = await _approved_worker(test_client)
    await test_client.post(
        "/api/ideas/import/github",
        json={"installation_id": "12345", "repo_full_name": "cauld/event-app", "default_branch": "main"},
    )
    claim = (
        await test_client.post(
            "/api/worker/claim",
            json={"worker_id": worker["id"], "capabilities": ["repo_index"]},
            headers={"Authorization": f"Bearer {credentials['api_token']}"},
        )
    ).json()["claim"]

    from backend.app.services.local_workers import LocalWorkerService

    result = await LocalWorkerService().process_sqs_records(
        [
            {
                "body": json.dumps(
                    {
                        "worker_id": worker["id"],
                        "type": "job_failed",
                        "payload": {
                            "work_item_id": claim["job"]["id"],
                            "claim_token": claim["job"]["claim_token"],
                            "error": "openclaude failed",
                            "retryable": True,
                        },
                    }
                )
            }
        ]
    )
    assert result == {"processed": 1, "rejected": 0}
    job = await get_repository().get_work_item(claim["job"]["id"])
    assert job.status == "failed_retryable"


@pytest.mark.asyncio
async def test_sqs_events_from_revoked_worker_are_rejected(test_client: AsyncClient):
    _, _, worker, credentials = await _approved_worker(test_client)
    await test_client.post(
        "/api/ideas/import/github",
        json={"installation_id": "12345", "repo_full_name": "cauld/revoked-worker-app", "default_branch": "main"},
    )
    claim = (
        await test_client.post(
            "/api/worker/claim",
            json={"worker_id": worker["id"], "capabilities": ["repo_index"]},
            headers={"Authorization": f"Bearer {credentials['api_token']}"},
        )
    ).json()["claim"]

    await test_client.post(f"/api/local-workers/{worker['id']}/revoke")

    from backend.app.services.local_workers import LocalWorkerService

    result = await LocalWorkerService().process_sqs_records(
        [
            {
                "body": json.dumps(
                    {
                        "worker_id": worker["id"],
                        "type": "job_completed",
                        "payload": {
                            "work_item_id": claim["job"]["id"],
                            "claim_token": claim["job"]["claim_token"],
                            "result": {"commit_sha": "should-not-apply"},
                        },
                    }
                )
            }
        ]
    )
    assert result == {"processed": 0, "rejected": 1}

    job = await get_repository().get_work_item(claim["job"]["id"])
    assert job.status == "claimed"
    lease = await get_repository().get_worker_credential_lease(worker["id"])
    assert lease.expires_at <= utcnow()


@pytest.mark.asyncio
async def test_local_worker_dashboard_redacts_claim_tokens(test_client: AsyncClient):
    _, _, worker, credentials = await _approved_worker(test_client)
    await test_client.post(
        "/api/ideas/import/github",
        json={"installation_id": "12345", "repo_full_name": "cauld/dashboard-jobs", "default_branch": "main"},
    )
    await test_client.post(
        "/api/worker/claim",
        json={"worker_id": worker["id"], "capabilities": ["repo_index"]},
        headers={"Authorization": f"Bearer {credentials['api_token']}"},
    )

    dashboard = await test_client.get("/api/local-workers")
    assert dashboard.status_code == 200
    assert dashboard.json()["jobs"]
    assert all("claim_token" not in job for job in dashboard.json()["jobs"])
    assert dashboard.json()["jobs"][0]["worker_state"]["has_claim_token"] is True


@pytest.mark.asyncio
async def test_revoked_worker_cannot_update_claimed_job_with_shared_token(test_client: AsyncClient):
    original_token = settings.worker_auth_token
    settings.worker_auth_token = "shared-test-token"
    try:
        _, _, worker, credentials = await _approved_worker(test_client)
        await test_client.post(
            "/api/ideas/import/github",
            json={"installation_id": "12345", "repo_full_name": "cauld/revoked-direct-api", "default_branch": "main"},
        )
        claim = (
            await test_client.post(
                "/api/worker/claim",
                json={"worker_id": worker["id"], "capabilities": ["repo_index"]},
                headers={"Authorization": f"Bearer {credentials['api_token']}"},
            )
        ).json()["claim"]

        await test_client.post(f"/api/local-workers/{worker['id']}/revoke")
        response = await test_client.post(
            f"/api/worker/jobs/{claim['job']['id']}/heartbeat",
            headers={"x-idearefinery-worker-token": "shared-test-token"},
            json={
                "worker_id": worker["id"],
                "claim_token": claim["job"]["claim_token"],
                "logs": "should not apply",
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Worker is not approved"
    finally:
        settings.worker_auth_token = original_token
