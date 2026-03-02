"""Tests for reasoning event persistence and artifact creation."""

from __future__ import annotations

import time

from src.command_center.events import record_event
from src.command_center.repository import get_repository


def test_reasoning_events_create_artifacts() -> None:
    repo = get_repository()
    job = repo.create_job("Reasoning events")
    job_id = job["id"]
    now = time.time()

    record_event(
        "architect_candidate_generated",
        {
            "job_id": job_id,
            "stage": "architect_agent",
            "candidate_index": 1,
            "candidate_meta": {"rationale": "x"},
        },
        now,
    )
    record_event(
        "critic_debate_completed",
        {
            "job_id": job_id,
            "stage": "architect_agent",
            "winner_index": 0,
            "winner_score": 88,
            "report": {"debate": []},
        },
        now + 0.01,
    )
    record_event(
        "reasoning_thinking",
        {"job_id": job_id, "source": "coder", "thinking": "assumptions..."},
        now + 0.02,
    )
    record_event(
        "tdd_iteration_failed",
        {"job_id": job_id, "file": "src/main.py", "stderr": "assert failed"},
        now + 0.03,
    )
    artifacts = repo.list_artifacts(job_id)
    types = {a["artifact_type"] for a in artifacts}
    assert "architecture_candidate" in types
    assert "critic_report" in types
    assert "thinking_trace" in types
    assert "tdd_stderr" in types
