from __future__ import annotations

from datetime import timedelta

import pytest

from backend.app.repository import (
    CodeIndexArtifact,
    FactoryRun,
    GitHubInstallation,
    Idea,
    InMemoryRepository,
    ProjectTwin,
    TemplateArtifact,
    TemplatePack,
    WorkerEvent,
    set_repository,
    utcnow,
)
from backend.app.services.factory_run import FactoryRunService
from backend.app.services.review_packet import ReviewPacketService


async def _seed_project_and_template(repo: InMemoryRepository) -> ProjectTwin:
    idea = Idea(
        title="Factory State MVP",
        slug="factory-state-mvp",
        description="Project for factory state testing",
        source_type="github_project",
    )
    await repo.create_idea(idea)

    await repo.save_github_installation(
        GitHubInstallation(installation_id="101", account_login="acme")
    )

    project = ProjectTwin(
        idea_id=idea.id,
        provider="github",
        installation_id="101",
        owner="acme",
        repo="mvp-app",
        repo_full_name="acme/mvp-app",
        repo_url="https://github.com/acme/mvp-app",
        clone_url="https://github.com/acme/mvp-app.git",
        default_branch="main",
        detected_stack=["python", "fastapi"],
        test_commands=["pytest backend/tests", "graphify update ."],
    )
    await repo.save_project_twin(project)

    template = TemplatePack(
        template_id="factory-state-template",
        version="1.0.0",
        channel="stable",
        display_name="Factory State Template",
        description="Template for factory state testing",
        phases=[{"key": "build", "label": "Build"}],
        opencode_worker={
            "goal": "Build the project",
            "verification_commands": ["pytest backend/tests", "graphify update ."],
        },
    )
    await repo.save_template_pack(template)
    await repo.save_template_artifact(TemplateArtifact(
        template_id=template.template_id,
        artifact_key="AGENTS.md",
        content_type="text/markdown",
        uri="s3://templates/factory-state-template/AGENTS.md",
        content="# Guidance",
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
            "ring": "ring_1_scoped_execution",
            "allowed_capabilities": ["agent_branch_work", "test_verify"],
            "tool_integrations": [],
            "notes": ["scoped execution"],
        },
        "graphify_requirements": {
            "pre_task": ["Read graphify-out/GRAPH_REPORT.md for god nodes and community structure"],
            "post_task": ["Run 'graphify update .' after all code changes to keep the knowledge graph current"],
        },
    }


@pytest.fixture
def repo():
    r = InMemoryRepository()
    set_repository(r)
    return r


@pytest.mark.asyncio
async def test_factory_run_with_intent_creates_intent_and_system_events(repo):
    project = await _seed_project_and_template(repo)

    result = await FactoryRunService().create_factory_run(
        project_id=project.id,
        template_id="factory-state-template",
        config={"blueprint": _valid_blueprint()},
        intent={"summary": "Ship a compact factory-state MVP", "details": {"notes": "Keep it additive"}},
    )

    run = result["factory_run"]
    assert run["intent_id"] is not None
    assert run["correlation_id"]
    assert run["budget"] == {}
    assert run["stop_conditions"] == []
    assert result["factory_state"]["intent_summary"] == "Ship a compact factory-state MVP"

    stored_intent = await repo.get_intent(project.idea_id, run["intent_id"])
    assert stored_intent is not None
    assert stored_intent.summary == "Ship a compact factory-state MVP"
    assert run["id"] in stored_intent.factory_run_ids

    events = await repo.list_worker_events("system")
    event_types = [event.event_type for event in events]
    assert "intent_created" in event_types
    assert "factory_run_created" in event_types


@pytest.mark.asyncio
async def test_research_artifact_import_dedupes_and_preserves_raw_and_normalized(repo):
    project = await _seed_project_and_template(repo)
    run = await repo.create_factory_run(
        FactoryRun(
            idea_id=project.idea_id,
            template_id="factory-state-template",
            config={"blueprint": _valid_blueprint()},
        )
    )

    service = FactoryRunService()
    first = await service.create_research_artifact(
        run.id,
        title="Market scan",
        source="docs",
        raw_content="* Revenue is growing\n* Adoption is strong",
        raw_metadata={"url": "https://example.test/research"},
    )
    second = await service.create_research_artifact(
        run.id,
        title="Market scan",
        source="docs",
        raw_content="* Revenue is growing\n* Adoption is strong",
        raw_metadata={"url": "https://example.test/research"},
    )

    assert first["deduped"] is False
    assert second["deduped"] is True
    assert first["research_artifact"]["id"] == second["research_artifact"]["id"]
    artifacts = await repo.list_research_artifacts(run.id)
    assert len(artifacts) == 1
    assert artifacts[0].raw_content.startswith("* Revenue")
    assert artifacts[0].normalized["summary"] == "Revenue is growing"


@pytest.mark.asyncio
async def test_research_handoff_generates_typed_packet_and_approval_creates_work_item(repo):
    project = await _seed_project_and_template(repo)
    service = FactoryRunService()
    result = await service.create_factory_run(
        project_id=project.id,
        template_id="factory-state-template",
        config={"blueprint": _valid_blueprint()},
        intent={"summary": "Ship a compact factory-state MVP"},
    )
    run_id = result["factory_run"]["id"]

    await service.create_research_artifact(
        run_id,
        title="Customer notes",
        source="docs",
        raw_content="* Users want a compact state strip\n* They need research imports",
        raw_metadata={"origin": "manual"},
    )

    packet = await ReviewPacketService().create_research_handoff(run_id)
    assert packet["packet_type"] == "research_handoff"
    assert packet["research_artifact_ids"]
    assert packet["research_handoff"]["supported_facts"]
    assert packet["research_handoff"]["requirement_tags"]
    assert "review_packet_created" in str(packet["telemetry_events"])

    approval = await ReviewPacketService().submit_intervention(run_id, "approve", rationale="Looks good")
    assert approval["wait_window_state"] == "approved"

    work_items = await repo.list_work_items(project.idea_id)
    assert any(item.branch_name and item.branch_name.endswith("/research-handoff") for item in work_items)

    events = await repo.list_worker_events("system")
    event_types = [event.event_type for event in events]
    assert "review_packet_created" in event_types
    assert "research_handoff_approved" in event_types


@pytest.mark.asyncio
async def test_worker_events_are_sorted_by_creation_time(repo):
    now = utcnow()
    await repo.add_worker_event(WorkerEvent(worker_id="system", event_type="first", payload={}, created_at=now))
    await repo.add_worker_event(WorkerEvent(worker_id="system", event_type="second", payload={}, created_at=now + timedelta(seconds=1)))

    events = await repo.list_worker_events("system")
    assert [event.event_type for event in events] == ["first", "second"]


@pytest.mark.asyncio
async def test_research_artifact_and_handoff_routes(test_client, db_session):
    repo = db_session.repo
    project = await _seed_project_and_template(repo)

    create_response = await test_client.post(
        f"/api/projects/{project.id}/factory-runs",
        json={
            "template_id": "factory-state-template",
            "config": {"blueprint": _valid_blueprint()},
            "intent": {"summary": "Ship the factory state MVP"},
        },
    )
    assert create_response.status_code == 201
    run_id = create_response.json()["factory_run"]["id"]

    import_response = await test_client.post(
        f"/api/factory-runs/{run_id}/research-artifacts",
        json={
            "title": "Customer note",
            "source": "docs",
            "raw_content": "* Research import works\n* Handoff should be typed",
            "raw_metadata": {"origin": "manual"},
        },
    )
    assert import_response.status_code == 201
    artifact = import_response.json()["research_artifact"]
    assert artifact["normalized"]["summary"] == "Research import works"

    handoff_response = await test_client.post(f"/api/factory-runs/{run_id}/research-handoff")
    assert handoff_response.status_code == 201
    packet = handoff_response.json()
    assert packet["packet_type"] == "research_handoff"
    assert packet["research_artifact_ids"] == [artifact["id"]]
    assert packet["research_handoff"]["supported_facts"]
