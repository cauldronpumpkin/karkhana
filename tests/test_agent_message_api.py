"""API integration tests for Week 1 agent message endpoints."""

from __future__ import annotations

import importlib

from fastapi.testclient import TestClient

from src.dashboard.event_bus import EventBus


def _load_server_module():
    import src.dashboard.server as server

    return importlib.reload(server)


def test_agent_message_read_endpoints_and_pending_filter() -> None:
    server = _load_server_module()
    client = TestClient(server.app)

    job = client.post("/api/command-center/jobs", json={"idea": "Build a CRM"}).json()
    job_id = job["id"]

    created = server.command_center.repo.create_agent_message(
        job_id=job_id,
        from_agent="coder_agent",
        to_agent="pm_agent",
        message_type="clarification_request",
        topic="lead_scoring",
        content={"question": "Do we need weighted scoring?"},
        blocking=True,
    )
    assert created is not None

    all_resp = client.get(f"/api/command-center/jobs/{job_id}/agent-messages")
    assert all_resp.status_code == 200
    all_messages = all_resp.json()
    assert len(all_messages) == 1
    assert all_messages[0]["topic"] == "lead_scoring"

    pending_resp = client.get(f"/api/command-center/jobs/{job_id}/agent-messages/pending")
    assert pending_resp.status_code == 200
    pending = pending_resp.json()
    assert len(pending) == 1
    assert pending[0]["status"] == "pending"


def test_agent_message_resolve_endpoint_updates_status_and_emits_event() -> None:
    server = _load_server_module()
    client = TestClient(server.app)

    job = client.post("/api/command-center/jobs", json={"idea": "Build a todo app"}).json()
    job_id = job["id"]

    created = server.command_center.repo.create_agent_message(
        job_id=job_id,
        from_agent="reviewer_agent",
        to_agent="architect_agent",
        message_type="dependency_approval_request",
        topic="sqlite_migration_tool",
        content={"dependency": "alembic"},
        blocking=True,
    )
    assert created is not None

    resolve_resp = client.post(
        f"/api/command-center/jobs/{job_id}/agent-messages/{created['id']}/resolve",
        json={
            "decision": {
                "status": "approved",
                "rationale": "Allowed for schema change management",
                "metadata": {"manual": True},
            }
        },
    )
    assert resolve_resp.status_code == 200
    resolved_payload = resolve_resp.json()["message"]
    assert resolved_payload["status"] == "resolved"
    assert resolved_payload["content_json"]["decision"]["status"] == "approved"

    history_count = len(EventBus.get().history)
    event_types: list[str] = []
    resolved_event_payload = None

    with client.websocket_connect("/ws") as ws:
        for _ in range(history_count):
            event = ws.receive_json()
            event_types.append(event["type"])
            if event["type"] == "agent_message_resolved":
                resolved_event_payload = event["payload"]

    assert "agent_message_resolved" in event_types
    assert resolved_event_payload is not None
    assert resolved_event_payload["message_id"] == created["id"]
    assert resolved_event_payload["from_agent"] == "reviewer_agent"
    assert resolved_event_payload["to_agent"] == "architect_agent"
    assert resolved_event_payload["message_type"] == "dependency_approval_request"
    assert resolved_event_payload["blocking"] is True


def test_agent_message_endpoints_return_404_for_missing_job() -> None:
    server = _load_server_module()
    client = TestClient(server.app)

    missing_job = "missing-job-id"
    assert client.get(f"/api/command-center/jobs/{missing_job}/agent-messages").status_code == 404
    assert client.get(f"/api/command-center/jobs/{missing_job}/agent-messages/pending").status_code == 404
    assert (
        client.post(
            f"/api/command-center/jobs/{missing_job}/agent-messages/1/resolve",
            json={"decision": {"status": "approved", "rationale": "n/a"}},
        ).status_code
        == 404
    )
