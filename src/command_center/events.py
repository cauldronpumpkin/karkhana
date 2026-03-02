"""Event persistence and projection helpers for Command Center."""

from __future__ import annotations

import json
from typing import Any

from src.command_center.models import JobStatus
from src.command_center.repository import get_repository


STAGE_ORDER = [
    "pm_agent",
    "pm_consensus",
    "architect_agent",
    "taskmaster",
    "coder_agent",
    "reviewer_agent",
    "sandbox_executor",
]


def _progress_for_stage(stage: str | None) -> float:
    if not stage:
        return 0.0
    try:
        idx = STAGE_ORDER.index(stage)
    except ValueError:
        return 0.0
    return round((idx / max(len(STAGE_ORDER), 1)) * 100, 1)


def _log_level_for_event(event_type: str) -> str:
    if event_type == "job_log":
        return "info"
    if event_type in {"error", "job_failed"}:
        return "error"
    if event_type in {"waiting_for_approval"}:
        return "warn"
    if event_type == "agent_message_escalated":
        return "warn"
    if event_type in {"tdd_iteration_failed", "tdd_budget_exhausted"}:
        return "warn"
    if event_type == "context_compaction_failed":
        return "error"
    return "info"


def _message_for_event(event_type: str, payload: dict[str, Any]) -> str:
    stage = payload.get("stage")
    if event_type == "job_log":
        return payload.get("message", "")
    if event_type == "stage_start":
        return f"Stage started: {stage}"
    if event_type == "stage_complete":
        return f"Stage completed: {stage}"
    if event_type == "code_generated":
        return f"Generated code for {payload.get('file_path', payload.get('file', 'unknown file'))}"
    if event_type == "tdd_test_generated":
        return f"Generated tests for {payload.get('file', 'unknown file')}"
    if event_type == "review_result":
        return "Review passed" if payload.get("passed") else "Review failed"
    if event_type == "sandbox_result":
        return "Sandbox passed" if payload.get("passed") else "Sandbox failed"
    if event_type == "waiting_for_approval":
        return f"Waiting for approval at {stage}"
    if event_type == "stage_approved":
        return f"Approval resolved for {stage}"
    if event_type == "error":
        return payload.get("message", "Pipeline error")
    if event_type == "job_started":
        return "Job started"
    if event_type == "job_completed":
        return "Job completed"
    if event_type == "job_stopped":
        return "Job stopped"
    if event_type == "job_failed":
        return payload.get("message", "Job failed")
    if event_type == "agent_message_created":
        return f"Agent message created: {payload.get('message_type', 'unknown')} ({payload.get('topic', 'no topic')})"
    if event_type == "agent_message_resolved":
        return f"Agent message resolved: {payload.get('message_id', 'unknown')}"
    if event_type == "agent_message_escalated":
        return f"Agent message escalated: {payload.get('message_id', 'unknown')}"
    if event_type == "reasoning_config_applied":
        return "Reasoning configuration applied"
    if event_type == "architect_candidate_generated":
        return f"Architect candidate generated: {payload.get('candidate_index')}"
    if event_type == "critic_debate_completed":
        return f"Critic selected candidate {payload.get('winner_index')} with score {payload.get('winner_score')}"
    if event_type == "tdd_iteration_started":
        return f"TDD iteration started ({payload.get('iteration')})"
    if event_type == "tdd_iteration_failed":
        return f"TDD iteration failed ({payload.get('iteration')})"
    if event_type == "tdd_iteration_passed":
        return f"TDD iteration passed ({payload.get('iteration')})"
    if event_type == "tdd_budget_exhausted":
        return "TDD budget exhausted"
    if event_type == "reasoning_thinking":
        return f"Thinking trace captured from {payload.get('source', 'unknown')}"
    if event_type == "build_started":
        return "Build started"
    if event_type == "build_complete":
        return "Build complete"
    if event_type == "context_usage_updated":
        return (
            "Context usage updated: "
            f"{payload.get('fill_percent', 0)}% ({payload.get('estimated_tokens', 0)}/{payload.get('limit_tokens', 0)} tokens)"
        )
    if event_type == "context_compaction_started":
        return "Context compaction started"
    if event_type == "context_compaction_completed":
        return "Context compaction completed"
    if event_type == "context_compaction_failed":
        return payload.get("message", "Context compaction failed")
    return event_type


def _maybe_store_artifact(job_id: str, event_type: str, payload: dict[str, Any], created_at: float) -> None:
    repo = get_repository()
    stage = payload.get("stage")
    if event_type == "stage_output" and stage in {"pm_agent", "pm_consensus"}:
        repo.add_artifact(job_id, "prd", json.dumps(payload.get("output", {}), indent=2), stage, created_at)
    elif event_type == "stage_output" and stage == "architect_agent":
        repo.add_artifact(job_id, "architecture", json.dumps(payload.get("output", {}), indent=2), stage, created_at)
    elif event_type == "code_generated":
        key = payload.get("file_path") or payload.get("file")
        repo.add_artifact(job_id, "generated_code", payload.get("code", ""), key, created_at)
    elif event_type == "context_compaction_completed":
        summary = str(payload.get("summary_text", ""))
        repo.add_artifact(job_id, "context_compaction_summary", summary, "context", created_at)
    elif event_type == "architect_candidate_generated":
        repo.add_artifact(
            job_id,
            "architecture_candidate",
            json.dumps(payload.get("candidate_meta", {}), indent=2),
            str(payload.get("candidate_index")),
            created_at,
        )
    elif event_type == "critic_debate_completed":
        report_payload = payload.get("report", payload)
        repo.add_artifact(job_id, "critic_report", json.dumps(report_payload, indent=2), "architect_agent", created_at)
    elif event_type in {"tdd_iteration_failed", "tdd_budget_exhausted"}:
        repo.add_artifact(
            job_id,
            "tdd_stderr",
            str(payload.get("stderr", payload.get("message", "")))[:4000],
            str(payload.get("file", "")),
            created_at,
        )
    elif event_type == "tdd_test_generated":
        repo.add_artifact(
            job_id,
            "tdd_test_code",
            str(payload.get("code", "")),
            str(payload.get("test_file_path", payload.get("file", ""))),
            created_at,
        )
    elif event_type == "reasoning_thinking":
        repo.add_artifact(
            job_id,
            "thinking_trace",
            str(payload.get("thinking", ""))[:12000],
            str(payload.get("source", "")),
            created_at,
        )


def record_event(event_type: str, payload: dict[str, Any], created_at: float) -> None:
    """Persist a job-scoped event and update projections."""
    job_id = payload.get("job_id")
    if not job_id:
        return

    repo = get_repository()
    stage = payload.get("stage")
    repo.add_event(job_id, event_type, stage, payload, created_at)

    repo.add_log(
        job_id=job_id,
        level=payload.get("level", _log_level_for_event(event_type)),
        source=payload.get("source", stage or event_type),
        message=_message_for_event(event_type, payload),
        meta=payload,
        created_at=created_at,
    )

    if event_type == "job_created":
        repo.update_job_status(job_id, JobStatus.QUEUED.value)
    elif event_type == "job_started":
        repo.update_job_status(job_id, JobStatus.RUNNING.value, current_stage="start", progress_percent=1.0)
    elif event_type == "job_status_changed":
        status = payload.get("status")
        if isinstance(status, str):
            repo.update_job_status(job_id, status)
    elif event_type == "job_progress":
        repo.update_job_stage(
            job_id,
            payload.get("stage", "") or "",
            float(payload.get("progress_percent", 0.0)),
        )
    elif event_type == "stage_start":
        repo.update_job_stage(job_id, stage or "", _progress_for_stage(stage))
    elif event_type == "waiting_for_approval":
        repo.update_job_status(
            job_id,
            JobStatus.WAITING_APPROVAL.value,
            current_stage=stage,
            progress_percent=_progress_for_stage(stage),
        )
        repo.create_decision(
            job_id=job_id,
            stage=stage or "unknown",
            decision_type="approval",
            required=True,
            prompt={"data": payload.get("data", {})},
            status="pending",
        )
    elif event_type == "stage_approved":
        repo.resolve_decision(
            job_id=job_id,
            stage=stage or "unknown",
            response={"edited_data": payload.get("edited_data")},
            status="approved",
        )
        repo.update_job_status(job_id, JobStatus.RUNNING.value, current_stage=stage)
    elif event_type in {"job_completed", "build_complete"}:
        repo.update_job_status(job_id, JobStatus.COMPLETED.value, current_stage="complete", progress_percent=100.0)
    elif event_type == "job_stopped":
        repo.update_job_status(job_id, JobStatus.STOPPED.value, current_stage="stopped")
    elif event_type in {"job_failed"}:
        repo.update_job_status(
            job_id,
            JobStatus.FAILED.value,
            error_message=payload.get("message"),
            current_stage=payload.get("stage", "failed"),
        )

    _maybe_store_artifact(job_id, event_type, payload, created_at)
