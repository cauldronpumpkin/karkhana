"""Pydantic models for Command Center APIs and orchestration."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class JobStatus(str, Enum):
    """Allowed job lifecycle statuses."""

    QUEUED = "queued"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


ReasoningProfile = Literal["fast", "balanced", "deep"]
ThinkingVisibility = Literal["off", "internal", "logs"]

_REASONING_PROFILE_PRESETS: dict[str, dict[str, Any]] = {
    "fast": {
        "architect_tot_paths": 2,
        "architect_tot_parallel": False,
        "critic_enabled": False,
        "thinking_modules_enabled": False,
        "tdd_enabled": False,
        "tdd_time_split_percent": 20,
        "tdd_max_iterations": 2,
        "tdd_fail_open": True,
    },
    "balanced": {
        "architect_tot_paths": 3,
        "architect_tot_parallel": True,
        "critic_enabled": True,
        "thinking_modules_enabled": True,
        "tdd_enabled": True,
        "tdd_time_split_percent": 40,
        "tdd_max_iterations": 5,
        "tdd_fail_open": True,
    },
    "deep": {
        "architect_tot_paths": 5,
        "architect_tot_parallel": True,
        "critic_enabled": True,
        "thinking_modules_enabled": True,
        "tdd_enabled": True,
        "tdd_time_split_percent": 60,
        "tdd_max_iterations": 8,
        "tdd_fail_open": False,
    },
}


class ReasoningConfig(BaseModel):
    """Resolved reasoning configuration used by runtime stages."""

    enabled: bool = False
    profile: ReasoningProfile = "balanced"
    architect_tot_paths: int = Field(default=3, ge=1, le=8)
    architect_tot_parallel: bool = True
    critic_enabled: bool = True
    thinking_modules_enabled: bool = True
    thinking_visibility: ThinkingVisibility = "logs"
    tdd_enabled: bool = True
    tdd_time_split_percent: int = Field(default=40, ge=0, le=100)
    tdd_max_iterations: int = Field(default=5, ge=1, le=20)
    tdd_fail_open: bool = True

    @classmethod
    def from_profile(cls, profile: ReasoningProfile, *, enabled: bool = True) -> "ReasoningConfig":
        preset = _REASONING_PROFILE_PRESETS.get(profile, _REASONING_PROFILE_PRESETS["balanced"])
        return cls(enabled=enabled, profile=profile, **preset)

    @model_validator(mode="after")
    def _normalize_disabled(self) -> "ReasoningConfig":
        if not self.enabled:
            self.architect_tot_paths = 1
            self.architect_tot_parallel = False
            self.critic_enabled = False
            self.thinking_modules_enabled = False
            self.tdd_enabled = False
        return self


class JobReasoningLaunchOptions(BaseModel):
    """Launch-time overrides supplied by CLI/API command execution."""

    enabled: bool | None = None
    profile: ReasoningProfile | None = None
    architect_tot_paths: int | None = Field(default=None, ge=1, le=8)
    architect_tot_parallel: bool | None = None
    critic_enabled: bool | None = None
    thinking_modules_enabled: bool | None = None
    thinking_visibility: ThinkingVisibility | None = None
    tdd_enabled: bool | None = None
    tdd_time_split_percent: int | None = Field(default=None, ge=0, le=100)
    tdd_max_iterations: int | None = Field(default=None, ge=1, le=20)
    tdd_fail_open: bool | None = None


class JobReasoningConfig(BaseModel):
    """Job-scoped reasoning config with optional persistent/launch overrides."""

    job_id: str = Field(min_length=1)
    use_global_defaults: bool = True
    override: ReasoningConfig | None = None
    launch_override: JobReasoningLaunchOptions | None = None


def resolve_reasoning_config(
    *,
    env_defaults: ReasoningConfig,
    global_defaults: ReasoningConfig | None = None,
    job_config: JobReasoningConfig | None = None,
    launch_override: JobReasoningLaunchOptions | None = None,
) -> ReasoningConfig:
    """
    Resolve effective reasoning config using precedence:
    launch override > job override > global defaults > env defaults.
    """
    current = env_defaults.model_copy(deep=True)

    if global_defaults is not None:
        current = global_defaults.model_copy(deep=True)

    if job_config is not None and not job_config.use_global_defaults and job_config.override is not None:
        current = job_config.override.model_copy(deep=True)

    merged_launch = launch_override or (job_config.launch_override if job_config else None)
    if merged_launch is not None:
        launch_data = merged_launch.model_dump(exclude_none=True)
        if "profile" in launch_data:
            profile = str(launch_data["profile"])
            profiled = ReasoningConfig.from_profile(profile, enabled=bool(launch_data.get("enabled", current.enabled)))
            current = profiled
        launch_data.pop("profile", None)
        current = current.model_copy(update=launch_data)

    return ReasoningConfig.model_validate(current.model_dump())


class AgentMessageType(str, Enum):
    """Allowed inter-agent message categories."""

    CLARIFICATION_REQUEST = "clarification_request"
    DEPENDENCY_APPROVAL_REQUEST = "dependency_approval_request"
    FEATURE_CHANGE_REQUEST = "feature_change_request"


class AgentMessageStatus(str, Enum):
    """Allowed inter-agent message lifecycle statuses."""

    PENDING = "pending"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class AgentDecisionStatus(str, Enum):
    """Allowed decision outcomes for resolved agent messages."""

    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_MORE_INFO = "needs_more_info"


class AgentMessage(BaseModel):
    """Persisted inter-agent communication record."""

    id: int
    job_id: str
    from_agent: str = Field(min_length=1)
    to_agent: str = Field(min_length=1)
    message_type: AgentMessageType
    topic: str = Field(min_length=1)
    content_json: dict[str, Any] = Field(default_factory=dict)
    status: AgentMessageStatus = AgentMessageStatus.PENDING
    blocking: bool = False
    created_at: float
    resolved_at: float | None = None


class ClarificationRequest(BaseModel):
    """Typed payload for clarification requests between agents."""

    question: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)
    assumptions: list[str] = Field(default_factory=list)


class DependencyApprovalRequest(BaseModel):
    """Typed payload for dependency approval requests."""

    dependency_name: str = Field(min_length=1)
    dependency_version: str | None = None
    purpose: str = Field(min_length=1)
    security_notes: str | None = None


class FeatureChangeRequest(BaseModel):
    """Typed payload for feature change requests."""

    requested_change: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    impact_assessment: dict[str, Any] = Field(default_factory=dict)


class AgentDecision(BaseModel):
    """Decision payload used when resolving an agent message."""

    status: AgentDecisionStatus
    rationale: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResolveAgentMessageRequest(BaseModel):
    """Request body for manually resolving an agent message."""

    decision: AgentDecision


class CreateJobRequest(BaseModel):
    """Request body for creating a new job."""

    idea: str = Field(min_length=1)
    approval_required: bool = False
    label: str | None = None
    reasoning: JobReasoningLaunchOptions | None = None


class ApproveJobRequest(BaseModel):
    """Request body for resolving an approval decision."""

    stage: str
    edited_data: dict[str, Any] | None = None


class JobSummary(BaseModel):
    """Summary view of a job."""

    id: str
    idea: str
    status: JobStatus
    approval_required: bool
    created_at: float
    started_at: float | None = None
    finished_at: float | None = None
    stopped_at: float | None = None
    error_message: str | None = None
    progress_percent: float = 0.0
    current_stage: str | None = None
    label: str | None = None


class JobDetail(JobSummary):
    """Detailed view of a job."""

    queue_position: int | None = None


class JobEventDTO(BaseModel):
    """Persisted event record."""

    id: int
    job_id: str
    event_type: str
    stage: str | None = None
    payload_json: dict[str, Any] = Field(default_factory=dict)
    created_at: float


class JobLogDTO(BaseModel):
    """Persisted log record."""

    id: int
    job_id: str
    level: str
    source: str
    message: str
    meta_json: dict[str, Any] = Field(default_factory=dict)
    created_at: float


class JobArtifactDTO(BaseModel):
    """Persisted artifact record."""

    id: int
    job_id: str
    artifact_type: str
    artifact_key: str | None = None
    content_text: str
    created_at: float


class JobDecisionDTO(BaseModel):
    """Persisted decision record."""

    id: int
    job_id: str
    stage: str
    decision_type: str
    required: bool
    status: str
    prompt_json: dict[str, Any] = Field(default_factory=dict)
    response_json: dict[str, Any] = Field(default_factory=dict)
    created_at: float
    resolved_at: float | None = None


class ChatCommandRequest(BaseModel):
    """Chat command request payload."""

    message: str = Field(min_length=1)
    active_job_id: str | None = None


class ChatCommandResponse(BaseModel):
    """Normalized command handling response."""

    action: str
    ok: bool
    ui_message: str
    target_job_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class ParsedCommand(BaseModel):
    """Internal parsed command representation."""

    action: str
    args: dict[str, Any] = Field(default_factory=dict)
    ok: bool = True
    error: str | None = None


class CompactionPriorityWeights(BaseModel):
    """Priority weights used by context compaction scoring."""

    coding_context: int = Field(default=40, ge=0, le=100)
    user_intent: int = Field(default=30, ge=0, le=100)
    timeline_continuity: int = Field(default=20, ge=0, le=100)
    open_risks: int = Field(default=10, ge=0, le=100)


class ContextCompactionConfig(BaseModel):
    """Config controlling context window tracking and auto-compaction."""

    context_limit_tk: int = Field(default=128, ge=1)
    trigger_fill_percent: int = Field(default=90, ge=1, le=99)
    target_fill_percent: int = Field(default=40, ge=1, le=98)
    min_messages_to_compact: int = Field(default=8, ge=1)
    cooldown_calls: int = Field(default=2, ge=0)
    priority_weights: CompactionPriorityWeights = Field(default_factory=CompactionPriorityWeights)

    @model_validator(mode="after")
    def _validate_thresholds(self) -> "ContextCompactionConfig":
        if self.target_fill_percent >= self.trigger_fill_percent:
            raise ValueError("target_fill_percent must be lower than trigger_fill_percent")
        return self


class JobContextConfig(BaseModel):
    """Job-scoped context config with optional override."""

    job_id: str = Field(min_length=1)
    use_global_defaults: bool = True
    override: ContextCompactionConfig | None = None


class ContextUsageSnapshot(BaseModel):
    """Current usage snapshot for a job's effective context window."""

    job_id: str = Field(min_length=1)
    estimated_tokens: int = Field(ge=0)
    limit_tokens: int = Field(ge=1)
    fill_percent: float = Field(ge=0.0)
    last_compacted_at: float | None = None
    compaction_count: int = Field(default=0, ge=0)
    last_summary_text: str | None = None
    last_compaction_before_percent: float | None = None
    last_compaction_after_percent: float | None = None
