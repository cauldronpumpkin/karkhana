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
from backend.app.services.policy_engine import RING_1_SCOPED_EXECUTION


async def _seed_project_and_template(repo: InMemoryRepository) -> ProjectTwin:
    idea = Idea(
        title="Bundle Test",
        slug="bundle-test",
        description="Project for worker context bundle testing",
        source_type="github_project",
    )
    await repo.create_idea(idea)

    await repo.save_github_installation(
        GitHubInstallation(installation_id="77", account_login="acme")
    )

    project = ProjectTwin(
        idea_id=idea.id,
        provider="github",
        installation_id="77",
        owner="acme",
        repo="bundle-app",
        repo_full_name="acme/bundle-app",
        repo_url="https://github.com/acme/bundle-app",
        clone_url="https://github.com/acme/bundle-app.git",
        default_branch="main",
        detected_stack=["python", "fastapi"],
        test_commands=["pytest backend/tests"],
    )
    await repo.save_project_twin(project)

    template = TemplatePack(
        template_id="bundle-template",
        version="1.2.3",
        channel="stable",
        display_name="Bundle Template",
        description="Template for bundle testing",
        phases=[
            {"key": "scaffold", "label": "Project Scaffolding"},
            {"key": "backend", "label": "Backend API"},
        ],
        opencode_worker={
            "goal": "Build the bundle test application",
            "verification_commands": ["pytest backend/tests", "graphify update ."],
        },
    )
    await repo.save_template_pack(template)

    await repo.save_template_artifact(TemplateArtifact(
        template_id=template.template_id,
        artifact_key="AGENTS.md",
        content_type="text/markdown",
        uri="s3://templates/bundle-template/AGENTS.md",
        content="# Guidance",
    ))
    await repo.save_template_artifact(TemplateArtifact(
        template_id=template.template_id,
        artifact_key="policies/code-standards.md",
        content_type="text/markdown",
        uri="s3://templates/bundle-template/policies/code-standards.md",
        content="# Code standards",
    ))

    index = CodeIndexArtifact(
        project_id=project.id,
        idea_id=idea.id,
        commit_sha="abc123",
        file_inventory=[
            {"path": "backend/app/main.py", "size": 1200, "kind": "source"},
            {"path": "backend/app/services/factory_run.py", "size": 32000, "kind": "source"},
        ],
        test_commands=["pytest backend/tests"],
        architecture_summary="FastAPI backend with deterministic worker contracts",
    )
    await repo.put_code_index(index)

    return project


def _blueprint() -> dict:
    return {
        "blueprint_id": "bp-bundle-001",
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


@pytest.mark.asyncio
async def test_worker_context_bundle_and_scaffold_manifest_are_compact_and_stable() -> None:
    repo = InMemoryRepository()
    set_repository(repo)
    project = await _seed_project_and_template(repo)

    service = FactoryRunService()
    result = await service.create_factory_run(
        project_id=project.id,
        template_id="bundle-template",
        config={"blueprint": _blueprint()},
    )

    payload = result["work_item"]["payload"]
    bundle = payload["worker_context_bundle"]
    scaffold_manifest = payload["scaffold_manifest"]

    assert payload["task_id"]
    assert bundle["schema_version"] == "v1"
    assert bundle["factory_run_id"] == result["factory_run"]["id"]
    assert bundle["factory_phase_id"] == payload["factory_phase_id"]
    assert bundle["factory_batch_id"] == payload["factory_batch_id"]
    assert bundle["template_id"] == "bundle-template"
    assert bundle["template_version"] == "1.2.3"
    assert bundle["module_ids"] == ["backend/app"]
    assert bundle["task_type"] == "factory_phase:scaffold"
    assert "backend/app/main.py" in bundle["files_likely_needed"]
    assert ".karkhana/**" in bundle["files_forbidden"]
    assert "pytest backend/tests" in bundle["verification_commands"]
    assert "graphify update ." in bundle["verification_commands"]
    assert any(card["key"] == "AGENTS.md" for card in bundle["context_cards"])
    assert any(asset["key"] == "AGENTS.md" for asset in bundle["template_assets"])
    assert bundle["output_contract"]["schema_version"] == "worker_output_contract.v1"
    assert bundle["output_contract"]["required_fields"]
    assert bundle["duplicate_work_key"]
    assert bundle["graph_context"]["report_path"] == "graphify-out/GRAPH_REPORT.md"
    assert bundle["graph_context"]["source"] == "code_index"
    assert bundle["graph_context"]["commit_sha"] == "abc123"
    assert scaffold_manifest["scaffold_mode"] == "planned"
    assert scaffold_manifest["generated_files"] == []
    assert scaffold_manifest["file_hashes"] == {}
    assert scaffold_manifest["template_id"] == "bundle-template"
    assert scaffold_manifest["template_version"] == "1.2.3"
    assert scaffold_manifest["files_forbidden"] == bundle["files_forbidden"]

    phases = await repo.list_factory_phases(result["factory_run"]["id"])
    batches = await repo.list_factory_batches(phases[0].id)
    first_batch = batches[0]

    factory_run = await repo.get_factory_run(result["factory_run"]["id"])
    phase = phases[0]

    first_contract = await service._build_worker_contract(
        project=project,
        template=await repo.get_template_pack("bundle-template"),
        factory_run=factory_run,
        phase=phase,
        batch=first_batch,
        template_context=await service._build_template_context(await repo.get_template_pack("bundle-template"), target_path="."),
    )
    second_contract = await service._build_worker_contract(
        project=project,
        template=await repo.get_template_pack("bundle-template"),
        factory_run=factory_run,
        phase=phase,
        batch=first_batch,
        template_context=await service._build_template_context(await repo.get_template_pack("bundle-template"), target_path="."),
    )

    assert first_contract["worker_context_bundle"]["duplicate_work_key"] == second_contract["worker_context_bundle"]["duplicate_work_key"]
