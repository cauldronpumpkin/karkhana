from __future__ import annotations

import pytest

from backend.app.repository import ProjectTwin, TemplatePack, utcnow
from backend.app.services.policy_engine import (
    OPENCODE_SERVER_REQUIRED_CAPABILITIES,
    PERMISSION_RINGS,
    ProjectBlueprint,
    PythonPolicyEngine,
    RING_0_READONLY,
    RING_1_SCOPED_EXECUTION,
    RING_2_TOOL_INTEGRATION,
    RING_3_HIGH_RISK_APPROVAL,
    WorkerPermissionProfile,
    blueprint_permission_profile_to_worker_policy,
    validate_engine_for_autonomy_level,
    validate_worker_capabilities_for_autonomy,
)


def _project() -> ProjectTwin:
    return ProjectTwin(
        idea_id="idea-001",
        provider="github",
        installation_id="99",
        owner="acme",
        repo="demo",
        repo_full_name="acme/demo",
        repo_url="https://github.com/acme/demo",
        clone_url="https://github.com/acme/demo.git",
        default_branch="main",
        id="project-001",
    )


def _template() -> TemplatePack:
    return TemplatePack(
        template_id="tpl-001",
        version="1.2.3",
        channel="stable",
        display_name="Demo",
        description="Demo template",
        phases=[{"key": "build", "label": "Build"}],
        opencode_worker={"goal": "Build the demo"},
    )


def _blueprint(permission_profile: WorkerPermissionProfile, **overrides) -> ProjectBlueprint:
    base = {
        "blueprint_id": "bp-001",
        "project_id": "project-001",
        "template_id": "tpl-001",
        "template_version": "1.2.3",
        "target_stack": ["python"],
        "files_or_modules": ["backend/app"],
        "dependencies": ["fastapi"],
        "build_steps": ["Implement scoped backend changes"],
        "verification_commands": ["pytest backend/tests", "graphify update ."],
        "required_capabilities": ["agent_branch_work", "test_verify"],
        "permission_profile": permission_profile,
        "graphify_requirements": {
            "pre_task": ["Read graphify-out/GRAPH_REPORT.md for god nodes and community structure"],
            "post_task": ["Run 'graphify update .' after all code changes to keep the knowledge graph current"],
        },
        "created_at": utcnow(),
    }
    base.update(overrides)
    return ProjectBlueprint(**base)


def test_valid_blueprint_passes() -> None:
    engine = PythonPolicyEngine()
    profile = WorkerPermissionProfile(
        ring=RING_1_SCOPED_EXECUTION,
        allowed_capabilities=["agent_branch_work", "test_verify"],
    )
    result = engine.validate_blueprint(_blueprint(profile), project=_project(), template=_template())

    assert result.status == "pass"
    assert result.executable is True
    assert result.issues == []
    assert result.feedback == []


def test_high_risk_blueprint_blocks_without_ring_3() -> None:
    engine = PythonPolicyEngine()
    profile = WorkerPermissionProfile(
        ring=RING_1_SCOPED_EXECUTION,
        allowed_capabilities=["agent_branch_work", "test_verify"],
    )
    blueprint = _blueprint(
        profile,
        build_steps=["Deploy to production"],
        verification_commands=["pytest backend/tests"],
    )

    result = engine.validate_blueprint(blueprint, project=_project(), template=_template())

    assert result.status == "block"
    assert result.executable is False
    assert any(issue.code == "high_risk_action" for issue in result.issues)
    assert any("ring_3_high_risk_approval" in item for item in result.feedback)


def test_warning_blueprint_still_executes() -> None:
    engine = PythonPolicyEngine()
    profile = WorkerPermissionProfile(
        ring=RING_1_SCOPED_EXECUTION,
        allowed_capabilities=["agent_branch_work", "test_verify"],
    )
    blueprint = _blueprint(
        profile,
        target_stack=[],
        files_or_modules=["."],
        verification_commands=[],
        graphify_requirements={"pre_task": ["Read graphify-out/GRAPH_REPORT.md for god nodes and community structure"], "post_task": []},
    )

    result = engine.validate_blueprint(blueprint, project=_project(), template=_template())

    assert result.status == "warn"
    assert result.executable is True
    assert any(issue.code == "missing_verification_commands" for issue in result.issues)
    assert any(issue.code == "missing_graphify_post_update" for issue in result.issues)
    assert any(issue.code == "missing_target_stack" for issue in result.issues)
    assert any(issue.code == "broad_file_scope" for issue in result.issues)


@pytest.mark.parametrize("ring", PERMISSION_RINGS)
def test_permission_profile_round_trip(ring: str) -> None:
    profile = WorkerPermissionProfile(
        ring=ring,
        allowed_capabilities=["agent_branch_work"],
        tool_integrations=["github_api"],
        notes=["demo"],
    )

    clone = WorkerPermissionProfile.from_dict(profile.to_dict())

    assert clone.ring == ring
    assert clone.allowed_capabilities == ["agent_branch_work"]
    assert clone.tool_integrations == ["github_api"]
    assert clone.notes == ["demo"]


# ── Permission profile → worker policy mapping tests ──

def test_blueprint_permission_ring_0_returns_readonly_policy() -> None:
    profile = WorkerPermissionProfile(ring=RING_0_READONLY)
    policy = blueprint_permission_profile_to_worker_policy(profile)
    assert policy["allow_file_edits"] is False
    assert policy["allow_shell_commands"] == []
    assert "Read-only inspection" in policy["notes"][0]


def test_blueprint_permission_ring_1_returns_scoped_policy() -> None:
    profile = WorkerPermissionProfile(ring=RING_1_SCOPED_EXECUTION)
    policy = blueprint_permission_profile_to_worker_policy(profile)
    assert policy["allow_file_edits"] is True
    assert "graphify" in policy["allow_shell_commands"]
    assert "curl" in " ".join(policy["deny_patterns"])
    assert "Scoped execution" in policy["notes"][0]


def test_blueprint_permission_ring_2_returns_tool_integration_policy() -> None:
    profile = WorkerPermissionProfile(ring=RING_2_TOOL_INTEGRATION)
    policy = blueprint_permission_profile_to_worker_policy(profile)
    assert policy["allow_file_edits"] is True
    assert "aws" in policy["allow_shell_commands"]
    assert "docker" in policy["allow_shell_commands"]
    assert "Tool integration" in policy["notes"][0]


def test_blueprint_permission_ring_3_returns_high_risk_policy() -> None:
    profile = WorkerPermissionProfile(ring=RING_3_HIGH_RISK_APPROVAL)
    policy = blueprint_permission_profile_to_worker_policy(profile)
    assert policy["allow_file_edits"] is True
    assert policy["allow_shell_commands"] == ["*"]
    assert "High-risk approval" in policy["notes"][0]


# ── Engine validation tests ──

def test_validate_engine_opencode_server_passes() -> None:
    validate_engine_for_autonomy_level("opencode-server", "autonomous_development")
    validate_engine_for_autonomy_level("opencode-server", "full_autopilot")


def test_validate_engine_limited_fails_for_high_autonomy() -> None:
    for engine in ("opencode", "openclaude", "codex"):
        for level in ("autonomous_development", "full_autopilot"):
            with pytest.raises(ValueError, match="limited fallback"):
                validate_engine_for_autonomy_level(engine, level)


def test_validate_engine_limited_passes_for_suggest_only() -> None:
    for engine in ("opencode", "openclaude", "codex"):
        validate_engine_for_autonomy_level(engine, "suggest_only")


# ── Worker capability validation tests ──

def test_worker_with_full_capabilities_passes_validation() -> None:
    caps = list(OPENCODE_SERVER_REQUIRED_CAPABILITIES)
    missing = validate_worker_capabilities_for_autonomy(caps, "autonomous_development")
    assert missing == []


def test_worker_missing_capabilities_returns_missing() -> None:
    caps = ["repo_index", "agent_branch_work"]
    missing = validate_worker_capabilities_for_autonomy(caps, "autonomous_development")
    assert len(missing) > 0
    assert "permission_guard" in missing
    assert "circuit_breaker" in missing


def test_worker_missing_capabilities_suggest_only_returns_empty() -> None:
    caps = ["repo_index"]
    missing = validate_worker_capabilities_for_autonomy(caps, "suggest_only")
    assert missing == []


def test_open_code_server_required_capabilities_are_defined() -> None:
    expected = {
        "permission_guard",
        "circuit_breaker",
        "litellm_proxy",
        "diff_api",
        "verification_runner",
        "graphify_update",
    }
    assert OPENCODE_SERVER_REQUIRED_CAPABILITIES == expected
