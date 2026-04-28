"""WorkflowEngine abstraction for Karkhana factory orchestration.

Design rationale:
- OpenCode local workers are the execution plane; backend/web are the control plane.
- We keep AWS serverless/pay-as-you-go: Lambda handles one transition per invocation,
  DynamoDB stores state, and SQS decouples workers from the backend.
- Temporal is intentionally deferred. It adds operational complexity (running a
  Temporal cluster or paying for Temporal Cloud) and is unnecessary while the
  factory run state machine is simple (phases -> batches -> verification -> repair).
- A future TemporalWorkflowEngine can implement the same WorkflowEngine protocol
  without changing callers. Temporal would give us: long-running workflows with
  timers, saga compensation, workflow replay, and visibility. The trade-off is
  infrastructure cost and operational surface area.
- When we do adopt Temporal, the migration path is:
  1. Implement TemporalWorkflowEngine(WorkflowEngine)
  2. Replace the default engine in FactoryOrchestratorService and LocalWorkerService
  3. Keep SqsDdbWorkflowEngine as a fallback for local/offline mode.
"""
from __future__ import annotations

from typing import Any, Protocol

from backend.app.repository import (
    BLOCKED_STATUS,
    FactoryBatch,
    FactoryPhase,
    FactoryRun,
    RepairTask,
    VerificationRun,
    WorkerEvent,
    get_repository,
    utcnow,
)
from backend.app.services.autonomy import can_auto_advance_phase, can_auto_repair
from backend.app.services.factory_run import FactoryRunService
from backend.app.services.factory_tracking import (
    FACTORY_ARTIFACT_PREFIX,
    FACTORY_WORKER_JOB_TYPE,
    refresh_factory_run_tracking_manifest,
    upsert_factory_verification,
)
from backend.app.services.local_workers import LocalWorkerService
from backend.app.services.project_twin import ProjectTwinService, to_jsonable
from backend.app.services.verification_repair import process_verification_result
from backend.app.services.worker_sqs import WorkerSqsPublisher


class WorkflowEngine(Protocol):
    """Contract for factory run orchestration.

    All implementations must keep workflow state durable and treat large
    logs/diffs/artifacts as URI references rather than inline blobs.
    """

    async def start_factory_run(
        self,
        project_id: str,
        template_id: str,
        autonomy_level: str = "autonomous_development",
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    async def enqueue_next_batch(
        self,
        run_id: str,
        phase_id: str,
        batch_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    async def record_worker_event(
        self,
        worker_id: str,
        event_type: str,
        payload: dict[str, Any],
        work_item_id: str | None = None,
    ) -> WorkerEvent: ...

    async def request_verification(
        self,
        factory_run_id: str,
        factory_batch_id: str,
        result: dict[str, Any],
    ) -> dict[str, Any]: ...

    async def request_repair(
        self,
        factory_run_id: str,
        factory_batch_id: str,
        reason: str,
    ) -> dict[str, Any]: ...

    async def pause_for_approval(
        self,
        factory_run_id: str,
        reason: str,
    ) -> dict[str, Any]: ...

    async def resume_after_approval(
        self,
        factory_run_id: str,
        next_phase_key: str | None = None,
    ) -> dict[str, Any]: ...

    async def mark_blocked(
        self,
        factory_run_id: str,
        reason: str,
    ) -> dict[str, Any]: ...

    async def mark_complete(
        self,
        factory_run_id: str,
    ) -> dict[str, Any]: ...


class SqsDdbWorkflowEngine:
    """Serverless workflow engine backed by DynamoDB and SQS.

    - State is durable in DynamoDB via Repository.
    - Worker notifications go through SQS (WorkerSqsPublisher).
    - Large artifacts are stored as S3-compatible URIs, never inline.
    - Each Lambda invocation handles exactly one transition.
    """

    def __init__(
        self,
        repo: Any | None = None,
        sqs_publisher: WorkerSqsPublisher | None = None,
        factory_run_service: FactoryRunService | None = None,
    ) -> None:
        self._repo = repo or get_repository()
        self._sqs = sqs_publisher or WorkerSqsPublisher()
        self._factory_service = factory_run_service or FactoryRunService()
        self._project_service = ProjectTwinService(sqs_publisher=self._sqs)

    async def start_factory_run(
        self,
        project_id: str,
        template_id: str,
        autonomy_level: str = "autonomous_development",
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Delegate to FactoryRunService for bootstrapping.

        Future TemporalWorkflowEngine could instead start a workflow execution
        and return the workflow handle/run ID.
        """
        return await self._factory_service.create_factory_run(
            project_id=project_id,
            template_id=template_id,
            autonomy_level=autonomy_level,
            config=config,
        )

    async def enqueue_next_batch(
        self,
        run_id: str,
        phase_id: str,
        batch_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Enqueue a work item for the next phase/batch.

        Mirrors the original FactoryOrchestratorService._enqueue_next_phase logic
        but exposed as a WorkflowEngine primitive so callers don't hardcode
        FactoryRun transitions.
        """
        run = await self._repo.get_factory_run(run_id)
        if not run:
            return {"action": "noop", "reason": "run_not_found"}

        next_phase = await self._repo.get_factory_phase(run_id, phase_id)
        if not next_phase:
            return {"action": "noop", "reason": "phase_not_found"}

        # Find the most recent completed work item to infer project_id/idea_id
        phases = await self._repo.list_factory_phases(run_id)
        completed_item = None
        for phase in phases:
            if phase.status == "completed":
                batches = await self._repo.list_factory_batches(phase.id)
                for batch in batches:
                    if batch.work_item_id:
                        item = await self._repo.get_work_item(batch.work_item_id)
                        if item:
                            completed_item = item
                            break

        if not completed_item:
            return {"action": "noop", "reason": "no_completed_item_for_context"}

        project = await self._repo.get_project_twin_by_id(completed_item.project_id)
        template = await self._repo.get_template_pack(run.template_id)
        if not project or not template:
            run.status = "failed"
            run.completed_at = utcnow()
            await self._repo.save_factory_run(run)
            await refresh_factory_run_tracking_manifest(self._repo, run_id)
            return {"action": "run_failed", "reason": "missing_project_or_template"}

        next_batch = FactoryBatch(
            factory_phase_id=next_phase.id,
            factory_run_id=run.id,
            batch_key=batch_config.get("batch_key", f"{next_phase.phase_key}-batch-1") if batch_config else f"{next_phase.phase_key}-batch-1",
        )
        await self._repo.save_factory_batch(next_batch)

        contract = await self._factory_service._build_worker_contract(
            project=project,
            template=template,
            factory_run=run,
            phase=next_phase,
            batch=next_batch,
        )

        work_item = await self._project_service.enqueue_job(
            idea_id=completed_item.idea_id,
            project_id=completed_item.project_id,
            job_type=FACTORY_WORKER_JOB_TYPE,
            payload=contract,
            idempotency_key=f"factory:{run.id}:phase:{next_phase.phase_key}",
            priority=60,
        )

        next_batch.work_item_id = work_item.id
        await self._repo.save_factory_batch(next_batch)

        next_phase.status = "running"
        next_phase.started_at = utcnow()
        await self._repo.save_factory_phase(next_phase)

        run.status = "running"
        await self._repo.save_factory_run(run)
        await refresh_factory_run_tracking_manifest(self._repo, run_id)

        return {
            "action": "phase_advanced",
            "next_phase": next_phase.phase_key,
            "work_item_id": work_item.id,
        }

    async def record_worker_event(
        self,
        worker_id: str,
        event_type: str,
        payload: dict[str, Any],
        work_item_id: str | None = None,
    ) -> WorkerEvent:
        """Persist a worker event."""
        event = WorkerEvent(
            worker_id=worker_id,
            event_type=event_type,
            payload=payload,
            work_item_id=work_item_id,
        )
        await self._repo.add_worker_event(event)
        return event

    async def request_verification(
        self,
        factory_run_id: str,
        factory_batch_id: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        """Process a verification result.

        Delegates to the existing verification_repair module so we don't
        duplicate classification and repair logic. The engine boundary here
        ensures callers don't hardcode FactoryRun transitions.
        """
        passed = bool(result.get("tests_passed", True))
        return await process_verification_result(
            factory_run_id=factory_run_id,
            factory_batch_id=factory_batch_id,
            passed=passed,
            result=result,
        )

    async def request_repair(
        self,
        factory_run_id: str,
        factory_batch_id: str,
        reason: str,
    ) -> dict[str, Any]:
        """Create a repair task for a failed batch.

        Uses the same underlying repair pipeline as verification failure handling.
        """
        return await process_verification_result(
            factory_run_id=factory_run_id,
            factory_batch_id=factory_batch_id,
            passed=False,
            result={"test_output": reason, "summary": reason},
        )

    async def pause_for_approval(
        self,
        factory_run_id: str,
        reason: str,
    ) -> dict[str, Any]:
        """Pause a run awaiting human approval before advancing.

        Sets the run status to 'awaiting_approval' and refreshes the manifest.
        """
        run = await self._repo.get_factory_run(factory_run_id)
        if not run:
            return {"action": "noop", "reason": "run_not_found"}
        run.status = "awaiting_approval"
        await self._repo.save_factory_run(run)
        await refresh_factory_run_tracking_manifest(self._repo, factory_run_id)
        return {"action": "awaiting_approval", "reason": reason, "factory_run_id": factory_run_id}

    async def resume_after_approval(
        self,
        factory_run_id: str,
        next_phase_key: str | None = None,
    ) -> dict[str, Any]:
        """Resume a run after human approval.

        Finds the next pending phase (or the one matching next_phase_key) and
        enqueues it via enqueue_next_batch.
        """
        run = await self._repo.get_factory_run(factory_run_id)
        if not run:
            return {"action": "noop", "reason": "run_not_found"}

        phases = await self._repo.list_factory_phases(factory_run_id)
        next_phase = None
        if next_phase_key:
            next_phase = next((p for p in phases if p.phase_key == next_phase_key and p.status == "pending"), None)
        if not next_phase:
            for p in phases:
                if p.status == "pending":
                    next_phase = p
                    break

        if not next_phase:
            return await self.mark_complete(factory_run_id)

        run.status = "running"
        await self._repo.save_factory_run(run)
        return await self.enqueue_next_batch(factory_run_id, next_phase.id)

    async def mark_blocked(
        self,
        factory_run_id: str,
        reason: str,
    ) -> dict[str, Any]:
        """Block a run and refresh tracking.

        Keeps large failure details as URI references when possible.
        """
        run = await self._repo.get_factory_run(factory_run_id)
        if not run:
            return {"action": "noop", "reason": "run_not_found"}
        run.status = BLOCKED_STATUS
        await self._repo.save_factory_run(run)
        await refresh_factory_run_tracking_manifest(self._repo, factory_run_id)
        return {"action": "blocked", "reason": reason, "factory_run_id": factory_run_id}

    async def mark_complete(
        self,
        factory_run_id: str,
    ) -> dict[str, Any]:
        """Complete a run and refresh tracking."""
        run = await self._repo.get_factory_run(factory_run_id)
        if not run:
            return {"action": "noop", "reason": "run_not_found"}
        run.status = "completed"
        run.completed_at = utcnow()
        await self._repo.save_factory_run(run)
        await refresh_factory_run_tracking_manifest(self._repo, factory_run_id)
        return {"action": "run_completed", "factory_run_id": factory_run_id}

    async def on_task_completed(self, work_item_id: str) -> dict[str, Any] | None:
        """Orchestration handler for a completed work item.

        This replaces the deep hardcoding in FactoryOrchestratorService
        by routing through the WorkflowEngine primitives.
        """
        item = await self._repo.get_work_item(work_item_id)
        if not item or item.status != "completed":
            return None

        payload = item.payload or {}
        factory_run_id = payload.get("factory_run_id")
        if not factory_run_id:
            return None

        run = await self._repo.get_factory_run(factory_run_id)
        if not run or run.status in ("completed", "failed", BLOCKED_STATUS):
            return None

        phase_id = payload.get("factory_phase_id")
        batch_id = payload.get("factory_batch_id")

        batch = await self._repo.get_factory_batch(batch_id) if batch_id else None
        if batch:
            batch.status = "completed"
            batch.completed_at = utcnow()
            result = item.result or {}
            artifacts = result.get("phase_artifacts") or {}
            batch.output_uri = (
                artifacts.get("output_uri")
                or f"{FACTORY_ARTIFACT_PREFIX}/{factory_run_id}/{batch_id}/output"
            )
            await self._repo.save_factory_batch(batch)

            passed = bool(result.get("tests_passed", True))
            await upsert_factory_verification(
                self._repo, run=run, batch=batch, result=result, passed=passed,
            )

            if not passed:
                vr_result = await self.request_verification(
                    factory_run_id=factory_run_id,
                    factory_batch_id=batch_id,
                    result=result,
                )
                action = vr_result.get("action", "")
                if action.startswith("blocked"):
                    phase = await self._repo.get_factory_phase(factory_run_id, phase_id) if phase_id else None
                    if phase:
                        phase.status = BLOCKED_STATUS
                        phase.completed_at = utcnow()
                        await self._repo.save_factory_phase(phase)
                    await refresh_factory_run_tracking_manifest(self._repo, factory_run_id)
                    return vr_result
                return vr_result

        phase = await self._repo.get_factory_phase(factory_run_id, phase_id) if phase_id else None
        if phase:
            phase.status = "completed"
            phase.completed_at = utcnow()
            phase.output_uri = f"{FACTORY_ARTIFACT_PREFIX}/{factory_run_id}/{phase_id}/summary"
            await self._repo.save_factory_phase(phase)

        phases = await self._repo.list_factory_phases(factory_run_id)
        current_order = phase.phase_order if phase else 0
        next_phase = None
        for p in phases:
            if p.phase_order > current_order and p.status == "pending":
                next_phase = p
                break

        if next_phase:
            if can_auto_advance_phase(run):
                return await self.enqueue_next_batch(factory_run_id, next_phase.id)
            return await self.pause_for_approval(factory_run_id, f"Next phase {next_phase.phase_key} requires approval")

        return await self.mark_complete(factory_run_id)

    async def on_task_failed(self, work_item_id: str) -> dict[str, Any] | None:
        """Orchestration handler for a failed work item."""
        item = await self._repo.get_work_item(work_item_id)
        if not item or item.status != "failed_terminal":
            return None

        payload = item.payload or {}
        factory_run_id = payload.get("factory_run_id")
        if not factory_run_id:
            return None

        run = await self._repo.get_factory_run(factory_run_id)
        if not run or run.status in ("completed", "failed", BLOCKED_STATUS):
            return None

        phase_id = payload.get("factory_phase_id")
        batch_id = payload.get("factory_batch_id")

        if batch_id:
            batch = await self._repo.get_factory_batch(batch_id)
            if batch:
                batch.status = "failed"
                batch.completed_at = utcnow()
                batch.output_uri = (
                    f"{FACTORY_ARTIFACT_PREFIX}/{factory_run_id}/{batch_id}/failure"
                )
                await self._repo.save_factory_batch(batch)

                if can_auto_repair(run):
                    vr_result = await self.request_repair(
                        factory_run_id=factory_run_id,
                        factory_batch_id=batch_id,
                        reason=item.error or "Factory batch failed",
                    )
                    action = vr_result.get("action", "")
                    if action.startswith("blocked") or action == "repair_created":
                        if phase_id:
                            phase = await self._repo.get_factory_phase(factory_run_id, phase_id)
                            if phase and action.startswith("blocked"):
                                phase.status = BLOCKED_STATUS
                                phase.completed_at = utcnow()
                                await self._repo.save_factory_phase(phase)
                        await refresh_factory_run_tracking_manifest(self._repo, factory_run_id)
                        return vr_result

        if phase_id:
            phase = await self._repo.get_factory_phase(factory_run_id, phase_id)
            if phase:
                phase.status = "failed"
                phase.completed_at = utcnow()
                await self._repo.save_factory_phase(phase)

        run.status = "failed"
        run.completed_at = utcnow()
        await self._repo.save_factory_run(run)
        await refresh_factory_run_tracking_manifest(self._repo, factory_run_id)
        return {"action": "run_failed", "factory_run_id": factory_run_id}
