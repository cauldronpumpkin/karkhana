"""Regression tests to ensure Week 1 changes do not break existing behavior."""

from __future__ import annotations

import asyncio
import importlib

from fastapi.testclient import TestClient

from src.dashboard.event_bus import EventBus


def _load_server_module():
    import src.dashboard.server as server

    return importlib.reload(server)


def test_existing_job_apis_continue_to_work() -> None:
    server = _load_server_module()
    client = TestClient(server.app)

    created = client.post("/api/command-center/jobs", json={"idea": "Build an invoicing app"})
    assert created.status_code == 200
    job = created.json()
    job_id = job["id"]

    jobs = client.get("/api/command-center/jobs")
    assert jobs.status_code == 200
    assert any(item["id"] == job_id for item in jobs.json())

    detail = client.get(f"/api/command-center/jobs/{job_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == job_id

    events = client.get(f"/api/command-center/jobs/{job_id}/events")
    logs = client.get(f"/api/command-center/jobs/{job_id}/logs")
    artifacts = client.get(f"/api/command-center/jobs/{job_id}/artifacts")
    assert events.status_code == 200
    assert logs.status_code == 200
    assert artifacts.status_code == 200


def test_existing_event_payload_shape_is_unchanged_for_legacy_events() -> None:
    bus = EventBus.get()

    asyncio.run(bus.emit("stage_start", {"job_id": "job123", "stage": "pm_agent"}))

    event = bus.history[-1].to_dict()
    assert set(event.keys()) == {"type", "job_id", "payload", "timestamp"}
    assert event["type"] == "stage_start"
    assert event["job_id"] == "job123"
    assert event["payload"]["stage"] == "pm_agent"
