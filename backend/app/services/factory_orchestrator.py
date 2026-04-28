"""Serverless orchestrator for Factory Run phase advancement.

Reacts to worker task completed/failed events, persists state in DynamoDB
through existing repository patterns, and enqueues the next phase command.
Exits immediately after each transition -- no long-running state.

Design constraints:
- Lambda never holds long-running state.
- OpenCode workers run outside Lambda (local machines).
- S3-compatible URIs for large artifacts (logs, diffs, reports).
- AWS pay-as-you-go: each Lambda invocation handles exactly one transition.
- FactoryOrchestratorService now delegates to WorkflowEngine so that a future
  TemporalWorkflowEngine can be swapped in without changing callers.
"""
from __future__ import annotations

from typing import Any

from backend.app.services.workflow_engine import SqsDdbWorkflowEngine, WorkflowEngine


class FactoryOrchestratorService:
    def __init__(self, workflow_engine: WorkflowEngine | None = None) -> None:
        self._engine = workflow_engine or SqsDdbWorkflowEngine()

    @staticmethod
    def is_factory_job(payload: dict[str, Any] | None) -> bool:
        return bool((payload or {}).get("factory_run_id"))

    async def on_task_completed(self, work_item_id: str) -> dict[str, Any] | None:
        return await self._engine.on_task_completed(work_item_id)

    async def on_task_failed(self, work_item_id: str) -> dict[str, Any] | None:
        return await self._engine.on_task_failed(work_item_id)
