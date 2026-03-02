"""Week 2 unit tests for routing, dedupe, and budget controls."""

from __future__ import annotations

import asyncio

from src.graph.agent_comms import (
    is_duplicate_request,
    request_fingerprint,
    route_request_targets,
)
from src.graph.flow import agent_coordinator_node
from src.types.state import WorkingState


def test_router_selects_expected_targets() -> None:
    assert route_request_targets("clarification_request", "requirements_scope", {"area": "requirements"}) == ["pm_agent"]
    assert route_request_targets("clarification_request", "arch_constraints", {"area": "architecture"}) == [
        "architect_agent"
    ]
    assert route_request_targets(
        "dependency_approval_request",
        "unsafe_eval_lib",
        {"security_concern": True},
    ) == ["architect_agent", "reviewer_agent"]
    assert route_request_targets("feature_change_request", "add_admin_portal", {}) == ["pm_agent"]


def test_dedupe_blocks_repeated_requests() -> None:
    request = {
        "from_agent": "coder_agent",
        "to_agent": "pm_agent",
        "message_type": "clarification_request",
        "topic": "requirements_scope",
        "content_json": {"question": "Clarify auth scope"},
    }
    fingerprint = request_fingerprint(request)
    existing = [{**request, "dedupe_key": fingerprint}]
    assert is_duplicate_request(request, pending_requests=existing, resolved_requests=[]) is True
    assert is_duplicate_request({**request, "topic": "different"}, pending_requests=existing, resolved_requests=[]) is False


def test_budget_exhaustion_triggers_escalation_action() -> None:
    state = WorkingState(
        raw_idea="Test idea",
        job_id="job-budget",
        agent_comms_enabled=True,
        coordination_budget=0,
        agent_outbox=[
            {
                "from_agent": "coder_agent",
                "message_type": "clarification_request",
                "topic": "requirements_scope",
                "blocking": True,
                "content_json": {"area": "requirements", "force_unresolved": True},
            }
        ],
    )
    result = asyncio.run(agent_coordinator_node(state))
    assert result["coordination_action"] == "escalate"
    assert result["coordination_budget"] == 0
