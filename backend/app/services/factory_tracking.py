from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from backend.app.repository import (
    BLOCKED_STATUS,
    FactoryBatch,
    FactoryPhase,
    FactoryRun,
    FactoryRunTrackingManifest,
    ProjectTwin,
    RepairTask,
    VerificationRun,
    WorkItem,
    get_repository,
    utcnow,
)

FACTORY_ARTIFACT_PREFIX = "s3://factory-artifacts"
FACTORY_WORKER_JOB_TYPE = "agent_branch_work"
GRAPHIFY_PRE_TASK = [
    "Read graphify-out/GRAPH_REPORT.md for god nodes and community structure",
    "Read graphify-out/wiki/index.md if it exists for codebase navigation",
]
GRAPHIFY_POST_TASK = [
    "Run 'graphify update .' after all code changes to keep the knowledge graph current",
]


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _status_counter(items: list[Any], key: str = "status") -> dict[str, int]:
    counter = Counter((getattr(item, key, None) or "unknown") for item in items)
    return dict(sorted(counter.items()))


def _work_item_status(batch: FactoryBatch, work_items: dict[str, WorkItem]) -> str:
    item = work_items.get(batch.work_item_id or "")
    return item.status if item else batch.status


def _work_item_from_batch(batch: FactoryBatch, work_items: dict[str, WorkItem]) -> WorkItem | None:
    if not batch.work_item_id:
        return None
    return work_items.get(batch.work_item_id)


def compose_worker_prompt(
    *,
    project: ProjectTwin,
    template_id: str,
    template_version: str,
    factory_run: FactoryRun,
    phase: FactoryPhase,
    batch: FactoryBatch,
    template_docs: list[dict[str, Any]],
    context_files: list[dict[str, str]],
    constraints: list[dict[str, Any]],
    quality_gates: list[dict[str, Any]],
    deliverables: list[str],
    verification_commands: list[str],
    graphify_instructions: dict[str, list[str]] | None = None,
    goal: str | None = None,
) -> str:
    instructions = graphify_instructions or {"pre_task": GRAPHIFY_PRE_TASK, "post_task": GRAPHIFY_POST_TASK}
    docs_overview = "\n".join(
        f"- {doc.get('key', 'doc')} ({doc.get('content_type', 'text/plain')}): {doc.get('uri', '')}"
        for doc in template_docs
    ) or "- No template docs were attached."
    context_overview = "\n".join(
        f"- {entry.get('role', 'source')}: {entry.get('path', '')}"
        for entry in context_files
    ) or "- No code context files were attached."
    constraint_overview = "\n".join(f"- {item.get('description', '')}" for item in constraints) or "- No explicit constraints."
    quality_overview = "\n".join(
        f"- {gate.get('phase', phase.phase_key)}: {gate.get('command', gate.get('type', 'check'))}"
        for gate in quality_gates
    ) or "- No quality gates."
    deliverable_overview = "\n".join(f"- {item}" for item in deliverables) or "- No deliverables."
    verification_overview = "\n".join(f"- {item}" for item in verification_commands) or "- No verification commands."
    goal_text = goal or f"Execute factory phase '{phase.phase_key}' for project {project.repo_full_name}"
    prompt = f"""
Graphify instructions:
{chr(10).join(f"- {line}" for line in instructions.get('pre_task', GRAPHIFY_PRE_TASK))}

Task goal:
{goal_text}

Repository:
- Project: {project.repo_full_name}
- Idea ID: {project.idea_id}
- Template: {template_id} v{template_version}
- Run: {factory_run.id}
- Phase: {phase.phase_key} ({phase.phase_order})
- Batch: {batch.batch_key}
- Branch: factory/{factory_run.id[:8]}/{phase.phase_key}
- Base branch: {project.default_branch}

Context files:
{context_overview}

Template docs available from the central registry:
{docs_overview}

Constraints:
{constraint_overview}

Quality gates:
{quality_overview}

Deliverables:
{deliverable_overview}

Verification commands:
{verification_overview}

Graphify aftercare:
{chr(10).join(f"- {line}" for line in instructions.get('post_task', GRAPHIFY_POST_TASK))}

Before editing, follow the graphify instructions above. Keep changes scoped to this branch, preserve the project workspace, and report the exact files changed plus test outcomes.
""".strip()
    return prompt


def build_tracking_manifest(
    *,
    run: FactoryRun,
    phases: list[FactoryPhase],
    batches: list[FactoryBatch],
    verifications: list[VerificationRun],
    work_items: list[WorkItem],
    project: ProjectTwin | None,
    latest_index: Any | None,
    snapshot_uri: str | None = None,
    repair_tasks: list[RepairTask] | None = None,
) -> FactoryRunTrackingManifest:
    work_items_by_id = {item.id: item for item in work_items}
    phase_summary = [
        {
            "id": phase.id,
            "phase_key": phase.phase_key,
            "phase_order": phase.phase_order,
            "status": phase.status,
            "started_at": _iso(phase.started_at),
            "completed_at": _iso(phase.completed_at),
        }
        for phase in sorted(phases, key=lambda item: item.phase_order)
    ]
    batch_summary = []
    for batch in sorted(batches, key=lambda item: (item.created_at, item.batch_key)):
        work_item = _work_item_from_batch(batch, work_items_by_id)
        batch_summary.append({
            "id": batch.id,
            "factory_phase_id": batch.factory_phase_id,
            "batch_key": batch.batch_key,
            "status": _work_item_status(batch, work_items_by_id),
            "worker_id": batch.worker_id,
            "work_item_id": batch.work_item_id,
            "work_item_status": work_item.status if work_item else None,
            "input_uri": batch.input_uri,
            "output_uri": batch.output_uri,
            "started_at": _iso(batch.started_at),
            "completed_at": _iso(batch.completed_at),
        })

    latest_verification = sorted(verifications, key=lambda item: item.created_at)[-1] if verifications else None
    repair_tasks_list = repair_tasks or []
    latest_repair = sorted(repair_tasks_list, key=lambda item: item.created_at)[-1] if repair_tasks_list else None
    verification_state = {
        "status": latest_verification.status if latest_verification else "pending",
        "verification_run_id": latest_verification.id if latest_verification else None,
        "factory_batch_id": latest_verification.factory_batch_id if latest_verification else None,
        "result_summary": latest_verification.result_summary if latest_verification else "",
        "result_uri": latest_verification.result_uri if latest_verification else None,
        "completed_at": _iso(latest_verification.completed_at) if latest_verification else None,
        "passed": bool(latest_verification and latest_verification.status in {"passed", "completed", "succeeded", "success"}),
        "failure_classification": latest_verification.failure_classification if latest_verification else "",
        "repair_state": {
            "total_repairs": len(repair_tasks_list),
            "latest_repair_id": latest_repair.id if latest_repair else None,
            "latest_repair_status": latest_repair.status if latest_repair else None,
            "latest_repair_classification": latest_repair.failure_classification if latest_repair else None,
            "latest_issue_summary": latest_repair.issue_summary if latest_repair and latest_repair.issue_summary else None,
        },
    }

    queue_counts = _status_counter(work_items)
    active_work_items = [item for item in work_items if item.status in {"queued", "waiting_for_machine", "failed_retryable", "claimed", "running"}]
    latest_work_item = sorted(work_items, key=lambda item: item.updated_at)[-1] if work_items else None
    worker_queue_state = {
        "status": latest_work_item.status if latest_work_item else run.status,
        "queued": queue_counts.get("queued", 0) + queue_counts.get("waiting_for_machine", 0),
        "running": queue_counts.get("claimed", 0) + queue_counts.get("running", 0),
        "retryable": queue_counts.get("failed_retryable", 0),
        "failed": queue_counts.get("failed_terminal", 0),
        "active_work_item_id": latest_work_item.id if latest_work_item else None,
        "active_worker_id": latest_work_item.worker_id if latest_work_item else None,
        "active_batch_count": len(active_work_items),
        "total_work_items": len(work_items),
    }

    latest_commit = latest_index.commit_sha if latest_index else None
    graphify_status = "pending"
    if run.status == "failed":
        graphify_status = "failed"
    elif any(item.result and item.result.get("graphify_updated") for item in work_items):
        graphify_status = "updated"
    elif any(item.status in {"claimed", "running"} for item in work_items):
        graphify_status = "running"
    elif any(item.status == "completed" for item in work_items):
        graphify_status = "missing"

    manifest = FactoryRunTrackingManifest(
        factory_run_id=run.id,
        idea_id=run.idea_id,
        template_id=run.template_id,
        template_version=run.config.get("template_version", ""),
        run_config=run.config or {},
        run_status=run.status,
        phase_summary=phase_summary,
        batch_summary=batch_summary,
        verification_summary=[
            {
                "id": verification.id,
                "factory_batch_id": verification.factory_batch_id,
                "status": verification.status,
                "verification_type": verification.verification_type,
                "result_summary": verification.result_summary,
                "result_uri": verification.result_uri,
                "completed_at": _iso(verification.completed_at),
            }
            for verification in sorted(verifications, key=lambda item: item.created_at)
        ],
        last_indexed_commit=latest_commit or (project.last_indexed_commit if project else None),
        graphify_status=graphify_status,
        worker_queue_state=worker_queue_state,
        verification_state=verification_state,
        artifact_uris={
            "tracking_manifest_uri": snapshot_uri,
            "worker_logs_uri": next((item.logs_pointer for item in work_items if item.logs_pointer), None),
            "verification_output_uri": verification_state.get("result_uri"),
            "batch_output_uris": {
                batch.id: batch.output_uri
                for batch in batches
                if batch.output_uri
            },
        },
        snapshot_uri=snapshot_uri,
        completed_at=run.completed_at,
    )
    return manifest


def build_tracking_summary(manifest: FactoryRunTrackingManifest) -> dict[str, Any]:
    completed_phases = sum(1 for phase in manifest.phase_summary if phase.get("status") == "completed")
    total_phases = len(manifest.phase_summary)
    completed_batches = sum(1 for batch in manifest.batch_summary if batch.get("status") == "completed")
    total_batches = len(manifest.batch_summary)
    return {
        "factory_run_id": manifest.factory_run_id,
        "run_status": manifest.run_status,
        "template": {
            "template_id": manifest.template_id,
            "template_version": manifest.template_version,
        },
        "phase_progress": {
            "completed": completed_phases,
            "total": total_phases,
            "active": max(total_phases - completed_phases, 0),
        },
        "batch_progress": {
            "completed": completed_batches,
            "total": total_batches,
            "active": max(total_batches - completed_batches, 0),
        },
        "graphify_status": manifest.graphify_status,
        "verification_state": manifest.verification_state,
        "worker_queue_state": manifest.worker_queue_state,
        "last_indexed_commit": manifest.last_indexed_commit,
        "tracking_manifest_uri": manifest.snapshot_uri,
        "updated_at": manifest.updated_at.isoformat() if manifest.updated_at else None,
    }


async def upsert_factory_verification(
    repo: Any,
    *,
    run: FactoryRun,
    batch: FactoryBatch,
    result: dict[str, Any],
    passed: bool,
    error: str | None = None,
) -> VerificationRun:
    verifications = await repo.list_verification_runs(batch.id)
    verification = next((item for item in verifications if item.verification_type == "post_task"), None)
    verification_output_uri = result.get("verification_output_uri") or f"{FACTORY_ARTIFACT_PREFIX}/{run.id}/{batch.id}/verification.json"
    result_summary = result.get("summary") or result.get("test_output") or error or ""
    status = "passed" if passed else "failed"
    if verification:
        verification.status = status
        verification.result_uri = verification_output_uri
        verification.result_summary = result_summary
        verification.completed_at = utcnow()
    else:
        verification = VerificationRun(
            factory_batch_id=batch.id,
            factory_run_id=run.id,
            verification_type="post_task",
            status=status,
            result_uri=verification_output_uri,
            result_summary=result_summary,
            completed_at=utcnow(),
        )
    await repo.save_verification_run(verification)
    return verification


def build_repair_plan(
    *,
    run: FactoryRun,
    batch: FactoryBatch,
    reason: str,
) -> dict[str, Any]:
    return {
        "factory_run_id": run.id,
        "factory_phase_id": batch.factory_phase_id,
        "factory_batch_id": batch.id,
        "repair_job_type": FACTORY_WORKER_JOB_TYPE,
        "reason": reason,
        "prompt": (
            f"Repair the failed factory batch {batch.batch_key} for run {run.id}. "
            f"Analyze the failure reason, make the smallest safe fix, and preserve the branch-based workflow."
        ),
    }


def build_watchdog_snapshot(
    *,
    run: FactoryRun,
    batches: list[FactoryBatch],
    work_items: list[WorkItem],
) -> dict[str, Any]:
    active_batches = [batch for batch in batches if batch.status in {"pending", "running", "failed"}]
    active_work_items = [item for item in work_items if item.status in {"queued", "waiting_for_machine", "failed_retryable", "claimed", "running"}]
    return {
        "factory_run_id": run.id,
        "run_status": run.status,
        "active_batches": len(active_batches),
        "active_work_items": len(active_work_items),
        "stale_candidate_work_items": [
            item.id for item in active_work_items if item.heartbeat_at is None and item.claimed_at is None
        ],
    }


async def collect_factory_run_bundle(repo: Any, run_id: str) -> dict[str, Any] | None:
    run = await repo.get_factory_run(run_id)
    if not run:
        return None
    phases = await repo.list_factory_phases(run.id)
    batches: list[FactoryBatch] = []
    verifications: list[VerificationRun] = []
    work_items: list[WorkItem] = []
    for phase in phases:
        phase_batches = await repo.list_factory_batches(phase.id)
        batches.extend(phase_batches)
        for batch in phase_batches:
            if batch.work_item_id:
                work_item = await repo.get_work_item(batch.work_item_id)
                if work_item:
                    work_items.append(work_item)
            verifications.extend(await repo.list_verification_runs(batch.id))

    project = await repo.get_project_twin(run.idea_id)
    latest_index = await repo.get_latest_code_index(run.idea_id)
    repair_tasks = await repo.list_repair_tasks(run.id)
    manifest = await repo.get_factory_run_tracking_manifest(run.id)
    if not manifest:
        manifest = build_tracking_manifest(
            run=run,
            phases=phases,
            batches=batches,
            verifications=verifications,
            work_items=work_items,
            project=project,
            latest_index=latest_index,
            snapshot_uri=f"{FACTORY_ARTIFACT_PREFIX}/{run.id}/tracking-manifest.json",
            repair_tasks=repair_tasks,
        )
        await repo.save_factory_run_tracking_manifest(manifest)
        run.tracking_manifest_uri = manifest.snapshot_uri
        await repo.save_factory_run(run)

    return {
        "factory_run": run,
        "phases": phases,
        "batches": batches,
        "verifications": verifications,
        "work_items": work_items,
        "tracking_manifest": manifest,
        "tracking_summary": build_tracking_summary(manifest),
        "project": project,
        "latest_index": latest_index,
        "repair_tasks": repair_tasks,
    }


async def refresh_factory_run_tracking_manifest(repo: Any, run_id: str) -> FactoryRunTrackingManifest | None:
    bundle = await collect_factory_run_bundle(repo, run_id)
    if not bundle:
        return None
    run = bundle["factory_run"]
    snapshot_uri = (
        bundle["tracking_manifest"].snapshot_uri
        if bundle["tracking_manifest"] and bundle["tracking_manifest"].snapshot_uri
        else f"{FACTORY_ARTIFACT_PREFIX}/{run.id}/tracking-manifest.json"
    )
    manifest = build_tracking_manifest(
        run=run,
        phases=bundle["phases"],
        batches=bundle["batches"],
        verifications=bundle["verifications"],
        work_items=bundle["work_items"],
        project=bundle["project"],
        latest_index=bundle["latest_index"],
        snapshot_uri=snapshot_uri,
        repair_tasks=bundle.get("repair_tasks"),
    )
    await repo.save_factory_run_tracking_manifest(manifest)
    run.tracking_manifest_uri = manifest.snapshot_uri
    await repo.save_factory_run(run)
    return manifest
