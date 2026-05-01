from __future__ import annotations

from dataclasses import dataclass

from .commands import SafeCommandPolicy
from .models import JobContract, JobResult, JobStatus


@dataclass(slots=True)
class MockEngine:
    """Deterministic engine used until real execution is wired in."""

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
            command=job.command,
            return_code=0,
            stdout=f"mocked: {job.command}",
            tests_passed=job.command.startswith("pytest") or "pytest" in job.command,
        )
