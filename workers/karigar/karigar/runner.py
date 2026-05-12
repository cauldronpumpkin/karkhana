from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .backend_client import BackendClient

from .artifacts import normalize_output_dir, write_json_artifact, write_text_artifact
from .commands import SafeCommandPolicy
from .engines import MockEngine, get_engine
from .execution import CommandExecution, MockCommandRunner, SystemCommandRunner
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
            runner_for_verifications = self.command_runner or (
                SystemCommandRunner() if job.engine_name not in ("mock", "") else MockCommandRunner()
            )
            result.verification_results = self._run_verifications(job, runner_for_verifications)
            result.failure_reason = self._failure_reason(result, git_state)
        result.status = self._status_from_failure(result.failure_reason)
        result.summary = self._summary(job, result)
        result.review_report_path = str(self._write_review_report(job, result, git_state))
        result.completed_at = self._now()
        self._write_artifacts(job, result)
        return result

    def _base_result(self, job: JobContract) -> JobResult:
        """Dispatch to the appropriate engine based on job.engine_name."""
        engine = get_engine(job.engine_name)
        return engine.run(job)

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

    def _run_verifications(self, job: JobContract, runner: object | None = None) -> list[dict[str, object]]:
        policy = SafeCommandPolicy()
        cmd_runner = runner or self.command_runner or MockCommandRunner()
        results: list[dict[str, object]] = []
        for command in policy.iter_verified_commands(job.verification_commands):
            if policy.is_denied(command) or (job.denied_commands and any(bad in command for bad in job.denied_commands)):
                results.append(self._blocked_execution(command, "command denied by policy"))
                continue
            if job.allowed_commands and not any(good in command for good in job.allowed_commands):
                results.append(self._blocked_execution(command, "command not explicitly allowed"))
                continue
            execution = cmd_runner.run(command, job.command_timeout_seconds, cwd=job.repository_path, env=job.env)  # type: ignore[union-attr]
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
        engine_tag = f" [{job.engine_name}]" if job.engine_name not in ("mock", "") else ""
        return f"{job.task_title}: verification complete{engine_tag}"

    def _write_review_report(self, job: JobContract, result: JobResult, git_state: GitState) -> Path:
        report = build_review_report(task_title=job.task_title, branch_name=job.branch_name, changed_files=git_state.changed_files, verification_results=result.verification_results, logs_path=result.logs_path or "", diff_path=result.diff_path, next_recommendation="Run graphify update and then request human approval before merge.", graphify_required=git_state.code_or_docs_changed)
        return write_text_artifact(self._job_dir(job) / "review.md", report)

    def _write_artifacts(self, job: JobContract, result: JobResult) -> None:
        base = self._job_dir(job)
        write_json_artifact(base / "job.json", asdict(job))
        write_json_artifact(base / "result.json", result.to_dict())
        write_text_artifact(base / "logs.txt", self._build_logs(job, result))
        if result.diff_path:
            if job.engine_name in ("mock", ""):
                write_text_artifact(Path(result.diff_path), "diff unavailable in mock engine\n")
            else:
                try:
                    import subprocess
                    diff_result = subprocess.run(
                        ["git", "diff", "HEAD"],
                        cwd=job.repository_path,
                        capture_output=True, text=True, timeout=10
                    )
                    diff_content = diff_result.stdout if diff_result.returncode == 0 else "diff unavailable\n"
                    write_text_artifact(Path(result.diff_path), diff_content or "no changes\n")
                except Exception:
                    write_text_artifact(Path(result.diff_path), "diff generation failed\n")

    def _blocked_execution(self, command: str, summary: str) -> dict[str, object]:
        return {"command": command, "status": "blocked", "summary": summary, "stdout": "", "stderr": "", "exit_code": None, "duration_seconds": 0.0}

    def _execution_result(self, execution: CommandExecution, status: str) -> dict[str, object]:
        return {"command": execution.command, "status": status, "summary": (execution.stdout or execution.stderr or "completed")[:160], "stdout": execution.stdout, "stderr": execution.stderr, "exit_code": execution.return_code, "duration_seconds": execution.duration_seconds, "timed_out": execution.timed_out}

    def _build_logs(self, job: JobContract, result: JobResult) -> str:
        return json.dumps({"job_id": job.job_id, "status": result.status.value, "summary": result.summary}, indent=2, sort_keys=True)

    def run_backend_loop(
        self,
        api_base_url: str,
        worker_id: str,
        worker_token: str = "",
        poll_interval: float = 5.0,
        max_jobs: int = 0,
        factory_run_id: str = "",
    ) -> None:
        """Continuously claim jobs from backend, execute, and report results.

        Args:
            api_base_url: Backend API URL (e.g. https://api.karkhana.one)
            worker_id: Worker identifier
            worker_token: Auth token for the worker
            poll_interval: Seconds between job polls when idle
            max_jobs: Exit after this many jobs (0 = run forever)
            factory_run_id: If set, auto-create ledger entries after each job
        """
        from .backend_client import BackendClient

        client = BackendClient(
            api_base_url=api_base_url,
            worker_id=worker_id,
            worker_token=worker_token,
        )

        jobs_completed = 0
        consecutive_errors = 0

        while True:
            if max_jobs and jobs_completed >= max_jobs:
                break

            try:
                claim = client.claim_job()
            except Exception as exc:
                consecutive_errors += 1
                backoff = min(poll_interval * (2 ** min(consecutive_errors, 5)), 300)
                time.sleep(backoff)
                continue

            job_id = claim.get("job_id", "")
            claim_token = claim.get("claim_token", "")

            if not job_id:
                # No job available — idle poll
                consecutive_errors = 0
                time.sleep(poll_interval)
                continue

            consecutive_errors = 0

            # ── Emit job:started event ─────────────────────────────────
            if factory_run_id:
                self._emit_event_safe(
                    client,
                    factory_run_id,
                    "job:started",
                    {
                        "job_id": job_id,
                        "task_title": claim.get("task_title", ""),
                        "engine_name": claim.get("engine_name", "mock"),
                        "repository_path": claim.get("repository_path", ""),
                    },
                )

            result_dict: dict[str, object] = {}
            try:
                result = self.run_job(claim)

                # ── Emit job:checkpoint after verifications ────────────
                if factory_run_id:
                    self._emit_event_safe(
                        client,
                        factory_run_id,
                        "job:checkpoint",
                        {
                            "job_id": job_id,
                            "status": result.status.value,
                            "verification_count": len(result.verification_results),
                            "changed_files": result.changed_files,
                            "summary": result.summary,
                        },
                    )

                # ── Auto-Repair: retry on verification failure ─────
                auto_repair_enabled = (
                    claim.get("engine_config", {}).get("auto_repair", False)
                    or claim.get("metadata", {}).get("auto_repair", False)
                )
                if (
                    auto_repair_enabled
                    and result.status
                    not in (JobStatus.SUCCESS, JobStatus.BLOCKED, JobStatus.CANCELLED)
                ):
                    from .auto_repair import AutoRepairEngine

                    repair_engine = AutoRepairEngine(
                        max_retries=3,
                        backend_client=client if factory_run_id else None,
                        factory_run_id=factory_run_id,
                    )
                    result, _repair_history = repair_engine.execute_with_repair(
                        claim, self.run_job
                    )

                result_dict = result.to_dict()

                if result.status == JobStatus.SUCCESS:
                    client.complete_job(
                        job_id=job_id,
                        claim_token=claim_token,
                        result=result_dict,
                        logs=json.dumps(result_dict),
                        engine=result.engine_used,
                        branch_name=result.branch_name or "",
                    )
                    # ── Emit job:completed event ──────────────────────
                    if factory_run_id:
                        self._emit_event_safe(
                            client,
                            factory_run_id,
                            "job:completed",
                            {
                                "job_id": job_id,
                                "status": "success",
                                "engine_used": result.engine_used,
                                "summary": result.summary,
                                "branch_name": result.branch_name or "",
                            },
                        )
                elif result.status in (JobStatus.FAILED, JobStatus.TIMED_OUT):
                    client.fail_job(
                        job_id=job_id,
                        claim_token=claim_token,
                        error=result.failure_reason or result.summary,
                        retryable=result.status == JobStatus.TIMED_OUT,
                        logs=json.dumps(result_dict),
                    )
                    # ── Emit job:failed event ─────────────────────────
                    if factory_run_id:
                        self._emit_event_safe(
                            client,
                            factory_run_id,
                            "job:failed",
                            {
                                "job_id": job_id,
                                "status": result.status.value,
                                "error": result.failure_reason or result.summary,
                                "retryable": result.status == JobStatus.TIMED_OUT,
                            },
                        )
                else:
                    # BLOCKED, CANCELLED — report as failure, not retryable
                    client.fail_job(
                        job_id=job_id,
                        claim_token=claim_token,
                        error=result.failure_reason or result.summary,
                        retryable=False,
                        logs=json.dumps(result_dict),
                    )
                    # ── Emit job:failed event (blocked/cancelled) ─────
                    if factory_run_id:
                        self._emit_event_safe(
                            client,
                            factory_run_id,
                            "job:failed",
                            {
                                "job_id": job_id,
                                "status": result.status.value,
                                "error": result.failure_reason or result.summary,
                                "retryable": False,
                            },
                        )
            except Exception:
                # Best-effort failure report
                try:
                    client.fail_job(
                        job_id=job_id,
                        claim_token=claim_token,
                        error="Karigar execution exception",
                        retryable=True,
                    )
                    # ── Emit job:failed event (execution exception) ────
                    if factory_run_id:
                        self._emit_event_safe(
                            client,
                            factory_run_id,
                            "job:failed",
                            {
                                "job_id": job_id,
                                "status": "exception",
                                "error": "Karigar execution exception",
                                "retryable": True,
                            },
                        )
                except Exception:
                    pass

            jobs_completed += 1

            # ── Auto-append to Factory Run Ledger ─────────────────
            if factory_run_id:
                try:
                    from .backend_client import _build_ledger_body
                    client.create_ledger_entry(
                        run_id=factory_run_id,
                        title=f"Job {job_id}: {result_dict.get('summary', 'completed')[:80]}",
                        status="completed" if result.status == JobStatus.SUCCESS else "failed",
                        stage="execution",
                        body=_build_ledger_body(result_dict, job_id),
                    )
                except Exception:
                    # Ledger is best-effort — don't block job processing
                    pass

    @staticmethod
    def _emit_event_safe(
        client: "BackendClient",
        run_id: str,
        event_type: str,
        payload: dict[str, object],
    ) -> None:
        """Best-effort emit a run-scoped event to the backend WebSocket channel."""
        try:
            client.emit_event(run_id=run_id, event_type=event_type, payload=payload)  # type: ignore[union-attr]
        except Exception:
            # Emit failures must never block job processing
            pass

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
