"""Single-runner queue executor for Command Center jobs."""

from __future__ import annotations

import asyncio


class CommandCenterRunner:
    """Executes queued jobs sequentially using the service callbacks."""

    def __init__(self, service: "CommandCenterService") -> None:
        self.service = service
        self._task: asyncio.Task | None = None

    def ensure_started(self) -> None:
        """Start runner loop if not currently active."""
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._loop())

    async def _loop(self) -> None:
        while True:
            job = await self.service.dequeue_next_job()
            if job is None:
                break
            await self.service.run_job(job)


# Circular typing support
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.command_center.service import CommandCenterService

