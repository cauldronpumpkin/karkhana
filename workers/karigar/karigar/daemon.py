from __future__ import annotations

import json
import os
import signal
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .auto_repair import AutoRepairEngine
from .backend_client import BackendClient, _build_ledger_body
from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from .models import JobResult, JobStatus
from .runner import KarigarRunner


# ── sentinel for unset defaults ────────────────────────────────
_UNSET = object()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ======================================================================
# Config & State data-classes
# ======================================================================


@dataclass(slots=True)
class DaemonConfig:
    """Configuration for the Karigar daemon controller.

    Attributes:
        poll_interval: Seconds between job polls when idle (default 20).
        heartbeat_interval: Seconds between heartbeat calls for in-flight jobs
            (default 15).
        run_once: When ``True``, execute a single claim-execute-report cycle
            and exit.  Intended for Windows service / Tauri desktop worker
            integration.
        state_dir: Directory where ``daemon.json`` and other runtime state
            is persisted (default ``~/.karigar``).
    """

    poll_interval: float = 20.0
    heartbeat_interval: float = 15.0
    run_once: bool = False
    state_dir: Path = field(default_factory=lambda: Path.home() / ".karigar")


@dataclass
class DaemonState:
    """Persistent daemon state written to ``daemon.json``.

    Attributes:
        worker_id: The worker's backend identifier.
        last_seen_job: ID of the most recently processed job.
        jobs_completed_today: Successful + failed jobs for the current UTC day.
        jobs_failed_today: Jobs that ended in FAILED / TIMED_OUT.
        total_spend: Running estimate of total token spend in USD (informational).
        today: ISO date string for the day these counters represent.
        last_heartbeat_utc: ISO timestamp of the most recent heartbeat.
    """

    worker_id: str = ""
    last_seen_job: str = ""
    jobs_completed_today: int = 0
    jobs_failed_today: int = 0
    total_spend: float = 0.0
    today: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    last_heartbeat_utc: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DaemonState":
        return cls(
            worker_id=str(data.get("worker_id", "")),
            last_seen_job=str(data.get("last_seen_job", "")),
            jobs_completed_today=int(data.get("jobs_completed_today", 0)),
            jobs_failed_today=int(data.get("jobs_failed_today", 0)),
            total_spend=float(data.get("total_spend", 0.0)),
            today=str(data.get("today", "")),
            last_heartbeat_utc=str(data.get("last_heartbeat_utc", "")),
        )


# ======================================================================
# Daemon controller
# ======================================================================


class DaemonController:
    """Orchestrates the poll-claim-execute-report loop with daemon features.

    Wraps ``KarigarRunner`` and ``BackendClient``, adding:

    * Graceful shutdown on SIGTERM / SIGINT.
    * Persistent state file at ``~/.karigar/daemon.json``.
    * Heartbeat thread that pings the backend every 15 s for in-flight jobs.
    * Circuit-breaker integration for daily caps and per-job retry limits.
    * ``--run-once`` mode for Tauri / Windows service integration.
    """

    def __init__(
        self,
        runner: KarigarRunner,
        client: BackendClient,
        config: DaemonConfig | None = None,
        circuit_config: CircuitBreakerConfig | None = None,
        factory_run_id: str = "",
    ) -> None:
        self.runner = runner
        self.client = client
        self.config = config or DaemonConfig()
        self.circuit = CircuitBreaker(config=circuit_config or CircuitBreakerConfig())
        self.factory_run_id = factory_run_id

        # ── mutable runtime state ──────────────────────────
        self.state = self._load_state()
        self.state.worker_id = client.worker_id

        self._shutdown = threading.Event()
        self._heartbeat_stop = threading.Event()
        self._current_job_id: str = ""
        self._current_claim_token: str = ""
        self._current_result: JobResult | None = None

        # Ensure state directory exists
        self.config.state_dir.mkdir(parents=True, exist_ok=True)

    # ── public entry points ─────────────────────────────────

    def run(self) -> None:
        """Start the daemon loop.  Blocks until shutdown or ``--run-once``."""
        self._install_signal_handlers()
        print(f"[karigar] Daemon starting (worker={self.client.worker_id}, "
              f"poll={self.config.poll_interval}s, "
              f"heartbeat={self.config.heartbeat_interval}s, "
              f"run_once={self.config.run_once})")

        try:
            while not self._shutdown.is_set():
                self._check_day_rollover()
                self._run_cycle()

                if self.config.run_once:
                    break

                # Idle sleep with early wake on shutdown
                self._sleep_interruptible(self.config.poll_interval)
        finally:
            self._shutdown_cleanup()

    def status(self) -> dict[str, Any]:
        """Return the current daemon state as a dict (for CLI ``status``)."""
        self._check_day_rollover()
        return {
            **self.state.to_dict(),
            "circuit": self.circuit.get_state(),
            "daemon_running": not self._shutdown.is_set(),
            "current_job": self._current_job_id or None,
            "state_file": str(self._state_path()),
        }

    # ── signal handling ─────────────────────────────────────

    def _install_signal_handlers(self) -> None:
        """Register SIGTERM / SIGINT handlers (best-effort on Windows)."""
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                signal.signal(sig, self._handle_signal)
            except (AttributeError, ValueError):
                # SIGTERM / SIGINT may not exist on all platforms; ignore.
                pass

    def _handle_signal(self, signum: int, frame: Any) -> None:
        sig_name = signal.Signals(signum).name
        print(f"\n[karigar] Received {sig_name} — shutting down gracefully...",
              file=sys.stderr)
        self._shutdown.set()

    # ── main cycle ──────────────────────────────────────────

    def _run_cycle(self) -> None:
        """Claim → execute → report (one iteration)."""
        # ── Circuit breaker check ───────────────────────────
        if not self.circuit.can_claim():
            return

        # ── Claim ───────────────────────────────────────────
        claim = self._claim_with_retry()
        if claim is None:
            return  # shutdown or persistent failure

        job_id = claim.get("job_id", "")
        claim_token = claim.get("claim_token", "")
        self._current_job_id = job_id
        self._current_claim_token = claim_token
        self._current_result = None

        if not job_id:
            self._reset_current()
            return

        self.circuit.record_claim(job_id)

        # Estimate tokens before execution (best-effort budgeting)
        prompt = str(claim.get("task_prompt") or claim.get("prompt") or "")
        if prompt:
            self.circuit.record_tokens(self.circuit.estimate_tokens(prompt))

        # ── Heartbeat thread ────────────────────────────────
        self._heartbeat_stop.clear()
        heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, daemon=True
        )
        heartbeat_thread.start()

        try:
            # ── Execute ─────────────────────────────────────
            result = self.runner.run_job(claim)

            # ── Auto-Repair ─────────────────────────────────
            result = self._try_auto_repair(claim, result)

            self._current_result = result

            # ── Report ──────────────────────────────────────
            self._report_result(job_id, claim_token, result)

            # ── Update state ────────────────────────────────
            self._update_state_after_job(result)

            # ── Ledger ──────────────────────────────────────
            self._append_ledger(job_id, result)

        except Exception as exc:
            print(f"[karigar] Job {job_id} failed unexpectedly: {exc}",
                  file=sys.stderr)
            try:
                self.client.fail_job(
                    job_id=job_id,
                    claim_token=claim_token,
                    error=f"Karigar daemon exception: {exc}",
                    retryable=True,
                )
            except Exception:
                pass
            self.state.jobs_failed_today += 1
        finally:
            self._heartbeat_stop.set()
            if heartbeat_thread.is_alive():
                heartbeat_thread.join(timeout=2.0)
            self._reset_current()
            self._save_state()

    # ── claim with retry ────────────────────────────────────

    def _claim_with_retry(self) -> dict[str, Any] | None:
        """Attempt to claim a job with exponential backoff on failure.

        Returns the claim dict or ``None`` when shutdown is requested.
        """
        consecutive_errors = 0
        max_backoff = 300.0

        while not self._shutdown.is_set():
            try:
                claim = self.client.claim_job()
                return claim
            except Exception as exc:
                consecutive_errors += 1
                backoff = min(
                    self.config.poll_interval * (2 ** min(consecutive_errors, 5)),
                    max_backoff,
                )
                print(
                    f"[karigar] Claim failed (attempt {consecutive_errors}): "
                    f"{exc} — retrying in {backoff:.0f}s",
                    file=sys.stderr,
                )
                if self._sleep_interruptible(backoff):
                    return None  # shutdown
        return None

    # ── auto-repair ─────────────────────────────────────────

    def _try_auto_repair(
        self, claim: dict[str, Any], result: JobResult
    ) -> JobResult:
        """Apply auto-repair when enabled and the job failed verification."""
        auto_repair_enabled = (
            claim.get("engine_config", {}).get("auto_repair", False)
            or claim.get("metadata", {}).get("auto_repair", False)
        )
        if not auto_repair_enabled:
            return result
        if result.status in (JobStatus.SUCCESS, JobStatus.BLOCKED, JobStatus.CANCELLED):
            return result

        from .auto_repair import AutoRepairEngine

        job_id = claim.get("job_id", "")
        max_retries = min(
            self.circuit.config.max_retries_per_job,
            3,  # never exceed 3 auto-repair attempts
        )

        repair_engine = AutoRepairEngine(
            max_retries=max_retries,
            backend_client=self.client if self.factory_run_id else None,
            factory_run_id=self.factory_run_id,
        )
        repaired_result, _history = repair_engine.execute_with_repair(
            claim, self.runner.run_job
        )
        return repaired_result

    # ── result reporting ────────────────────────────────────

    def _report_result(
        self, job_id: str, claim_token: str, result: JobResult
    ) -> None:
        """Report success, failure, or terminal status to the backend."""
        result_dict = result.to_dict()

        if result.status == JobStatus.SUCCESS:
            self.client.complete_job(
                job_id=job_id,
                claim_token=claim_token,
                result=result_dict,
                logs=json.dumps(result_dict),
                engine=result.engine_used,
                branch_name=result.branch_name or "",
            )
        elif result.status in (JobStatus.FAILED, JobStatus.TIMED_OUT):
            self.client.fail_job(
                job_id=job_id,
                claim_token=claim_token,
                error=result.failure_reason or result.summary,
                retryable=result.status == JobStatus.TIMED_OUT,
                logs=json.dumps(result_dict),
            )
        else:
            # BLOCKED, CANCELLED — not retryable
            self.client.fail_job(
                job_id=job_id,
                claim_token=claim_token,
                error=result.failure_reason or result.summary,
                retryable=False,
                logs=json.dumps(result_dict),
            )

    # ── ledger ──────────────────────────────────────────────

    def _append_ledger(self, job_id: str, result: JobResult) -> None:
        if not self.factory_run_id:
            return
        try:
            result_dict = result.to_dict()
            self.client.create_ledger_entry(
                run_id=self.factory_run_id,
                title=f"Job {job_id}: {result_dict.get('summary', 'completed')[:80]}",
                status="completed" if result.status == JobStatus.SUCCESS else "failed",
                stage="execution",
                body=_build_ledger_body(result_dict, job_id),
            )
        except Exception:
            pass  # ledger is best-effort

    # ── heartbeat thread ────────────────────────────────────

    def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats while a job is in-flight."""
        while not self._heartbeat_stop.is_set():
            job_id = self._current_job_id
            token = self._current_claim_token
            if job_id and token:
                try:
                    self.client.heartbeat_job(
                        job_id=job_id,
                        claim_token=token,
                        logs=json.dumps({"ts": _now_iso()}),
                    )
                    self.state.last_heartbeat_utc = _now_iso()
                except Exception:
                    pass  # heartbeat is best-effort
            self._heartbeat_stop.wait(self.config.heartbeat_interval)

    # ── state management ────────────────────────────────────

    def _state_path(self) -> Path:
        return self.config.state_dir / "daemon.json"

    def _load_state(self) -> DaemonState:
        path = self._state_path()
        try:
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                # Restore circuit breaker counters from saved state
                circuit_data = data.pop("circuit", {})
                if circuit_data:
                    self.circuit = CircuitBreaker.from_state(
                        circuit_data, self.circuit.config
                    )
                return DaemonState.from_dict(data)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[karigar] Warning: could not load state file {path}: {exc}",
                  file=sys.stderr)
        return DaemonState()

    def _save_state(self) -> None:
        self._check_day_rollover()
        data = self.state.to_dict()
        # Merge circuit breaker counters
        data["circuit"] = self.circuit.get_state()
        try:
            self._state_path().write_text(
                json.dumps(data, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            print(f"[karigar] Warning: could not save state: {exc}",
                  file=sys.stderr)

    def _check_day_rollover(self) -> None:
        """Reset daily counters when the UTC date changes."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self.state.today != today:
            self.state.today = today
            self.state.jobs_completed_today = 0
            self.state.jobs_failed_today = 0

    def _update_state_after_job(self, result: JobResult) -> None:
        """Update counters after a job completes."""
        self.state.last_seen_job = result.job_id
        self.state.jobs_completed_today += 1
        if result.status in (JobStatus.FAILED, JobStatus.TIMED_OUT):
            self.state.jobs_failed_today += 1

        # Crude spend estimate: ~$0.15 per 1M tokens
        tokens_used = (
            self.circuit.estimate_tokens(result.summary or "")
            + sum(
                self.circuit.estimate_tokens(str(v.get("summary", "")))
                for v in result.verification_results
            )
        )
        spend = (tokens_used / 1_000_000) * 0.15
        self.state.total_spend += spend

    # ── helpers ─────────────────────────────────────────────

    def _sleep_interruptible(self, seconds: float) -> bool:
        """Sleep for *seconds*, waking early if shutdown is requested.

        Returns ``True`` when the sleep was interrupted by shutdown.
        """
        elapsed = 0.0
        tick = 0.5  # check every 500 ms
        while elapsed < seconds:
            if self._shutdown.is_set():
                return True
            time.sleep(min(tick, seconds - elapsed))
            elapsed += tick
        return False

    def _reset_current(self) -> None:
        """Clear the current-job tracking fields."""
        self._current_job_id = ""
        self._current_claim_token = ""
        self._current_result = None

    def _shutdown_cleanup(self) -> None:
        """Save state and clean up on shutdown."""
        print("[karigar] Shutting down — saving state...", file=sys.stderr)
        self._heartbeat_stop.set()
        self._save_state()
        print(f"[karigar] State saved to {self._state_path()}", file=sys.stderr)


__all__ = ["DaemonConfig", "DaemonController", "DaemonState"]
