"""Command Center orchestration service."""

from __future__ import annotations

import asyncio
from collections import deque
from typing import Any

from src.command_center.models import (
    AgentMessageStatus,
    ChatCommandResponse,
    ContextCompactionConfig,
    ContextUsageSnapshot,
    JobContextConfig,
    JobReasoningConfig,
    JobReasoningLaunchOptions,
    JobStatus,
    ReasoningConfig,
    resolve_reasoning_config,
)
from src.command_center.parser import parse_chat_message
from src.command_center.repository import get_repository
from src.command_center.runner import CommandCenterRunner


class CommandCenterService:
    """Single source of truth for job queue and orchestration operations."""

    _instance: "CommandCenterService | None" = None
    _REASONING_DEFAULTS_KEY = "reasoning_defaults"

    def __init__(self) -> None:
        self.repo = get_repository()
        self.queue: deque[str] = deque()
        self.active_job_id: str | None = None
        self._active_pipeline_task: asyncio.Task | None = None
        self._queue_lock = asyncio.Lock()
        self.runner = CommandCenterRunner(self)
        self._bootstrapped = False

    @classmethod
    def get(cls) -> "CommandCenterService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def bootstrap(self) -> None:
        """Recover queue state after restart."""
        if self._bootstrapped:
            return
        self._bootstrapped = True

        recoverable = self.repo.list_jobs_by_status(
            [JobStatus.QUEUED.value, JobStatus.RUNNING.value, JobStatus.WAITING_APPROVAL.value]
        )
        for job in recoverable:
            if job["status"] in {JobStatus.RUNNING.value, JobStatus.WAITING_APPROVAL.value}:
                self.repo.update_job_status(job["id"], JobStatus.QUEUED.value, current_stage="recovered")
            self.queue.append(job["id"])
        if self.queue:
            self.runner.ensure_started()

    def _env_reasoning_defaults(self) -> ReasoningConfig:
        from src.config import config

        return ReasoningConfig.model_validate(config.reasoning.model_dump())

    def get_reasoning_defaults(self) -> ReasoningConfig:
        row = self.repo.get_app_setting(self._REASONING_DEFAULTS_KEY)
        if not row:
            return self._env_reasoning_defaults()
        value = row.get("value_json") or {}
        if not isinstance(value, dict):
            return self._env_reasoning_defaults()
        try:
            return ReasoningConfig.model_validate(value)
        except Exception:
            return self._env_reasoning_defaults()

    def set_reasoning_defaults(self, cfg: ReasoningConfig) -> ReasoningConfig:
        self.repo.upsert_app_setting(self._REASONING_DEFAULTS_KEY, cfg.model_dump())
        return cfg

    def get_job_reasoning_config(self, job_id: str) -> JobReasoningConfig:
        row = self.repo.get_job_reasoning_settings(job_id)
        if not row:
            return JobReasoningConfig(job_id=job_id, use_global_defaults=True, override=None, launch_override=None)
        raw_override = row.get("override_json") or {}
        raw_launch = row.get("launch_override_json") or {}
        override = ReasoningConfig.model_validate(raw_override) if isinstance(raw_override, dict) and raw_override else None
        launch_override = (
            JobReasoningLaunchOptions.model_validate(raw_launch)
            if isinstance(raw_launch, dict) and raw_launch
            else None
        )
        return JobReasoningConfig(
            job_id=job_id,
            use_global_defaults=bool(row.get("use_global_defaults", True)),
            override=override,
            launch_override=launch_override,
        )

    def set_job_reasoning_config(
        self,
        job_id: str,
        *,
        use_global_defaults: bool,
        override: ReasoningConfig | None,
        launch_override: JobReasoningLaunchOptions | None = None,
    ) -> JobReasoningConfig:
        self.repo.upsert_job_reasoning_settings(
            job_id,
            use_global_defaults=use_global_defaults,
            override=override.model_dump() if override else {},
            launch_override=launch_override.model_dump(exclude_none=True) if launch_override else {},
        )
        return JobReasoningConfig(
            job_id=job_id,
            use_global_defaults=use_global_defaults,
            override=override,
            launch_override=launch_override,
        )

    def resolve_job_reasoning(
        self,
        job_id: str,
        *,
        launch_override: JobReasoningLaunchOptions | None = None,
    ) -> ReasoningConfig:
        env_defaults = self._env_reasoning_defaults()
        global_defaults = self.get_reasoning_defaults()
        job_cfg = self.get_job_reasoning_config(job_id)
        return resolve_reasoning_config(
            env_defaults=env_defaults,
            global_defaults=global_defaults,
            job_config=job_cfg,
            launch_override=launch_override,
        )

    async def enqueue_job(
        self,
        idea: str,
        approval_required: bool = False,
        label: str | None = None,
        reasoning: JobReasoningLaunchOptions | None = None,
    ) -> dict[str, Any]:
        """Create and queue a new job."""
        from src.dashboard.event_bus import EventBus

        job = self.repo.create_job(idea=idea, approval_required=approval_required, label=label)
        if reasoning is not None:
            self.repo.upsert_job_reasoning_settings(
                job["id"],
                use_global_defaults=True,
                override={},
                launch_override=reasoning.model_dump(exclude_none=True),
            )
        async with self._queue_lock:
            self.queue.append(job["id"])

        bus = EventBus.get()
        await bus.emit(
            "job_created",
            {"job_id": job["id"], "idea": job["idea"], "approval_required": approval_required},
        )
        await bus.emit("job_queued", {"job_id": job["id"], "status": JobStatus.QUEUED.value})
        await bus.emit("job_status_changed", {"job_id": job["id"], "status": JobStatus.QUEUED.value})
        effective_reasoning = self.resolve_job_reasoning(job["id"], launch_override=reasoning)
        await bus.emit("reasoning_config_applied", {"job_id": job["id"], "reasoning_config": effective_reasoning.model_dump()})

        self.runner.ensure_started()
        return self.repo.get_job(job["id"]) or job

    async def dequeue_next_job(self) -> dict[str, Any] | None:
        """Pop next queued job that is still queueable."""
        async with self._queue_lock:
            while self.queue:
                job_id = self.queue.popleft()
                job = self.repo.get_job(job_id)
                if not job:
                    continue
                if job["status"] == JobStatus.QUEUED.value:
                    return job
            return None

    async def run_job(self, job: dict[str, Any]) -> None:
        """Execute a single job through LangGraph."""
        from src.dashboard.event_bus import EventBus
        from src.graph.flow import app as workflow_app
        from src.llm.context_manager import ContextManager
        from src.config import config
        from src.types.state import WorkingState

        job_id = job["id"]
        self.active_job_id = job_id
        self.repo.update_job_status(job_id, JobStatus.RUNNING.value, current_stage="start", progress_percent=1.0)

        bus = EventBus.get()
        await ContextManager.get().initialize_job(job_id, job["idea"])
        await bus.emit("job_started", {"job_id": job_id})
        await bus.emit("job_status_changed", {"job_id": job_id, "status": JobStatus.RUNNING.value})
        await bus.emit("build_started", {"job_id": job_id, "idea": job["idea"]})

        reasoning_config = self.resolve_job_reasoning(job_id)
        await bus.emit("reasoning_config_applied", {"job_id": job_id, "reasoning_config": reasoning_config.model_dump()})

        state = WorkingState(
            raw_idea=job["idea"],
            dashboard_mode=True,
            job_id=job_id,
            approval_required=bool(job.get("approval_required")),
            agent_comms_enabled=bool(config.agent_comms.enabled),
            coordination_budget=int(config.agent_comms.max_rounds),
            agent_comms_escalate_blocking_only=bool(config.agent_comms.escalate_blocking_only),
            reasoning_config=reasoning_config.model_dump(),
        )
        config = {"configurable": {"thread_id": f"job_{job_id}"}}

        self._active_pipeline_task = asyncio.create_task(workflow_app.ainvoke(state.model_dump(), config))
        try:
            result = await self._active_pipeline_task
            current = self.repo.get_job(job_id) or {}
            if current.get("status") != JobStatus.STOPPED.value:
                self.repo.update_job_status(job_id, JobStatus.COMPLETED.value, current_stage="complete", progress_percent=100.0)
                await bus.emit(
                    "job_completed",
                    {
                        "job_id": job_id,
                        "files_generated": len(result.get("completed_files", [])),
                        "llm_calls": result.get("llm_calls_count", 0),
                    },
                )
                await bus.emit("job_status_changed", {"job_id": job_id, "status": JobStatus.COMPLETED.value})
                await bus.emit("build_complete", {"job_id": job_id})
        except asyncio.CancelledError:
            self.repo.update_job_status(job_id, JobStatus.STOPPED.value, current_stage="stopped")
            await bus.emit("job_stopped", {"job_id": job_id})
            await bus.emit("job_status_changed", {"job_id": job_id, "status": JobStatus.STOPPED.value})
        except Exception as exc:
            self.repo.update_job_status(
                job_id,
                JobStatus.FAILED.value,
                error_message=str(exc),
                current_stage="failed",
            )
            await bus.emit("job_failed", {"job_id": job_id, "message": str(exc)})
            await bus.emit("job_status_changed", {"job_id": job_id, "status": JobStatus.FAILED.value})
            await bus.emit("error", {"job_id": job_id, "message": f"Pipeline failed: {exc}"})
        finally:
            self._active_pipeline_task = None
            self.active_job_id = None

    def get_context_defaults(self) -> ContextCompactionConfig:
        from src.llm.context_manager import ContextManager

        return ContextManager.get().get_global_defaults()

    def set_context_defaults(self, cfg: ContextCompactionConfig) -> ContextCompactionConfig:
        from src.llm.context_manager import ContextManager

        return ContextManager.get().set_global_defaults(cfg)

    def get_job_context_config(self, job_id: str) -> JobContextConfig:
        from src.llm.context_manager import ContextManager

        return ContextManager.get().get_job_config(job_id)

    def set_job_context_config(
        self,
        job_id: str,
        *,
        use_global_defaults: bool,
        override: ContextCompactionConfig | None,
    ) -> JobContextConfig:
        from src.llm.context_manager import ContextManager

        return ContextManager.get().set_job_config(
            job_id,
            use_global_defaults=use_global_defaults,
            override=override,
        )

    def get_job_context_state(self, job_id: str) -> ContextUsageSnapshot:
        from src.llm.context_manager import ContextManager

        return ContextManager.get().get_usage_snapshot(job_id)

    def get_job_context_compactions(self, job_id: str, limit: int = 100) -> list[dict[str, Any]]:
        from src.llm.context_manager import ContextManager

        return ContextManager.get().list_compactions(job_id, limit=limit)

    async def stop_job(self, job_id: str) -> bool:
        """Stop a queued or running job."""
        from src.dashboard.event_bus import EventBus

        if self.active_job_id == job_id and self._active_pipeline_task and not self._active_pipeline_task.done():
            self._active_pipeline_task.cancel()
            return True

        removed = False
        async with self._queue_lock:
            updated = deque()
            while self.queue:
                queued_job = self.queue.popleft()
                if queued_job == job_id:
                    removed = True
                else:
                    updated.append(queued_job)
            self.queue = updated

        if removed:
            self.repo.update_job_status(job_id, JobStatus.STOPPED.value, current_stage="stopped")
            bus = EventBus.get()
            await bus.emit("job_stopped", {"job_id": job_id})
            await bus.emit("job_status_changed", {"job_id": job_id, "status": JobStatus.STOPPED.value})
            return True
        return False

    async def approve_job(self, job_id: str, stage: str | None = None, edited_data: dict[str, Any] | None = None) -> bool:
        """Resolve a pending approval gate."""
        from src.dashboard.event_bus import EventBus

        decision_stage = stage
        if not decision_stage:
            decisions = self.repo.list_decisions(job_id)
            pending = [d for d in decisions if d.get("status") == "pending"]
            if not pending:
                return False
            decision_stage = pending[-1]["stage"]

        EventBus.get().approve(decision_stage, edited_data, job_id=job_id)
        await EventBus.get().emit(
            "stage_approved",
            {"job_id": job_id, "stage": decision_stage, "edited_data": edited_data or {}},
        )
        await EventBus.get().emit("job_decision_resolved", {"job_id": job_id, "stage": decision_stage})
        return True

    def list_jobs(self) -> list[dict[str, Any]]:
        return self.repo.list_jobs()

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        job = self.repo.get_job(job_id)
        if not job:
            return None
        queue_ids = list(self.queue)
        job["queue_position"] = queue_ids.index(job_id) + 1 if job_id in queue_ids else None
        return job

    def get_job_events(self, job_id: str) -> list[dict[str, Any]]:
        return self.repo.list_events(job_id)

    def get_job_logs(self, job_id: str) -> list[dict[str, Any]]:
        return self.repo.list_logs(job_id)

    def get_job_artifacts(self, job_id: str) -> list[dict[str, Any]]:
        return self.repo.list_artifacts(job_id)

    def get_job_decisions(self, job_id: str) -> list[dict[str, Any]]:
        return self.repo.list_decisions(job_id)

    def get_agent_messages(self, job_id: str, pending_only: bool = False, limit: int = 1000) -> list[dict[str, Any]]:
        status = AgentMessageStatus.PENDING.value if pending_only else None
        return self.repo.list_agent_messages(job_id, status=status, limit=limit)

    async def create_agent_message(
        self,
        job_id: str,
        from_agent: str,
        to_agent: str,
        message_type: str,
        topic: str,
        content: dict[str, Any] | None = None,
        *,
        blocking: bool = False,
        round_number: int | None = None,
    ) -> dict[str, Any] | None:
        from src.dashboard.event_bus import EventBus

        message = self.repo.create_agent_message(
            job_id=job_id,
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=message_type,
            topic=topic,
            content=content,
            status=AgentMessageStatus.PENDING.value,
            blocking=blocking,
        )
        if message:
            await EventBus.get().emit_agent_message_event(
                "agent_message_created",
                message,
                round_number=round_number,
            )
        return message

    async def resolve_agent_message(
        self,
        job_id: str,
        message_id: int,
        decision: dict[str, Any],
        *,
        status: str = AgentMessageStatus.RESOLVED.value,
        round_number: int | None = None,
    ) -> dict[str, Any] | None:
        from src.dashboard.event_bus import EventBus

        message = self.repo.resolve_agent_message(job_id, message_id, decision=decision, status=status)
        if message:
            await EventBus.get().emit_agent_message_event(
                "agent_message_resolved",
                message,
                round_number=round_number,
            )
        return message

    async def escalate_agent_message(
        self,
        job_id: str,
        message_id: int,
        reason: str,
        *,
        escalated_by: str = "agent_coordinator",
        round_number: int | None = None,
    ) -> dict[str, Any] | None:
        from src.dashboard.event_bus import EventBus

        message = self.repo.escalate_agent_message(
            job_id=job_id,
            message_id=message_id,
            reason=reason,
            escalated_by=escalated_by,
        )
        if message:
            await EventBus.get().emit_agent_message_event(
                "agent_message_escalated",
                message,
                round_number=round_number,
                escalation_reason=reason,
            )
        return message

    async def handle_chat(self, message: str, active_job_id: str | None = None) -> ChatCommandResponse:
        """Parse and execute a chat command."""
        command = parse_chat_message(message, active_job_id=active_job_id)
        if not command.ok:
            return ChatCommandResponse(action=command.action, ok=False, ui_message=command.error or "Invalid command")

        action = command.action
        args = command.args

        if action == "help":
            return ChatCommandResponse(action="help", ok=True, ui_message=args.get("message", ""))

        if action == "run":
            reasoning_payload = args.get("reasoning")
            reasoning = (
                JobReasoningLaunchOptions.model_validate(reasoning_payload)
                if isinstance(reasoning_payload, dict) and reasoning_payload
                else None
            )
            job = await self.enqueue_job(
                idea=args["idea"],
                approval_required=bool(args.get("approval_required", False)),
                reasoning=reasoning,
            )
            return ChatCommandResponse(
                action="run",
                ok=True,
                target_job_id=job["id"],
                ui_message=f"Queued job {job['id']} ({'approval on' if job['approval_required'] else 'approval off'}).",
                data={"job": job},
            )

        if action == "jobs":
            jobs = self.list_jobs()
            return ChatCommandResponse(
                action="jobs",
                ok=True,
                ui_message=f"Found {len(jobs)} jobs.",
                data={"jobs": jobs},
            )

        if action == "job":
            job_id = args.get("job_id")
            job = self.get_job(job_id)
            if not job:
                return ChatCommandResponse(action="job", ok=False, ui_message=f"Job {job_id} not found.")
            return ChatCommandResponse(action="job", ok=True, target_job_id=job_id, ui_message=f"Loaded job {job_id}.", data={"job": job})

        if action == "logs":
            job_id = args.get("job_id")
            logs = self.get_job_logs(job_id)
            return ChatCommandResponse(
                action="logs",
                ok=True,
                target_job_id=job_id,
                ui_message=f"Loaded {len(logs)} logs for {job_id}.",
                data={"logs": logs},
            )

        if action == "stop":
            job_id = args.get("job_id")
            stopped = await self.stop_job(job_id)
            if not stopped:
                return ChatCommandResponse(action="stop", ok=False, target_job_id=job_id, ui_message=f"Could not stop job {job_id}.")
            return ChatCommandResponse(action="stop", ok=True, target_job_id=job_id, ui_message=f"Stop signal sent for {job_id}.")

        if action == "approve":
            job_id = args.get("job_id")
            stage = args.get("stage")
            approved = await self.approve_job(job_id, stage=stage)
            if not approved:
                return ChatCommandResponse(action="approve", ok=False, target_job_id=job_id, ui_message=f"No pending approval found for {job_id}.")
            return ChatCommandResponse(action="approve", ok=True, target_job_id=job_id, ui_message=f"Approved {job_id}.")

        return ChatCommandResponse(action=action, ok=False, ui_message="Unsupported command.")
