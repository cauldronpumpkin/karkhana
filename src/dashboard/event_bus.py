"""Async event bus for streaming pipeline events to the dashboard."""

import asyncio
import time
from typing import Any, Callable, Coroutine

AGENT_MESSAGE_EVENT_TYPES = {
    "agent_message_created",
    "agent_message_resolved",
    "agent_message_escalated",
}


class Event:
    """A single pipeline event."""

    __slots__ = ("type", "payload", "timestamp", "job_id")

    def __init__(self, event_type: str, payload: dict[str, Any] | None = None):
        self.type = event_type
        self.payload = payload or {}
        self.timestamp = time.time()
        self.job_id = self.payload.get("job_id")

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "job_id": self.job_id,
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
        # Stage gates: key -> asyncio.Event where key is either "stage" or "job_id:stage"
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

    def clear(self):
        """Clear the history and any pending gates."""
        self._history = []
        self._approval_gates = {}
        self._approval_edits = {}

    def subscribe(self, callback: Subscriber):
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Subscriber):
        self._subscribers = [s for s in self._subscribers if s is not callback]

    async def emit(self, event_type: str, payload: dict[str, Any] | None = None):
        """Emit an event to all subscribers."""
        event = Event(event_type, payload)
        self._history.append(event)

        # Persist command-center events when a job context is present.
        try:
            from src.command_center.events import record_event

            record_event(event.type, event.payload, event.timestamp)
        except Exception:
            pass

        tasks = [sub(event) for sub in self._subscribers]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def emit_agent_message_event(
        self,
        event_type: str,
        message: dict[str, Any],
        *,
        round_number: int | None = None,
        escalation_reason: str | None = None,
    ) -> None:
        """Emit a normalized inter-agent communication event payload."""
        if event_type not in AGENT_MESSAGE_EVENT_TYPES:
            raise ValueError(f"Unsupported agent message event type: {event_type}")

        payload = {
            "job_id": message.get("job_id"),
            "message_id": message.get("id"),
            "from_agent": message.get("from_agent"),
            "to_agent": message.get("to_agent"),
            "message_type": message.get("message_type"),
            "topic": message.get("topic"),
            "blocking": bool(message.get("blocking", False)),
            "status": message.get("status"),
            "created_at": message.get("created_at"),
            "resolved_at": message.get("resolved_at"),
            "content_json": message.get("content_json", {}),
        }
        if round_number is not None:
            payload["round"] = round_number
        if escalation_reason:
            payload["escalation_reason"] = escalation_reason

        await self.emit(event_type, payload)

    @property
    def history(self) -> list[Event]:
        return list(self._history)

    async def wait_for_approval(self, stage: str, data: dict[str, Any], job_id: str | None = None) -> dict[str, Any]:
        """
        Block the pipeline until the dashboard user approves this stage.
        Returns the (possibly edited) data.
        """
        gate_key = f"{job_id}:{stage}" if job_id else stage
        gate = asyncio.Event()
        self._approval_gates[gate_key] = gate
        self._approval_edits.pop(gate_key, None)

        await self.emit("waiting_for_approval", {"job_id": job_id, "stage": stage, "data": data})

        # Block until user clicks Approve in the dashboard
        await gate.wait()

        # Clean up
        self._approval_gates.pop(gate_key, None)
        edited = self._approval_edits.pop(gate_key, data)
        return edited

    def approve(self, stage: str, edited_data: dict[str, Any] | None = None, job_id: str | None = None):
        """Called by the server when the user approves a stage."""
        gate_key = f"{job_id}:{stage}" if job_id else stage
        gate = self._approval_gates.get(gate_key)

        # Backward-compat fallback: approve by stage if scoped gate not found.
        if gate is None and job_id:
            gate_key = stage
            gate = self._approval_gates.get(gate_key)

        if gate is None:
            return

        if edited_data is not None:
            self._approval_edits[gate_key] = edited_data
        gate.set()

    @property
    def pending_approvals(self) -> list[str]:
        """Stages currently waiting for user approval."""
        return [s for s, g in self._approval_gates.items() if not g.is_set()]
