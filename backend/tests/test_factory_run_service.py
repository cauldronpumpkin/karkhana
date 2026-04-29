from __future__ import annotations

import pytest

from backend.app.repository import (
    CodeIndexArtifact,
    GitHubInstallation,
    Idea,
    InMemoryRepository,
    ProjectTwin,
    TemplateArtifact,
    TemplatePack,
    set_repository,
)
from backend.app.services.factory_run import FactoryRunService
from backend.app.services.policy_engine import PolicyBlockedError, RING_1_SCOPED_EXECUTION


async def _seed_project_and_template(repo: InMemoryRepository) -> ProjectTwin:
    idea = Idea(
        title="Factory Service Test",
        slug="factory-service-test",
        description="Project for factory run service testing",
        source_type="github_project",
    )
    await repo.create_idea(idea)

    await repo.save_github_installation(
        GitHubInstallation(installation_id="99", account_login="acme")
    )

    project = ProjectTwin(
        idea_id=idea.id,
        provider="github",
        installation_id="99",
        owner="acme",
        repo="my-app",
        repo_full_name="acme/my-app",
        repo_url="https://github.com/acme/my-app",
        clone_url="https://github.com/acme/my-app.git",
        default_branch="main",
        detected_stack=["python", "fastapi"],
        test_commands=["pytest backend/tests"],
    )
    await repo.save_project_twin(project)

    template = TemplatePack(
        template_id="fullstack-saas-v1",
        version="2.0.0",
        channel="stable",
        display_name="Fullstack SaaS",
        description="Full-stack SaaS app template",
        phases=[
            {"key": "scaffold", "label": "Project Scaffolding"},
            {"key": "backend", "label": "Backend API"},
        ],
        opencode_worker={
            "goal": "Build the fullstack SaaS application",
            "verification_commands": ["pytest backend/tests", "graphify update ."],
        },
    )
    await repo.save_template_pack(template)
    await repo.save_template_artifact(TemplateArtifact(
        template_id="fullstack-saas-v1",
        artifact_key="policies/code-standards.md",
        content_type="text/markdown",
        uri="s3://templates/fullstack-saas-v1/policies/code-standards.md",
        content="# Code Standards",
    ))

    index = CodeIndexArtifact(
        project_id=project.id,
        idea_id=idea.id,
        commit_sha="abc123",
        file_inventory=[{"path": "backend/app/main.py", "size": 1200, "kind": "source"}],
        test_commands=["pytest backend/tests"],
        architecture_summary="FastAPI backend with DynamoDB storage",
    )
    await repo.put_code_index(index)

    return project


def _valid_blueprint() -> dict:
    return {
        "blueprint_id": "bp-valid-001",
        "target_stack": ["python", "fastapi"],
        "files_or_modules": ["backend/app"],
        "dependencies": ["fastapi"],
        "build_steps": ["Implement scoped backend changes"],
        "verification_commands": ["pytest backend/tests", "graphify update ."],
        "required_capabilities": ["agent_branch_work", "test_verify"],
        "permission_profile": {
            "ring": RING_1_SCOPED_EXECUTION,
            "allowed_capabilities": ["agent_branch_work", "test_verify"],
            "tool_integrations": [],
            "notes": ["scoped execution"],
        },
        "graphify_requirements": {
            "pre_task": ["Read graphify-out/GRAPH_REPORT.md for god nodes and community structure"],
            "post_task": ["Run 'graphify update .' after all code changes to keep the knowledge graph current"],
        },
    }


def _warning_blueprint() -> dict:
    blueprint = _valid_blueprint()
    blueprint.update(
        {
            "blueprint_id": "bp-warn-001",
            "target_stack": [],
            "files_or_modules": ["."],
            "verification_commands": [],
            "graphify_requirements": {
                "pre_task": ["Read graphify-out/GRAPH_REPORT.md for god nodes and community structure"],
                "post_task": [],
            },
        }
    )
    return blueprint


def _blocked_blueprint() -> dict:
    blueprint = _valid_blueprint()
    blueprint.update(
        {
            "blueprint_id": "bp-block-001",
            "build_steps": ["Deploy to production", "rm -rf /"],
        }
    )
    return blueprint


@pytest.mark.asyncio
async def test_factory_run_service_valid_blueprint_includes_policy_payload() -> None:
    repo = InMemoryRepository()
    set_repository(repo)
    project = await _seed_project_and_template(repo)

    result = await FactoryRunService().create_factory_run(
        project_id=project.id,
        template_id="fullstack-saas-v1",
        config={"blueprint": _valid_blueprint()},
    )

    assert result["factory_run"]["config"]["project_blueprint"]["blueprint_id"] == "bp-valid-001"
    assert result["factory_run"]["config"]["policy_result"]["status"] == "pass"
    assert result["factory_run"]["config"]["template_manifest"]["id"] == "fullstack-saas-v1"
    assert "graphify update ." in result["factory_run"]["config"]["verification_commands"]
    assert "resolved_agents_hierarchy" in result["factory_run"]["config"]
    assert result["work_item"]["payload"]["project_blueprint"]["blueprint_id"] == "bp-valid-001"
    assert result["work_item"]["payload"]["permission_profile"]["ring"] == RING_1_SCOPED_EXECUTION
    assert result["work_item"]["payload"]["policy_result"]["status"] == "pass"
    assert result["work_item"]["payload"]["template_manifest"]["id"] == "fullstack-saas-v1"


@pytest.mark.asyncio
async def test_factory_run_service_warning_persists_planner_feedback() -> None:
    repo = InMemoryRepository()
    set_repository(repo)
    project = await _seed_project_and_template(repo)

    result = await FactoryRunService().create_factory_run(
        project_id=project.id,
        template_id="fullstack-saas-v1",
        config={"blueprint": _warning_blueprint()},
    )

    assert result["factory_run"]["config"]["policy_result"]["status"] == "warn"
    assert result["factory_run"]["config"]["planner_feedback"]
    assert result["factory_run"]["config"]["template_manifest"]["id"] == "fullstack-saas-v1"
    assert result["work_item"]["payload"]["policy_result"]["status"] == "warn"


@pytest.mark.asyncio
async def test_factory_run_service_blocked_blueprint_creates_no_run() -> None:
    repo = InMemoryRepository()
    set_repository(repo)
    project = await _seed_project_and_template(repo)

    with pytest.raises(PolicyBlockedError) as exc_info:
        await FactoryRunService().create_factory_run(
            project_id=project.id,
            template_id="fullstack-saas-v1",
            config={"blueprint": _blocked_blueprint()},
        )

    assert exc_info.value.policy_result.status == "block"
    assert len(await repo.list_factory_runs()) == 0
    assert len(await repo.list_work_items()) == 0
