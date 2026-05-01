from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .artifacts import normalize_output_dir, write_json_artifact, write_text_artifact
from .commands import SafeCommandPolicy
from .engines import MockEngine
from .execution import CommandExecution, MockCommandRunner
from .git_state import GitState, detect_git_state
from .models import JobContract, JobResult, JobStatus
from .review import build_review_report


@dataclass(slots=True)
class KarigarRunner:
    workspace: Path
    artifacts_dirname: str = "artifacts"
    command_runner: object | None = None

    def run_job(self, job_data: dict[str, object]) -> JobResult:
        job = JobContract.from_mapping(job_data)
        job_dir = self._job_dir(job)
        started_at = self._now()
        result = self._base_result(job)
        result.started_at = started_at
        result.logs_path = str(job_dir / "logs.txt")
        git_state = self._detect_git_state(Path(job.repository_path))
        result.diff_path = str(job_dir / "diff.patch") if git_state.is_repo and git_state.changed_files else None
        result.changed_files = git_state.changed_files
        result.git_state = git_state.to_dict()
        validation_error = self._validate(job)
        if validation_error:
            result.failure_reason = validation_error
        else:
            result.verification_results = self._run_verifications(job)
            result.failure_reason = self._failure_reason(result, git_state)
        result.status = self._status_from_failure(result.failure_reason)
        result.summary = self._summary(job, result)
        result.review_report_path = str(self._write_review_report(job, result, git_state))
        result.completed_at = self._now()
        self._write_artifacts(job, result)
        return result

    def _base_result(self, job: JobContract) -> JobResult:
        return MockEngine().run(job)

    def _validate(self, job: JobContract) -> str | None:
        missing = job.missing_required_fields()
        return f"missing required fields: {', '.join(missing)}" if missing else None

    def _status_from_failure(self, failure_reason: str | None) -> JobStatus:
        if failure_reason is None:
            return JobStatus.SUCCESS
        if failure_reason in {"graphify_update_required", "verification_blocked"}:
            return JobStatus.BLOCKED
        if failure_reason == "verification_timeout":
            return JobStatus.TIMED_OUT
        return JobStatus.FAILED

    def _failure_reason(self, result: JobResult, git_state: GitState) -> str | None:
        if any(item["status"] == "blocked" for item in result.verification_results):
            if git_state.code_or_docs_changed and not any("graphify update" in item["command"].lower() for item in result.verification_results):
                return "graphify_update_required"
            return "verification_blocked"
        if any(item["status"] == "timed_out" for item in result.verification_results):
            return "verification_timeout"
        if any(item["status"] == "failed" for item in result.verification_results):
            return "verification_failed"
        if git_state.code_or_docs_changed and not any("graphify update" in item["command"].lower() for item in result.verification_results):
            return "graphify_update_required"
        return None

    def _run_verifications(self, job: JobContract) -> list[dict[str, object]]:
        policy = SafeCommandPolicy()
        runner = self.command_runner or MockCommandRunner()
        results: list[dict[str, object]] = []
        for command in policy.iter_verified_commands(job.verification_commands):
            if policy.is_denied(command) or (job.denied_commands and any(bad in command for bad in job.denied_commands)):
                results.append(self._blocked_execution(command, "command denied by policy"))
                continue
            if job.allowed_commands and not any(good in command for good in job.allowed_commands):
                results.append(self._blocked_execution(command, "command not explicitly allowed"))
                continue
            execution = runner.run(command, job.command_timeout_seconds, cwd=job.repository_path, env=job.env)  # type: ignore[union-attr]
            status = "timed_out" if execution.timed_out else ("failed" if execution.return_code else "passed")
            results.append(self._execution_result(execution, status))
        return results

    def _job_dir(self, job: JobContract) -> Path:
        return normalize_output_dir(self.workspace / job.output_dir / job.job_id)

    def _detect_git_state(self, repo_root: Path) -> GitState:
        return detect_git_state(repo_root)

    def _summary(self, job: JobContract, result: JobResult) -> str:
        if result.failure_reason:
            return f"{job.task_title}: {result.failure_reason}"
        return f"{job.task_title}: verification complete"

    def _write_review_report(self, job: JobContract, result: JobResult, git_state: GitState) -> Path:
        report = build_review_report(task_title=job.task_title, branch_name=job.branch_name, changed_files=git_state.changed_files, verification_results=result.verification_results, logs_path=result.logs_path or "", diff_path=result.diff_path, next_recommendation="Run graphify update and then request human approval before merge.", graphify_required=git_state.code_or_docs_changed)
        return write_text_artifact(self._job_dir(job) / "review.md", report)

    def _write_artifacts(self, job: JobContract, result: JobResult) -> None:
        base = self._job_dir(job)
        write_json_artifact(base / "job.json", asdict(job))
        write_json_artifact(base / "result.json", result.to_dict())
        write_text_artifact(base / "logs.txt", self._build_logs(job, result))
        if result.diff_path:
            write_text_artifact(Path(result.diff_path), "diff unavailable in mock engine\n")

    def _blocked_execution(self, command: str, summary: str) -> dict[str, object]:
        return {"command": command, "status": "blocked", "summary": summary, "stdout": "", "stderr": "", "exit_code": None, "duration_seconds": 0.0}

    def _execution_result(self, execution: CommandExecution, status: str) -> dict[str, object]:
        return {"command": execution.command, "status": status, "summary": (execution.stdout or execution.stderr or "completed")[:160], "stdout": execution.stdout, "stderr": execution.stderr, "exit_code": execution.return_code, "duration_seconds": execution.duration_seconds, "timed_out": execution.timed_out}

    def _build_logs(self, job: JobContract, result: JobResult) -> str:
        return json.dumps({"job_id": job.job_id, "status": result.status.value, "summary": result.summary}, indent=2, sort_keys=True)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
