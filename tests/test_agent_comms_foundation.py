"""Week 1 foundation tests for inter-agent communication models and schema."""

from __future__ import annotations

from pydantic import ValidationError

from src.command_center.db import get_connection, init_db
from src.command_center.models import (
    AgentDecision,
    AgentDecisionStatus,
    AgentMessage,
    AgentMessageStatus,
    AgentMessageType,
    ClarificationRequest,
    DependencyApprovalRequest,
    FeatureChangeRequest,
)


def test_agent_protocol_dtos_validate() -> None:
    clarification = ClarificationRequest(
        question="Do we need OAuth login in MVP?",
        context={"source_stage": "coder_agent"},
        assumptions=["Email/password exists"],
    )
    assert clarification.question.startswith("Do we")

    dependency = DependencyApprovalRequest(
        dependency_name="fastapi-users",
        dependency_version="13.0.0",
        purpose="Authentication scaffolding",
    )
    assert dependency.dependency_name == "fastapi-users"

    feature = FeatureChangeRequest(
        requested_change="Add role-based admin dashboard",
        reason="Support moderation workflows",
        impact_assessment={"timeline_days": 3},
    )
    assert feature.impact_assessment["timeline_days"] == 3

    decision = AgentDecision(
        status=AgentDecisionStatus.APPROVED,
        rationale="Within scope and architecture constraints.",
    )
    assert decision.status == AgentDecisionStatus.APPROVED

    message = AgentMessage(
        id=1,
        job_id="job123",
        from_agent="coder_agent",
        to_agent="pm_agent",
        message_type=AgentMessageType.CLARIFICATION_REQUEST,
        topic="auth_scope",
        content_json={"question": clarification.question},
        status=AgentMessageStatus.PENDING,
        blocking=True,
        created_at=1.0,
    )
    assert message.message_type == AgentMessageType.CLARIFICATION_REQUEST
    assert message.blocking is True


def test_agent_protocol_dtos_reject_invalid_payloads() -> None:
    try:
        ClarificationRequest(question="")
        raise AssertionError("Expected ValidationError")
    except ValidationError:
        pass

    try:
        DependencyApprovalRequest(dependency_name="", purpose="")
        raise AssertionError("Expected ValidationError")
    except ValidationError:
        pass


def test_agent_message_migration_is_idempotent() -> None:
    init_db()
    init_db()

    with get_connection() as conn:
        table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_messages'"
        ).fetchone()
        assert table is not None

        columns = conn.execute("PRAGMA table_info(agent_messages)").fetchall()
        column_names = {row["name"] for row in columns}
        assert {
            "id",
            "job_id",
            "from_agent",
            "to_agent",
            "message_type",
            "topic",
            "content_json",
            "status",
            "blocking",
            "created_at",
            "resolved_at",
        }.issubset(column_names)

        indexes = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='agent_messages'"
        ).fetchall()
        index_names = {row["name"] for row in indexes}
        assert "idx_agent_messages_job_created" in index_names
        assert "idx_agent_messages_job_status" in index_names
