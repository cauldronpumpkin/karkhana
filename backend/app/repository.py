from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
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
class WorkItem:
    idea_id: str
    project_id: str
    job_type: str
    payload: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "queued"
    priority: int = 50
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
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass
class AgentRun:
    work_item_id: str
    idea_id: str
    project_id: str
    engine: str
    agent_name: str | None = None
    model: str | None = None
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
    async def save_project_twin(self, project: ProjectTwin) -> ProjectTwin: ...
    async def get_project_twin(self, idea_id: str) -> ProjectTwin | None: ...
    async def get_project_twin_by_id(self, project_id: str) -> ProjectTwin | None: ...
    async def list_project_twins(self) -> list[ProjectTwin]: ...
    async def put_code_index(self, artifact: CodeIndexArtifact) -> CodeIndexArtifact: ...
    async def get_latest_code_index(self, idea_id: str) -> CodeIndexArtifact | None: ...
    async def enqueue_work_item(self, item: WorkItem) -> WorkItem: ...
    async def save_work_item(self, item: WorkItem) -> WorkItem: ...
    async def get_work_item(self, item_id: str) -> WorkItem | None: ...
    async def list_work_items(self, idea_id: str | None = None, statuses: set[str] | None = None) -> list[WorkItem]: ...
    async def add_agent_run(self, run: AgentRun) -> AgentRun: ...
    async def save_agent_run(self, run: AgentRun) -> AgentRun: ...
    async def list_agent_runs(self, idea_id: str) -> list[AgentRun]: ...
    async def add_project_commit(self, commit: ProjectCommit) -> ProjectCommit: ...
    async def list_project_commits(self, idea_id: str) -> list[ProjectCommit]: ...


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
        self.project_twins: dict[str, ProjectTwin] = {}
        self.code_indexes: dict[str, list[CodeIndexArtifact]] = {}
        self.work_items: dict[str, WorkItem] = {}
        self.agent_runs: dict[str, AgentRun] = {}
        self.project_commits: dict[str, ProjectCommit] = {}

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

    async def enqueue_work_item(self, item: WorkItem) -> WorkItem:
        if item.idempotency_key:
            for existing in self.work_items.values():
                if existing.idempotency_key == item.idempotency_key and existing.status not in {"completed", "cancelled"}:
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

    async def _refresh_project_queue_count(self, project_id: str) -> None:
        project = await self.get_project_twin_by_id(project_id)
        if project:
            project.open_queue_count = len([
                item for item in self.work_items.values()
                if item.project_id == project_id and item.status not in {"completed", "cancelled", "failed_terminal"}
            ])
            project.updated_at = utcnow()


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
        response = self.table.query(KeyConditionExpression=condition)
        return [_clean_from_dynamo(i) for i in response.get("Items", [])]

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

    async def enqueue_work_item(self, item: WorkItem) -> WorkItem:
        if item.idempotency_key:
            for existing in await self.list_work_items(statuses={"queued", "claimed", "running", "waiting_for_machine", "failed_retryable"}):
                if existing.idempotency_key == item.idempotency_key:
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
            response = self.table.query(
                IndexName="GSI2",
                KeyConditionExpression=self._Key("GSI2PK").eq(f"IDEA#{idea_id}") & self._Key("GSI2SK").begins_with("JOB#"),
            )
            raw = [_clean_from_dynamo(item) for item in response.get("Items", [])]
        else:
            response = self.table.query(
                IndexName="GSI1",
                KeyConditionExpression=self._Key("GSI1PK").eq("WORK_ITEMS"),
            )
            raw = [_clean_from_dynamo(item) for item in response.get("Items", [])]
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

    def _work_item(self, item: dict[str, Any]) -> WorkItem:
        return WorkItem(id=item["id"], idea_id=item["idea_id"], project_id=item["project_id"], job_type=item["job_type"], payload=item.get("payload") or {}, status=item.get("status", "queued"), priority=int(item.get("priority", 50)), idempotency_key=item.get("idempotency_key"), worker_id=item.get("worker_id"), claim_token=item.get("claim_token"), claimed_at=_dt(item.get("claimed_at")), heartbeat_at=_dt(item.get("heartbeat_at")), run_after=_dt(item.get("run_after")), retry_count=int(item.get("retry_count", 0)), timeout_seconds=int(item.get("timeout_seconds", 900)), logs=item.get("logs", ""), logs_pointer=item.get("logs_pointer"), result=item.get("result"), error=item.get("error"), branch_name=item.get("branch_name"), created_at=_dt(item.get("created_at")) or utcnow(), updated_at=_dt(item.get("updated_at")) or utcnow())

    def _agent_run(self, item: dict[str, Any]) -> AgentRun:
        return AgentRun(id=item["id"], work_item_id=item["work_item_id"], idea_id=item["idea_id"], project_id=item["project_id"], engine=item["engine"], agent_name=item.get("agent_name"), model=item.get("model"), status=item.get("status", "running"), prompt=item.get("prompt", ""), output=item.get("output", ""), started_at=_dt(item.get("started_at")) or utcnow(), completed_at=_dt(item.get("completed_at")))

    def _project_commit(self, item: dict[str, Any]) -> ProjectCommit:
        return ProjectCommit(id=item["id"], idea_id=item["idea_id"], project_id=item["project_id"], work_item_id=item["work_item_id"], branch_name=item["branch_name"], commit_sha=item["commit_sha"], message=item["message"], author=item.get("author"), status=item.get("status", "pushed"), created_at=_dt(item.get("created_at")) or utcnow())


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
