"""Working state for the Software Factory."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

from src.types.error import ErrorLog


class WorkingState(BaseModel):
    """Central state object passed between agents."""

    # Input
    raw_idea: str

    # Generated artifacts
    prd: dict[str, Any] | None = None
    tech_stack: dict[str, Any] | None = None
    file_tree: dict[str, list[str]] | None = None

    # Current execution context
    current_file: str | None = None
    current_code: str | None = None

    # Progress tracking
    completed_files: set[str] = Field(default_factory=set)
    pending_files: list[str] = Field(default_factory=list)

    # Error handling with self-healing support
    error_log: list[ErrorLog] = Field(default_factory=list)

    # Dashboard / human-in-the-loop
    dashboard_mode: bool = False

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    llm_calls_count: int = 0
    total_generation_time_seconds: float = 0.0

    class Config:
        extra = "allow"
