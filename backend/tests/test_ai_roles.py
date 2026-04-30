from __future__ import annotations

import pytest

from backend.app.services.ai_roles import FactoryRole, ROLE_DEFINITIONS, RolePromptBuilder
from backend.app.services.llm import LLMService


def _planner_context() -> dict:
    return {
        "project": {"repo_full_name": "acme/app", "default_branch": "main"},
        "template": {"template_id": "fullstack-saas-v1", "version": "1.0.0"},
        "factory_run_id": "run_123",
        "run_config": {"template_id": "fullstack-saas-v1", "template_version": "1.0.0"},
        "code_context": {"template_docs": [{"key": "docs/setup.md"}]},
        "research_context": {"notes": ["prior run completed"]},
    }


def _worker_context() -> dict:
    return {
        "project": {"repo_full_name": "acme/app", "default_branch": "main"},
        "template": {"template_id": "fullstack-saas-v1", "version": "1.0.0"},
        "factory_run_id": "run_123",
        "phase": {"phase_key": "backend", "phase_order": 2},
        "batch": {"batch_key": "backend-batch-1"},
        "branch_name": "factory/run_123/backend",
        "phase_key": "backend",
        "project_repo_full_name": "acme/app",
        "context_files": [{"path": "backend/app/main.py", "role": "source"}],
        "constraints": [{"id": "no-secrets", "description": "Never commit secrets"}],
        "quality_gates": [{"phase": "backend", "command": "pytest backend/tests"}],
        "deliverables": ["Working backend phase"],
        "verification_commands": ["pytest backend/tests", "graphify update ."],
        "graphify_instructions": {
            "pre_task": ["Read graphify-out/GRAPH_REPORT.md"],
            "post_task": ["Run 'graphify update .' after all code changes"],
        },
        "ledger_context": {
            "ledger_path": "karkhana-runs/run_123.md",
            "sections": {"Current goal": "Implement the backend phase"},
        },
        "goal": "Implement the backend phase",
    }


def _bug_fixer_context() -> dict:
    return {
        "project": {"repo_full_name": "acme/app", "default_branch": "main"},
        "factory_run_id": "run_123",
        "batch": {"batch_key": "backend-batch-1"},
        "batch_key": "backend-batch-1",
        "failure_classification": "test",
        "command_output": "FAILED test_login - AssertionError",
        "recent_diff": "diff --git a/app.py b/app.py",
        "changed_files": ["app.py"],
        "acceptance_criteria": ["`pytest backend/tests` exits with code 0"],
        "attempt_number": 1,
        "graphify_instructions": {
            "pre_task": ["Read graphify-out/GRAPH_REPORT.md"],
            "post_task": ["Run 'graphify update .' after all code changes"],
        },
    }


def test_every_required_role_has_definition():
    for role in FactoryRole:
        definition = ROLE_DEFINITIONS[role]
        assert definition.name
        assert definition.purpose
        assert definition.prompt_template.strip()
        assert definition.required_inputs
        assert definition.output_schema["type"] == "object"


def test_planner_prompt_generation_and_validation():
    contract = RolePromptBuilder.build(FactoryRole.PLANNER, _planner_context())
    assert contract["role"] == "planner"
    assert contract["messages"][0]["role"] == "system"
    assert "Role: Planner" in contract["prompt"]
    assert "Do not write implementation code" in contract["prompt"]
    assert contract["prompt_template"].startswith("Role: Planner")
    assert contract["output_schema"]["type"] == "object"

    with pytest.raises(ValueError, match="Missing required inputs"):
        RolePromptBuilder.build(
            FactoryRole.PLANNER,
            {
                "project": {},
                "template": {},
                "factory_run_id": "run_123",
                "run_config": {},
                "code_context": {},
            },
        )


def test_worker_prompt_generation_and_validation():
    contract = RolePromptBuilder.build(FactoryRole.WORKER, _worker_context())
    assert contract["role"] == "worker"
    assert "Role: Worker" in contract["prompt"]
    assert "Read graphify-out/GRAPH_REPORT.md" in contract["prompt"]
    assert "Run graphify update . after code changes" in contract["prompt"]
    assert "Factory Run Ledger" in contract["prompt"]
    assert "karkhana-runs/run_123.md" in contract["prompt"]
    assert contract["prompt_template"].startswith("Role: Worker")
    assert contract["messages"][1]["content"] == contract["prompt"]
    assert contract["output_schema"]["properties"]["branch_name"]["type"] == "string"
    assert contract["output_schema"]["properties"]["ledger_updated"]["type"] == "boolean"
    assert contract["output_schema"]["properties"]["ledger_sections_updated"]["type"] == "array"

    with pytest.raises(ValueError, match="Missing required inputs"):
        RolePromptBuilder.build(
            FactoryRole.WORKER,
            {
                "project": {},
                "template": {},
                "factory_run_id": "run_123",
                "phase": {},
                "batch": {},
                "branch_name": "factory/run_123/backend",
                "phase_key": "backend",
                "project_repo_full_name": "acme/app",
                "context_files": [],
                "constraints": [],
                "quality_gates": [],
                "deliverables": [],
                "verification_commands": [],
                "ledger_context": {},
                "goal": "Implement backend",
            },
        )


def test_bug_fixer_prompt_generation_and_validation():
    contract = RolePromptBuilder.build(FactoryRole.BUG_FIXER, _bug_fixer_context())
    assert contract["role"] == "bug_fixer"
    assert "Role: Bug Fixer" in contract["prompt"]
    assert "Make the smallest safe fix" in contract["prompt"]
    assert "graphify update ." in contract["prompt"]
    assert contract["prompt_template"].startswith("Role: Bug Fixer")
    assert contract["output_schema"]["properties"]["repair_attempted"]["type"] == "boolean"

    with pytest.raises(ValueError, match="Missing required inputs"):
        RolePromptBuilder.build(
            FactoryRole.BUG_FIXER,
            {
                "project": {},
                "factory_run_id": "run_123",
                "batch": {},
                "batch_key": "backend-batch-1",
                "failure_classification": "test",
                "command_output": "FAILED",
                "recent_diff": "",
                "changed_files": [],
                "acceptance_criteria": [],
                "attempt_number": 1,
            },
        )


def test_role_contracts_use_default_provider_and_model():
    defaults = LLMService().get_provider()
    contract = RolePromptBuilder.build(FactoryRole.PLANNER, _planner_context())
    assert contract["provider"] == defaults["provider"]
    assert contract["model"] == defaults["model"]
