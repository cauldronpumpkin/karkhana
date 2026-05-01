from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class JobStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    BLOCKED = "blocked"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class JobContract:
    job_id: str
    repository_path: str
    task_title: str
    task_prompt: str
    branch_name: str
    engine_name: str
    allowed_paths: list[str] = field(default_factory=list)
    denied_paths: list[str] = field(default_factory=list)
    allowed_commands: list[str] = field(default_factory=list)
    denied_commands: list[str] = field(default_factory=list)
    verification_commands: list[str] = field(default_factory=list)
    step_timeout_seconds: int = 600
    command_timeout_seconds: int = 300
    output_dir: str = "artifacts"
    metadata: dict[str, Any] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)
    repo_root: str = ""
    worktree_path: str = ""
    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    allow_network: bool = False
    allow_git_write: bool = False
    job_type: str = "mock"

    @property
    def validated(self) -> bool:
        return all([self.job_id, self.repository_path, self.task_title, self.task_prompt, self.branch_name, self.engine_name])

    def missing_required_fields(self) -> list[str]:
        missing: list[str] = []
        for field_name in ("job_id", "repository_path", "task_title", "task_prompt", "branch_name", "engine_name"):
            if not getattr(self, field_name):
                missing.append(field_name)
        return missing

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "JobContract":
        repository_path = str(data.get("repository_path") or data.get("repo_root") or data.get("worktree_path") or ".")
        branch_name = str(data.get("branch_name") or data.get("desired_branch_name") or "karigar/local-review")
        return cls(
            job_id=str(data.get("job_id") or data.get("id") or ""),
            repository_path=repository_path,
            task_title=str(data.get("task_title") or data.get("title") or "Karigar local job"),
            task_prompt=str(data.get("task_prompt") or data.get("prompt") or ""),
            branch_name=branch_name,
            engine_name=str(data.get("engine_name") or data.get("engine") or "mock"),
            allowed_paths=[str(item) for item in data.get("allowed_paths") or []],
            denied_paths=[str(item) for item in data.get("denied_paths") or []],
            allowed_commands=[str(item) for item in data.get("allowed_commands") or []],
            denied_commands=[str(item) for item in data.get("denied_commands") or []],
            verification_commands=[str(item) for item in (data.get("verification_commands") or data.get("verify_commands") or [])],
            step_timeout_seconds=int(data.get("step_timeout_seconds") or data.get("step_time_limit_seconds") or 600),
            command_timeout_seconds=int(data.get("command_timeout_seconds") or data.get("verification_timeout_seconds") or 300),
            output_dir=str(data.get("output_dir") or data.get("artifacts_dir") or "artifacts"),
            metadata=dict(data.get("metadata") or {}),
            payload=dict(data.get("payload") or {}),
            repo_root=str(data.get("repo_root") or repository_path),
            worktree_path=str(data.get("worktree_path") or repository_path),
            command=str(data.get("command") or ""),
            args=[str(item) for item in data.get("args") or []],
            env={str(key): str(value) for key, value in (data.get("env") or {}).items()},
            allow_network=bool(data.get("allow_network", False)),
            allow_git_write=bool(data.get("allow_git_write", False)),
            job_type=str(data.get("job_type") or "mock"),
        )


@dataclass(slots=True)
class JobResult:
    job_id: str
    status: JobStatus
    summary: str
    engine_used: str = "mock"
    branch_name: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    changed_files: list[str] = field(default_factory=list)
    verification_results: list[dict[str, Any]] = field(default_factory=list)
    logs_path: str | None = None
    diff_path: str | None = None
    failure_reason: str | None = None
    structured_events: list[dict[str, Any]] = field(default_factory=list)
    review_report_path: str | None = None
    command: str = ""
    return_code: int = 0
    stdout: str = ""
    stderr: str = ""
    commit_sha: str | None = None
    tests_passed: bool = False
    graphify_updated: bool = False
    ledger_updated: bool = False
    blocked_reason: str | None = None
    error: str | None = None
    artifacts: list[str] = field(default_factory=list)
    git_state: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "summary": self.summary,
            "engine_used": self.engine_used,
            "branch_name": self.branch_name,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "changed_files": self.changed_files,
            "verification_results": self.verification_results,
            "logs_path": self.logs_path,
            "diff_path": self.diff_path,
            "failure_reason": self.failure_reason,
            "structured_events": self.structured_events,
            "review_report_path": self.review_report_path,
            "command": self.command,
            "return_code": self.return_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "commit_sha": self.commit_sha,
            "tests_passed": self.tests_passed,
            "graphify_updated": self.graphify_updated,
            "ledger_updated": self.ledger_updated,
            "blocked_reason": self.blocked_reason,
            "error": self.error,
            "artifacts": self.artifacts,
            "git_state": self.git_state,
        }
