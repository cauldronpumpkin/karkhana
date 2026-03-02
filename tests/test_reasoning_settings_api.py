"""API tests for reasoning settings and precedence."""

from __future__ import annotations

import importlib

from fastapi.testclient import TestClient

from src.command_center.models import JobReasoningLaunchOptions, ReasoningConfig
from src.command_center.service import CommandCenterService


def _load_server_module():
    import src.dashboard.server as server

    return importlib.reload(server)


def test_reasoning_settings_global_and_job_override_crud() -> None:
    server = _load_server_module()
    client = TestClient(server.app)

    global_payload = {
        "enabled": True,
        "profile": "balanced",
        "architect_tot_paths": 3,
        "architect_tot_parallel": True,
        "critic_enabled": True,
        "thinking_modules_enabled": True,
        "thinking_visibility": "logs",
        "tdd_enabled": True,
        "tdd_time_split_percent": 40,
        "tdd_max_iterations": 5,
        "tdd_fail_open": True,
    }
    put_global = client.put("/api/command-center/settings/reasoning", json=global_payload)
    assert put_global.status_code == 200
    assert put_global.json()["enabled"] is True

    get_global = client.get("/api/command-center/settings/reasoning")
    assert get_global.status_code == 200
    assert get_global.json()["profile"] == "balanced"

    job = client.post("/api/command-center/jobs", json={"idea": "Build with reasoning"}).json()
    job_id = job["id"]
    override_payload = {
        "job_id": job_id,
        "use_global_defaults": False,
        "override": {
            "enabled": True,
            "profile": "deep",
            "architect_tot_paths": 5,
            "architect_tot_parallel": True,
            "critic_enabled": True,
            "thinking_modules_enabled": True,
            "thinking_visibility": "logs",
            "tdd_enabled": True,
            "tdd_time_split_percent": 70,
            "tdd_max_iterations": 9,
            "tdd_fail_open": False,
        },
        "launch_override": None,
    }
    put_job = client.put(f"/api/command-center/jobs/{job_id}/reasoning-settings", json=override_payload)
    assert put_job.status_code == 200
    assert put_job.json()["use_global_defaults"] is False
    assert put_job.json()["override"]["profile"] == "deep"

    get_job = client.get(f"/api/command-center/jobs/{job_id}/reasoning-settings")
    assert get_job.status_code == 200
    assert get_job.json()["override"]["tdd_max_iterations"] == 9


def test_reasoning_precedence_launch_overrides_job_and_global() -> None:
    service = CommandCenterService.get()
    global_cfg = ReasoningConfig(
        enabled=True,
        profile="balanced",
        architect_tot_paths=3,
        architect_tot_parallel=True,
        critic_enabled=True,
        thinking_modules_enabled=True,
        thinking_visibility="logs",
        tdd_enabled=True,
        tdd_time_split_percent=40,
        tdd_max_iterations=5,
        tdd_fail_open=True,
    )
    service.set_reasoning_defaults(global_cfg)
    job = service.repo.create_job("Reasoning precedence")
    service.set_job_reasoning_config(
        job["id"],
        use_global_defaults=False,
        override=ReasoningConfig(
            enabled=True,
            profile="deep",
            architect_tot_paths=5,
            architect_tot_parallel=True,
            critic_enabled=True,
            thinking_modules_enabled=True,
            thinking_visibility="logs",
            tdd_enabled=True,
            tdd_time_split_percent=70,
            tdd_max_iterations=8,
            tdd_fail_open=False,
        ),
    )

    resolved = service.resolve_job_reasoning(
        job["id"],
        launch_override=JobReasoningLaunchOptions(
            profile="fast",
            enabled=True,
            critic_enabled=False,
            tdd_time_split_percent=15,
        ),
    )
    assert resolved.profile == "fast"
    assert resolved.critic_enabled is False
    assert resolved.tdd_time_split_percent == 15
