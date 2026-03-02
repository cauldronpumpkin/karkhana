"""Week 2 integration/failure/regression tests for autonomous inter-agent communication."""

from __future__ import annotations

import asyncio
from typing import Any

from src.agents.architect_agent import ArchitectAgent
from src.agents.coder_agent import CoderAgent
from src.agents.pm_agent import PMAgent
from src.agents.pm_consensus import PMConsensusAgent
from src.agents.reviewer_agent import ReviewerAgent
from src.agents.taskmaster import Taskmaster
from src.command_center.repository import get_repository
from src.graph.flow import app
from src.sandbox.executor import SandboxExecutor
from src.types.state import WorkingState


def _decision_status(message: dict[str, Any]) -> str:
    content = message.get("content_json", {})
    if not isinstance(content, dict):
        return ""
    decision = content.get("decision", {})
    if not isinstance(decision, dict):
        return ""
    return str(decision.get("status", ""))


def _patch_base_pipeline(monkeypatch, *, file_name: str = "main.py") -> None:
    async def fake_generate_prd(self, idea: str) -> dict[str, Any]:
        _ = self
        return {
            "title": "Test Project",
            "problem_statement": idea,
            "core_features": [{"description": "Core flow"}],
            "technical_constraints": [],
        }

    async def fake_merge_prds(self, drafts: list[dict[str, Any]]) -> dict[str, Any]:
        _ = self
        return drafts[0]

    async def fake_architecture(self, prd: dict[str, Any]) -> dict[str, Any]:
        _ = self
        _ = prd
        return {"file_tree": {"src": [file_name]}, "frontend": {"framework": "nextjs"}}

    async def fake_review(self, file_path: str, code_content: str, project_context: dict[str, Any]) -> dict[str, Any]:
        _ = (self, file_path, code_content, project_context)
        return {"passed": True, "issues": []}

    async def fake_write(self, file_path: str, prd_context: dict, tech_stack: dict, requirements: list[str], existing_files: dict[str, str]) -> str:
        _ = (self, file_path, prd_context, tech_stack, requirements, existing_files)
        return "print('ok')"

    async def fake_execute(self, command: list[str], cwd) -> tuple[int, str, str]:
        _ = (self, command, cwd)
        return 0, "", ""

    monkeypatch.setattr(PMAgent, "generate_prd", fake_generate_prd)
    monkeypatch.setattr(PMConsensusAgent, "merge_prds", fake_merge_prds)
    monkeypatch.setattr(ArchitectAgent, "generate_architecture", fake_architecture)
    monkeypatch.setattr(ArchitectAgent, "generate_coordination_requests", lambda self, *, prd, architecture: [])
    monkeypatch.setattr(Taskmaster, "generate_coordination_requests", lambda self, *, all_files, pending_files, completed_files: [])
    monkeypatch.setattr(CoderAgent, "generate_coordination_requests", lambda self, **kwargs: [])
    monkeypatch.setattr(CoderAgent, "write_file", fake_write)
    monkeypatch.setattr(ReviewerAgent, "review_code", fake_review)
    monkeypatch.setattr(SandboxExecutor, "execute", fake_execute)


def _run_flow(*, job_id: str, agent_comms_enabled: bool, budget: int = 8) -> dict[str, Any]:
    state = WorkingState(
        raw_idea="Build test app",
        job_id=job_id,
        dashboard_mode=False,
        approval_required=False,
        agent_comms_enabled=agent_comms_enabled,
        coordination_budget=budget,
        agent_comms_escalate_blocking_only=True,
    )
    config = {"configurable": {"thread_id": f"thread-{job_id}"}}
    return asyncio.run(app.ainvoke(state.model_dump(), config))


def test_coder_clarification_to_pm_then_resume(monkeypatch) -> None:
    _patch_base_pipeline(monkeypatch)

    write_calls = {"count": 0}

    def coder_requests(self, *, file_path: str, requirements: list[str], prd_context: dict[str, Any], resolved_requests: list[dict[str, Any]] | None = None):
        _ = (self, file_path, requirements, prd_context)
        resolved_requests = resolved_requests or []
        if any(str(item.get("topic")) == "requirements_scope" for item in resolved_requests):
            return []
        return [
            {
                "from_agent": "coder_agent",
                "message_type": "clarification_request",
                "topic": "requirements_scope",
                "blocking": True,
                "content_json": {"area": "requirements", "question": "Clarify scope"},
            }
        ]

    async def write_once(self, file_path: str, prd_context: dict, tech_stack: dict, requirements: list[str], existing_files: dict[str, str]) -> str:
        _ = (self, file_path, prd_context, tech_stack, requirements, existing_files)
        write_calls["count"] += 1
        return "print('clarified')"

    monkeypatch.setattr(CoderAgent, "generate_coordination_requests", coder_requests)
    monkeypatch.setattr(CoderAgent, "write_file", write_once)

    result = _run_flow(job_id="job-clarify", agent_comms_enabled=True, budget=8)
    resolved = result.get("resolved_agent_requests", [])

    assert write_calls["count"] == 1
    assert any(
        msg.get("from_agent") == "coder_agent"
        and msg.get("to_agent") == "pm_agent"
        and msg.get("message_type") == "clarification_request"
        and _decision_status(msg) == "approved"
        for msg in resolved
    )


def test_coder_dependency_request_rejected_then_generates_without_dependency(monkeypatch) -> None:
    _patch_base_pipeline(monkeypatch)

    requirements_seen: list[list[str]] = []

    def coder_requests(self, *, file_path: str, requirements: list[str], prd_context: dict[str, Any], resolved_requests: list[dict[str, Any]] | None = None):
        _ = (self, file_path, requirements, prd_context)
        resolved_requests = resolved_requests or []
        if any(
            msg.get("message_type") == "dependency_approval_request" and _decision_status(msg) == "rejected"
            for msg in resolved_requests
        ):
            return []
        return [
            {
                "from_agent": "coder_agent",
                "message_type": "dependency_approval_request",
                "topic": "unsafe-eval-lib",
                "blocking": True,
                "content_json": {
                    "dependency_name": "unsafe-eval-lib",
                    "purpose": "Runtime expression support",
                    "security_concern": True,
                },
            }
        ]

    async def write_after_decision(self, file_path: str, prd_context: dict, tech_stack: dict, requirements: list[str], existing_files: dict[str, str]) -> str:
        _ = (self, file_path, prd_context, tech_stack, existing_files)
        requirements_seen.append(list(requirements))
        if any("Do not use dependency: unsafe-eval-lib" in req for req in requirements):
            return "print('safe path')"
        return "import unsafe_eval_lib\nprint('unsafe path')"

    monkeypatch.setattr(CoderAgent, "generate_coordination_requests", coder_requests)
    monkeypatch.setattr(CoderAgent, "write_file", write_after_decision)

    result = _run_flow(job_id="job-dependency", agent_comms_enabled=True, budget=8)
    resolved = result.get("resolved_agent_requests", [])

    assert any("Do not use dependency: unsafe-eval-lib" in req for batch in requirements_seen for req in batch)
    assert "unsafe_eval_lib" not in str(result.get("current_code", ""))
    assert any(
        msg.get("from_agent") == "coder_agent"
        and msg.get("message_type") == "dependency_approval_request"
        and _decision_status(msg) == "rejected"
        for msg in resolved
    )


def test_reviewer_mismatch_requests_pm_clarification_then_passes_on_retry(monkeypatch) -> None:
    _patch_base_pipeline(monkeypatch)

    coder_calls = {"count": 0}
    reviewer_calls = {"count": 0}

    async def coder_write(self, file_path: str, prd_context: dict, tech_stack: dict, requirements: list[str], existing_files: dict[str, str]) -> str:
        _ = (self, file_path, prd_context, tech_stack, requirements, existing_files)
        coder_calls["count"] += 1
        return f"print('iteration {coder_calls['count']}')"

    async def reviewer_review(self, file_path: str, code_content: str, project_context: dict[str, Any]) -> dict[str, Any]:
        _ = (self, file_path, code_content, project_context)
        reviewer_calls["count"] += 1
        if reviewer_calls["count"] == 1:
            return {
                "passed": False,
                "issues": [{"type": "requirement_mismatch", "description": "Requirement mismatch for scope"}],
            }
        return {"passed": True, "issues": []}

    monkeypatch.setattr(CoderAgent, "write_file", coder_write)
    monkeypatch.setattr(ReviewerAgent, "review_code", reviewer_review)

    result = _run_flow(job_id="job-review-retry", agent_comms_enabled=True, budget=8)
    resolved = result.get("resolved_agent_requests", [])

    assert coder_calls["count"] >= 2
    assert reviewer_calls["count"] >= 2
    assert any(
        msg.get("from_agent") == "reviewer_agent"
        and msg.get("to_agent") == "pm_agent"
        and msg.get("message_type") == "clarification_request"
        and _decision_status(msg) == "approved"
        for msg in resolved
    )


def test_blocking_unresolved_request_escalates(monkeypatch) -> None:
    _patch_base_pipeline(monkeypatch)

    monkeypatch.setattr(
        ArchitectAgent,
        "generate_coordination_requests",
        lambda self, *, prd, architecture: [
            {
                "from_agent": "architect_agent",
                "message_type": "clarification_request",
                "topic": "unresolved_blocking_case",
                "blocking": True,
                "content_json": {"area": "requirements", "force_unresolved": True},
            }
        ],
    )

    result = _run_flow(job_id="job-escalate", agent_comms_enabled=True, budget=1)
    resolved = result.get("resolved_agent_requests", [])

    assert any(str(msg.get("status")) == "escalated" for msg in resolved)
    assert result.get("agent_blocked_reason")


def test_non_blocking_unresolved_request_logs_and_proceeds(monkeypatch) -> None:
    _patch_base_pipeline(monkeypatch)

    monkeypatch.setattr(
        ArchitectAgent,
        "generate_coordination_requests",
        lambda self, *, prd, architecture: [
            {
                "from_agent": "architect_agent",
                "message_type": "clarification_request",
                "topic": "unresolved_non_blocking_case",
                "blocking": False,
                "content_json": {"area": "requirements", "force_unresolved": True},
            }
        ],
    )

    result = _run_flow(job_id="job-nonblocking", agent_comms_enabled=True, budget=2)
    resolved = result.get("resolved_agent_requests", [])

    assert any(_decision_status(msg) == "needs_more_info" for msg in resolved)
    assert not any(str(msg.get("status")) == "escalated" for msg in resolved)
    assert result.get("current_code")


def test_regression_with_agent_comms_disabled_uses_old_path(monkeypatch) -> None:
    _patch_base_pipeline(monkeypatch)

    # If this gets called while comms are disabled, routing is broken.
    def should_not_run(self, **kwargs):
        raise AssertionError("generate_coordination_requests should not run when AGENT_COMMS_ENABLED=false")

    monkeypatch.setattr(CoderAgent, "generate_coordination_requests", should_not_run)

    result = _run_flow(job_id="job-disabled", agent_comms_enabled=False, budget=8)
    repo = get_repository()

    assert result.get("coordination_rounds", 0) == 0
    assert result.get("resolved_agent_requests", []) == []
    assert repo.list_agent_messages("job-disabled") == []
