"""Pydantic models for dashboard WebSocket messages."""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


# ── Server → Client (outgoing events) ──────────────────────────


class WSEvent(BaseModel):
    """Event sent from server to dashboard client."""

    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: float


# ── Client → Server (incoming commands) ────────────────────────


class ApproveCommand(BaseModel):
    """User approves a stage gate, optionally with edits."""

    action: Literal["approve"] = "approve"
    stage: str
    edited_data: dict[str, Any] | None = None


class RerunCommand(BaseModel):
    """User requests re-running a specific stage."""

    action: Literal["rerun"] = "rerun"
    stage: str


class WSCommand(BaseModel):
    """Wrapper for any incoming WebSocket command."""

    action: str
    stage: str | None = None
    job_id: str | None = None
    message: str | None = None
    edited_data: dict[str, Any] | None = None


# ── Pipeline status snapshot ───────────────────────────────────


class StageStatus(BaseModel):
    """Status of a single pipeline stage."""

    name: str
    status: Literal["pending", "running", "waiting", "done", "error"] = "pending"
    output: Any | None = None
    error: str | None = None


class PipelineSnapshot(BaseModel):
    """Full pipeline status for initial dashboard load."""

    stages: list[StageStatus] = Field(default_factory=list)
    generated_files: dict[str, str] = Field(default_factory=dict)
    build_started: bool = False
    build_complete: bool = False
