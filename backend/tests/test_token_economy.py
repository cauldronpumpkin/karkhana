from __future__ import annotations

import pytest

from backend.app.repository import (
    FactoryBatch,
    FactoryPhase,
    FactoryRun,
    Idea,
    InMemoryRepository,
    ProjectTwin,
    WorkItem,
    GitHubInstallation,
    set_repository,
    utcnow,
)
from backend.app.services.factory_tracking import build_tracking_manifest, build_tracking_summary, normalize_token_economy
from backend.app.services.project_twin import ProjectTwinService


class _NoopPublisher:
    async def send_job_available(self, item, project) -> None:  # pragma: no cover - test helper
        return None


async def _seed_project(repo: InMemoryRepository) -> tuple[Idea, ProjectTwin]:
    idea = Idea(
        title="Token Economy Test",
        slug="token-economy-test",
        description="Project for token economy telemetry tests",
        source_type="github_project",
    )
    await repo.create_idea(idea)
    await repo.save_github_installation(GitHubInstallation(installation_id="99", account_login="acme"))
    project = ProjectTwin(
        idea_id=idea.id,
        provider="github",
        installation_id="99",
        owner="acme",
        repo="token-app",
        repo_full_name="acme/token-app",
        repo_url="https://github.com/acme/token-app",
        clone_url="https://github.com/acme/token-app.git",
        default_branch="main",
    )
    await repo.save_project_twin(project)
    return idea, project


@pytest.mark.asyncio
async def test_normalize_token_economy_computes_cache_hit_rate_and_duplicate_flag() -> None:
    repo = InMemoryRepository()
    set_repository(repo)
    item = WorkItem(
        idea_id="idea-001",
        project_id="project-001",
        job_type="repo_index",
        payload={"duplicate_work_key": "dup-001"},
        status="completed",
    )

    normalized = normalize_token_economy(
        {
            "worker_run_id": "worker-run-001",
            "provider": "openai",
            "model": "gpt-5.4-mini",
            "input_tokens_total": 120,
            "input_tokens_cached": 30,
            "output_tokens": 50,
            "cost_estimate_usd": 0.42,
        },
        work_item=item,
        payload=item.payload,
        result={"duplicate_work_detected": False},
    )

    assert normalized["cache_hit_rate"] == 0.25
    assert normalized["duplicate_work_detected"] is True
    assert normalized["success"] is True
    assert normalized["input_tokens_total"] == 120
    assert normalized["cost_estimate_usd"] == 0.42


@pytest.mark.asyncio
async def test_tracking_summary_aggregates_token_economy_and_duplicates() -> None:
    repo = InMemoryRepository()
    set_repository(repo)
    run = FactoryRun(idea_id="idea-001", template_id="tpl-001", status="running", config={"template_version": "1.0.0"})
    phase = FactoryPhase(factory_run_id=run.id, phase_key="scaffold", phase_order=1, status="completed")
    work_item_one = WorkItem(
        idea_id=run.idea_id,
        project_id="project-001",
        job_type="repo_index",
        status="completed",
        payload={"factory_run_id": run.id},
        result={
            "token_economy": {
                "worker_run_id": "worker-run-001",
                "provider": "openai",
                "model": "gpt-5.4-mini",
                "input_tokens_total": 100,
                "input_tokens_cached": 25,
                "output_tokens": 50,
                "cost_estimate_usd": 0.75,
            }
        },
    )
    work_item_two = WorkItem(
        idea_id=run.idea_id,
        project_id="project-001",
        job_type="repo_index",
        status="queued",
        payload={
            "factory_run_id": run.id,
            "duplicate_work_detected": True,
            "duplicate_work_key": "dup-001",
        },
    )
    batch = FactoryBatch(
        factory_phase_id=phase.id,
        factory_run_id=run.id,
        batch_key="scaffold-batch-1",
        status="completed",
        work_item_id=work_item_one.id,
    )

    manifest = build_tracking_manifest(
        run=run,
        phases=[phase],
        batches=[batch],
        verifications=[],
        work_items=[work_item_one, work_item_two],
        project=None,
        latest_index=None,
    )
    summary = build_tracking_summary(manifest)

    assert manifest.token_economy_totals["input_tokens_total"] == 100
    assert manifest.token_economy_totals["input_tokens_cached"] == 25
    assert manifest.token_economy_totals["cache_hit_rate"] == 0.25
    assert manifest.duplicate_work_count == 1
    assert summary["token_economy_totals"] == manifest.token_economy_totals
    assert summary["duplicate_work_count"] == 1


@pytest.mark.asyncio
async def test_duplicate_work_flag_propagates_through_completion() -> None:
    repo = InMemoryRepository()
    set_repository(repo)
    idea, project = await _seed_project(repo)
    svc = ProjectTwinService(sqs_publisher=_NoopPublisher())

    first = await svc.enqueue_job(
        idea_id=idea.id,
        project_id=project.id,
        job_type="repo_index",
        payload={"duplicate_work_key": "dup-001"},
        idempotency_key="dup-001",
    )
    second = await svc.enqueue_job(
        idea_id=idea.id,
        project_id=project.id,
        job_type="repo_index",
        payload={"duplicate_work_key": "dup-001"},
        idempotency_key="dup-001",
    )

    assert first.payload.get("duplicate_work_detected") is not True
    assert second.payload["duplicate_work_detected"] is True
    assert second.payload["duplicate_work_key"] == "dup-001"

    claimed = await repo.get_work_item(second.id)
    assert claimed is not None
    claimed.status = "claimed"
    claimed.worker_id = "worker-001"
    claimed.claim_token = "claim-001"
    claimed.claimed_at = utcnow()
    claimed.heartbeat_at = claimed.claimed_at
    await repo.save_work_item(claimed)

    completed = await svc.complete_job(
        job_id=claimed.id,
        claim_token="claim-001",
        worker_id="worker-001",
        result={
            "summary": "done",
            "token_economy": {
                "worker_run_id": "worker-run-002",
                "provider": "openai",
                "model": "gpt-5.4-mini",
                "input_tokens_total": 40,
                "input_tokens_cached": 10,
                "output_tokens": 20,
            },
        },
    )

    token_economy = completed["result"]["token_economy"]
    assert token_economy["duplicate_work_detected"] is True
    assert token_economy["cache_hit_rate"] == 0.25


@pytest.mark.asyncio
async def test_enqueue_job_threads_ledger_metadata() -> None:
    repo = InMemoryRepository()
    set_repository(repo)
    idea, project = await _seed_project(repo)
    svc = ProjectTwinService(sqs_publisher=_NoopPublisher())

    item = await svc.enqueue_job(
        idea_id=idea.id,
        project_id=project.id,
        job_type="repo_index",
        payload={"reason": "manual"},
        ledger_policy="required",
        ledger_path="./karkhana-runs\\run.md",
    )

    assert item.ledger_policy == "required"
    assert item.ledger_path == "karkhana-runs/run.md"
    assert item.payload["ledger_policy"] == "required"
    assert item.payload["ledger_path"] == "karkhana-runs/run.md"
