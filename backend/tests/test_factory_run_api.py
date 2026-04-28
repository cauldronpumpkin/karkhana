from __future__ import annotations

import pytest
from httpx import AsyncClient

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
from backend.app.services.policy_engine import RING_1_SCOPED_EXECUTION


async def _seed_project_and_template(repo: InMemoryRepository) -> dict:
    idea = Idea(
        title="Factory Test",
        slug="factory-test",
        description="Project for factory run testing",
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
            {"key": "scaffold", "label": "Project Scaffolding", "config": {"timeout": 300}},
            {"key": "backend", "label": "Backend API"},
            {"key": "frontend", "label": "Frontend UI"},
            {"key": "integration", "label": "Integration Tests"},
        ],
        quality_gates=[
            {"phase": "scaffold", "type": "lint", "command": "ruff check ."},
        ],
        constraints=[
            {"id": "no-secrets", "description": "Never commit secrets or API keys"},
            {"id": "test-coverage", "description": "All new code must have tests"},
        ],
        opencode_worker={
            "goal": "Build the fullstack SaaS application",
            "deliverables": [
                "Working implementation matching phase goal",
                "Passing test suite",
                "Updated graphify knowledge graph",
            ],
            "verification_commands": ["pytest backend/tests", "graphify update ."],
        },
    )
    await repo.save_template_pack(template)

    await repo.save_template_artifact(TemplateArtifact(
        template_id="fullstack-saas-v1",
        artifact_key="policies/code-standards.md",
        content_type="text/markdown",
        uri="s3://templates/fullstack-saas-v1/policies/code-standards.md",
        content="# Code Standards\n\nFollow PEP 8.",
    ))
    await repo.save_template_artifact(TemplateArtifact(
        template_id="fullstack-saas-v1",
        artifact_key="configs/docker.yml",
        content_type="application/json",
        uri="s3://templates/fullstack-saas-v1/configs/docker.yml",
        content='{"dockerfile": "Dockerfile"}',
    ))

    index = CodeIndexArtifact(
        project_id=project.id,
        idea_id=idea.id,
        commit_sha="abc123",
        file_inventory=[
            {"path": "backend/app/main.py", "size": 1200, "kind": "source"},
            {"path": "backend/app/repository.py", "size": 50000, "kind": "source"},
        ],
        test_commands=["pytest backend/tests"],
        architecture_summary="FastAPI backend with DynamoDB storage",
    )
    await repo.put_code_index(index)

    return {"idea": idea, "project": project, "template": template, "index": index}


@pytest.mark.asyncio
async def test_create_factory_run(test_client: AsyncClient, db_session):
    repo = db_session.repo
    seed = await _seed_project_and_template(repo)
    project = seed["project"]

    response = await test_client.post(
        f"/api/projects/{project.id}/factory-runs",
        json={
            "template_id": "fullstack-saas-v1",
            "config": {"stack": "python-fastapi"},
        },
    )

    assert response.status_code == 201
    data = response.json()

    assert data["factory_run"]["status"] == "running"
    assert data["factory_run"]["template_id"] == "fullstack-saas-v1"
    assert data["factory_run"]["config"]["template_version"] == "2.0.0"
    assert data["factory_run"]["config"]["stack"] == "python-fastapi"
    assert data["factory_run"]["config"]["role_contracts"]["planner"]["role"] == "planner"
    assert data["factory_run"]["config"]["role_contracts"]["batch_planner"]["role"] == "batch_planner"
    assert data["factory_run"]["idea_id"] == seed["idea"].id
    assert data["factory_run"]["tracking_manifest_uri"] is not None
    assert data["tracking_manifest"]["factory_run_id"] == data["factory_run"]["id"]
    assert data["tracking_manifest"]["template_version"] == "2.0.0"
    assert data["tracking_summary"]["template"]["template_version"] == "2.0.0"
    assert data["tracking_summary"]["phase_progress"]["total"] == 4
    assert data["tracking_summary"]["worker_queue_state"]["status"] in {"queued", "running", "claimed"}

    assert len(data["phases"]) == 4
    assert data["phases"][0]["phase_key"] == "scaffold"
    assert data["phases"][0]["phase_order"] == 1
    assert data["phases"][1]["phase_key"] == "backend"
    assert data["phases"][3]["phase_key"] == "integration"

    assert data["first_batch"] is not None
    assert data["first_batch"]["batch_key"] == "scaffold-batch-1"
    assert data["first_batch"]["status"] == "pending"

    assert data["work_item"] is not None
    assert data["work_item"]["status"] == "queued"
    assert data["work_item"]["job_type"] == "agent_branch_work"
    assert data["work_item"]["priority"] == 60
    assert data["work_item"]["payload"]["role"] == "worker"
    assert data["work_item"]["payload"]["role_prompt"].startswith("Role: Worker")
    assert data["work_item"]["payload"]["role_prompt_template"].startswith("Role: Worker")
    assert "project" in data["work_item"]["payload"]["role_required_inputs"]
    assert data["work_item"]["payload"]["role_output_schema"]["type"] == "object"
    assert data["work_item"]["payload"]["role_model"]
    assert data["work_item"]["payload"]["verifier_contract"]["role"] == "verifier"
    assert data["work_item"]["payload"]["factory_job_type"] == "factory_phase:scaffold"
    assert data["work_item"]["payload"]["execution_type"] == "agent_branch_work"


@pytest.mark.asyncio
async def test_create_factory_run_work_item_contract(test_client: AsyncClient, db_session):
    repo = db_session.repo
    seed = await _seed_project_and_template(repo)
    project = seed["project"]
    blueprint = {
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

    response = await test_client.post(
        f"/api/projects/{project.id}/factory-runs",
        json={"template_id": "fullstack-saas-v1", "config": {"blueprint": blueprint}},
    )
    assert response.status_code == 201
    data = response.json()
    payload = data["work_item"]["payload"]

    assert "goal" in payload
    assert payload["goal"] == "Build the fullstack SaaS application"
    assert payload["project_blueprint"]["blueprint_id"] == "bp-valid-001"
    assert payload["project_blueprint"]["template_version"] == "2.0.0"
    assert payload["permission_profile"]["ring"] == RING_1_SCOPED_EXECUTION
    assert payload["required_capabilities"] == ["agent_branch_work", "test_verify"]
    assert payload["policy_result"]["status"] == "pass"
    assert data["factory_run"]["config"]["project_blueprint"]["blueprint_id"] == "bp-valid-001"
    assert data["factory_run"]["config"]["policy_result"]["status"] == "pass"

    assert payload["project_twin"]["project_id"] == project.id
    assert payload["project_twin"]["repo_full_name"] == "acme/my-app"
    assert payload["project_twin"]["clone_url"] == "https://github.com/acme/my-app.git"
    assert payload["project_twin"]["default_branch"] == "main"
    assert "python" in payload["project_twin"]["detected_stack"]

    assert payload["branch"].startswith("factory/")
    assert payload["base_branch"] == "main"

    assert len(payload["context_files"]) > 0
    context_paths = [f["path"] for f in payload["context_files"]]
    assert "graphify-out/GRAPH_REPORT.md" in context_paths

    assert len(payload["template_docs"]) == 3
    doc_keys = [d["key"] for d in payload["template_docs"]]
    assert "policies/code-standards.md" in doc_keys
    assert "configs/docker.yml" in doc_keys
    assert "AGENTS.md" in doc_keys

    assert payload["template_version"] == "2.0.0"
    assert payload["template_id"] == "fullstack-saas-v1"

    assert len(payload["constraints"]) == 2
    assert payload["constraints"][0]["id"] == "no-secrets"

    assert len(payload["quality_gates"]) == 1

    assert len(payload["deliverables"]) == 3

    assert "pytest backend/tests" in payload["verification_commands"]
    assert "graphify update ." in payload["verification_commands"]

    assert payload["role"] == "worker"
    assert payload["role_prompt"].startswith("Role: Worker")
    assert payload["role_prompt_template"].startswith("Role: Worker")
    assert "project" in payload["role_required_inputs"]
    assert "Read graphify-out/GRAPH_REPORT.md" in payload["role_prompt"]
    assert "graphify_instructions" in payload["role_prompt"]
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["content"] == payload["role_prompt"]

    assert "pre_task" in payload["graphify_instructions"]
    assert "post_task" in payload["graphify_instructions"]
    assert any("GRAPH_REPORT.md" in instruction for instruction in payload["graphify_instructions"]["pre_task"])
    assert any("graphify update ." in instruction for instruction in payload["graphify_instructions"]["post_task"])

    schema = payload["response_schema"]
    assert schema["type"] == "object"
    assert "summary" in schema["required"]
    assert "files_modified" in schema["required"]
    assert "tests_passed" in schema["required"]
    assert "graphify_updated" in schema["required"]
    assert "branch_name" in schema["required"]
    assert "commit_sha" in schema["properties"]
    assert "branch_name" in schema["properties"]
    assert "phase_artifacts" in schema["properties"]
    assert payload["verifier_contract"]["role"] == "verifier"
    assert payload["verifier_contract"]["output_schema"]["type"] == "object"


@pytest.mark.asyncio
async def test_create_factory_run_warning_persists_policy_result(test_client: AsyncClient, db_session):
    repo = db_session.repo
    seed = await _seed_project_and_template(repo)
    project = seed["project"]
    blueprint = {
        "blueprint_id": "bp-warn-001",
        "target_stack": [],
        "files_or_modules": ["."],
        "dependencies": [],
        "build_steps": ["Implement scoped backend changes"],
        "verification_commands": [],
        "required_capabilities": ["agent_branch_work", "test_verify"],
        "permission_profile": {
            "ring": RING_1_SCOPED_EXECUTION,
            "allowed_capabilities": ["agent_branch_work", "test_verify"],
            "tool_integrations": [],
            "notes": ["scoped execution"],
        },
        "graphify_requirements": {
            "pre_task": ["Read graphify-out/GRAPH_REPORT.md for god nodes and community structure"],
            "post_task": [],
        },
    }

    response = await test_client.post(
        f"/api/projects/{project.id}/factory-runs",
        json={"template_id": "fullstack-saas-v1", "config": {"blueprint": blueprint}},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["factory_run"]["config"]["policy_result"]["status"] == "warn"
    assert data["factory_run"]["config"]["planner_feedback"]
    assert data["work_item"]["payload"]["policy_result"]["status"] == "warn"
    assert data["work_item"]["payload"]["permission_profile"]["ring"] == RING_1_SCOPED_EXECUTION
    assert data["work_item"]["payload"]["project_blueprint"]["blueprint_id"] == "bp-warn-001"
    assert any("verification" in item.lower() for item in data["factory_run"]["config"]["planner_feedback"])


@pytest.mark.asyncio
async def test_create_factory_run_blocked_by_policy_returns_structured_detail(test_client: AsyncClient, db_session):
    repo = db_session.repo
    seed = await _seed_project_and_template(repo)
    project = seed["project"]
    blueprint = {
        "blueprint_id": "bp-block-001",
        "target_stack": ["python", "fastapi"],
        "files_or_modules": ["backend/app"],
        "dependencies": ["fastapi"],
        "build_steps": ["Deploy to production", "rm -rf /"],
        "verification_commands": ["pytest backend/tests"],
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

    response = await test_client.post(
        f"/api/projects/{project.id}/factory-runs",
        json={"template_id": "fullstack-saas-v1", "config": {"blueprint": blueprint}},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error"] == "policy_blocked"
    assert detail["policy_result"]["status"] == "block"
    assert any(issue["code"] == "high_risk_action" for issue in detail["policy_result"]["issues"])
    assert len(await repo.list_factory_runs()) == 0
    assert len(await repo.list_work_items()) == 0


@pytest.mark.asyncio
async def test_create_factory_run_project_not_found(test_client: AsyncClient, db_session):
    response = await test_client.post(
        "/api/projects/nonexistent-id/factory-runs",
        json={"template_id": "fullstack-saas-v1"},
    )
    assert response.status_code == 400
    assert "Project twin not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_factory_run_template_not_found(test_client: AsyncClient, db_session):
    repo = db_session.repo
    seed = await _seed_project_and_template(repo)
    project = seed["project"]

    response = await test_client.post(
        f"/api/projects/{project.id}/factory-runs",
        json={"template_id": "nonexistent-template"},
    )
    assert response.status_code == 400
    assert "Template pack not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_factory_runs(test_client: AsyncClient, db_session):
    repo = db_session.repo
    seed = await _seed_project_and_template(repo)
    project = seed["project"]

    await test_client.post(
        f"/api/projects/{project.id}/factory-runs",
        json={"template_id": "fullstack-saas-v1"},
    )
    await test_client.post(
        f"/api/projects/{project.id}/factory-runs",
        json={"template_id": "fullstack-saas-v1", "config": {"stack": "nextjs"}},
    )

    response = await test_client.get(f"/api/projects/{project.id}/factory-runs")
    assert response.status_code == 200
    data = response.json()
    assert len(data["factory_runs"]) == 2


@pytest.mark.asyncio
async def test_get_factory_run(test_client: AsyncClient, db_session):
    repo = db_session.repo
    seed = await _seed_project_and_template(repo)
    project = seed["project"]

    created = await test_client.post(
        f"/api/projects/{project.id}/factory-runs",
        json={"template_id": "fullstack-saas-v1"},
    )
    factory_run_id = created.json()["factory_run"]["id"]

    response = await test_client.get(f"/api/factory-runs/{factory_run_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["factory_run"]["id"] == factory_run_id
    assert len(data["phases"]) == 4
    assert len(data["batches"]) >= 1
    assert len(data["verifications"]) == 0


@pytest.mark.asyncio
async def test_get_factory_run_not_found(test_client: AsyncClient, db_session):
    response = await test_client.get("/api/factory-runs/nonexistent")
    assert response.status_code == 404
