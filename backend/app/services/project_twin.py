from __future__ import annotations

import re
import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta
from typing import Any

from backend.app.config import settings
from backend.app.repository import (
    AgentRun,
    CodeIndexArtifact,
    GitHubInstallation,
    Idea,
    ProjectCommit,
    ProjectTwin,
    Report,
    WorkItem,
    get_repository,
    utcnow,
)

CLAIMABLE_STATUSES = {"queued", "waiting_for_machine", "failed_retryable"}
OPEN_JOB_STATUSES = {"queued", "waiting_for_machine", "failed_retryable", "claimed", "running"}
TERMINAL_STATUSES = {"completed", "cancelled", "failed_terminal"}


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return to_jsonable(asdict(value))
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    return value


class ProjectTwinService:
    async def import_github_project(self, data: dict[str, Any]) -> dict[str, Any]:
        repo = get_repository()
        owner = (data.get("owner") or "").strip()
        repo_name = (data.get("repo") or data.get("repo_name") or "").strip()
        full_name = (data.get("repo_full_name") or f"{owner}/{repo_name}").strip("/")
        if "/" in full_name and (not owner or not repo_name):
            owner, repo_name = full_name.split("/", 1)
        if not owner or not repo_name:
            raise ValueError("owner and repo are required")

        installation_id = str(data.get("installation_id") or "")
        if not installation_id:
            raise ValueError("installation_id is required for GitHub App backed imports")

        await repo.save_github_installation(
            GitHubInstallation(
                installation_id=installation_id,
                account_login=owner,
                account_type=data.get("account_type") or "User",
            )
        )

        title = data.get("title") or full_name
        description = data.get("description") or (
            f"Existing GitHub project imported from {full_name}. "
            f"Current status: {data.get('current_status') or 'not yet assessed'}."
        )
        idea = Idea(
            title=title,
            slug=self._slug(title),
            description=description,
            current_phase=data.get("current_phase") or "build",
            source_type="github_project",
        )
        await repo.create_idea(idea)

        project = ProjectTwin(
            idea_id=idea.id,
            provider="github",
            installation_id=installation_id,
            owner=owner,
            repo=repo_name,
            repo_full_name=full_name,
            repo_url=data.get("repo_url") or f"https://github.com/{full_name}",
            clone_url=data.get("clone_url") or f"https://github.com/{full_name}.git",
            default_branch=data.get("default_branch") or "main",
            active_branch=data.get("active_branch"),
            deploy_url=data.get("deploy_url"),
            desired_outcome=data.get("desired_outcome"),
            current_status=data.get("current_status"),
        )
        await repo.save_project_twin(project)

        job = await self.enqueue_job(
            idea_id=idea.id,
            project_id=project.id,
            job_type="repo_index",
            payload={"reason": "initial_import", "default_branch": project.default_branch},
            idempotency_key=f"repo_index:{project.id}:initial",
        )
        return {"idea": to_jsonable(idea), "project": to_jsonable(project), "job": to_jsonable(job)}

    async def get_project_status(self, idea_id: str) -> dict[str, Any]:
        repo = get_repository()
        idea = await repo.get_idea(idea_id)
        project = await repo.get_project_twin(idea_id)
        if not idea or not project:
            raise ValueError("Project twin not found")
        latest_index = await repo.get_latest_code_index(idea_id)
        jobs = await repo.list_work_items(idea_id)
        runs = await repo.list_agent_runs(idea_id)
        commits = await repo.list_project_commits(idea_id)
        return {
            "idea": to_jsonable(idea),
            "project": to_jsonable(project),
            "latest_index": to_jsonable(latest_index) if latest_index else None,
            "jobs": [to_jsonable(job) for job in jobs],
            "agent_runs": [to_jsonable(run) for run in runs[:10]],
            "commits": [to_jsonable(commit) for commit in commits[:10]],
        }

    async def enqueue_reindex(self, idea_id: str) -> WorkItem:
        project = await get_repository().get_project_twin(idea_id)
        if not project:
            raise ValueError("Project twin not found")
        project.index_status = "queued"
        await get_repository().save_project_twin(project)
        return await self.enqueue_job(
            idea_id=idea_id,
            project_id=project.id,
            job_type="repo_index",
            payload={"reason": "manual_reindex", "default_branch": project.default_branch},
            idempotency_key=f"repo_index:{project.id}:{int(utcnow().timestamp())}",
        )

    async def enqueue_job(
        self,
        idea_id: str,
        project_id: str,
        job_type: str,
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
        priority: int = 50,
    ) -> WorkItem:
        return await get_repository().enqueue_work_item(
            WorkItem(
                idea_id=idea_id,
                project_id=project_id,
                job_type=job_type,
                payload=payload or {},
                idempotency_key=idempotency_key,
                priority=priority,
                timeout_seconds=settings.worker_claim_timeout_seconds,
            )
        )

    async def list_jobs(self, idea_id: str | None = None) -> list[dict[str, Any]]:
        await self.requeue_expired_claims()
        return [to_jsonable(item) for item in await get_repository().list_work_items(idea_id)]

    async def claim_job(self, worker_id: str, capabilities: list[str] | None = None) -> dict[str, Any] | None:
        repo = get_repository()
        await self.requeue_expired_claims()
        running_projects = {
            item.project_id for item in await repo.list_work_items(statuses={"claimed", "running"})
        }
        for item in await repo.list_work_items(statuses=CLAIMABLE_STATUSES):
            if item.project_id in running_projects:
                continue
            if capabilities and item.job_type not in capabilities:
                continue
            project = await repo.get_project_twin_by_id(item.project_id)
            if not project:
                item.status = "failed_terminal"
                item.error = "Project twin not found"
                await repo.save_work_item(item)
                continue
            item.status = "claimed"
            item.worker_id = worker_id
            item.claim_token = str(uuid.uuid4())
            item.claimed_at = utcnow()
            item.heartbeat_at = item.claimed_at
            await repo.save_work_item(item)
            return {"job": to_jsonable(item), "project": to_jsonable(project)}
        return None

    async def heartbeat_job(self, job_id: str, claim_token: str, worker_id: str, logs: str = "") -> dict[str, Any]:
        item = await self._locked_job(job_id, claim_token, worker_id)
        item.status = "running"
        item.heartbeat_at = utcnow()
        if logs:
            item.logs = self._append_log(item.logs, logs)
        await get_repository().save_work_item(item)
        return to_jsonable(item)

    async def complete_job(self, job_id: str, claim_token: str, worker_id: str, result: dict[str, Any] | None = None, logs: str = "") -> dict[str, Any]:
        repo = get_repository()
        item = await self._locked_job(job_id, claim_token, worker_id)
        result = result or {}
        item.status = "completed"
        item.result = result
        item.heartbeat_at = utcnow()
        if result.get("branch_name"):
            item.branch_name = result["branch_name"]
        if logs:
            item.logs = self._append_log(item.logs, logs)
        await repo.save_work_item(item)

        project = await repo.get_project_twin_by_id(item.project_id)
        if project:
            project.health_status = "healthy" if result.get("tests_passed", item.job_type == "repo_index") else project.health_status
            if item.job_type == "repo_index":
                await self._store_code_index(project, item, result)
            await repo.save_project_twin(project)

        if result.get("commit_sha") and result.get("branch_name"):
            await repo.add_project_commit(
                ProjectCommit(
                    idea_id=item.idea_id,
                    project_id=item.project_id,
                    work_item_id=item.id,
                    branch_name=result["branch_name"],
                    commit_sha=result["commit_sha"],
                    message=result.get("commit_message") or f"Idea Refinery job {item.id}",
                    author=result.get("author"),
                )
            )
        return to_jsonable(item)

    async def fail_job(self, job_id: str, claim_token: str, worker_id: str, error: str, retryable: bool = True, logs: str = "") -> dict[str, Any]:
        item = await self._locked_job(job_id, claim_token, worker_id)
        item.retry_count += 1
        item.error = error
        if logs:
            item.logs = self._append_log(item.logs, logs)
        if retryable and item.retry_count <= settings.worker_max_retries:
            item.status = "failed_retryable"
            item.run_after = utcnow() + timedelta(minutes=min(30, item.retry_count * 2))
        else:
            item.status = "failed_terminal"
        await get_repository().save_work_item(item)
        return to_jsonable(item)

    async def requeue_expired_claims(self) -> None:
        repo = get_repository()
        now = utcnow()
        for item in await repo.list_work_items(statuses={"claimed", "running"}):
            heartbeat = item.heartbeat_at or item.claimed_at or item.updated_at
            if heartbeat and (now - heartbeat).total_seconds() > item.timeout_seconds:
                item.status = "waiting_for_machine"
                item.worker_id = None
                item.claim_token = None
                item.error = "Worker heartbeat expired"
                await repo.save_work_item(item)

    async def _locked_job(self, job_id: str, claim_token: str, worker_id: str) -> WorkItem:
        item = await get_repository().get_work_item(job_id)
        if not item:
            raise ValueError("Job not found")
        if item.claim_token != claim_token or item.worker_id != worker_id:
            raise ValueError("Job claim does not belong to this worker")
        if item.status in TERMINAL_STATUSES:
            raise ValueError(f"Job is already terminal: {item.status}")
        return item

    async def _store_code_index(self, project: ProjectTwin, item: WorkItem, result: dict[str, Any]) -> None:
        index = result.get("code_index") or {}
        commit_sha = result.get("commit_sha") or index.get("commit_sha") or project.last_indexed_commit or "unknown"
        artifact = CodeIndexArtifact(
            project_id=project.id,
            idea_id=project.idea_id,
            commit_sha=commit_sha,
            file_inventory=index.get("file_inventory") or [],
            manifests=index.get("manifests") or [],
            dependency_graph=index.get("dependency_graph") or {},
            route_map=index.get("route_map") or [],
            test_commands=index.get("test_commands") or [],
            architecture_summary=index.get("architecture_summary") or "",
            risks=index.get("risks") or [],
            todos=index.get("todos") or [],
            searchable_chunks=index.get("searchable_chunks") or [],
        )
        await get_repository().put_code_index(artifact)
        project.last_indexed_commit = commit_sha
        project.detected_stack = index.get("detected_stack") or project.detected_stack
        project.test_commands = index.get("test_commands") or project.test_commands
        project.index_status = "indexed"
        if artifact.architecture_summary:
            await get_repository().put_report(
                Report(
                    idea_id=project.idea_id,
                    phase="tech_spec",
                    title="Codebase Dossier",
                    content=artifact.architecture_summary,
                    content_path=f"CODE_INDEX#{artifact.id}",
                )
            )

    def _slug(self, title: str) -> str:
        return re.sub(r"[^\w-]", "", title.lower().replace(" ", "-")) or "idea"

    def _append_log(self, current: str, new: str) -> str:
        text = f"{current.rstrip()}\n{new.strip()}".strip()
        return text[-20000:]
