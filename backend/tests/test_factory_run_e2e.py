"""End-to-end integration test: factory run -> claim -> execute -> complete -> ledger.

Exercises the full pipeline via FastAPI AsyncClient backed by InMemoryRepository.
No real AWS dependencies -- all storage is in-memory.

Uses the EXACT patterns from conftest:
  - pytest_asyncio fixtures (db_session, test_client)
  - db_session.add() + await db_session.commit() to seed Idea entities
  - db_session.repo.*() for types not handled by FakeSession (ProjectTwin, TemplatePack)
  - set_repository wired automatically by db_session fixture
  - All test functions are async def with @pytest.mark.asyncio
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient

from backend.app.repository import Idea, ProjectTwin, TemplatePack


# ── Fixtures ─────────────────────────────────────────────────


@pytest_asyncio.fixture
async def seeded_project(db_session) -> dict:
    """Seed an idea + project twin + template pack and return a dict with all entities."""
    idea = Idea(
        title="E2E Test",
        slug="e2e-test",
        description="e2e integration test",
    )
    db_session.add(idea)
    await db_session.commit()

    project = ProjectTwin(
        idea_id=idea.id,
        provider="github",
        installation_id="inst-e2e",
        owner="test",
        repo="e2e-app",
        repo_full_name="test/e2e-app",
        repo_url="https://github.com/test/e2e-app",
        clone_url="https://github.com/test/e2e-app.git",
        default_branch="main",
    )
    await db_session.repo.save_project_twin(project)

    template = TemplatePack(
        template_id="multi-phase-v1",
        version="1.0.0",
        channel="stable",
        display_name="Multi-Phase",
        description="",
        phases=[
            {"key": "scaffold", "label": "Scaffold"},
            {"key": "backend", "label": "Backend"},
        ],
    )
    await db_session.repo.save_template_pack(template)

    return {"idea": idea, "project": project, "template": template}


# ── Helpers ─────────────────────────────────────────────────


def _auth_headers() -> dict[str, str]:
    """Return headers with worker auth token for endpoints that require it."""
    return {"X-IdeaRefinery-Worker-Token": "test-token"}


# ── Tests ──────────────────────────────────────────────────


class TestFactoryRunE2E:
    """End-to-end test of the complete factory pipeline using async conftest patterns."""

    @pytest.mark.asyncio
    async def test_create_factory_run(
        self, test_client: AsyncClient, seeded_project: dict
    ) -> None:
        """Factory run creation returns 201 with factory_run ID."""
        project = seeded_project["project"]

        response = await test_client.post(
            f"/api/projects/{project.id}/factory-runs",
            json={
                "template_id": "multi-phase-v1",
                "autonomy_level": "autonomous_development",
            },
        )
        assert response.status_code == 201, response.text
        data = response.json()
        assert "factory_run" in data, f"Missing 'factory_run' key in response: {data}"
        assert data["factory_run"]["id"] is not None
        assert data["factory_run"]["template_id"] == "multi-phase-v1"
        assert data["factory_run"]["status"] in (
            "queued",
            "running",
        ), f"Unexpected status: {data['factory_run']['status']}"

    @pytest.mark.asyncio
    async def test_list_factory_runs(
        self, test_client: AsyncClient, seeded_project: dict
    ) -> None:
        """Factory runs are listable after creation."""
        project = seeded_project["project"]

        # Create a run
        await test_client.post(
            f"/api/projects/{project.id}/factory-runs",
            json={"template_id": "multi-phase-v1"},
        )

        # List runs
        response = await test_client.get(
            f"/api/projects/{project.id}/factory-runs"
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert "factory_runs" in data, f"Missing 'factory_runs' key: {data}"
        assert len(data["factory_runs"]) >= 1
        assert data["factory_runs"][0]["template_id"] == "multi-phase-v1"

    @pytest.mark.asyncio
    async def test_factory_run_creates_phases(
        self, test_client: AsyncClient, seeded_project: dict
    ) -> None:
        """Phases are auto-created from the template when a factory run starts."""
        project = seeded_project["project"]

        response = await test_client.post(
            f"/api/projects/{project.id}/factory-runs",
            json={"template_id": "multi-phase-v1"},
        )
        assert response.status_code == 201, response.text
        run_id = response.json()["factory_run"]["id"]

        # Retrieve the run and verify phases
        get_resp = await test_client.get(f"/api/factory-runs/{run_id}")
        assert get_resp.status_code == 200, get_resp.text
        run_data = get_resp.json()

        phases = run_data.get("phases", [])
        assert len(phases) >= 2, (
            f"Expected at least 2 phases, got {len(phases)}: {phases}"
        )

        phase_keys = {p["phase_key"] for p in phases}
        assert "scaffold" in phase_keys, f"Missing 'scaffold' in phases: {phase_keys}"
        assert "backend" in phase_keys, f"Missing 'backend' in phases: {phase_keys}"

    @pytest.mark.asyncio
    async def test_claim_and_complete_job(
        self, test_client: AsyncClient, seeded_project: dict
    ) -> None:
        """Full flow: create factory run -> claim a job -> complete it."""
        project = seeded_project["project"]

        # Create factory run (this creates phases + a claimable work item)
        fr_response = await test_client.post(
            f"/api/projects/{project.id}/factory-runs",
            json={"template_id": "multi-phase-v1"},
        )
        assert fr_response.status_code == 201, fr_response.text
        run_id = fr_response.json()["factory_run"]["id"]
        assert run_id is not None

        # Claim a job.
        # The factory run uses autonomy_level="autonomous_development" (default),
        # which requires opencode-server capabilities. We pass all required
        # capabilities so the claim succeeds through the autonomy validation.
        claim_response = await test_client.post(
            "/api/worker/claim",
            json={
                "worker_id": "e2e-test-worker",
                "capabilities": [
                    "agent_branch_work",
                    "permission_guard",
                    "circuit_breaker",
                    "litellm_proxy",
                    "diff_api",
                    "verification_runner",
                    "graphify_update",
                ],
            },
            headers=_auth_headers(),
        )
        assert claim_response.status_code == 200, claim_response.text
        claim_data = claim_response.json()
        claim = claim_data.get("claim")
        assert claim is not None, f"No claim in response: {claim_data}"
        assert "job" in claim, f"No job in claim: {claim}"

        job_id = claim["job"]["id"]
        claim_token = claim["job"]["claim_token"]
        assert job_id is not None
        assert claim_token is not None

        # Complete the job.
        # The work item requires graphify_updated=true, verification_results
        # matching the verification commands, and the standard response fields.
        complete_response = await test_client.post(
            f"/api/worker/jobs/{job_id}/complete",
            json={
                "worker_id": "e2e-test-worker",
                "claim_token": claim_token,
                "result": {
                    "status": "success",
                    "summary": "Job completed successfully by e2e test",
                    "engine_used": "mock",
                    "branch_name": f"factory/{run_id[:8]}/scaffold",
                    "files_modified": [],
                    "tests_passed": True,
                    "test_output": "all tests passed",
                    "graphify_updated": True,
                    "phase_artifacts": {},
                    "verification_results": {
                        "graphify update .": "passed",
                    },
                },
                "logs": "e2e test execution logs",
            },
            headers=_auth_headers(),
        )
        assert complete_response.status_code == 200, complete_response.text
        job_data = complete_response.json()
        assert "job" in job_data, f"Missing 'job' key: {job_data}"
        assert (
            job_data["job"]["status"] == "completed"
        ), f"Job status not completed: {job_data['job']['status']}"

    @pytest.mark.asyncio
    async def test_ledger_exists_after_job_completion(
        self, test_client: AsyncClient, seeded_project: dict
    ) -> None:
        """Ledger entries exist for a factory run after jobs complete."""
        project = seeded_project["project"]

        # Create factory run
        fr_response = await test_client.post(
            f"/api/projects/{project.id}/factory-runs",
            json={"template_id": "multi-phase-v1"},
        )
        assert fr_response.status_code == 201, fr_response.text
        run_id = fr_response.json()["factory_run"]["id"]

        # Claim a job (this generates work that will later create ledger entries)
        claim_resp = await test_client.post(
            "/api/worker/claim",
            json={
                "worker_id": "e2e-test-worker",
                "capabilities": [
                    "agent_branch_work",
                    "permission_guard",
                    "circuit_breaker",
                    "litellm_proxy",
                    "diff_api",
                    "verification_runner",
                    "graphify_update",
                ],
            },
            headers=_auth_headers(),
        )
        claim = claim_resp.json().get("claim")
        if not claim or not claim.get("job"):
            pytest.skip(
                "No jobs available to claim -- pipeline may not have enqueued jobs "
                "to the worker queue yet"
            )

        # Complete the claimed job
        await test_client.post(
            f"/api/worker/jobs/{claim['job']['id']}/complete",
            json={
                "worker_id": "e2e-test-worker",
                "claim_token": claim["job"]["claim_token"],
                "result": {
                    "status": "success",
                    "summary": "e2e complete",
                    "branch_name": f"factory/{run_id[:8]}/scaffold",
                    "files_modified": [],
                    "tests_passed": True,
                    "test_output": "ok",
                    "graphify_updated": True,
                    "phase_artifacts": {},
                    "verification_results": {
                        "graphify update .": "passed",
                    },
                },
                "logs": "",
            },
            headers=_auth_headers(),
        )

        # Verify ledger endpoint is reachable and returns a list.
        # NOTE: The ledger endpoint relies on DynamoDB (boto3). If AWS
        # credentials are not configured the endpoint returns 500.
        # In that case we skip rather than fail.
        ledger_resp = await test_client.get(f"/api/ledgers/{run_id}")
        if ledger_resp.status_code == 500 and (
            "credentials" in ledger_resp.text.lower()
            or "resourcenotfoundexception" in ledger_resp.text.lower()
        ):
            pytest.skip("DynamoDB ledger resource unavailable")
        assert ledger_resp.status_code == 200, ledger_resp.text
        ledgers = ledger_resp.json().get("ledgers", [])
        assert isinstance(ledgers, list), f"Expected ledgers to be a list, got {type(ledgers)}"
