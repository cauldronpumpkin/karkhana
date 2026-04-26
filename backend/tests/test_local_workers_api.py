from __future__ import annotations

import json
from datetime import timedelta

import pytest
from httpx import AsyncClient

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
            },
        },
    )
    assert event.status_code == 200

    status = (await test_client.get(f"/api/ideas/{idea_id}/project")).json()
    assert status["project"]["last_indexed_commit"] == "def456"
    assert status["jobs"][0]["status"] == "completed"


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
    assert result == {"processed": 1}
    job = await get_repository().get_work_item(claim["job"]["id"])
    assert job.status == "failed_retryable"
