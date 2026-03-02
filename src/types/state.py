"""Working state for the Software Factory."""

from operator import add
from datetime import datetime
from typing import Any, Annotated
from pydantic import BaseModel, Field

from src.types.error import ErrorLog


class WorkingState(BaseModel):
    """Central state object passed between agents."""

    # Input
    raw_idea: str

    # Generated artifacts
    prd_drafts: Annotated[list[dict[str, Any]], add] = Field(default_factory=list)
    prd: dict[str, Any] | None = None
    tech_stack: dict[str, Any] | None = None
    file_tree: dict[str, list[str]] | None = None

    # Current execution context
    current_file: str | None = None
    current_code: str | None = None
    review_passed: bool = True
    review_issues: list[dict[str, Any]] = Field(default_factory=list)

    # Progress tracking
    completed_files: set[str] = Field(default_factory=set)
    pending_files: list[str] = Field(default_factory=list)

    # Error handling with self-healing support
    error_log: list[ErrorLog] = Field(default_factory=list)

    # Dashboard / human-in-the-loop
    dashboard_mode: bool = False
    job_id: str | None = None
    approval_required: bool = False
    agent_inbox: list[dict[str, Any]] = Field(default_factory=list)
    agent_outbox: list[dict[str, Any]] = Field(default_factory=list)
    pending_agent_requests: list[dict[str, Any]] = Field(default_factory=list)
    resolved_agent_requests: list[dict[str, Any]] = Field(default_factory=list)
    coordination_rounds: int = 0
    coordination_budget: int = 8
    agent_blocked_reason: str | None = None
    agent_comms_enabled: bool = False
    agent_comms_escalate_blocking_only: bool = True
    coordination_origin: str | None = None
    coordination_action: str | None = None
    reasoning_config: dict[str, Any] = Field(default_factory=dict)
    reasoning_metrics: dict[str, Any] = Field(default_factory=dict)
    architecture_candidates: list[dict[str, Any]] = Field(default_factory=list)
    critic_report: dict[str, Any] | None = None
    generated_files_map: dict[str, str] = Field(default_factory=dict)
    tdd_loop_stats: dict[str, Any] = Field(default_factory=dict)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    llm_calls_count: int = 0
    total_generation_time_seconds: float = 0.0

    class Config:
        extra = "allow"
