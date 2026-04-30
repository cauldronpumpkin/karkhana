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
from backend.app.services.factory_tracking import collect_factory_run_bundle, refresh_factory_run_tracking_manifest
from backend.app.services.factory_tracking import normalize_token_economy
from backend.app.services.factory_run_ledger import extract_compact_ledger_context, validate_ledger_metadata
from backend.app.services.worker_sqs import WorkerSqsPublisher

CLAIMABLE_STATUSES = {"queued", "waiting_for_machine", "failed_retryable"}
OPEN_JOB_STATUSES = {"queued", "waiting_for_machine", "failed_retryable", "claimed", "running"}
TERMINAL_STATUSES = {"completed", "cancelled", "failed_terminal"}
DUPLICATE_WORK_MATCH_STATUSES = OPEN_JOB_STATUSES | {"completed"}


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


def _duplicate_work_keys(item: WorkItem) -> set[str]:
    payload = item.payload or {}
    keys = {
        key
        for key in (
            payload.get("duplicate_work_key"),
            item.idempotency_key,
            item.dedupe_hash,
        )
        if key
    }
    return keys


def _duplicate_work_detected(item: WorkItem) -> bool:
    payload = item.payload or {}
    result = item.result or {}
    token_economy = result.get("token_economy") if isinstance(result, dict) else {}
    return bool(
        payload.get("duplicate_work_detected")
        or payload.get("duplicate_work_key")
        or result.get("duplicate_work_detected")
        or (token_economy.get("duplicate_work_detected") if isinstance(token_economy, dict) else False)
    )


class ProjectTwinService:
    def __init__(self, sqs_publisher: WorkerSqsPublisher | None = None) -> None:
        self.sqs_publisher = sqs_publisher or WorkerSqsPublisher()

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
        factory_runs = []
        for run in (await repo.list_factory_runs(idea_id=idea_id))[:5]:
            bundle = await collect_factory_run_bundle(repo, run.id)
            if bundle:
                factory_runs.append({
                    "factory_run": to_jsonable(bundle["factory_run"]),
                    "tracking_manifest": to_jsonable(bundle["tracking_manifest"]),
                    "tracking_summary": bundle["tracking_summary"],
                    "phases": [to_jsonable(phase) for phase in bundle["phases"]],
                })
        return {
            "idea": to_jsonable(idea),
            "project": to_jsonable(project),
            "latest_index": to_jsonable(latest_index) if latest_index else None,
            "jobs": [to_jsonable(job) for job in jobs],
            "agent_runs": [to_jsonable(run) for run in runs[:10]],
            "commits": [to_jsonable(commit) for commit in commits[:10]],
            "factory_runs": factory_runs,
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
        factory_run_id: str | None = None,
        parent_work_item_id: str | None = None,
        rationale: str | None = None,
        correlation_id: str | None = None,
        dedupe_hash: str | None = None,
        budget: dict[str, Any] | None = None,
        stop_conditions: list[str] | None = None,
        branch_name: str | None = None,
        ledger_path: str | None = None,
        ledger_policy: str = "none",
    ) -> WorkItem:
        repo = get_repository()
        ledger_metadata = validate_ledger_metadata(
            ledger_path=ledger_path,
            ledger_policy=ledger_policy,
        )
        payload_data = dict(payload or {})
        effective_factory_run_id = factory_run_id or payload_data.get("factory_run_id")
        payload_data["factory_run_id"] = effective_factory_run_id
        payload_data["ledger_policy"] = ledger_metadata["ledger_policy"]
        payload_data["ledger_path"] = ledger_metadata["ledger_path"]
        payload_data["ledger_context"] = extract_compact_ledger_context(ledger_metadata["ledger_path"])
        item = WorkItem(
            idea_id=idea_id,
            project_id=project_id,
            job_type=job_type,
            payload=payload_data,
            idempotency_key=idempotency_key,
            priority=priority,
            timeout_seconds=settings.worker_claim_timeout_seconds,
            factory_run_id=effective_factory_run_id,
            parent_work_item_id=parent_work_item_id,
            rationale=rationale,
            correlation_id=correlation_id,
            dedupe_hash=dedupe_hash,
            budget=dict(budget or {}),
            stop_conditions=list(stop_conditions or []),
            branch_name=branch_name,
            ledger_path=ledger_metadata["ledger_path"],
            ledger_policy=ledger_metadata["ledger_policy"],
        )
        await self._mark_duplicate_work(item, repo=repo)
        await repo.save_work_item(item)
        project = await repo.get_project_twin_by_id(project_id)
        if project:
            await self.sqs_publisher.send_job_available(item, project)
        return item

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
            if capabilities:
                autonomy_level = (item.payload or {}).get("autonomy_level", "")
                from backend.app.services.autonomy import validate_worker_capabilities_for_autonomy
                missing = validate_worker_capabilities_for_autonomy(
                    capabilities, autonomy_level, worker_name=worker_id
                )
                if missing:
                    item.status = "failed_terminal"
                    item.error = (
                        f"Worker '{worker_id}' missing required capabilities for "
                        f"autonomy level '{autonomy_level}': {', '.join(missing)}. "
                        f"High-autonomy Factory Runs require opencode-server engine."
                    )
                    await repo.save_work_item(item)
                    continue
            item.status = "claimed"
            item.worker_id = worker_id
            item.claim_token = str(uuid.uuid4())
            item.claimed_at = utcnow()
            item.heartbeat_at = item.claimed_at
            await repo.save_work_item(item)
            await self._refresh_factory_tracking(item)
            return {"job": to_jsonable(item), "project": to_jsonable(project)}
        return None

    async def heartbeat_job(self, job_id: str, claim_token: str, worker_id: str, logs: str = "") -> dict[str, Any]:
        item = await self._locked_job(job_id, claim_token, worker_id)
        item.status = "running"
        item.heartbeat_at = utcnow()
        if logs:
            item.logs = self._append_log(item.logs, logs)
        await get_repository().save_work_item(item)
        await self._refresh_factory_tracking(item)
        return to_jsonable(item)

    async def complete_job(self, job_id: str, claim_token: str, worker_id: str, result: dict[str, Any] | None = None, logs: str = "") -> dict[str, Any]:
        repo = get_repository()
        item = await self._locked_job(job_id, claim_token, worker_id)
        result = dict(result or {})
        payload = item.payload or {}
        factory_run_id = payload.get("factory_run_id")
        ledger_sections_updated = result.get("ledger_sections_updated") or []
        if result.get("ledger_updated"):
            result["ledger_updated"] = True
            result["ledger_sections_updated"] = list(ledger_sections_updated)
        if item.ledger_policy in {"required", "strict"} and not result.get("ledger_updated"):
            warning = (
                "factory run ledger must be updated before completion. "
                "Set ledger_updated=true and ledger_sections_updated in the result."
            )
            result["ledger_validation_warnings"] = list(result.get("ledger_validation_warnings") or []) + [warning]
            if item.ledger_policy == "strict":
                item.status = "failed_terminal"
                item.error = warning
                item.result = result
                item.logs = self._append_log(item.logs, logs or f"[WARNING] {warning}")
                item.heartbeat_at = utcnow()
                await repo.save_work_item(item)
                await self._refresh_factory_tracking(item)
                return to_jsonable(item)
            item.logs = self._append_log(item.logs, f"[WARNING] {warning}")
        if factory_run_id and item.job_type != "repo_index":
            graphify_updated = result.get("graphify_updated", False)
            verification_commands = payload.get("verification_commands") or []
            has_graphify_cmd = any("graphify update" in cmd for cmd in verification_commands)
            if has_graphify_cmd and not graphify_updated:
                logs_combined = f"{logs}\n" if logs else ""
                logs_combined += (
                    "[WARNING] graphify update . must be run before completion to keep the "
                    "knowledge graph current. Set graphify_updated=true in the result."
                )
                item.logs = self._append_log(item.logs, logs_combined)
        result["token_economy"] = normalize_token_economy(
            result.get("token_economy"),
            work_item=item,
            payload=payload,
            result=result,
        )
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
        await self._refresh_factory_tracking(item)

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
        await self._refresh_factory_tracking(item)
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
                await self._refresh_factory_tracking(item)

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

    async def _refresh_factory_tracking(self, item: WorkItem) -> None:
        payload = item.payload or {}
        factory_run_id = payload.get("factory_run_id")
        if not factory_run_id:
            return
        await refresh_factory_run_tracking_manifest(get_repository(), factory_run_id)

    async def _mark_duplicate_work(self, item: WorkItem, *, repo: Any) -> None:
        payload = dict(item.payload or {})
        candidate_keys = [key for key in (payload.get("duplicate_work_key"), item.idempotency_key, item.dedupe_hash) if key]
        if not candidate_keys:
            item.payload = payload
            return

        existing_items = await repo.list_work_items(
            idea_id=item.idea_id,
            statuses=DUPLICATE_WORK_MATCH_STATUSES,
        )
        for existing in existing_items:
            if existing.id == item.id or existing.project_id != item.project_id:
                continue
            if _duplicate_work_keys(existing) & set(candidate_keys):
                payload["duplicate_work_detected"] = True
                payload.setdefault("duplicate_work_key", next(
                    key for key in candidate_keys if key in _duplicate_work_keys(existing)
                ))
                item.payload = payload
                return

        item.payload = payload
