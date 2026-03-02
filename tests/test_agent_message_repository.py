"""Repository tests for Week 1 inter-agent message persistence."""

from __future__ import annotations

from src.command_center.repository import get_repository


def test_repository_create_list_and_resolve_agent_message() -> None:
    repo = get_repository()
    job = repo.create_job("Build a small booking MVP")

    created = repo.create_agent_message(
        job_id=job["id"],
        from_agent="coder_agent",
        to_agent="pm_agent",
        message_type="clarification_request",
        topic="timezone_handling",
        content={"question": "Should all timestamps be UTC?"},
        blocking=True,
    )

    assert created is not None
    assert created["job_id"] == job["id"]
    assert created["status"] == "pending"
    assert created["blocking"] is True

    all_messages = repo.list_agent_messages(job["id"])
    assert len(all_messages) == 1
    assert all_messages[0]["id"] == created["id"]

    pending_messages = repo.list_agent_messages(job["id"], status="pending")
    assert len(pending_messages) == 1

    resolved = repo.resolve_agent_message(
        job_id=job["id"],
        message_id=created["id"],
        decision={"status": "approved", "rationale": "Use UTC storage, localize in UI."},
    )
    assert resolved is not None
    assert resolved["status"] == "resolved"
    assert resolved["resolved_at"] is not None
    assert resolved["content_json"]["decision"]["status"] == "approved"

    pending_after = repo.list_agent_messages(job["id"], status="pending")
    assert pending_after == []


def test_repository_resolve_returns_none_for_wrong_job() -> None:
    repo = get_repository()
    job_a = repo.create_job("Job A")
    job_b = repo.create_job("Job B")

    created = repo.create_agent_message(
        job_id=job_a["id"],
        from_agent="reviewer_agent",
        to_agent="architect_agent",
        message_type="dependency_approval_request",
        topic="http_client_lib",
        content={"dependency": "httpx"},
    )
    assert created is not None

    wrong_job_resolution = repo.resolve_agent_message(
        job_id=job_b["id"],
        message_id=created["id"],
        decision={"status": "rejected", "rationale": "Wrong job"},
    )
    assert wrong_job_resolution is None
