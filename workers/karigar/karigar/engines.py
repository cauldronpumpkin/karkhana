from __future__ import annotations

import shlex
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone

from .commands import SafeCommandPolicy
from .models import JobContract, JobResult, JobStatus


# ---------------------------------------------------------------------------
# Engine registry
# ---------------------------------------------------------------------------

_ENGINE_REGISTRY: dict[str, type[RealEngine]] = {}


def register_engine(engine_cls: type[RealEngine]) -> type[RealEngine]:
    """Register an engine class so it can be looked up by name."""
    _ENGINE_REGISTRY[engine_cls.engine_name] = engine_cls
    return engine_cls


def get_engine(name: str) -> RealEngine:
    """Retrieve an engine instance by name."""
    cls = _ENGINE_REGISTRY.get(name)
    if cls is None:
        raise ValueError(f"Unknown engine: {name}. Available: {list(_ENGINE_REGISTRY.keys())}")
    return cls()


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class RealEngine(ABC):
    """Abstract base for all job execution engines."""

    engine_name: str = "base"

    @abstractmethod
    def run(self, job: JobContract) -> JobResult:
        """Execute a job contract and return a structured result."""
        ...

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Concrete engines
# ---------------------------------------------------------------------------


@register_engine
@dataclass(slots=True)
class MockEngine(RealEngine):
    """Deterministic engine used until real execution is wired in."""

    engine_name = "mock"
    policy: SafeCommandPolicy = SafeCommandPolicy()

    def run(self, job: JobContract) -> JobResult:
        """Produce a structured result without executing untrusted commands."""

        if not job.command:
            return JobResult(job_id=job.job_id, status=JobStatus.BLOCKED, summary="No command provided", blocked_reason="missing_command")
        if not self.policy.is_allowed(job.command):
            return JobResult(job_id=job.job_id, status=JobStatus.BLOCKED, summary="Command denied by policy", command=job.command, blocked_reason="unsafe_command")
        return JobResult(
            job_id=job.job_id,
            status=JobStatus.SUCCESS,
            summary="Mock execution completed",
            engine_used="mock",
            command=job.command,
            return_code=0,
            stdout=f"mocked: {job.command}",
            tests_passed=job.command.startswith("pytest") or "pytest" in job.command,
        )


@register_engine
@dataclass(slots=True)
class OpenCodeEngine(RealEngine):
    """Execute tasks via the opencode CLI tool."""

    engine_name = "opencode"

    def run(self, job: JobContract) -> JobResult:
        """Run opencode with the job's task prompt."""

        if not job.task_prompt:
            return JobResult(
                job_id=job.job_id,
                status=JobStatus.BLOCKED,
                summary="No task prompt provided",
                engine_used="opencode",
                blocked_reason="missing_task_prompt",
            )

        started_at = self._now()

        # Primary command
        primary_cmd = f"opencode run --prompt {shlex.quote(job.task_prompt)}"
        result = self._run_command(primary_cmd, job)

        # Fallback to chat if run subcommand isn't available
        if result is not None and result.returncode != 0:
            fallback_cmd = f"opencode chat -q {shlex.quote(job.task_prompt)}"
            result = self._run_command(fallback_cmd, job)

        completed_at = self._now()

        if result is None:
            return JobResult(
                job_id=job.job_id,
                status=JobStatus.TIMED_OUT,
                summary="OpenCode execution timed out",
                engine_used="opencode",
                started_at=started_at,
                completed_at=completed_at,
            )

        if result.returncode != 0:
            return JobResult(
                job_id=job.job_id,
                status=JobStatus.FAILED,
                summary="OpenCode execution failed",
                engine_used="opencode",
                command=primary_cmd,
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                failure_reason=result.stderr[:500] if result.stderr else f"Exit code {result.returncode}",
                started_at=started_at,
                completed_at=completed_at,
            )

        changed_files = self._detect_changed_files(job.repository_path)
        commit_sha = self._get_commit_sha(job.repository_path)
        tests_passed = "PASS" in result.stdout or "All tests passed" in result.stdout

        return JobResult(
            job_id=job.job_id,
            status=JobStatus.SUCCESS,
            summary="OpenCode execution completed",
            engine_used="opencode",
            command=primary_cmd,
            return_code=0,
            stdout=result.stdout,
            stderr=result.stderr,
            changed_files=changed_files,
            commit_sha=commit_sha,
            tests_passed=tests_passed,
            structured_events=[{"event": "opencode_completed", "timestamp": completed_at}],
            started_at=started_at,
            completed_at=completed_at,
        )

    def _run_command(self, command: str, job: JobContract) -> subprocess.CompletedProcess[str] | None:
        """Run a shell command with timeout handling."""
        try:
            return subprocess.run(
                command,
                shell=True,
                cwd=job.repository_path,
                capture_output=True,
                text=True,
                timeout=job.step_timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return None

    @staticmethod
    def _detect_changed_files(repo_path: str) -> list[str]:
        """Detect files changed since HEAD via git diff."""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return [line for line in result.stdout.strip().splitlines() if line]
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return []

    @staticmethod
    def _get_commit_sha(repo_path: str) -> str | None:
        """Retrieve the current HEAD commit SHA."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return None


@register_engine
@dataclass(slots=True)
class HermesAgentEngine(RealEngine):
    """Execute tasks via the hermes CLI tool."""

    engine_name = "hermes"

    def run(self, job: JobContract) -> JobResult:
        """Run hermes with the job's task prompt."""

        if not job.task_prompt:
            return JobResult(
                job_id=job.job_id,
                status=JobStatus.BLOCKED,
                summary="No task prompt provided",
                engine_used="hermes",
                blocked_reason="missing_task_prompt",
            )

        started_at = self._now()

        model = job.metadata.get("hermes_model") or job.payload.get("hermes_model")
        if model:
            command = f"hermes chat -m {shlex.quote(str(model))} -q {shlex.quote(job.task_prompt)}"
        else:
            command = f"hermes chat -q {shlex.quote(job.task_prompt)}"

        result = self._run_command(command, job)
        completed_at = self._now()

        if result is None:
            return JobResult(
                job_id=job.job_id,
                status=JobStatus.TIMED_OUT,
                summary="Hermes execution timed out",
                engine_used="hermes",
                started_at=started_at,
                completed_at=completed_at,
            )

        if result.returncode != 0:
            return JobResult(
                job_id=job.job_id,
                status=JobStatus.FAILED,
                summary="Hermes execution failed",
                engine_used="hermes",
                command=command,
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                failure_reason=result.stderr[:500] if result.stderr else f"Exit code {result.returncode}",
                started_at=started_at,
                completed_at=completed_at,
            )

        changed_files = self._detect_changed_files(job.repository_path)
        commit_sha = self._get_commit_sha(job.repository_path)
        tests_passed = "PASS" in result.stdout or "All tests passed" in result.stdout

        return JobResult(
            job_id=job.job_id,
            status=JobStatus.SUCCESS,
            summary="Hermes execution completed",
            engine_used="hermes",
            command=command,
            return_code=0,
            stdout=result.stdout,
            stderr=result.stderr,
            changed_files=changed_files,
            commit_sha=commit_sha,
            tests_passed=tests_passed,
            structured_events=[{"event": "hermes_completed", "timestamp": completed_at}],
            started_at=started_at,
            completed_at=completed_at,
        )

    def _run_command(self, command: str, job: JobContract) -> subprocess.CompletedProcess[str] | None:
        """Run a shell command with timeout handling."""
        try:
            return subprocess.run(
                command,
                shell=True,
                cwd=job.repository_path,
                capture_output=True,
                text=True,
                timeout=job.step_timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return None

    @staticmethod
    def _detect_changed_files(repo_path: str) -> list[str]:
        """Detect files changed since HEAD via git diff."""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return [line for line in result.stdout.strip().splitlines() if line]
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return []

    @staticmethod
    def _get_commit_sha(repo_path: str) -> str | None:
        """Retrieve the current HEAD commit SHA."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return None
