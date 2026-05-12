from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .models import JobResult, JobStatus


# ---------------------------------------------------------------------------
# Failure classification
# ---------------------------------------------------------------------------


class FailureClass(Enum):
    TEST_FAILURE = "test_failure"
    COMPILE_ERROR = "compile_error"
    REVIEW_REJECTION = "review_rejection"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class RepairAction(Enum):
    RETRY_WITH_DIAGNOSTICS = "retry_with_diagnostics"
    RETRY_WITH_LARGER_CONTEXT = "retry_with_larger_context"
    RETRY_SAME = "retry_same"
    ESCALATE = "escalate"


# ---------------------------------------------------------------------------
# Auto-repair engine
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class RepairAttempt:
    """Record of a single repair attempt for ledger tracking."""
    attempt: int
    status: str
    failure_class: str
    strategy: str
    failure_reason: str = ""
    summary: str = ""
    started_at: str = ""
    completed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt": self.attempt,
            "status": self.status,
            "failure_class": self.failure_class,
            "strategy": self.strategy,
            "failure_reason": self.failure_reason,
            "summary": self.summary,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass(slots=True)
class AutoRepairEngine:
    """Handles automatic retry and repair of failed job executions.

    When a verification step fails, the engine classifies the failure type,
    selects a repair strategy, and retries up to ``max_retries`` times before
    escalating the job to terminal ``failed``.

    Attributes:
        max_retries: Maximum repair attempts before escalation (default 3).
        backend_client: Optional BackendClient for ledger entry recording.
        factory_run_id: Optional factory run ID for ledger entries.
        _can_retry: Optional callback ``(job_id: str, attempt: int) -> bool``
            called before each retry to check (and consume) retry budget.
            When it returns ``False`` the engine escalates immediately.
        _on_repair: Optional callback ``(event: dict) -> None`` called after
            each repair attempt classification and on exhaustion.  Event dict
            has a ``"type"`` key (``"repair_attempt"`` or ``"repair_exhausted"``)
            plus contextual fields.
    """

    max_retries: int = 3
    backend_client: Any = None
    factory_run_id: str = ""
    _can_retry: Any = None     # Callable[[str, int], bool]
    _on_repair: Any = None     # Callable[[dict[str, Any]], None]

    # ── Public API ────────────────────────────────────────────

    def execute_with_repair(
        self,
        job_data: dict[str, Any],
        run_job_fn: Any,
    ) -> tuple[JobResult, list[RepairAttempt]]:
        """Wrap a job execution with automatic repair on verification failure.

        Args:
            job_data: Raw job claim dict (passed to ``run_job_fn``).
            run_job_fn: Callable that takes ``job_data`` and returns ``JobResult``.

        Returns:
            Tuple of ``(final_result, repair_history)``.  ``repair_history``
            contains one entry per execution (initial + retries).
        """
        repair_history: list[RepairAttempt] = []
        last_result: JobResult | None = None
        job_id = str(job_data.get("job_id", "unknown"))
        _exhaustion_emitted = False

        for attempt in range(self.max_retries + 1):
            result = run_job_fn(job_data)
            last_result = result

            entry = RepairAttempt(
                attempt=attempt,
                status=result.status.value,
                failure_class="",
                strategy="initial" if attempt == 0 else "",
                failure_reason=result.failure_reason or "",
                summary=result.summary,
                started_at=result.started_at or "",
                completed_at=result.completed_at or "",
            )

            if result.status == JobStatus.SUCCESS:
                entry.failure_class = "none"
                repair_history.append(entry)
                return result, repair_history

            # Blocked / Cancelled are not retryable
            if result.status in (JobStatus.BLOCKED, JobStatus.CANCELLED):
                repair_history.append(entry)
                return result, repair_history

            # ── Circuit breaker check (only after initial attempt) ──
            if attempt > 0 and self._can_retry is not None:
                if not self._can_retry(job_id, attempt):
                    entry.strategy = "circuit_breaker_blocked"
                    entry.failure_class = "circuit_breaker"
                    repair_history.append(entry)
                    break

            # Classify and determine repair strategy
            failure_class = self.classify_failure(result.to_dict())
            entry.failure_class = failure_class.value

            if self.should_escalate(attempt):
                entry.strategy = "escalate"
                repair_history.append(entry)
                if not _exhaustion_emitted and self._on_repair is not None:
                    _exhaustion_emitted = True
                    self._on_repair(self._build_repair_event(
                        "repair_exhausted", job_id, attempt, failure_class.value,
                        strategy="escalate", status=result.status.value,
                        total_attempts=len(repair_history),
                    ))
                break

            strategy = self.get_repair_strategy(failure_class, attempt)
            entry.strategy = strategy.value

            if strategy == RepairAction.ESCALATE:
                repair_history.append(entry)
                if not _exhaustion_emitted and self._on_repair is not None:
                    _exhaustion_emitted = True
                    self._on_repair(self._build_repair_event(
                        "repair_exhausted", job_id, attempt, failure_class.value,
                        strategy="escalate", status=result.status.value,
                        total_attempts=len(repair_history),
                    ))
                break

            repair_history.append(entry)

            # ── Emit repair attempt event (skip initial run) ──
            if attempt > 0 and self._on_repair is not None:
                self._on_repair(self._build_repair_event(
                    "repair_attempt", job_id, attempt, failure_class.value,
                    strategy=strategy.value, status=result.status.value,
                ))

            # Apply repair modifications to job_data for next attempt
            self._apply_repair(job_data, result, strategy, failure_class, attempt)

            # Create ledger entry for this repair attempt
            self._record_repair_ledger(job_data, entry)

        # ── Exhausted all retries ─────────────────────────────
        if last_result is not None:
            # Annotate the last result with repair history
            last_result.error = _build_escalation_error(repair_history)
        # Emit exhaustion event if not already emitted above
        if not _exhaustion_emitted and self._on_repair is not None:
            self._on_repair(self._build_repair_event(
                "repair_exhausted", job_id,
                attempt=len(repair_history),
                failure_class="exhausted",
                strategy="exhausted",
                status=last_result.status.value if last_result else "failed",
                total_attempts=len(repair_history),
            ))
        self._record_escalation_ledger(job_data, repair_history)
        return last_result or JobResult(
            job_id=str(job_data.get("job_id", "unknown")),
            status=JobStatus.FAILED,
            summary="Auto-repair exhausted retries",
        ), repair_history

    # ── Classification ────────────────────────────────────────

    def classify_failure(self, result: dict[str, Any]) -> FailureClass:
        """Inspect a result dict and return the failure class.

        Heuristics (in priority order):
            - TIMEOUT status → ``TIMEOUT``
            - verification stderr contains "Error:" / "error:" / "SyntaxError" → ``COMPILE_ERROR``
            - verification results with "test" in command and "failed" status → ``TEST_FAILURE``
            - failure_reason is "review_rejection" → ``REVIEW_REJECTION``
            - everything else → ``UNKNOWN``
        """
        status = result.get("status", "")
        if status == JobStatus.TIMED_OUT.value:
            return FailureClass.TIMEOUT

        failure_reason = str(result.get("failure_reason", "") or "").lower()
        if "review" in failure_reason:
            return FailureClass.REVIEW_REJECTION

        verification: list[dict[str, Any]] = result.get("verification_results", [])
        for v in verification:
            v_status = v.get("status", "")
            if v_status != "failed":
                continue
            cmd = str(v.get("command", "") or "").lower()
            stderr = str(v.get("stderr", "") or "")
            stdout = str(v.get("stdout", "") or "")
            combined = (stderr + stdout).lower()

            # Test failures
            if "test" in cmd or "pytest" in cmd or "unittest" in cmd:
                return FailureClass.TEST_FAILURE

            # Compilation-like errors
            compile_markers = [
                "syntaxerror", "syntax error", "compilation error",
                "compile error", "traceback", "typeerror", "nameerror",
                "indentationerror", "attributeerror",
            ]
            if any(marker in combined for marker in compile_markers):
                return FailureClass.COMPILE_ERROR

            # Check stderr for error markers
            error_markers = ["error:", "error ", "failed:", "assertionerror"]
            if any(marker in combined for marker in error_markers):
                return FailureClass.COMPILE_ERROR

        # Look at stdout/stderr at result level
        result_stderr = str(result.get("stderr", "") or "").lower()
        result_stdout = str(result.get("stdout", "") or "").lower()
        combined = (result_stderr + result_stdout)
        error_markers = ["syntaxerror", "compile error", "traceback", "error:"]
        if any(marker in combined for marker in error_markers):
            return FailureClass.COMPILE_ERROR

        return FailureClass.UNKNOWN

    # ── Strategy selection ────────────────────────────────────

    def get_repair_strategy(
        self, failure_class: FailureClass, attempt: int
    ) -> RepairAction:
        """Return the repair action for a given failure class and attempt number.

        Strategy per failure class:
            - TEST_FAILURE → RETRY_WITH_DIAGNOSTICS
            - COMPILE_ERROR → RETRY_WITH_DIAGNOSTICS
            - REVIEW_REJECTION → RETRY_WITH_LARGER_CONTEXT
            - TIMEOUT → RETRY_SAME (larger timeout window)
            - UNKNOWN → RETRY_SAME
        """
        if failure_class == FailureClass.TEST_FAILURE:
            return RepairAction.RETRY_WITH_DIAGNOSTICS
        if failure_class == FailureClass.COMPILE_ERROR:
            return RepairAction.RETRY_WITH_DIAGNOSTICS
        if failure_class == FailureClass.REVIEW_REJECTION:
            return RepairAction.RETRY_WITH_LARGER_CONTEXT
        if failure_class == FailureClass.TIMEOUT:
            return RepairAction.RETRY_SAME
        return RepairAction.RETRY_SAME

    def should_escalate(self, attempt: int) -> bool:
        """Return True when the retry budget is exhausted."""
        return attempt >= self.max_retries

    @staticmethod
    def _build_repair_event(
        event_type: str,
        job_id: str,
        attempt: int,
        failure_class: str,
        strategy: str,
        status: str,
        total_attempts: int = 0,
        **extra: Any,
    ) -> dict[str, Any]:
        """Build a structured event dict for repair lifecycle tracking."""
        event: dict[str, Any] = {
            "type": event_type,
            "job_id": job_id,
            "attempt": attempt,
            "failure_class": failure_class,
            "strategy": strategy,
            "status": status,
        }
        if total_attempts:
            event["total_attempts"] = total_attempts
        if extra:
            event.update(extra)
        return event

    # ── Repair application ────────────────────────────────────

    def _apply_repair(
        self,
        job_data: dict[str, Any],
        result: JobResult,
        strategy: RepairAction,
        failure_class: FailureClass,
        attempt: int,
    ) -> None:
        """Modify ``job_data`` in-place to improve chances on the next attempt."""
        if strategy == RepairAction.RETRY_WITH_DIAGNOSTICS:
            self._inject_diagnostics(job_data, result)
        elif strategy == RepairAction.RETRY_WITH_LARGER_CONTEXT:
            self._inject_context(job_data, result)
        # RETRY_SAME: no modification needed

    def _inject_diagnostics(self, job_data: dict[str, Any], result: JobResult) -> None:
        """Append failure diagnostics to the task prompt for re-execution."""
        diag = _build_diagnostic_brief(result)
        if not diag:
            return
        prompt = str(job_data.get("task_prompt") or job_data.get("prompt") or "")
        job_data["task_prompt"] = (
            prompt
            + "\n\n[Auto-Repair] The previous attempt failed. Use this diagnostic to fix:\n"
            + diag
        )

    def _inject_context(self, job_data: dict[str, Any], result: JobResult) -> None:
        """Expand the task prompt with additional context from the failed run."""
        context = _build_context_brief(result)
        if not context:
            return
        prompt = str(job_data.get("task_prompt") or job_data.get("prompt") or "")
        job_data["task_prompt"] = (
            prompt
            + "\n\n[Auto-Repair] The previous attempt was rejected. Additional context:\n"
            + context
        )

    # ── Ledger recording ──────────────────────────────────────

    def _record_repair_ledger(
        self, job_data: dict[str, Any], entry: RepairAttempt
    ) -> None:
        """Create a ledger entry for a single repair attempt (best-effort)."""
        if not self.backend_client or not self.factory_run_id:
            return
        job_id = str(job_data.get("job_id", "unknown"))
        try:
            self.backend_client.create_ledger_entry(
                run_id=self.factory_run_id,
                title=f"Repair attempt {entry.attempt} for Job {job_id}",
                status="active",
                stage="repair",
                body=_build_repair_ledger_body(entry, job_id),
            )
        except Exception:
            pass

    def _record_escalation_ledger(
        self, job_data: dict[str, Any], history: list[RepairAttempt]
    ) -> None:
        """Create a final ledger entry when retries are exhausted (best-effort)."""
        if not self.backend_client or not self.factory_run_id:
            return
        job_id = str(job_data.get("job_id", "unknown"))
        try:
            self.backend_client.create_ledger_entry(
                run_id=self.factory_run_id,
                title=f"Auto-repair exhausted for Job {job_id}",
                status="failed",
                stage="repair",
                body=_build_escalation_ledger_body(history, job_id),
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------


def _build_diagnostic_brief(result: JobResult) -> str:
    """Extract a short diagnostic snippet from a failed JobResult."""
    parts: list[str] = []

    failure = result.failure_reason or ""
    if failure:
        parts.append(f"Failure reason: {failure}")

    for v in result.verification_results:
        if v.get("status") != "failed":
            continue
        cmd = v.get("command", "")
        stderr = str(v.get("stderr", "") or "")
        stdout = str(v.get("stdout", "") or "")
        if stderr:
            parts.append(f"Command `{cmd}` stderr:\n{stderr[:800]}")
        if stdout:
            parts.append(f"Command `{cmd}` stdout:\n{stdout[:800]}")

    # Fallback: engine-level stderr/stdout
    if not parts and result.stderr:
        parts.append(f"Engine stderr:\n{result.stderr[:800]}")
    if not parts and result.stdout:
        parts.append(f"Engine stdout:\n{result.stdout[:800]}")

    return "\n\n".join(parts) if parts else ""


def _build_context_brief(result: JobResult) -> str:
    """Build a context summary for review-rejection retries."""
    parts: list[str] = []

    if result.failure_reason:
        parts.append(f"Rejection reason: {result.failure_reason}")

    if result.changed_files:
        parts.append(f"Changed files: {', '.join(result.changed_files)}")

    for v in result.verification_results:
        summary = v.get("summary", "")
        if summary:
            parts.append(f"Verification: {summary}")

    return "\n".join(parts) if parts else ""


def _build_escalation_error(history: list[RepairAttempt]) -> str:
    """Build an error message summarising all repair attempts."""
    lines = [f"Auto-repair exhausted after {len(history)} attempts:"]
    for entry in history:
        lines.append(
            f"  Attempt {entry.attempt}: {entry.status} "
            f"({entry.failure_class}, strategy={entry.strategy})"
        )
    return "\n".join(lines)


def _build_repair_ledger_body(entry: RepairAttempt, job_id: str) -> str:
    """Build a markdown ledger body for a single repair attempt."""
    return "\n".join([
        f"# Repair Attempt {entry.attempt} — Job {job_id}",
        "",
        f"**Status:** {entry.status}",
        f"**Failure class:** {entry.failure_class}",
        f"**Strategy:** {entry.strategy}",
        f"**Failure reason:** {entry.failure_reason}",
        f"**Summary:** {entry.summary}",
        "",
    ])


def _build_escalation_ledger_body(history: list[RepairAttempt], job_id: str) -> str:
    """Build a markdown ledger body for exhausted retries."""
    lines = [
        f"# Auto-Repair Exhausted — Job {job_id}",
        "",
        f"**Total attempts:** {len(history)}",
        "",
        "## Attempt History",
        "",
        "| Attempt | Status | Failure Class | Strategy | Summary |",
        "|---------|--------|---------------|----------|---------|",
    ]
    for entry in history:
        lines.append(
            f"| {entry.attempt} | {entry.status} | {entry.failure_class} "
            f"| {entry.strategy} | {entry.summary[:60]} |"
        )
    lines.append("")
    return "\n".join(lines)


__all__ = [
    "AutoRepairEngine",
    "FailureClass",
    "RepairAction",
    "RepairAttempt",
]
