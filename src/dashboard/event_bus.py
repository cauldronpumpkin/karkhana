"""Async event bus for streaming pipeline events to the dashboard."""

import asyncio
import time
from typing import Any, Callable, Coroutine


class Event:
    """A single pipeline event."""

    __slots__ = ("type", "payload", "timestamp")

    def __init__(self, event_type: str, payload: dict[str, Any] | None = None):
        self.type = event_type
        self.payload = payload or {}
        self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }


# Type alias for subscriber callbacks
Subscriber = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """
    Singleton async event bus.

    Usage:
        bus = EventBus.get()
        bus.subscribe(my_handler)
        await bus.emit("stage_start", {"stage": "pm_agent"})
    """

    _instance: "EventBus | None" = None

    def __init__(self):
        self._subscribers: list[Subscriber] = []
        self._history: list[Event] = []
        # Stage gates: stage_name -> asyncio.Event that blocks until user approves
        self._approval_gates: dict[str, asyncio.Event] = {}
        # Edited payloads from the user (e.g. modified PRD JSON)
        self._approval_edits: dict[str, Any] = {}

    @classmethod
    def get(cls) -> "EventBus":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        """Reset the singleton (useful for tests)."""
        cls._instance = None

    # ── Pub / Sub ──────────────────────────────────────────────

    def subscribe(self, callback: Subscriber):
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Subscriber):
        self._subscribers = [s for s in self._subscribers if s is not callback]

    async def emit(self, event_type: str, payload: dict[str, Any] | None = None):
        """Emit an event to all subscribers."""
        event = Event(event_type, payload)
        self._history.append(event)
        tasks = [sub(event) for sub in self._subscribers]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    @property
    def history(self) -> list[Event]:
        return list(self._history)

    # ── Stage Gates (human-in-the-loop) ────────────────────────

    async def wait_for_approval(self, stage: str, data: dict[str, Any]) -> dict[str, Any]:
        """
        Block the pipeline until the dashboard user approves this stage.
        Returns the (possibly edited) data.
        """
        gate = asyncio.Event()
        self._approval_gates[stage] = gate
        self._approval_edits.pop(stage, None)

        await self.emit("waiting_for_approval", {"stage": stage, "data": data})

        # Block until user clicks Approve in the dashboard
        await gate.wait()

        # Clean up
        del self._approval_gates[stage]
        edited = self._approval_edits.pop(stage, data)
        return edited

    def approve(self, stage: str, edited_data: dict[str, Any] | None = None):
        """Called by the server when the user approves a stage."""
        gate = self._approval_gates.get(stage)
        if gate is None:
            return  # No gate waiting — ignore
        if edited_data is not None:
            self._approval_edits[stage] = edited_data
        gate.set()

    @property
    def pending_approvals(self) -> list[str]:
        """Stages currently waiting for user approval."""
        return [s for s, g in self._approval_gates.items() if not g.is_set()]
