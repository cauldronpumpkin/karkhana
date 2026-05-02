from __future__ import annotations

import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _dt(value: datetime | str | None) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def _iso(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()


def _clean_for_dynamo(value: Any) -> Any:
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _clean_for_dynamo(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_clean_for_dynamo(v) for v in value]
    return value


def _clean_from_dynamo(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: _clean_from_dynamo(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean_from_dynamo(v) for v in value]
    return value


LEDGER_POLICIES = frozenset({"none", "read_only", "required", "strict"})


def _validate_ledger_fields(ledger_policy: str | None, ledger_path: str | None) -> tuple[str, str | None]:
    policy = (ledger_policy or "none").strip().lower()
    if policy not in LEDGER_POLICIES:
        raise ValueError(f"Invalid ledger_policy: {ledger_policy}")

    path = ledger_path.strip() if isinstance(ledger_path, str) else ledger_path
    if path == "":
        path = None
    if policy != "none" and not path:
        raise ValueError("ledger_path is required when ledger_policy is not 'none'")
    if path:
        normalized = path.replace("\\", "/")
        if normalized.startswith("/") or normalized.startswith("~") or ":" in normalized.split("/", 1)[0]:
            raise ValueError("ledger_path must be a relative path")
        if any(part == ".." for part in normalized.split("/")):
            raise ValueError("ledger_path must not contain traversal segments")
    return policy, path


@dataclass
class Idea:
    title: str
    slug: str
    description: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    current_phase: str = "capture"
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    status: str = "active"
    source_type: str = "manual"


@dataclass
class Score:
    idea_id: str
    dimension: str
    value: float
    rationale: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    scored_at: datetime = field(default_factory=utcnow)


@dataclass
class Message:
    idea_id: str
    role: str
    content: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=utcnow)
    metadata_: dict | None = None


@dataclass
class ProjectMemory:
    key: str
    value: str
    category: str
    idea_id: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class PhaseRecord:
    idea_id: str
    phase: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = field(default_factory=utcnow)
    completed_at: datetime | None = None
    notes: dict | None = None


@dataclass
class ResearchTask:
    idea_id: str
    prompt_text: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "pending"
    result_file_path: str | None = None
    result_content: str | None = None
    topic: str | None = None
    created_at: datetime = field(default_factory=utcnow)
    completed_at: datetime | None = None


@dataclass
class ArtifactMetadata:
    source: str
    source_uri: str | None = None
    actor: str | None = None
    correlation_id: str | None = None
    dedupe_hash: str | None = None
    tags: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class Intent:
    idea_id: str
    project_id: str
    summary: str
    details: dict = field(default_factory=dict)
    correlation_id: str | None = None
    dedupe_hash: str | None = None
    budget: dict = field(default_factory=dict)
    stop_conditions: list[str] = field(default_factory=list)
    factory_run_ids: list[str] = field(default_factory=list)
    source: str = "manual"
    status: str = "active"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class Report:
    idea_id: str
    phase: str
    title: str
    content: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content_path: str = ""
    generated_at: datetime = field(default_factory=utcnow)


@dataclass
class IdeaRelationship:
    source_idea_id: str
    target_idea_id: str
    relation_type: str
    description: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class GitHubInstallation:
    installation_id: str
    account_login: str
    account_type: str = "User"
    status: str = "active"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class ProjectTwin:
    idea_id: str
    provider: str
    installation_id: str
    owner: str
    repo: str
    repo_full_name: str
    repo_url: str
    clone_url: str
    default_branch: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    active_branch: str | None = None
    deploy_url: str | None = None
    desired_outcome: str | None = None
    current_status: str | None = None
    detected_stack: list[str] = field(default_factory=list)
    test_commands: list[str] = field(default_factory=list)
    last_indexed_commit: str | None = None
    index_status: str = "not_indexed"
    health_status: str = "unknown"
    open_queue_count: int = 0
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class CodeIndexArtifact:
    project_id: str
    idea_id: str
    commit_sha: str
    file_inventory: list[dict] = field(default_factory=list)
    manifests: list[dict] = field(default_factory=list)
    dependency_graph: dict = field(default_factory=dict)
    route_map: list[dict] = field(default_factory=list)
    test_commands: list[str] = field(default_factory=list)
    architecture_summary: str = ""
    risks: list[str] = field(default_factory=list)
    todos: list[str] = field(default_factory=list)
    searchable_chunks: list[dict] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class ResearchArtifact:
    factory_run_id: str
    title: str
    source: str
    raw_content: str | None = None
    raw_content_uri: str | None = None
    raw_metadata: dict = field(default_factory=dict)
    normalized: dict = field(default_factory=dict)
    artifact_metadata: ArtifactMetadata = field(default_factory=lambda: ArtifactMetadata(source="research"))
    dedupe_hash: str = ""
    status: str = "active"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class WorkItem:
    idea_id: str
    project_id: str
    job_type: str
    payload: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "queued"
    priority: int = 50
    factory_run_id: str | None = None
    parent_work_item_id: str | None = None
    rationale: str | None = None
    correlation_id: str | None = None
    dedupe_hash: str | None = None
    budget: dict = field(default_factory=dict)
    stop_conditions: list[str] = field(default_factory=list)
    idempotency_key: str | None = None
    worker_id: str | None = None
    claim_token: str | None = None
    claimed_at: datetime | None = None
    heartbeat_at: datetime | None = None
    run_after: datetime | None = None
    retry_count: int = 0
    timeout_seconds: int = 900
    logs: str = ""
    logs_pointer: str | None = None
    result: dict | None = None
    error: str | None = None
    branch_name: str | None = None
    agent_run_id: str | None = None
    ledger_policy: str = "none"
    ledger_path: str | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        self.ledger_policy, self.ledger_path = _validate_ledger_fields(self.ledger_policy, self.ledger_path)


@dataclass
class AgentRun:
    work_item_id: str
    idea_id: str
    project_id: str
    engine: str
    agent_name: str | None = None
    model: str | None = None
    command: str | None = None
    branch_name: str | None = None
    status: str = "running"
    prompt: str = ""
    output: str = ""
    started_at: datetime = field(default_factory=utcnow)
    completed_at: datetime | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class ProjectCommit:
    idea_id: str
    project_id: str
    work_item_id: str
    branch_name: str
    commit_sha: str
    message: str
    author: str | None = None
    status: str = "pushed"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class LocalWorker:
    display_name: str
    machine_name: str
    platform: str
    engine: str = "opencode"
    status: str = "approved"
    capabilities: list[str] = field(default_factory=list)
    config: dict = field(default_factory=dict)
    api_token_hash: str | None = None
    last_seen_at: datetime | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class WorkerConnectionRequest:
    display_name: str
    machine_name: str
    platform: str
    engine: str = "opencode"
    capabilities: list[str] = field(default_factory=list)
    requested_config: dict = field(default_factory=dict)
    status: str = "pending"
    worker_id: str | None = None
    tenant_id: str | None = None
    decision_reason: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class WorkerCredentialLease:
    worker_id: str
    api_token_hash: str
    access_key_id: str
    secret_access_key: str
    session_token: str
    expires_at: datetime
    command_queue_url: str = ""
    event_queue_url: str = ""
    region: str = "us-east-1"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class WorkerEvent:
    worker_id: str
    event_type: str
    payload: dict = field(default_factory=dict)
    work_item_id: str | None = None
    factory_run_id: str | None = None
    research_artifact_id: str | None = None
    review_packet_id: str | None = None
    correlation_id: str | None = None
    idempotency_key: str | None = None
    actor: str | None = None
    status: str = "received"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class TemplateArtifact:
    template_id: str
    artifact_key: str
    content_type: str
    uri: str
    content: str = ""
    version: str = "1.0.0"
    compatibility: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata_: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class TemplatePack:
    template_id: str
    version: str
    channel: str
    display_name: str
    description: str
    phases: list[dict] = field(default_factory=list)
    quality_gates: list[dict] = field(default_factory=list)
    default_stack: dict = field(default_factory=dict)
    constraints: list[dict] = field(default_factory=list)
    opencode_worker: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class TemplateManifest:
    template_id: str
    version: str
    artifact_keys: list[str] = field(default_factory=list)
    metadata_: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class TemplateMemory:
    template_id: str
    key: str
    value: str
    category: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class TemplateUpdateProposal:
    template_id: str
    proposed_by: str
    change_type: str
    description: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    payload_uri: str | None = None
    status: str = "pending"
    created_at: datetime = field(default_factory=utcnow)
    reviewed_at: datetime | None = None


@dataclass
class FactoryRunTrackingManifest:
    factory_run_id: str
    idea_id: str
    template_id: str
    template_version: str
    run_config: dict = field(default_factory=dict)
    run_status: str = "queued"
    phase_summary: list[dict] = field(default_factory=list)
    batch_summary: list[dict] = field(default_factory=list)
    verification_summary: list[dict] = field(default_factory=list)
    last_indexed_commit: str | None = None
    graphify_status: str = "pending"
    worker_queue_state: dict = field(default_factory=dict)
    verification_state: dict = field(default_factory=dict)
    artifact_uris: dict = field(default_factory=dict)
    token_economy_totals: dict = field(default_factory=dict)
    duplicate_work_count: int = 0
    snapshot_uri: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    completed_at: datetime | None = None


@dataclass
class FactoryRun:
    idea_id: str
    template_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "queued"
    config: dict = field(default_factory=dict)
    intent_id: str | None = None
    run_type: str = "standard"
    correlation_id: str | None = None
    dedupe_hash: str | None = None
    budget: dict = field(default_factory=dict)
    stop_conditions: list[str] = field(default_factory=list)
    tracking_manifest_uri: str | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    completed_at: datetime | None = None


@dataclass
class FactoryPhase:
    factory_run_id: str
    phase_key: str
    phase_order: int
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "pending"
    config_override: dict = field(default_factory=dict)
    output_uri: str | None = None
    created_at: datetime = field(default_factory=utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class FactoryBatch:
    factory_phase_id: str
    factory_run_id: str
    batch_key: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "pending"
    worker_id: str | None = None
    work_item_id: str | None = None
    input_uri: str | None = None
    output_uri: str | None = None
    created_at: datetime = field(default_factory=utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass
class VerificationRun:
    factory_batch_id: str
    factory_run_id: str
    verification_type: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "pending"
    result_uri: str | None = None
    result_summary: str = ""
    failure_classification: str = ""
    command_output: str = ""
    changed_files: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=utcnow)
    completed_at: datetime | None = None


WAIT_WINDOW_STATES = frozenset({
    "awaiting_review",
    "wait_window",
    "no_objection_recorded",
    "ready_to_continue",
    "approved",
    "rejected",
    "modification_requested",
    "paused",
})

IMPACT_SCORES = frozenset({"low", "medium", "high"})


@dataclass
class ReviewPacket:
    run_id: str
    promise: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    packet_type: str = "standard"
    status: str = "awaiting_review"
    wait_window_state: str = "awaiting_review"
    branch_name: str | None = None
    worker_id: str | None = None
    worker_display_name: str | None = None
    worker_machine_name: str | None = None
    autonomy_level: str | None = None
    template_id: str | None = None
    template_version: str | None = None
    blast_radius: dict = field(default_factory=dict)
    safety_net_results: dict = field(default_factory=dict)
    execution_trace: dict = field(default_factory=dict)
    changed_files: list[str] = field(default_factory=list)
    diff_summary_uri: str | None = None
    evaluator_verdict: dict = field(default_factory=dict)
    decision_gates: dict = field(default_factory=dict)
    allowed_actions: list[str] = field(default_factory=list)
    research_artifact_ids: list[str] = field(default_factory=list)
    research_handoff: dict = field(default_factory=dict)
    expert_reviews: list[dict] = field(default_factory=list)
    council_summary: dict = field(default_factory=dict)
    telemetry_events: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=utcnow)
    wait_window_started_at: datetime | None = None
    expires_at: datetime | None = None
    resolved_at: datetime | None = None
    updated_at: datetime = field(default_factory=utcnow)


FAILURE_CLASSIFICATIONS = frozenset({
    "test", "build", "lint", "type", "migration",
    "runtime", "integration", "dependency", "flaky",
    "ambiguous", "security",
})

SECURITY_FAILURE = "security"
BLOCKED_STATUS = "blocked"

AUTONOMY_SUGGEST_ONLY = "suggest_only"
AUTONOMY_AUTONOMOUS_DEVELOPMENT = "autonomous_development"
AUTONOMY_FULL_AUTOPILOT = "full_autopilot"
AUTONOMY_LEVELS = frozenset({
    AUTONOMY_SUGGEST_ONLY,
    AUTONOMY_AUTONOMOUS_DEVELOPMENT,
    AUTONOMY_FULL_AUTOPILOT,
})


@dataclass
class RepairTask:
    factory_run_id: str
    factory_batch_id: str
    failure_classification: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "pending"
    attempt_number: int = 1
    command_output: str = ""
    recent_diff: str = ""
    changed_files: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    guardrails: list[str] = field(default_factory=list)
    issue_summary: str = ""
    work_item_id: str | None = None
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    completed_at: datetime | None = None


class Repository:
    async def create_idea(self, idea: Idea) -> Idea: ...
    async def get_idea(self, idea_id: str) -> Idea | None: ...
    async def list_active_ideas(self) -> list[Idea]: ...
    async def save_idea(self, idea: Idea) -> Idea: ...
    async def list_scores(self, idea_id: str) -> list[Score]: ...
    async def put_score(self, score: Score) -> Score: ...
    async def delete_score(self, idea_id: str, dimension: str) -> None: ...
    async def add_message(self, message: Message) -> Message: ...
    async def list_messages(self, idea_id: str) -> list[Message]: ...
    async def upsert_memory(self, memory: ProjectMemory) -> ProjectMemory: ...
    async def get_memory(self, key: str, idea_id: str | None = None) -> ProjectMemory | None: ...
    async def list_memories(self, idea_id: str | None = None, category: str | None = None) -> list[ProjectMemory]: ...
    async def delete_memory(self, key: str, idea_id: str | None = None) -> bool: ...
    async def add_phase_record(self, record: PhaseRecord) -> PhaseRecord: ...
    async def add_research_task(self, task: ResearchTask) -> ResearchTask: ...
    async def get_research_task(self, idea_id: str, task_id: str) -> ResearchTask | None: ...
    async def save_research_task(self, task: ResearchTask) -> ResearchTask: ...
    async def list_research_tasks(self, idea_id: str, statuses: set[str] | None = None) -> list[ResearchTask]: ...
    async def put_report(self, report: Report) -> Report: ...
    async def get_report(self, idea_id: str, phase: str) -> Report | None: ...
    async def list_reports(self, idea_id: str) -> list[Report]: ...
    async def add_relationship(self, relationship: IdeaRelationship) -> IdeaRelationship: ...
    async def list_relationships(self, idea_id: str) -> list[IdeaRelationship]: ...
    async def save_github_installation(self, installation: GitHubInstallation) -> GitHubInstallation: ...
    async def list_github_installations(self) -> list[GitHubInstallation]: ...
    async def get_github_installation(self, installation_id: str) -> GitHubInstallation | None: ...
    async def save_intent(self, intent: Intent) -> Intent: ...
    async def get_intent(self, idea_id: str, intent_id: str) -> Intent | None: ...
    async def list_intents(self, idea_id: str | None = None, project_id: str | None = None) -> list[Intent]: ...
    async def save_project_twin(self, project: ProjectTwin) -> ProjectTwin: ...
    async def get_project_twin(self, idea_id: str) -> ProjectTwin | None: ...
    async def get_project_twin_by_id(self, project_id: str) -> ProjectTwin | None: ...
    async def list_project_twins(self) -> list[ProjectTwin]: ...
    async def put_code_index(self, artifact: CodeIndexArtifact) -> CodeIndexArtifact: ...
    async def get_latest_code_index(self, idea_id: str) -> CodeIndexArtifact | None: ...
    async def save_research_artifact(self, artifact: ResearchArtifact) -> ResearchArtifact: ...
    async def get_research_artifact(self, factory_run_id: str, artifact_id: str) -> ResearchArtifact | None: ...
    async def list_research_artifacts(self, factory_run_id: str, statuses: set[str] | None = None) -> list[ResearchArtifact]: ...
    async def enqueue_work_item(self, item: WorkItem) -> WorkItem: ...
    async def save_work_item(self, item: WorkItem) -> WorkItem: ...
    async def get_work_item(self, item_id: str) -> WorkItem | None: ...
    async def list_work_items(self, idea_id: str | None = None, statuses: set[str] | None = None) -> list[WorkItem]: ...
    async def add_agent_run(self, run: AgentRun) -> AgentRun: ...
    async def save_agent_run(self, run: AgentRun) -> AgentRun: ...
    async def list_agent_runs(self, idea_id: str) -> list[AgentRun]: ...
    async def add_project_commit(self, commit: ProjectCommit) -> ProjectCommit: ...
    async def list_project_commits(self, idea_id: str) -> list[ProjectCommit]: ...
    async def save_local_worker(self, worker: LocalWorker) -> LocalWorker: ...
    async def get_local_worker(self, worker_id: str) -> LocalWorker | None: ...
    async def list_local_workers(self) -> list[LocalWorker]: ...
    async def delete_local_worker(self, worker_id: str) -> None: ...
    async def save_worker_connection_request(self, request: WorkerConnectionRequest) -> WorkerConnectionRequest: ...
    async def get_worker_connection_request(self, request_id: str) -> WorkerConnectionRequest | None: ...
    async def list_worker_connection_requests(self) -> list[WorkerConnectionRequest]: ...
    async def save_worker_credential_lease(self, lease: WorkerCredentialLease) -> WorkerCredentialLease: ...
    async def get_worker_credential_lease(self, worker_id: str) -> WorkerCredentialLease | None: ...
    async def add_worker_event(self, event: WorkerEvent) -> WorkerEvent: ...
    async def list_worker_events(self, worker_id: str | None = None) -> list[WorkerEvent]: ...
    async def save_template_pack(self, pack: TemplatePack) -> TemplatePack: ...
    async def get_template_pack(self, template_id: str) -> TemplatePack | None: ...
    async def list_template_packs(self) -> list[TemplatePack]: ...
    async def save_template_artifact(self, artifact: TemplateArtifact) -> TemplateArtifact: ...
    async def get_template_artifact(self, template_id: str, artifact_key: str) -> TemplateArtifact | None: ...
    async def list_template_artifacts(self, template_id: str) -> list[TemplateArtifact]: ...
    async def save_template_manifest(self, manifest: TemplateManifest) -> TemplateManifest: ...
    async def get_template_manifest(self, template_id: str, version: str) -> TemplateManifest | None: ...
    async def list_template_manifests(self, template_id: str) -> list[TemplateManifest]: ...
    async def upsert_template_memory(self, memory: TemplateMemory) -> TemplateMemory: ...
    async def get_template_memory(self, template_id: str, key: str) -> TemplateMemory | None: ...
    async def list_template_memories(self, template_id: str, category: str | None = None) -> list[TemplateMemory]: ...
    async def delete_template_memory(self, template_id: str, key: str) -> bool: ...
    async def save_template_update_proposal(self, proposal: TemplateUpdateProposal) -> TemplateUpdateProposal: ...
    async def get_template_update_proposal(self, template_id: str, proposal_id: str) -> TemplateUpdateProposal | None: ...
    async def list_template_update_proposals(self, template_id: str, status: str | None = None) -> list[TemplateUpdateProposal]: ...
    async def save_factory_run_tracking_manifest(self, manifest: FactoryRunTrackingManifest) -> FactoryRunTrackingManifest: ...
    async def get_factory_run_tracking_manifest(self, run_id: str) -> FactoryRunTrackingManifest | None: ...
    async def create_factory_run(self, run: FactoryRun) -> FactoryRun: ...
    async def save_factory_run(self, run: FactoryRun) -> FactoryRun: ...
    async def get_factory_run(self, run_id: str) -> FactoryRun | None: ...
    async def list_factory_runs(self, idea_id: str | None = None, template_id: str | None = None, intent_id: str | None = None, statuses: set[str] | None = None) -> list[FactoryRun]: ...
    async def save_factory_phase(self, phase: FactoryPhase) -> FactoryPhase: ...
    async def get_factory_phase(self, run_id: str, phase_id: str) -> FactoryPhase | None: ...
    async def list_factory_phases(self, run_id: str) -> list[FactoryPhase]: ...
    async def save_factory_batch(self, batch: FactoryBatch) -> FactoryBatch: ...
    async def get_factory_batch(self, batch_id: str) -> FactoryBatch | None: ...
    async def list_factory_batches(self, phase_id: str) -> list[FactoryBatch]: ...
    async def save_verification_run(self, run: VerificationRun) -> VerificationRun: ...
    async def get_verification_run(self, run_id: str) -> VerificationRun | None: ...
    async def list_verification_runs(self, batch_id: str) -> list[VerificationRun]: ...
    async def save_repair_task(self, task: RepairTask) -> RepairTask: ...
    async def get_repair_task(self, task_id: str) -> RepairTask | None: ...
    async def list_repair_tasks(self, factory_run_id: str, statuses: set[str] | None = None) -> list[RepairTask]: ...
    async def list_repair_tasks_for_batch(self, factory_batch_id: str) -> list[RepairTask]: ...
    async def save_review_packet(self, packet: ReviewPacket) -> ReviewPacket: ...
    async def get_review_packet(self, run_id: str) -> ReviewPacket | None: ...
    async def get_review_packet_by_id(self, packet_id: str) -> ReviewPacket | None: ...
    async def list_review_packets(self, wait_window_states: set[str] | None = None, statuses: set[str] | None = None) -> list[ReviewPacket]: ...


class InMemoryRepository(Repository):
    def __init__(self) -> None:
        self.ideas: dict[str, Idea] = {}
        self.scores: dict[tuple[str, str], Score] = {}
        self.messages: dict[str, list[Message]] = {}
        self.memories: dict[tuple[str | None, str], ProjectMemory] = {}
        self.phase_records: list[PhaseRecord] = []
        self.research: dict[tuple[str, str], ResearchTask] = {}
        self.reports: dict[tuple[str, str], Report] = {}
        self.relationships: list[IdeaRelationship] = []
        self.github_installations: dict[str, GitHubInstallation] = {}
        self.intents: dict[tuple[str, str], Intent] = {}
        self.intents_by_project: dict[tuple[str, str], Intent] = {}
        self.project_twins: dict[str, ProjectTwin] = {}
        self.code_indexes: dict[str, list[CodeIndexArtifact]] = {}
        self.research_artifacts: dict[tuple[str, str], ResearchArtifact] = {}
        self.work_items: dict[str, WorkItem] = {}
        self.agent_runs: dict[str, AgentRun] = {}
        self.project_commits: dict[str, ProjectCommit] = {}
        self.local_workers: dict[str, LocalWorker] = {}
        self.worker_requests: dict[str, WorkerConnectionRequest] = {}
        self.worker_leases: dict[str, WorkerCredentialLease] = {}
        self.worker_events: dict[str, WorkerEvent] = {}
        self.template_packs: dict[str, TemplatePack] = {}
        self.template_artifacts: dict[tuple[str, str], TemplateArtifact] = {}
        self.template_manifests: dict[tuple[str, str], TemplateManifest] = {}
        self.template_memories: dict[tuple[str, str], TemplateMemory] = {}
        self.template_update_proposals: dict[str, TemplateUpdateProposal] = {}
        self.factory_tracking_manifests: dict[str, FactoryRunTrackingManifest] = {}
        self.factory_runs: dict[str, FactoryRun] = {}
        self.factory_phases: dict[str, FactoryPhase] = {}
        self.factory_batches: dict[str, FactoryBatch] = {}
        self.verification_runs: dict[str, VerificationRun] = {}
        self.repair_tasks: dict[str, RepairTask] = {}
        self.review_packets_by_run: dict[str, ReviewPacket] = {}
        self.review_packets: dict[str, ReviewPacket] = {}

    async def create_idea(self, idea: Idea) -> Idea:
        self.ideas[idea.id] = idea
        return idea

    async def get_idea(self, idea_id: str) -> Idea | None:
        return self.ideas.get(idea_id)

    async def list_active_ideas(self) -> list[Idea]:
        return sorted(
            [idea for idea in self.ideas.values() if idea.status == "active"],
            key=lambda i: i.updated_at,
            reverse=True,
        )

    async def save_idea(self, idea: Idea) -> Idea:
        idea.updated_at = utcnow()
        self.ideas[idea.id] = idea
        return idea

    async def list_scores(self, idea_id: str) -> list[Score]:
        return sorted([s for (iid, _), s in self.scores.items() if iid == idea_id], key=lambda s: s.dimension)

    async def put_score(self, score: Score) -> Score:
        self.scores[(score.idea_id, score.dimension)] = score
        return score

    async def delete_score(self, idea_id: str, dimension: str) -> None:
        self.scores.pop((idea_id, dimension), None)

    async def add_message(self, message: Message) -> Message:
        self.messages.setdefault(message.idea_id, []).append(message)
        self.messages[message.idea_id].sort(key=lambda m: m.timestamp)
        return message

    async def list_messages(self, idea_id: str) -> list[Message]:
        return list(self.messages.get(idea_id, []))

    async def upsert_memory(self, memory: ProjectMemory) -> ProjectMemory:
        existing = self.memories.get((memory.idea_id, memory.key))
        if existing:
            existing.value = memory.value
            existing.category = memory.category
            existing.updated_at = utcnow()
            return existing
        self.memories[(memory.idea_id, memory.key)] = memory
        return memory

    async def get_memory(self, key: str, idea_id: str | None = None) -> ProjectMemory | None:
        return self.memories.get((idea_id, key))

    async def list_memories(self, idea_id: str | None = None, category: str | None = None) -> list[ProjectMemory]:
        memories = [m for (iid, _), m in self.memories.items() if iid == idea_id]
        if category:
            memories = [m for m in memories if m.category == category]
        return sorted(memories, key=lambda m: m.created_at)

    async def delete_memory(self, key: str, idea_id: str | None = None) -> bool:
        return self.memories.pop((idea_id, key), None) is not None

    async def add_phase_record(self, record: PhaseRecord) -> PhaseRecord:
        self.phase_records.append(record)
        return record

    async def add_research_task(self, task: ResearchTask) -> ResearchTask:
        self.research[(task.idea_id, task.id)] = task
        return task

    async def get_research_task(self, idea_id: str, task_id: str) -> ResearchTask | None:
        return self.research.get((idea_id, task_id))

    async def save_research_task(self, task: ResearchTask) -> ResearchTask:
        self.research[(task.idea_id, task.id)] = task
        return task

    async def list_research_tasks(self, idea_id: str, statuses: set[str] | None = None) -> list[ResearchTask]:
        tasks = [t for (iid, _), t in self.research.items() if iid == idea_id]
        if statuses:
            tasks = [t for t in tasks if t.status in statuses]
        return sorted(tasks, key=lambda t: t.completed_at or t.created_at, reverse="completed" in (statuses or set()))

    async def put_report(self, report: Report) -> Report:
        self.reports[(report.idea_id, report.phase)] = report
        return report

    async def get_report(self, idea_id: str, phase: str) -> Report | None:
        return self.reports.get((idea_id, phase))

    async def list_reports(self, idea_id: str) -> list[Report]:
        return [r for (iid, _), r in self.reports.items() if iid == idea_id]

    async def add_relationship(self, relationship: IdeaRelationship) -> IdeaRelationship:
        self.relationships.append(relationship)
        return relationship

    async def list_relationships(self, idea_id: str) -> list[IdeaRelationship]:
        return [
            r for r in self.relationships
            if r.source_idea_id == idea_id or r.target_idea_id == idea_id
        ]

    async def save_github_installation(self, installation: GitHubInstallation) -> GitHubInstallation:
        installation.updated_at = utcnow()
        self.github_installations[installation.installation_id] = installation
        return installation

    async def list_github_installations(self) -> list[GitHubInstallation]:
        return sorted(self.github_installations.values(), key=lambda item: item.updated_at, reverse=True)

    async def get_github_installation(self, installation_id: str) -> GitHubInstallation | None:
        return self.github_installations.get(str(installation_id))

    async def save_intent(self, intent: Intent) -> Intent:
        intent.updated_at = utcnow()
        self.intents[(intent.idea_id, intent.id)] = intent
        self.intents_by_project[(intent.project_id, intent.id)] = intent
        return intent

    async def get_intent(self, idea_id: str, intent_id: str) -> Intent | None:
        return self.intents.get((idea_id, intent_id))

    async def list_intents(self, idea_id: str | None = None, project_id: str | None = None) -> list[Intent]:
        intents = list(self.intents.values())
        if idea_id:
            intents = [intent for intent in intents if intent.idea_id == idea_id]
        if project_id:
            intents = [intent for intent in intents if intent.project_id == project_id]
        return sorted(intents, key=lambda intent: intent.created_at, reverse=True)

    async def save_project_twin(self, project: ProjectTwin) -> ProjectTwin:
        project.updated_at = utcnow()
        self.project_twins[project.idea_id] = project
        return project

    async def get_project_twin(self, idea_id: str) -> ProjectTwin | None:
        return self.project_twins.get(idea_id)

    async def get_project_twin_by_id(self, project_id: str) -> ProjectTwin | None:
        for project in self.project_twins.values():
            if project.id == project_id:
                return project
        return None

    async def list_project_twins(self) -> list[ProjectTwin]:
        return sorted(self.project_twins.values(), key=lambda item: item.updated_at, reverse=True)

    async def put_code_index(self, artifact: CodeIndexArtifact) -> CodeIndexArtifact:
        self.code_indexes.setdefault(artifact.idea_id, []).append(artifact)
        self.code_indexes[artifact.idea_id].sort(key=lambda item: item.created_at, reverse=True)
        return artifact

    async def get_latest_code_index(self, idea_id: str) -> CodeIndexArtifact | None:
        indexes = self.code_indexes.get(idea_id, [])
        return indexes[0] if indexes else None

    async def save_research_artifact(self, artifact: ResearchArtifact) -> ResearchArtifact:
        artifact.updated_at = utcnow()
        self.research_artifacts[(artifact.factory_run_id, artifact.id)] = artifact
        return artifact

    async def get_research_artifact(self, factory_run_id: str, artifact_id: str) -> ResearchArtifact | None:
        return self.research_artifacts.get((factory_run_id, artifact_id))

    async def list_research_artifacts(self, factory_run_id: str, statuses: set[str] | None = None) -> list[ResearchArtifact]:
        artifacts = [artifact for (run_id, _), artifact in self.research_artifacts.items() if run_id == factory_run_id]
        if statuses:
            artifacts = [artifact for artifact in artifacts if artifact.status in statuses]
        return sorted(artifacts, key=lambda artifact: artifact.created_at)

    async def enqueue_work_item(self, item: WorkItem) -> WorkItem:
        if item.idempotency_key:
            for existing in self.work_items.values():
                if existing.idempotency_key == item.idempotency_key and existing.status not in {"completed", "cancelled"}:
                    return existing
        if item.dedupe_hash:
            for existing in self.work_items.values():
                if existing.dedupe_hash == item.dedupe_hash and existing.status not in {"completed", "cancelled", "failed_terminal"}:
                    return existing
        self.work_items[item.id] = item
        await self._refresh_project_queue_count(item.project_id)
        return item

    async def save_work_item(self, item: WorkItem) -> WorkItem:
        item.updated_at = utcnow()
        self.work_items[item.id] = item
        await self._refresh_project_queue_count(item.project_id)
        return item

    async def get_work_item(self, item_id: str) -> WorkItem | None:
        return self.work_items.get(item_id)

    async def list_work_items(self, idea_id: str | None = None, statuses: set[str] | None = None) -> list[WorkItem]:
        items = list(self.work_items.values())
        if idea_id:
            items = [item for item in items if item.idea_id == idea_id]
        if statuses:
            items = [item for item in items if item.status in statuses]
        return sorted(items, key=lambda item: (item.priority, item.created_at))

    async def add_agent_run(self, run: AgentRun) -> AgentRun:
        self.agent_runs[run.id] = run
        return run

    async def save_agent_run(self, run: AgentRun) -> AgentRun:
        self.agent_runs[run.id] = run
        return run

    async def list_agent_runs(self, idea_id: str) -> list[AgentRun]:
        return sorted([run for run in self.agent_runs.values() if run.idea_id == idea_id], key=lambda run: run.started_at, reverse=True)

    async def add_project_commit(self, commit: ProjectCommit) -> ProjectCommit:
        self.project_commits[commit.id] = commit
        return commit

    async def list_project_commits(self, idea_id: str) -> list[ProjectCommit]:
        return sorted([commit for commit in self.project_commits.values() if commit.idea_id == idea_id], key=lambda commit: commit.created_at, reverse=True)

    async def save_local_worker(self, worker: LocalWorker) -> LocalWorker:
        worker.updated_at = utcnow()
        self.local_workers[worker.id] = worker
        return worker

    async def get_local_worker(self, worker_id: str) -> LocalWorker | None:
        return self.local_workers.get(worker_id)

    async def list_local_workers(self) -> list[LocalWorker]:
        return sorted(self.local_workers.values(), key=lambda item: item.updated_at, reverse=True)

    async def delete_local_worker(self, worker_id: str) -> None:
        self.local_workers.pop(worker_id, None)
        self.worker_leases.pop(worker_id, None)
        self.worker_events = {event_id: event for event_id, event in self.worker_events.items() if event.worker_id != worker_id}

    async def save_worker_connection_request(self, request: WorkerConnectionRequest) -> WorkerConnectionRequest:
        request.updated_at = utcnow()
        self.worker_requests[request.id] = request
        return request

    async def get_worker_connection_request(self, request_id: str) -> WorkerConnectionRequest | None:
        return self.worker_requests.get(request_id)

    async def list_worker_connection_requests(self) -> list[WorkerConnectionRequest]:
        return sorted(self.worker_requests.values(), key=lambda item: item.created_at, reverse=True)

    async def save_worker_credential_lease(self, lease: WorkerCredentialLease) -> WorkerCredentialLease:
        self.worker_leases[lease.worker_id] = lease
        return lease

    async def get_worker_credential_lease(self, worker_id: str) -> WorkerCredentialLease | None:
        return self.worker_leases.get(worker_id)

    async def add_worker_event(self, event: WorkerEvent) -> WorkerEvent:
        self.worker_events[event.id] = event
        return event

    async def list_worker_events(self, worker_id: str | None = None) -> list[WorkerEvent]:
        events = list(self.worker_events.values())
        if worker_id:
            events = [event for event in events if event.worker_id == worker_id]
        return sorted(events, key=lambda item: item.created_at)

    async def _refresh_project_queue_count(self, project_id: str) -> None:
        project = await self.get_project_twin_by_id(project_id)
        if project:
            project.open_queue_count = len([
                item for item in self.work_items.values()
                if item.project_id == project_id and item.status not in {"completed", "cancelled", "failed_terminal"}
            ])
            project.updated_at = utcnow()

    async def save_template_pack(self, pack: TemplatePack) -> TemplatePack:
        pack.updated_at = utcnow()
        self.template_packs[pack.template_id] = pack
        return pack

    async def get_template_pack(self, template_id: str) -> TemplatePack | None:
        return self.template_packs.get(template_id)

    async def list_template_packs(self) -> list[TemplatePack]:
        return sorted(self.template_packs.values(), key=lambda p: p.updated_at, reverse=True)

    async def save_template_artifact(self, artifact: TemplateArtifact) -> TemplateArtifact:
        self.template_artifacts[(artifact.template_id, artifact.artifact_key)] = artifact
        return artifact

    async def get_template_artifact(self, template_id: str, artifact_key: str) -> TemplateArtifact | None:
        return self.template_artifacts.get((template_id, artifact_key))

    async def list_template_artifacts(self, template_id: str) -> list[TemplateArtifact]:
        return [a for (tid, _), a in self.template_artifacts.items() if tid == template_id]

    async def save_template_manifest(self, manifest: TemplateManifest) -> TemplateManifest:
        self.template_manifests[(manifest.template_id, manifest.version)] = manifest
        return manifest

    async def get_template_manifest(self, template_id: str, version: str) -> TemplateManifest | None:
        return self.template_manifests.get((template_id, version))

    async def list_template_manifests(self, template_id: str) -> list[TemplateManifest]:
        return sorted(
            [m for (tid, _), m in self.template_manifests.items() if tid == template_id],
            key=lambda m: m.created_at,
            reverse=True,
        )

    async def upsert_template_memory(self, memory: TemplateMemory) -> TemplateMemory:
        existing = self.template_memories.get((memory.template_id, memory.key))
        if existing:
            existing.value = memory.value
            existing.category = memory.category
            existing.updated_at = utcnow()
            return existing
        self.template_memories[(memory.template_id, memory.key)] = memory
        return memory

    async def get_template_memory(self, template_id: str, key: str) -> TemplateMemory | None:
        return self.template_memories.get((template_id, key))

    async def list_template_memories(self, template_id: str, category: str | None = None) -> list[TemplateMemory]:
        memories = [m for (tid, _), m in self.template_memories.items() if tid == template_id]
        if category:
            memories = [m for m in memories if m.category == category]
        return sorted(memories, key=lambda m: m.created_at)

    async def delete_template_memory(self, template_id: str, key: str) -> bool:
        return self.template_memories.pop((template_id, key), None) is not None

    async def save_template_update_proposal(self, proposal: TemplateUpdateProposal) -> TemplateUpdateProposal:
        self.template_update_proposals[proposal.id] = proposal
        return proposal

    async def get_template_update_proposal(self, template_id: str, proposal_id: str) -> TemplateUpdateProposal | None:
        p = self.template_update_proposals.get(proposal_id)
        return p if p and p.template_id == template_id else None

    async def list_template_update_proposals(self, template_id: str, status: str | None = None) -> list[TemplateUpdateProposal]:
        proposals = [p for p in self.template_update_proposals.values() if p.template_id == template_id]
        if status:
            proposals = [p for p in proposals if p.status == status]
        return sorted(proposals, key=lambda p: p.created_at, reverse=True)

    async def save_factory_run_tracking_manifest(self, manifest: FactoryRunTrackingManifest) -> FactoryRunTrackingManifest:
        self.factory_tracking_manifests[manifest.factory_run_id] = manifest
        return manifest

    async def get_factory_run_tracking_manifest(self, run_id: str) -> FactoryRunTrackingManifest | None:
        return self.factory_tracking_manifests.get(run_id)

    async def create_factory_run(self, run: FactoryRun) -> FactoryRun:
        self.factory_runs[run.id] = run
        return run

    async def save_factory_run(self, run: FactoryRun) -> FactoryRun:
        run.updated_at = utcnow()
        self.factory_runs[run.id] = run
        return run

    async def get_factory_run(self, run_id: str) -> FactoryRun | None:
        return self.factory_runs.get(run_id)

    async def list_factory_runs(self, idea_id: str | None = None, template_id: str | None = None, intent_id: str | None = None, statuses: set[str] | None = None) -> list[FactoryRun]:
        runs = list(self.factory_runs.values())
        if idea_id:
            runs = [r for r in runs if r.idea_id == idea_id]
        if template_id:
            runs = [r for r in runs if r.template_id == template_id]
        if intent_id:
            runs = [r for r in runs if r.intent_id == intent_id]
        if statuses:
            runs = [r for r in runs if r.status in statuses]
        return sorted(runs, key=lambda r: r.created_at, reverse=True)

    async def save_factory_phase(self, phase: FactoryPhase) -> FactoryPhase:
        self.factory_phases[phase.id] = phase
        return phase

    async def get_factory_phase(self, run_id: str, phase_id: str) -> FactoryPhase | None:
        phase = self.factory_phases.get(phase_id)
        return phase if phase and phase.factory_run_id == run_id else None

    async def list_factory_phases(self, run_id: str) -> list[FactoryPhase]:
        return sorted(
            [p for p in self.factory_phases.values() if p.factory_run_id == run_id],
            key=lambda p: p.phase_order,
        )

    async def save_factory_batch(self, batch: FactoryBatch) -> FactoryBatch:
        self.factory_batches[batch.id] = batch
        return batch

    async def get_factory_batch(self, batch_id: str) -> FactoryBatch | None:
        return self.factory_batches.get(batch_id)

    async def list_factory_batches(self, phase_id: str) -> list[FactoryBatch]:
        return sorted(
            [b for b in self.factory_batches.values() if b.factory_phase_id == phase_id],
            key=lambda b: b.created_at,
        )

    async def save_verification_run(self, run: VerificationRun) -> VerificationRun:
        self.verification_runs[run.id] = run
        return run

    async def get_verification_run(self, run_id: str) -> VerificationRun | None:
        return self.verification_runs.get(run_id)

    async def list_verification_runs(self, batch_id: str) -> list[VerificationRun]:
        return sorted(
            [v for v in self.verification_runs.values() if v.factory_batch_id == batch_id],
            key=lambda v: v.created_at,
        )

    async def save_repair_task(self, task: RepairTask) -> RepairTask:
        task.updated_at = utcnow()
        self.repair_tasks[task.id] = task
        return task

    async def get_repair_task(self, task_id: str) -> RepairTask | None:
        return self.repair_tasks.get(task_id)

    async def list_repair_tasks(self, factory_run_id: str, statuses: set[str] | None = None) -> list[RepairTask]:
        tasks = [t for t in self.repair_tasks.values() if t.factory_run_id == factory_run_id]
        if statuses:
            tasks = [t for t in tasks if t.status in statuses]
        return sorted(tasks, key=lambda t: t.created_at)

    async def list_repair_tasks_for_batch(self, factory_batch_id: str) -> list[RepairTask]:
        return sorted(
            [t for t in self.repair_tasks.values() if t.factory_batch_id == factory_batch_id],
            key=lambda t: t.created_at,
        )

    async def save_review_packet(self, packet: ReviewPacket) -> ReviewPacket:
        packet.updated_at = utcnow()
        self.review_packets_by_run[packet.run_id] = packet
        self.review_packets[packet.id] = packet
        return packet

    async def get_review_packet(self, run_id: str) -> ReviewPacket | None:
        return self.review_packets_by_run.get(run_id)

    async def get_review_packet_by_id(self, packet_id: str) -> ReviewPacket | None:
        return self.review_packets.get(packet_id)

    async def list_review_packets(self, wait_window_states: set[str] | None = None, statuses: set[str] | None = None) -> list[ReviewPacket]:
        packets = list(self.review_packets.values())
        if wait_window_states:
            packets = [p for p in packets if p.wait_window_state in wait_window_states]
        if statuses:
            packets = [p for p in packets if p.status in statuses]
        return sorted(packets, key=lambda p: p.created_at, reverse=True)


class DynamoDBRepository(Repository):
    def __init__(self, table_name: str, region_name: str = "us-east-1") -> None:
        import boto3
        from boto3.dynamodb.conditions import Key

        self._Key = Key
        self.table_name = table_name
        self.table = boto3.resource("dynamodb", region_name=region_name).Table(table_name)

    def _put(self, item: dict[str, Any]) -> None:
        self.table.put_item(Item=_clean_for_dynamo(item))

    def _query_pk(self, pk: str, prefix: str | None = None) -> list[dict[str, Any]]:
        condition = self._Key("PK").eq(pk)
        if prefix:
            condition &= self._Key("SK").begins_with(prefix)
        items: list[dict[str, Any]] = []
        kwargs: dict[str, Any] = {"KeyConditionExpression": condition}
        while True:
            response = self.table.query(**kwargs)
            items.extend(_clean_from_dynamo(i) for i in response.get("Items", []))
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
            kwargs["ExclusiveStartKey"] = last_key
        return items

    async def create_idea(self, idea: Idea) -> Idea:
        return await self.save_idea(idea)

    async def get_idea(self, idea_id: str) -> Idea | None:
        item = self.table.get_item(Key={"PK": f"IDEA#{idea_id}", "SK": "METADATA"}).get("Item")
        return self._idea(_clean_from_dynamo(item)) if item else None

    async def list_active_ideas(self) -> list[Idea]:
        response = self.table.query(
            IndexName="GSI1",
            KeyConditionExpression=self._Key("GSI1PK").eq("IDEAS#ACTIVE"),
            ScanIndexForward=False,
        )
        return [self._idea(_clean_from_dynamo(item)) for item in response.get("Items", [])]

    async def save_idea(self, idea: Idea) -> Idea:
        item = {
            "PK": f"IDEA#{idea.id}",
            "SK": "METADATA",
            "entity": "Idea",
            **idea.__dict__,
        }
        if idea.status == "active":
            item["GSI1PK"] = "IDEAS#ACTIVE"
            item["GSI1SK"] = f"{_iso(idea.updated_at)}#{idea.id}"
        self._put(item)
        self._put({"PK": f"SLUG#{idea.slug}", "SK": "IDEA", "idea_id": idea.id, "GSI1PK": f"SLUG#{idea.slug}", "GSI1SK": idea.id})
        return idea

    async def list_scores(self, idea_id: str) -> list[Score]:
        return [self._score(i) for i in self._query_pk(f"IDEA#{idea_id}", "SCORE#")]

    async def put_score(self, score: Score) -> Score:
        self._put({"PK": f"IDEA#{score.idea_id}", "SK": f"SCORE#{score.dimension}", "entity": "Score", "GSI2PK": f"IDEA#{score.idea_id}", "GSI2SK": f"SCORE#{score.dimension}", **score.__dict__})
        return score

    async def delete_score(self, idea_id: str, dimension: str) -> None:
        self.table.delete_item(Key={"PK": f"IDEA#{idea_id}", "SK": f"SCORE#{dimension}"})

    async def add_message(self, message: Message) -> Message:
        self._put({"PK": f"IDEA#{message.idea_id}", "SK": f"MSG#{_iso(message.timestamp)}#{message.id}", "entity": "Message", "GSI2PK": f"IDEA#{message.idea_id}", "GSI2SK": f"MSG#{_iso(message.timestamp)}#{message.id}", **message.__dict__})
        return message

    async def list_messages(self, idea_id: str) -> list[Message]:
        return [self._message(i) for i in self._query_pk(f"IDEA#{idea_id}", "MSG#")]

    async def upsert_memory(self, memory: ProjectMemory) -> ProjectMemory:
        pk = f"IDEA#{memory.idea_id}" if memory.idea_id else "MEMORY#GLOBAL"
        self._put({"PK": pk, "SK": f"MEMORY#{memory.category}#{memory.key}", "entity": "ProjectMemory", "GSI2PK": pk, "GSI2SK": f"MEMORY#{memory.category}#{memory.key}", **memory.__dict__})
        return memory

    async def get_memory(self, key: str, idea_id: str | None = None) -> ProjectMemory | None:
        for memory in await self.list_memories(idea_id):
            if memory.key == key:
                return memory
        return None

    async def list_memories(self, idea_id: str | None = None, category: str | None = None) -> list[ProjectMemory]:
        pk = f"IDEA#{idea_id}" if idea_id else "MEMORY#GLOBAL"
        prefix = f"MEMORY#{category}#" if category else "MEMORY#"
        return [self._memory(i) for i in self._query_pk(pk, prefix)]

    async def delete_memory(self, key: str, idea_id: str | None = None) -> bool:
        memory = await self.get_memory(key, idea_id)
        if not memory:
            return False
        pk = f"IDEA#{idea_id}" if idea_id else "MEMORY#GLOBAL"
        self.table.delete_item(Key={"PK": pk, "SK": f"MEMORY#{memory.category}#{key}"})
        return True

    async def add_phase_record(self, record: PhaseRecord) -> PhaseRecord:
        self._put({"PK": f"IDEA#{record.idea_id}", "SK": f"PHASE#{_iso(record.completed_at or record.started_at)}#{record.phase}", "entity": "PhaseRecord", "GSI2PK": f"IDEA#{record.idea_id}", "GSI2SK": f"PHASE#{_iso(record.completed_at or record.started_at)}#{record.phase}", **record.__dict__})
        return record

    async def add_research_task(self, task: ResearchTask) -> ResearchTask:
        return await self.save_research_task(task)

    async def get_research_task(self, idea_id: str, task_id: str) -> ResearchTask | None:
        item = self.table.get_item(Key={"PK": f"IDEA#{idea_id}", "SK": f"RESEARCH_TASK#{task_id}"}).get("Item")
        return self._research(_clean_from_dynamo(item)) if item else None

    async def save_research_task(self, task: ResearchTask) -> ResearchTask:
        self._put({"PK": f"IDEA#{task.idea_id}", "SK": f"RESEARCH_TASK#{task.id}", "entity": "ResearchTask", "GSI2PK": f"IDEA#{task.idea_id}", "GSI2SK": f"RESEARCH_TASK#{_iso(task.created_at)}#{task.id}", **task.__dict__})
        return task

    async def list_research_tasks(self, idea_id: str, statuses: set[str] | None = None) -> list[ResearchTask]:
        tasks = [self._research(i) for i in self._query_pk(f"IDEA#{idea_id}", "RESEARCH_TASK#")]
        if statuses:
            tasks = [t for t in tasks if t.status in statuses]
        return sorted(tasks, key=lambda t: t.completed_at or t.created_at)

    async def put_report(self, report: Report) -> Report:
        self._put({"PK": f"IDEA#{report.idea_id}", "SK": f"REPORT#{report.phase}", "entity": "Report", "GSI2PK": f"IDEA#{report.idea_id}", "GSI2SK": f"REPORT#{report.phase}", **report.__dict__})
        return report

    async def get_report(self, idea_id: str, phase: str) -> Report | None:
        item = self.table.get_item(Key={"PK": f"IDEA#{idea_id}", "SK": f"REPORT#{phase}"}).get("Item")
        return self._report(_clean_from_dynamo(item)) if item else None

    async def list_reports(self, idea_id: str) -> list[Report]:
        return [self._report(i) for i in self._query_pk(f"IDEA#{idea_id}", "REPORT#")]

    async def add_relationship(self, relationship: IdeaRelationship) -> IdeaRelationship:
        self._put({"PK": f"IDEA#{relationship.source_idea_id}", "SK": f"REL#{relationship.id}", "entity": "IdeaRelationship", "GSI2PK": f"IDEA#{relationship.target_idea_id}", "GSI2SK": f"REL#{relationship.id}", **relationship.__dict__})
        return relationship

    async def list_relationships(self, idea_id: str) -> list[IdeaRelationship]:
        source_items = self._query_pk(f"IDEA#{idea_id}", "REL#")
        target_response = self.table.query(
            IndexName="GSI2",
            KeyConditionExpression=self._Key("GSI2PK").eq(f"IDEA#{idea_id}") & self._Key("GSI2SK").begins_with("REL#"),
        )
        items = source_items + [_clean_from_dynamo(i) for i in target_response.get("Items", [])]
        seen: set[str] = set()
        relationships = []
        for item in items:
            if item["id"] not in seen:
                seen.add(item["id"])
                relationships.append(self._relationship(item))
        return relationships

    async def save_github_installation(self, installation: GitHubInstallation) -> GitHubInstallation:
        installation.updated_at = utcnow()
        self._put({
            "PK": f"GITHUB_INSTALLATION#{installation.installation_id}",
            "SK": "METADATA",
            "entity": "GitHubInstallation",
            "GSI1PK": "GITHUB_INSTALLATIONS",
            "GSI1SK": f"{_iso(installation.updated_at)}#{installation.installation_id}",
            **installation.__dict__,
        })
        return installation

    async def save_intent(self, intent: Intent) -> Intent:
        intent.updated_at = utcnow()
        self._put({
            "PK": f"IDEA#{intent.idea_id}",
            "SK": f"INTENT#{intent.id}",
            "entity": "Intent",
            "GSI1PK": f"PROJECT#{intent.project_id}",
            "GSI1SK": f"INTENT#{_iso(intent.created_at)}#{intent.id}",
            **intent.__dict__,
        })
        self.intents[(intent.idea_id, intent.id)] = intent
        self.intents_by_project[(intent.project_id, intent.id)] = intent
        return intent

    async def get_intent(self, idea_id: str, intent_id: str) -> Intent | None:
        item = self.table.get_item(Key={"PK": f"IDEA#{idea_id}", "SK": f"INTENT#{intent_id}"}).get("Item")
        return self._intent(_clean_from_dynamo(item)) if item else None

    async def list_intents(self, idea_id: str | None = None, project_id: str | None = None) -> list[Intent]:
        if idea_id:
            raw = [self._intent(_clean_from_dynamo(item)) for item in self._query_pk(f"IDEA#{idea_id}", "INTENT#")]
        elif project_id:
            response = self.table.query(
                IndexName="GSI1",
                KeyConditionExpression=self._Key("GSI1PK").eq(f"PROJECT#{project_id}") & self._Key("GSI1SK").begins_with("INTENT#"),
                ScanIndexForward=False,
            )
            raw = [self._intent(_clean_from_dynamo(item)) for item in response.get("Items", [])]
        else:
            raw = list(self.intents.values())
        return sorted(raw, key=lambda intent: intent.created_at, reverse=True)

    async def list_github_installations(self) -> list[GitHubInstallation]:
        response = self.table.query(
            IndexName="GSI1",
            KeyConditionExpression=self._Key("GSI1PK").eq("GITHUB_INSTALLATIONS"),
            ScanIndexForward=False,
        )
        return [self._github_installation(_clean_from_dynamo(item)) for item in response.get("Items", [])]

    async def get_github_installation(self, installation_id: str) -> GitHubInstallation | None:
        item = self.table.get_item(Key={"PK": f"GITHUB_INSTALLATION#{installation_id}", "SK": "METADATA"}).get("Item")
        return self._github_installation(_clean_from_dynamo(item)) if item else None

    async def save_project_twin(self, project: ProjectTwin) -> ProjectTwin:
        project.updated_at = utcnow()
        self._put({
            "PK": f"IDEA#{project.idea_id}",
            "SK": "PROJECT_TWIN",
            "entity": "ProjectTwin",
            "GSI1PK": "PROJECT_TWINS",
            "GSI1SK": f"{_iso(project.updated_at)}#{project.id}",
            "GSI2PK": f"PROJECT#{project.id}",
            "GSI2SK": "METADATA",
            **project.__dict__,
        })
        return project

    async def get_project_twin(self, idea_id: str) -> ProjectTwin | None:
        item = self.table.get_item(Key={"PK": f"IDEA#{idea_id}", "SK": "PROJECT_TWIN"}).get("Item")
        return self._project_twin(_clean_from_dynamo(item)) if item else None

    async def get_project_twin_by_id(self, project_id: str) -> ProjectTwin | None:
        response = self.table.query(
            IndexName="GSI2",
            KeyConditionExpression=self._Key("GSI2PK").eq(f"PROJECT#{project_id}") & self._Key("GSI2SK").eq("METADATA"),
            Limit=1,
        )
        items = response.get("Items", [])
        return self._project_twin(_clean_from_dynamo(items[0])) if items else None

    async def list_project_twins(self) -> list[ProjectTwin]:
        response = self.table.query(
            IndexName="GSI1",
            KeyConditionExpression=self._Key("GSI1PK").eq("PROJECT_TWINS"),
            ScanIndexForward=False,
        )
        return [self._project_twin(_clean_from_dynamo(item)) for item in response.get("Items", [])]

    async def put_code_index(self, artifact: CodeIndexArtifact) -> CodeIndexArtifact:
        self._put({
            "PK": f"IDEA#{artifact.idea_id}",
            "SK": f"CODE_INDEX#{_iso(artifact.created_at)}#{artifact.id}",
            "entity": "CodeIndexArtifact",
            "GSI2PK": f"PROJECT#{artifact.project_id}",
            "GSI2SK": f"CODE_INDEX#{_iso(artifact.created_at)}#{artifact.id}",
            **artifact.__dict__,
        })
        return artifact

    async def get_latest_code_index(self, idea_id: str) -> CodeIndexArtifact | None:
        items = self._query_pk(f"IDEA#{idea_id}", "CODE_INDEX#")
        if not items:
            return None
        return self._code_index(sorted(items, key=lambda item: item["created_at"], reverse=True)[0])

    async def save_research_artifact(self, artifact: ResearchArtifact) -> ResearchArtifact:
        artifact.updated_at = utcnow()
        self._put({
            "PK": f"FACTORY_RUN#{artifact.factory_run_id}",
            "SK": f"RESEARCH_ARTIFACT#{artifact.id}",
            "entity": "ResearchArtifact",
            "GSI1PK": "RESEARCH_ARTIFACTS",
            "GSI1SK": f"{_iso(artifact.created_at)}#{artifact.factory_run_id}#{artifact.id}",
            **asdict(artifact),
        })
        self.research_artifacts[(artifact.factory_run_id, artifact.id)] = artifact
        return artifact

    async def get_research_artifact(self, factory_run_id: str, artifact_id: str) -> ResearchArtifact | None:
        item = self.table.get_item(Key={"PK": f"FACTORY_RUN#{factory_run_id}", "SK": f"RESEARCH_ARTIFACT#{artifact_id}"}).get("Item")
        return self._research_artifact(_clean_from_dynamo(item)) if item else None

    async def list_research_artifacts(self, factory_run_id: str, statuses: set[str] | None = None) -> list[ResearchArtifact]:
        artifacts = [self._research_artifact(item) for item in self._query_pk(f"FACTORY_RUN#{factory_run_id}", "RESEARCH_ARTIFACT#")]
        if statuses:
            artifacts = [artifact for artifact in artifacts if artifact.status in statuses]
        return sorted(artifacts, key=lambda artifact: artifact.created_at)

    async def enqueue_work_item(self, item: WorkItem) -> WorkItem:
        if item.idempotency_key:
            for existing in await self.list_work_items(statuses={"queued", "claimed", "running", "waiting_for_machine", "failed_retryable"}):
                if existing.idempotency_key == item.idempotency_key:
                    return existing
        if item.dedupe_hash:
            for existing in await self.list_work_items(statuses={"queued", "claimed", "running", "waiting_for_machine", "failed_retryable"}):
                if existing.dedupe_hash == item.dedupe_hash:
                    return existing
        await self.save_work_item(item)
        return item

    async def save_work_item(self, item: WorkItem) -> WorkItem:
        item.updated_at = utcnow()
        self._put({
            "PK": f"JOB#{item.id}",
            "SK": "METADATA",
            "entity": "WorkItem",
            "GSI1PK": "WORK_ITEMS",
            "GSI1SK": f"{item.status}#{item.priority:03d}#{_iso(item.created_at)}#{item.id}",
            "GSI2PK": f"IDEA#{item.idea_id}",
            "GSI2SK": f"JOB#{_iso(item.created_at)}#{item.id}",
            **item.__dict__,
        })
        project = await self.get_project_twin_by_id(item.project_id)
        if project:
            project.open_queue_count = len([
                job for job in await self.list_work_items(project.idea_id)
                if job.status not in {"completed", "cancelled", "failed_terminal"}
            ])
            await self.save_project_twin(project)
        return item

    async def get_work_item(self, item_id: str) -> WorkItem | None:
        item = self.table.get_item(Key={"PK": f"JOB#{item_id}", "SK": "METADATA"}).get("Item")
        return self._work_item(_clean_from_dynamo(item)) if item else None

    async def list_work_items(self, idea_id: str | None = None, statuses: set[str] | None = None) -> list[WorkItem]:
        if idea_id:
            kwargs: dict[str, Any] = {
                "IndexName": "GSI2",
                "KeyConditionExpression": self._Key("GSI2PK").eq(f"IDEA#{idea_id}") & self._Key("GSI2SK").begins_with("JOB#"),
            }
        else:
            kwargs = {
                "IndexName": "GSI1",
                "KeyConditionExpression": self._Key("GSI1PK").eq("WORK_ITEMS"),
            }
        raw: list[dict[str, Any]] = []
        while True:
            response = self.table.query(**kwargs)
            raw.extend(_clean_from_dynamo(item) for item in response.get("Items", []))
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
            kwargs["ExclusiveStartKey"] = last_key
        jobs = [self._work_item(item) for item in raw if not statuses or item.get("status") in statuses]
        return sorted(jobs, key=lambda item: (item.priority, item.created_at))

    async def add_agent_run(self, run: AgentRun) -> AgentRun:
        return await self.save_agent_run(run)

    async def save_agent_run(self, run: AgentRun) -> AgentRun:
        self._put({
            "PK": f"IDEA#{run.idea_id}",
            "SK": f"AGENT_RUN#{_iso(run.started_at)}#{run.id}",
            "entity": "AgentRun",
            "GSI2PK": f"JOB#{run.work_item_id}",
            "GSI2SK": f"AGENT_RUN#{run.id}",
            **run.__dict__,
        })
        return run

    async def list_agent_runs(self, idea_id: str) -> list[AgentRun]:
        return [self._agent_run(item) for item in self._query_pk(f"IDEA#{idea_id}", "AGENT_RUN#")]

    async def add_project_commit(self, commit: ProjectCommit) -> ProjectCommit:
        self._put({
            "PK": f"IDEA#{commit.idea_id}",
            "SK": f"COMMIT#{_iso(commit.created_at)}#{commit.id}",
            "entity": "ProjectCommit",
            "GSI2PK": f"PROJECT#{commit.project_id}",
            "GSI2SK": f"COMMIT#{_iso(commit.created_at)}#{commit.id}",
            **commit.__dict__,
        })
        return commit

    async def list_project_commits(self, idea_id: str) -> list[ProjectCommit]:
        return [self._project_commit(item) for item in self._query_pk(f"IDEA#{idea_id}", "COMMIT#")]

    async def save_local_worker(self, worker: LocalWorker) -> LocalWorker:
        worker.updated_at = utcnow()
        self._put({
            "PK": f"LOCAL_WORKER#{worker.id}",
            "SK": "METADATA",
            "entity": "LocalWorker",
            "GSI1PK": "LOCAL_WORKERS",
            "GSI1SK": f"{worker.status}#{_iso(worker.updated_at)}#{worker.id}",
            **worker.__dict__,
        })
        return worker

    async def get_local_worker(self, worker_id: str) -> LocalWorker | None:
        item = self.table.get_item(Key={"PK": f"LOCAL_WORKER#{worker_id}", "SK": "METADATA"}).get("Item")
        return self._local_worker(_clean_from_dynamo(item)) if item else None

    async def list_local_workers(self) -> list[LocalWorker]:
        response = self.table.query(
            IndexName="GSI1",
            KeyConditionExpression=self._Key("GSI1PK").eq("LOCAL_WORKERS"),
        )
        return [self._local_worker(_clean_from_dynamo(item)) for item in response.get("Items", [])]

    async def delete_local_worker(self, worker_id: str) -> None:
        for item in self._query_pk(f"LOCAL_WORKER#{worker_id}"):
            self.table.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})

    async def save_worker_connection_request(self, request: WorkerConnectionRequest) -> WorkerConnectionRequest:
        request.updated_at = utcnow()
        self._put({
            "PK": f"WORKER_REQUEST#{request.id}",
            "SK": "METADATA",
            "entity": "WorkerConnectionRequest",
            "GSI1PK": "WORKER_REQUESTS",
            "GSI1SK": f"{request.status}#{_iso(request.created_at)}#{request.id}",
            **request.__dict__,
        })
        return request

    async def get_worker_connection_request(self, request_id: str) -> WorkerConnectionRequest | None:
        item = self.table.get_item(Key={"PK": f"WORKER_REQUEST#{request_id}", "SK": "METADATA"}).get("Item")
        return self._worker_connection_request(_clean_from_dynamo(item)) if item else None

    async def list_worker_connection_requests(self) -> list[WorkerConnectionRequest]:
        response = self.table.query(
            IndexName="GSI1",
            KeyConditionExpression=self._Key("GSI1PK").eq("WORKER_REQUESTS"),
        )
        return [self._worker_connection_request(_clean_from_dynamo(item)) for item in response.get("Items", [])]

    async def save_worker_credential_lease(self, lease: WorkerCredentialLease) -> WorkerCredentialLease:
        self._put({
            "PK": f"LOCAL_WORKER#{lease.worker_id}",
            "SK": "CREDENTIAL_LEASE",
            "entity": "WorkerCredentialLease",
            "GSI1PK": "WORKER_CREDENTIAL_LEASES",
            "GSI1SK": f"{_iso(lease.expires_at)}#{lease.worker_id}",
            **lease.__dict__,
        })
        return lease

    async def get_worker_credential_lease(self, worker_id: str) -> WorkerCredentialLease | None:
        item = self.table.get_item(Key={"PK": f"LOCAL_WORKER#{worker_id}", "SK": "CREDENTIAL_LEASE"}).get("Item")
        return self._worker_credential_lease(_clean_from_dynamo(item)) if item else None

    async def add_worker_event(self, event: WorkerEvent) -> WorkerEvent:
        self._put({
            "PK": f"LOCAL_WORKER#{event.worker_id}",
            "SK": f"EVENT#{_iso(event.created_at)}#{event.id}",
            "entity": "WorkerEvent",
            "GSI1PK": "WORKER_EVENTS",
            "GSI1SK": f"{_iso(event.created_at)}#{event.id}",
            **event.__dict__,
        })
        return event

    async def list_worker_events(self, worker_id: str | None = None) -> list[WorkerEvent]:
        if worker_id:
            raw = self._query_pk(f"LOCAL_WORKER#{worker_id}", "EVENT#")
        else:
            response = self.table.query(
                IndexName="GSI1",
                KeyConditionExpression=self._Key("GSI1PK").eq("WORKER_EVENTS"),
            )
            raw = [_clean_from_dynamo(item) for item in response.get("Items", [])]
        return sorted([self._worker_event(item) for item in raw], key=lambda item: item.created_at)

    async def save_template_pack(self, pack: TemplatePack) -> TemplatePack:
        pack.updated_at = utcnow()
        self._put({
            "PK": f"TEMPLATE#{pack.template_id}",
            "SK": "PACK#METADATA",
            "entity": "TemplatePack",
            "GSI1PK": "TEMPLATE_PACKS",
            "GSI1SK": f"{_iso(pack.updated_at)}#{pack.id}",
            **pack.__dict__,
        })
        return pack

    async def get_template_pack(self, template_id: str) -> TemplatePack | None:
        item = self.table.get_item(Key={"PK": f"TEMPLATE#{template_id}", "SK": "PACK#METADATA"}).get("Item")
        return self._template_pack(_clean_from_dynamo(item)) if item else None

    async def list_template_packs(self) -> list[TemplatePack]:
        response = self.table.query(
            IndexName="GSI1",
            KeyConditionExpression=self._Key("GSI1PK").eq("TEMPLATE_PACKS"),
            ScanIndexForward=False,
        )
        return [self._template_pack(_clean_from_dynamo(item)) for item in response.get("Items", [])]

    async def save_template_artifact(self, artifact: TemplateArtifact) -> TemplateArtifact:
        self._put({
            "PK": f"TEMPLATE#{artifact.template_id}",
            "SK": f"ARTIFACT#{artifact.artifact_key}",
            "entity": "TemplateArtifact",
            **artifact.__dict__,
        })
        return artifact

    async def get_template_artifact(self, template_id: str, artifact_key: str) -> TemplateArtifact | None:
        item = self.table.get_item(Key={"PK": f"TEMPLATE#{template_id}", "SK": f"ARTIFACT#{artifact_key}"}).get("Item")
        return self._template_artifact(_clean_from_dynamo(item)) if item else None

    async def list_template_artifacts(self, template_id: str) -> list[TemplateArtifact]:
        return [self._template_artifact(i) for i in self._query_pk(f"TEMPLATE#{template_id}", "ARTIFACT#")]

    async def save_template_manifest(self, manifest: TemplateManifest) -> TemplateManifest:
        self._put({
            "PK": f"TEMPLATE#{manifest.template_id}",
            "SK": f"MANIFEST#{manifest.version}",
            "entity": "TemplateManifest",
            **manifest.__dict__,
        })
        return manifest

    async def get_template_manifest(self, template_id: str, version: str) -> TemplateManifest | None:
        item = self.table.get_item(Key={"PK": f"TEMPLATE#{template_id}", "SK": f"MANIFEST#{version}"}).get("Item")
        return self._template_manifest(_clean_from_dynamo(item)) if item else None

    async def list_template_manifests(self, template_id: str) -> list[TemplateManifest]:
        return [self._template_manifest(i) for i in self._query_pk(f"TEMPLATE#{template_id}", "MANIFEST#")]

    async def upsert_template_memory(self, memory: TemplateMemory) -> TemplateMemory:
        existing = await self.get_template_memory(memory.template_id, memory.key)
        if existing:
            existing.value = memory.value
            existing.category = memory.category
            existing.updated_at = utcnow()
            self._put({
                "PK": f"TEMPLATE#{existing.template_id}",
                "SK": f"TMEM#{existing.category}#{existing.key}",
                "entity": "TemplateMemory",
                **existing.__dict__,
            })
            return existing
        self._put({
            "PK": f"TEMPLATE#{memory.template_id}",
            "SK": f"TMEM#{memory.category}#{memory.key}",
            "entity": "TemplateMemory",
            **memory.__dict__,
        })
        return memory

    async def get_template_memory(self, template_id: str, key: str) -> TemplateMemory | None:
        for m in await self.list_template_memories(template_id):
            if m.key == key:
                return m
        return None

    async def list_template_memories(self, template_id: str, category: str | None = None) -> list[TemplateMemory]:
        prefix = f"TMEM#{category}#" if category else "TMEM#"
        return [self._template_memory(i) for i in self._query_pk(f"TEMPLATE#{template_id}", prefix)]

    async def delete_template_memory(self, template_id: str, key: str) -> bool:
        memory = await self.get_template_memory(template_id, key)
        if not memory:
            return False
        self.table.delete_item(Key={"PK": f"TEMPLATE#{template_id}", "SK": f"TMEM#{memory.category}#{key}"})
        return True

    async def save_template_update_proposal(self, proposal: TemplateUpdateProposal) -> TemplateUpdateProposal:
        self._put({
            "PK": f"TEMPLATE#{proposal.template_id}",
            "SK": f"TProposal#{proposal.id}",
            "entity": "TemplateUpdateProposal",
            "GSI1PK": "T_PROPOSALS",
            "GSI1SK": f"{proposal.status}#{_iso(proposal.created_at)}#{proposal.id}",
            **proposal.__dict__,
        })
        return proposal

    async def get_template_update_proposal(self, template_id: str, proposal_id: str) -> TemplateUpdateProposal | None:
        item = self.table.get_item(Key={"PK": f"TEMPLATE#{template_id}", "SK": f"TProposal#{proposal_id}"}).get("Item")
        return self._template_update_proposal(_clean_from_dynamo(item)) if item else None

    async def list_template_update_proposals(self, template_id: str, status: str | None = None) -> list[TemplateUpdateProposal]:
        proposals = [self._template_update_proposal(i) for i in self._query_pk(f"TEMPLATE#{template_id}", "TProposal#")]
        if status:
            proposals = [p for p in proposals if p.status == status]
        return sorted(proposals, key=lambda p: p.created_at, reverse=True)

    async def save_factory_run_tracking_manifest(self, manifest: FactoryRunTrackingManifest) -> FactoryRunTrackingManifest:
        manifest.updated_at = utcnow()
        self._put({
            "PK": f"FACTORY_RUN#{manifest.factory_run_id}",
            "SK": "MANIFEST",
            "entity": "FactoryRunTrackingManifest",
            "GSI1PK": f"IDEA#{manifest.idea_id}",
            "GSI1SK": f"FRTM#{_iso(manifest.updated_at)}#{manifest.factory_run_id}",
            "GSI2PK": f"TEMPLATE#{manifest.template_id}",
            "GSI2SK": f"FRTM#{_iso(manifest.updated_at)}#{manifest.factory_run_id}",
            **manifest.__dict__,
        })
        self.factory_tracking_manifests[manifest.factory_run_id] = manifest
        return manifest

    async def get_factory_run_tracking_manifest(self, run_id: str) -> FactoryRunTrackingManifest | None:
        item = self.table.get_item(Key={"PK": f"FACTORY_RUN#{run_id}", "SK": "MANIFEST"}).get("Item")
        return self._factory_run_tracking_manifest(_clean_from_dynamo(item)) if item else None

    async def create_factory_run(self, run: FactoryRun) -> FactoryRun:
        return await self.save_factory_run(run)

    async def save_factory_run(self, run: FactoryRun) -> FactoryRun:
        run.updated_at = utcnow()
        self._put({
            "PK": f"FACTORY_RUN#{run.id}",
            "SK": "METADATA",
            "entity": "FactoryRun",
            "GSI1PK": f"IDEA#{run.idea_id}",
            "GSI1SK": f"FRUN#{_iso(run.created_at)}#{run.id}",
            "GSI2PK": f"TEMPLATE#{run.template_id}",
            "GSI2SK": f"FRUN#{_iso(run.created_at)}#{run.id}",
            **run.__dict__,
        })
        return run

    async def get_factory_run(self, run_id: str) -> FactoryRun | None:
        item = self.table.get_item(Key={"PK": f"FACTORY_RUN#{run_id}", "SK": "METADATA"}).get("Item")
        return self._factory_run(_clean_from_dynamo(item)) if item else None

    async def list_factory_runs(self, idea_id: str | None = None, template_id: str | None = None, intent_id: str | None = None, statuses: set[str] | None = None) -> list[FactoryRun]:
        if idea_id:
            response = self.table.query(
                IndexName="GSI1",
                KeyConditionExpression=self._Key("GSI1PK").eq(f"IDEA#{idea_id}") & self._Key("GSI1SK").begins_with("FRUN#"),
                ScanIndexForward=False,
            )
            raw = [_clean_from_dynamo(item) for item in response.get("Items", [])]
        elif template_id:
            response = self.table.query(
                IndexName="GSI2",
                KeyConditionExpression=self._Key("GSI2PK").eq(f"TEMPLATE#{template_id}") & self._Key("GSI2SK").begins_with("FRUN#"),
                ScanIndexForward=False,
            )
            raw = [_clean_from_dynamo(item) for item in response.get("Items", [])]
        else:
            response = self.table.query(
                IndexName="GSI1",
                KeyConditionExpression=self._Key("GSI1PK").begins_with("IDEA#"),
            )
            raw = [_clean_from_dynamo(item) for item in response.get("Items", []) if item.get("entity") == "FactoryRun"]
        runs = [self._factory_run(item) for item in raw]
        if intent_id:
            runs = [r for r in runs if r.intent_id == intent_id]
        if statuses:
            runs = [r for r in runs if r.status in statuses]
        return sorted(runs, key=lambda r: r.created_at, reverse=True)

    async def save_factory_phase(self, phase: FactoryPhase) -> FactoryPhase:
        self._put({
            "PK": f"FACTORY_RUN#{phase.factory_run_id}",
            "SK": f"PHASE#{phase.phase_order:03d}#{phase.phase_key}",
            "entity": "FactoryPhase",
            "GSI2PK": f"FRUN#{phase.factory_run_id}",
            "GSI2SK": f"PHASE#{phase.phase_order:03d}",
            **phase.__dict__,
        })
        return phase

    async def get_factory_phase(self, run_id: str, phase_id: str) -> FactoryPhase | None:
        for phase in await self.list_factory_phases(run_id):
            if phase.id == phase_id:
                return phase
        return None

    async def list_factory_phases(self, run_id: str) -> list[FactoryPhase]:
        return [self._factory_phase(i) for i in self._query_pk(f"FACTORY_RUN#{run_id}", "PHASE#")]

    async def save_factory_batch(self, batch: FactoryBatch) -> FactoryBatch:
        self._put({
            "PK": f"FACTORY_RUN#{batch.factory_run_id}",
            "SK": f"BATCH#{batch.factory_phase_id}#{batch.batch_key}",
            "entity": "FactoryBatch",
            "GSI2PK": f"FPHASE#{batch.factory_phase_id}",
            "GSI2SK": f"BATCH#{batch.batch_key}",
            **batch.__dict__,
        })
        return batch

    async def get_factory_batch(self, batch_id: str) -> FactoryBatch | None:
        response = self.table.query(
            IndexName="GSI2",
            KeyConditionExpression=self._Key("GSI2SK").begins_with("BATCH#"),
        )
        for item in response.get("Items", []):
            cleaned = _clean_from_dynamo(item)
            if cleaned.get("id") == batch_id:
                return self._factory_batch(cleaned)
        return None

    async def list_factory_batches(self, phase_id: str) -> list[FactoryBatch]:
        response = self.table.query(
            IndexName="GSI2",
            KeyConditionExpression=self._Key("GSI2PK").eq(f"FPHASE#{phase_id}"),
        )
        return sorted(
            [self._factory_batch(_clean_from_dynamo(item)) for item in response.get("Items", [])],
            key=lambda b: b.created_at,
        )

    async def save_verification_run(self, run: VerificationRun) -> VerificationRun:
        self._put({
            "PK": f"FACTORY_RUN#{run.factory_run_id}",
            "SK": f"VERIFY#{run.factory_batch_id}#{run.verification_type}",
            "entity": "VerificationRun",
            "GSI2PK": f"FBATCH#{run.factory_batch_id}",
            "GSI2SK": f"VERIFY#{run.verification_type}",
            **run.__dict__,
        })
        return run

    async def get_verification_run(self, run_id: str) -> VerificationRun | None:
        response = self.table.query(
            IndexName="GSI2",
            KeyConditionExpression=self._Key("GSI2SK").begins_with("VERIFY#"),
        )
        for item in response.get("Items", []):
            cleaned = _clean_from_dynamo(item)
            if cleaned.get("id") == run_id:
                return self._verification_run(cleaned)
        return None

    async def list_verification_runs(self, batch_id: str) -> list[VerificationRun]:
        response = self.table.query(
            IndexName="GSI2",
            KeyConditionExpression=self._Key("GSI2PK").eq(f"FBATCH#{batch_id}"),
        )
        return sorted(
            [self._verification_run(_clean_from_dynamo(item)) for item in response.get("Items", [])],
            key=lambda v: v.created_at,
        )

    async def save_repair_task(self, task: RepairTask) -> RepairTask:
        task.updated_at = utcnow()
        self._put({
            "PK": f"FACTORY_RUN#{task.factory_run_id}",
            "SK": f"REPAIR#{task.factory_batch_id}#{task.id}",
            "entity": "RepairTask",
            "GSI2PK": f"FBATCH#{task.factory_batch_id}",
            "GSI2SK": f"REPAIR#{task.id}",
            **task.__dict__,
        })
        return task

    async def get_repair_task(self, task_id: str) -> RepairTask | None:
        response = self.table.query(
            IndexName="GSI2",
            KeyConditionExpression=self._Key("GSI2SK").eq(f"REPAIR#{task_id}"),
        )
        for item in response.get("Items", []):
            cleaned = _clean_from_dynamo(item)
            if cleaned.get("id") == task_id:
                return self._repair_task(cleaned)
        return None

    async def list_repair_tasks(self, factory_run_id: str, statuses: set[str] | None = None) -> list[RepairTask]:
        response = self.table.query(
            KeyConditionExpression=self._Key("PK").eq(f"FACTORY_RUN#{factory_run_id}") & self._Key("SK").begins_with("REPAIR#"),
        )
        tasks = [self._repair_task(_clean_from_dynamo(item)) for item in response.get("Items", [])]
        if statuses:
            tasks = [t for t in tasks if t.status in statuses]
        return sorted(tasks, key=lambda t: t.created_at)

    async def list_repair_tasks_for_batch(self, factory_batch_id: str) -> list[RepairTask]:
        response = self.table.query(
            IndexName="GSI2",
            KeyConditionExpression=self._Key("GSI2PK").eq(f"FBATCH#{factory_batch_id}"),
        )
        return sorted(
            [self._repair_task(_clean_from_dynamo(item)) for item in response.get("Items", []) if item.get("SK", "").startswith("REPAIR#")],
            key=lambda t: t.created_at,
        )

    async def save_review_packet(self, packet: ReviewPacket) -> ReviewPacket:
        packet.updated_at = utcnow()
        self._put({
            "PK": f"FACTORY_RUN#{packet.run_id}",
            "SK": "REVIEW_PACKET",
            "entity": "ReviewPacket",
            "GSI1PK": "REVIEW_PACKETS",
            "GSI1SK": f"{packet.wait_window_state}#{_iso(packet.created_at)}#{packet.id}",
            "GSI2PK": f"REVIEW_PACKET#{packet.id}",
            "GSI2SK": "METADATA",
            **packet.__dict__,
        })
        return packet

    async def get_review_packet(self, run_id: str) -> ReviewPacket | None:
        item = self.table.get_item(Key={"PK": f"FACTORY_RUN#{run_id}", "SK": "REVIEW_PACKET"}).get("Item")
        return self._review_packet(_clean_from_dynamo(item)) if item else None

    async def get_review_packet_by_id(self, packet_id: str) -> ReviewPacket | None:
        item = self.table.get_item(Key={"PK": f"REVIEW_PACKET#{packet_id}", "SK": "METADATA"}).get("Item")
        return self._review_packet(_clean_from_dynamo(item)) if item else None

    async def list_review_packets(self, wait_window_states: set[str] | None = None, statuses: set[str] | None = None) -> list[ReviewPacket]:
        response = self.table.query(
            IndexName="GSI1",
            KeyConditionExpression=self._Key("GSI1PK").eq("REVIEW_PACKETS"),
            ScanIndexForward=False,
        )
        packets = [self._review_packet(_clean_from_dynamo(item)) for item in response.get("Items", [])]
        if wait_window_states:
            packets = [p for p in packets if p.wait_window_state in wait_window_states]
        if statuses:
            packets = [p for p in packets if p.status in statuses]
        return sorted(packets, key=lambda p: p.created_at, reverse=True)

    def _idea(self, item: dict[str, Any]) -> Idea:
        return Idea(id=item["id"], title=item["title"], slug=item["slug"], description=item["description"], current_phase=item.get("current_phase", "capture"), status=item.get("status", "active"), source_type=item.get("source_type", "manual"), created_at=_dt(item.get("created_at")) or utcnow(), updated_at=_dt(item.get("updated_at")) or utcnow())

    def _score(self, item: dict[str, Any]) -> Score:
        return Score(id=item["id"], idea_id=item["idea_id"], dimension=item["dimension"], value=float(item["value"]), rationale=item.get("rationale"), scored_at=_dt(item.get("scored_at")) or utcnow())

    def _message(self, item: dict[str, Any]) -> Message:
        return Message(id=item["id"], idea_id=item["idea_id"], role=item["role"], content=item["content"], timestamp=_dt(item.get("timestamp")) or utcnow(), metadata_=item.get("metadata_"))

    def _memory(self, item: dict[str, Any]) -> ProjectMemory:
        return ProjectMemory(id=item["id"], idea_id=item.get("idea_id"), key=item["key"], value=item["value"], category=item["category"], created_at=_dt(item.get("created_at")) or utcnow(), updated_at=_dt(item.get("updated_at")) or utcnow())

    def _research(self, item: dict[str, Any]) -> ResearchTask:
        return ResearchTask(id=item["id"], idea_id=item["idea_id"], prompt_text=item["prompt_text"], status=item.get("status", "pending"), result_file_path=item.get("result_file_path"), result_content=item.get("result_content"), topic=item.get("topic"), created_at=_dt(item.get("created_at")) or utcnow(), completed_at=_dt(item.get("completed_at")))

    def _artifact_metadata(self, item: dict[str, Any]) -> ArtifactMetadata:
        return ArtifactMetadata(
            source=item.get("source", "research"),
            source_uri=item.get("source_uri"),
            actor=item.get("actor"),
            correlation_id=item.get("correlation_id"),
            dedupe_hash=item.get("dedupe_hash"),
            tags=item.get("tags") or [],
            extra=item.get("extra") or {},
            created_at=_dt(item.get("created_at")) or utcnow(),
        )

    def _intent(self, item: dict[str, Any]) -> Intent:
        return Intent(
            id=item["id"],
            idea_id=item["idea_id"],
            project_id=item["project_id"],
            summary=item.get("summary", ""),
            details=item.get("details") or {},
            correlation_id=item.get("correlation_id"),
            dedupe_hash=item.get("dedupe_hash"),
            budget=item.get("budget") or {},
            stop_conditions=item.get("stop_conditions") or [],
            factory_run_ids=item.get("factory_run_ids") or [],
            source=item.get("source", "manual"),
            status=item.get("status", "active"),
            created_at=_dt(item.get("created_at")) or utcnow(),
            updated_at=_dt(item.get("updated_at")) or utcnow(),
        )

    def _report(self, item: dict[str, Any]) -> Report:
        return Report(id=item["id"], idea_id=item["idea_id"], phase=item["phase"], title=item["title"], content=item.get("content", ""), content_path=item.get("content_path", ""), generated_at=_dt(item.get("generated_at")) or utcnow())

    def _relationship(self, item: dict[str, Any]) -> IdeaRelationship:
        return IdeaRelationship(id=item["id"], source_idea_id=item["source_idea_id"], target_idea_id=item["target_idea_id"], relation_type=item["relation_type"], description=item.get("description"), created_at=_dt(item.get("created_at")) or utcnow())

    def _github_installation(self, item: dict[str, Any]) -> GitHubInstallation:
        return GitHubInstallation(id=item["id"], installation_id=str(item["installation_id"]), account_login=item["account_login"], account_type=item.get("account_type", "User"), status=item.get("status", "active"), created_at=_dt(item.get("created_at")) or utcnow(), updated_at=_dt(item.get("updated_at")) or utcnow())

    def _project_twin(self, item: dict[str, Any]) -> ProjectTwin:
        return ProjectTwin(id=item["id"], idea_id=item["idea_id"], provider=item.get("provider", "github"), installation_id=str(item["installation_id"]), owner=item["owner"], repo=item["repo"], repo_full_name=item["repo_full_name"], repo_url=item["repo_url"], clone_url=item["clone_url"], default_branch=item["default_branch"], active_branch=item.get("active_branch"), deploy_url=item.get("deploy_url"), desired_outcome=item.get("desired_outcome"), current_status=item.get("current_status"), detected_stack=item.get("detected_stack") or [], test_commands=item.get("test_commands") or [], last_indexed_commit=item.get("last_indexed_commit"), index_status=item.get("index_status", "not_indexed"), health_status=item.get("health_status", "unknown"), open_queue_count=int(item.get("open_queue_count", 0)), created_at=_dt(item.get("created_at")) or utcnow(), updated_at=_dt(item.get("updated_at")) or utcnow())

    def _code_index(self, item: dict[str, Any]) -> CodeIndexArtifact:
        return CodeIndexArtifact(id=item["id"], project_id=item["project_id"], idea_id=item["idea_id"], commit_sha=item["commit_sha"], file_inventory=item.get("file_inventory") or [], manifests=item.get("manifests") or [], dependency_graph=item.get("dependency_graph") or {}, route_map=item.get("route_map") or [], test_commands=item.get("test_commands") or [], architecture_summary=item.get("architecture_summary", ""), risks=item.get("risks") or [], todos=item.get("todos") or [], searchable_chunks=item.get("searchable_chunks") or [], created_at=_dt(item.get("created_at")) or utcnow())

    def _research_artifact(self, item: dict[str, Any]) -> ResearchArtifact:
        return ResearchArtifact(
            id=item["id"],
            factory_run_id=item["factory_run_id"],
            title=item.get("title", ""),
            source=item.get("source", ""),
            raw_content=item.get("raw_content"),
            raw_content_uri=item.get("raw_content_uri"),
            raw_metadata=item.get("raw_metadata") or {},
            normalized=item.get("normalized") or {},
            artifact_metadata=self._artifact_metadata(item.get("artifact_metadata") or {}),
            dedupe_hash=item.get("dedupe_hash", ""),
            status=item.get("status", "active"),
            created_at=_dt(item.get("created_at")) or utcnow(),
            updated_at=_dt(item.get("updated_at")) or utcnow(),
        )

    def _work_item(self, item: dict[str, Any]) -> WorkItem:
        return WorkItem(id=item["id"], idea_id=item["idea_id"], project_id=item["project_id"], job_type=item["job_type"], payload=item.get("payload") or {}, status=item.get("status", "queued"), priority=int(item.get("priority", 50)), factory_run_id=item.get("factory_run_id"), parent_work_item_id=item.get("parent_work_item_id"), rationale=item.get("rationale"), correlation_id=item.get("correlation_id"), dedupe_hash=item.get("dedupe_hash"), budget=item.get("budget") or {}, stop_conditions=item.get("stop_conditions") or [], idempotency_key=item.get("idempotency_key"), worker_id=item.get("worker_id"), claim_token=item.get("claim_token"), claimed_at=_dt(item.get("claimed_at")), heartbeat_at=_dt(item.get("heartbeat_at")), run_after=_dt(item.get("run_after")), retry_count=int(item.get("retry_count", 0)), timeout_seconds=int(item.get("timeout_seconds", 900)), logs=item.get("logs", ""), logs_pointer=item.get("logs_pointer"), result=item.get("result"), error=item.get("error"), branch_name=item.get("branch_name"), agent_run_id=item.get("agent_run_id"), ledger_policy=item.get("ledger_policy", "none"), ledger_path=item.get("ledger_path"), created_at=_dt(item.get("created_at")) or utcnow(), updated_at=_dt(item.get("updated_at")) or utcnow())

    def _agent_run(self, item: dict[str, Any]) -> AgentRun:
        return AgentRun(id=item["id"], work_item_id=item["work_item_id"], idea_id=item["idea_id"], project_id=item["project_id"], engine=item["engine"], agent_name=item.get("agent_name"), model=item.get("model"), command=item.get("command"), status=item.get("status", "running"), prompt=item.get("prompt", ""), output=item.get("output", ""), started_at=_dt(item.get("started_at")) or utcnow(), completed_at=_dt(item.get("completed_at")))

    def _project_commit(self, item: dict[str, Any]) -> ProjectCommit:
        return ProjectCommit(id=item["id"], idea_id=item["idea_id"], project_id=item["project_id"], work_item_id=item["work_item_id"], branch_name=item["branch_name"], commit_sha=item["commit_sha"], message=item["message"], author=item.get("author"), status=item.get("status", "pushed"), created_at=_dt(item.get("created_at")) or utcnow())

    def _local_worker(self, item: dict[str, Any]) -> LocalWorker:
        return LocalWorker(id=item["id"], display_name=item["display_name"], machine_name=item["machine_name"], platform=item["platform"], engine=item.get("engine", "opencode"), status=item.get("status", "approved"), capabilities=item.get("capabilities") or [], config=item.get("config") or {}, api_token_hash=item.get("api_token_hash"), last_seen_at=_dt(item.get("last_seen_at")), created_at=_dt(item.get("created_at")) or utcnow(), updated_at=_dt(item.get("updated_at")) or utcnow())

    def _worker_connection_request(self, item: dict[str, Any]) -> WorkerConnectionRequest:
        return WorkerConnectionRequest(id=item["id"], display_name=item["display_name"], machine_name=item["machine_name"], platform=item["platform"], engine=item.get("engine", "opencode"), capabilities=item.get("capabilities") or [], requested_config=item.get("requested_config") or {}, status=item.get("status", "pending"), worker_id=item.get("worker_id"), decision_reason=item.get("decision_reason"), created_at=_dt(item.get("created_at")) or utcnow(), updated_at=_dt(item.get("updated_at")) or utcnow())

    def _worker_credential_lease(self, item: dict[str, Any]) -> WorkerCredentialLease:
        return WorkerCredentialLease(id=item["id"], worker_id=item["worker_id"], api_token_hash=item["api_token_hash"], access_key_id=item.get("access_key_id", ""), secret_access_key=item.get("secret_access_key", ""), session_token=item.get("session_token", ""), expires_at=_dt(item.get("expires_at")) or utcnow(), command_queue_url=item.get("command_queue_url", ""), event_queue_url=item.get("event_queue_url", ""), region=item.get("region", "us-east-1"), created_at=_dt(item.get("created_at")) or utcnow())

    def _worker_event(self, item: dict[str, Any]) -> WorkerEvent:
        return WorkerEvent(id=item["id"], worker_id=item["worker_id"], event_type=item["event_type"], payload=item.get("payload") or {}, work_item_id=item.get("work_item_id"), factory_run_id=item.get("factory_run_id"), research_artifact_id=item.get("research_artifact_id"), review_packet_id=item.get("review_packet_id"), correlation_id=item.get("correlation_id"), idempotency_key=item.get("idempotency_key"), actor=item.get("actor"), status=item.get("status", "received"), created_at=_dt(item.get("created_at")) or utcnow())

    def _template_pack(self, item: dict[str, Any]) -> TemplatePack:
        return TemplatePack(id=item["id"], template_id=item["template_id"], version=item.get("version", "0.0.1"), channel=item.get("channel", "stable"), display_name=item.get("display_name", ""), description=item.get("description", ""), phases=item.get("phases") or [], quality_gates=item.get("quality_gates") or [], default_stack=item.get("default_stack") or {}, constraints=item.get("constraints") or [], opencode_worker=item.get("opencode_worker") or {}, created_at=_dt(item.get("created_at")) or utcnow(), updated_at=_dt(item.get("updated_at")) or utcnow())

    def _template_artifact(self, item: dict[str, Any]) -> TemplateArtifact:
        return TemplateArtifact(
            id=item["id"],
            template_id=item["template_id"],
            artifact_key=item["artifact_key"],
            content_type=item.get("content_type", ""),
            uri=item.get("uri", ""),
            content=item.get("content", ""),
            version=item.get("version", "1.0.0"),
            compatibility=item.get("compatibility") or {},
            metadata_=item.get("metadata_") or {},
            created_at=_dt(item.get("created_at")) or utcnow(),
        )

    def _template_manifest(self, item: dict[str, Any]) -> TemplateManifest:
        return TemplateManifest(id=item["id"], template_id=item["template_id"], version=item["version"], artifact_keys=item.get("artifact_keys") or [], metadata_=item.get("metadata_") or {}, created_at=_dt(item.get("created_at")) or utcnow())

    def _template_memory(self, item: dict[str, Any]) -> TemplateMemory:
        return TemplateMemory(id=item["id"], template_id=item["template_id"], key=item["key"], value=item["value"], category=item["category"], created_at=_dt(item.get("created_at")) or utcnow(), updated_at=_dt(item.get("updated_at")) or utcnow())

    def _template_update_proposal(self, item: dict[str, Any]) -> TemplateUpdateProposal:
        return TemplateUpdateProposal(id=item["id"], template_id=item["template_id"], proposed_by=item["proposed_by"], change_type=item["change_type"], description=item.get("description", ""), payload_uri=item.get("payload_uri"), status=item.get("status", "pending"), created_at=_dt(item.get("created_at")) or utcnow(), reviewed_at=_dt(item.get("reviewed_at")))

    def _factory_run(self, item: dict[str, Any]) -> FactoryRun:
        return FactoryRun(id=item["id"], idea_id=item["idea_id"], template_id=item["template_id"], status=item.get("status", "queued"), config=item.get("config") or {}, intent_id=item.get("intent_id"), run_type=item.get("run_type", "standard"), correlation_id=item.get("correlation_id"), dedupe_hash=item.get("dedupe_hash"), budget=item.get("budget") or {}, stop_conditions=item.get("stop_conditions") or [], tracking_manifest_uri=item.get("tracking_manifest_uri"), created_at=_dt(item.get("created_at")) or utcnow(), updated_at=_dt(item.get("updated_at")) or utcnow(), completed_at=_dt(item.get("completed_at")))

    def _factory_run_tracking_manifest(self, item: dict[str, Any]) -> FactoryRunTrackingManifest:
        return FactoryRunTrackingManifest(
            id=item["id"],
            factory_run_id=item["factory_run_id"],
            idea_id=item["idea_id"],
            template_id=item["template_id"],
            template_version=item.get("template_version", ""),
            run_config=item.get("run_config") or {},
            run_status=item.get("run_status", "queued"),
            phase_summary=item.get("phase_summary") or [],
            batch_summary=item.get("batch_summary") or [],
            verification_summary=item.get("verification_summary") or [],
            last_indexed_commit=item.get("last_indexed_commit"),
            graphify_status=item.get("graphify_status", "pending"),
            worker_queue_state=item.get("worker_queue_state") or {},
            verification_state=item.get("verification_state") or {},
            artifact_uris=item.get("artifact_uris") or {},
            token_economy_totals=item.get("token_economy_totals") or {},
            duplicate_work_count=int(item.get("duplicate_work_count", 0)),
            snapshot_uri=item.get("snapshot_uri"),
            created_at=_dt(item.get("created_at")) or utcnow(),
            updated_at=_dt(item.get("updated_at")) or utcnow(),
            completed_at=_dt(item.get("completed_at")),
        )

    def _factory_phase(self, item: dict[str, Any]) -> FactoryPhase:
        return FactoryPhase(id=item["id"], factory_run_id=item["factory_run_id"], phase_key=item["phase_key"], phase_order=int(item.get("phase_order", 0)), status=item.get("status", "pending"), config_override=item.get("config_override") or {}, output_uri=item.get("output_uri"), created_at=_dt(item.get("created_at")) or utcnow(), started_at=_dt(item.get("started_at")), completed_at=_dt(item.get("completed_at")))

    def _factory_batch(self, item: dict[str, Any]) -> FactoryBatch:
        return FactoryBatch(id=item["id"], factory_phase_id=item["factory_phase_id"], factory_run_id=item["factory_run_id"], batch_key=item["batch_key"], status=item.get("status", "pending"), worker_id=item.get("worker_id"), work_item_id=item.get("work_item_id"), input_uri=item.get("input_uri"), output_uri=item.get("output_uri"), created_at=_dt(item.get("created_at")) or utcnow(), started_at=_dt(item.get("started_at")), completed_at=_dt(item.get("completed_at")))

    def _verification_run(self, item: dict[str, Any]) -> VerificationRun:
        return VerificationRun(id=item["id"], factory_batch_id=item["factory_batch_id"], factory_run_id=item["factory_run_id"], verification_type=item["verification_type"], status=item.get("status", "pending"), result_uri=item.get("result_uri"), result_summary=item.get("result_summary", ""), failure_classification=item.get("failure_classification", ""), command_output=item.get("command_output", ""), changed_files=item.get("changed_files") or [], created_at=_dt(item.get("created_at")) or utcnow(), completed_at=_dt(item.get("completed_at")))

    def _repair_task(self, item: dict[str, Any]) -> RepairTask:
        return RepairTask(id=item["id"], factory_run_id=item["factory_run_id"], factory_batch_id=item["factory_batch_id"], failure_classification=item.get("failure_classification", ""), status=item.get("status", "pending"), attempt_number=int(item.get("attempt_number", 1)), command_output=item.get("command_output", ""), recent_diff=item.get("recent_diff", ""), changed_files=item.get("changed_files") or [], acceptance_criteria=item.get("acceptance_criteria") or [], guardrails=item.get("guardrails") or [], issue_summary=item.get("issue_summary", ""), work_item_id=item.get("work_item_id"), created_at=_dt(item.get("created_at")) or utcnow(), updated_at=_dt(item.get("updated_at")) or utcnow(), completed_at=_dt(item.get("completed_at")))

    def _review_packet(self, item: dict[str, Any]) -> ReviewPacket:
        return ReviewPacket(
            id=item["id"],
            run_id=item["run_id"],
            promise=item.get("promise", ""),
            packet_type=item.get("packet_type", "standard"),
            status=item.get("status", "awaiting_review"),
            wait_window_state=item.get("wait_window_state", "awaiting_review"),
            branch_name=item.get("branch_name"),
            worker_id=item.get("worker_id"),
            worker_display_name=item.get("worker_display_name"),
            worker_machine_name=item.get("worker_machine_name"),
            autonomy_level=item.get("autonomy_level"),
            template_id=item.get("template_id"),
            template_version=item.get("template_version"),
            blast_radius=item.get("blast_radius") or {},
            safety_net_results=item.get("safety_net_results") or {},
            execution_trace=item.get("execution_trace") or {},
            changed_files=item.get("changed_files") or [],
            diff_summary_uri=item.get("diff_summary_uri"),
            evaluator_verdict=item.get("evaluator_verdict") or {},
            decision_gates=item.get("decision_gates") or {},
            allowed_actions=item.get("allowed_actions") or [],
            research_artifact_ids=item.get("research_artifact_ids") or [],
            research_handoff=item.get("research_handoff") or {},
            telemetry_events=item.get("telemetry_events") or [],
            created_at=_dt(item.get("created_at")) or utcnow(),
            wait_window_started_at=_dt(item.get("wait_window_started_at")),
            expires_at=_dt(item.get("expires_at")),
            resolved_at=_dt(item.get("resolved_at")),
            updated_at=_dt(item.get("updated_at")) or utcnow(),
        )


_repo: Repository | None = None


def get_repository() -> Repository:
    global _repo
    if _repo is not None:
        return _repo
    storage = os.getenv("IDEAREFINERY_STORAGE", "memory").lower()
    if storage == "dynamodb":
        _repo = DynamoDBRepository(
            table_name=os.environ["DYNAMODB_TABLE_NAME"],
            region_name=os.getenv("AWS_REGION", "us-east-1"),
        )
    else:
        _repo = InMemoryRepository()
    return _repo


def set_repository(repo: Repository) -> None:
    global _repo
    _repo = repo
