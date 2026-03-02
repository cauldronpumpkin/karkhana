"""API tests for context settings/state endpoints."""

from __future__ import annotations

import importlib

from fastapi.testclient import TestClient


def _load_server_module():
    import src.dashboard.server as server

    return importlib.reload(server)


def test_context_settings_global_and_job_override_crud() -> None:
    server = _load_server_module()
    client = TestClient(server.app)

    global_payload = {
        "context_limit_tk": 64,
        "trigger_fill_percent": 88,
        "target_fill_percent": 35,
        "min_messages_to_compact": 5,
        "cooldown_calls": 1,
        "priority_weights": {
            "coding_context": 40,
            "user_intent": 30,
            "timeline_continuity": 20,
            "open_risks": 10,
        },
    }
    put_global = client.put("/api/command-center/settings/context", json=global_payload)
    assert put_global.status_code == 200
    assert put_global.json()["context_limit_tk"] == 64

    get_global = client.get("/api/command-center/settings/context")
    assert get_global.status_code == 200
    assert get_global.json()["trigger_fill_percent"] == 88

    job = client.post("/api/command-center/jobs", json={"idea": "Build context tools"}).json()
    job_id = job["id"]

    override_payload = {
        "job_id": job_id,
        "use_global_defaults": False,
        "override": {
            "context_limit_tk": 8,
            "trigger_fill_percent": 80,
            "target_fill_percent": 30,
            "min_messages_to_compact": 4,
            "cooldown_calls": 0,
            "priority_weights": {
                "coding_context": 50,
                "user_intent": 25,
                "timeline_continuity": 15,
                "open_risks": 10,
            },
        },
    }
    put_job = client.put(f"/api/command-center/jobs/{job_id}/context-settings", json=override_payload)
    assert put_job.status_code == 200
    assert put_job.json()["use_global_defaults"] is False
    assert put_job.json()["override"]["context_limit_tk"] == 8

    get_job = client.get(f"/api/command-center/jobs/{job_id}/context-settings")
    assert get_job.status_code == 200
    assert get_job.json()["override"]["trigger_fill_percent"] == 80

    state = client.get(f"/api/command-center/jobs/{job_id}/context-state")
    assert state.status_code == 200
    assert state.json()["job_id"] == job_id

    compactions = client.get(f"/api/command-center/jobs/{job_id}/context-compactions")
    assert compactions.status_code == 200
    assert isinstance(compactions.json(), list)


def test_context_settings_validation_rejects_invalid_thresholds() -> None:
    server = _load_server_module()
    client = TestClient(server.app)

    invalid_payload = {
        "context_limit_tk": 64,
        "trigger_fill_percent": 60,
        "target_fill_percent": 60,
        "min_messages_to_compact": 5,
        "cooldown_calls": 1,
        "priority_weights": {
            "coding_context": 40,
            "user_intent": 30,
            "timeline_continuity": 20,
            "open_risks": 10,
        },
    }
    resp = client.put("/api/command-center/settings/context", json=invalid_payload)
    assert resp.status_code == 422
