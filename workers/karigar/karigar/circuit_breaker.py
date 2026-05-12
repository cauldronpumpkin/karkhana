from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any


@dataclass(slots=True)
class CircuitBreakerConfig:
    """Limits that protect the worker and backend from runaway behaviour.

    Attributes:
        max_retries_per_job: Maximum repair / retry attempts for a single job
            before the circuit breaker refuses further retries (default 3).
        max_jobs_per_day: Hard ceiling on jobs claimed per UTC day.  Once
            reached the breaker will refuse ``can_claim()`` until the next
            UTC day (default 100).
        token_budget_per_day: Estimated token ceiling per UTC day.  When
            cumulative tokens exceed this budget the breaker refuses
            ``can_claim()``.  Tokens are estimated as ``chars / 4`` by the
            ``estimate_tokens()`` heuristic (default 1 000 000).
    """

    max_retries_per_job: int = 3
    max_jobs_per_day: int = 100
    token_budget_per_day: int = 1_000_000


@dataclass
class CircuitBreaker:
    """Per-day token budget, per-job max retries, and per-worker daily cap.

    Consulted by the daemon controller before every claim and before every
    retry.  The breaker is *not* thread-safe — the daemon runs a single
    coordinator thread.
    """

    config: CircuitBreakerConfig

    # ── private mutable state ──────────────────────────────
    _today: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    _jobs_today: int = 0
    _tokens_today: int = 0
    _job_retries: dict[str, int] = field(default_factory=dict)  # job_id → count

    def _check_day_rollover(self) -> None:
        """Reset daily counters when the UTC date changes."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != self._today:
            self._today = today
            self._jobs_today = 0
            self._tokens_today = 0
            self._job_retries.clear()

    # ── public queries ─────────────────────────────────────

    def can_claim(self) -> bool:
        """Return ``True`` when the daily caps have not been exceeded."""
        self._check_day_rollover()
        if self._jobs_today >= self.config.max_jobs_per_day:
            return False
        if self._tokens_today >= self.config.token_budget_per_day:
            return False
        return True

    def can_retry_job(self, job_id: str) -> bool:
        """Return ``True`` if *job_id* may be retried against its per-job cap."""
        retries = self._job_retries.get(job_id, 0)
        return retries < self.config.max_retries_per_job

    # ── record-keeping ─────────────────────────────────────

    def record_claim(self, job_id: str) -> None:
        """Record that *job_id* was claimed (increments daily counter + retry)."""
        self._check_day_rollover()
        self._jobs_today += 1
        self._job_retries[job_id] = self._job_retries.get(job_id, 0) + 1

    def try_retry(self, job_id: str) -> bool:
        """Check AND consume one retry slot for *job_id*.

        Returns ``True`` if the retry is allowed and has been consumed.
        Returns ``False`` when the per-job retry cap has been reached.

        Used by the daemon's auto-repair integration to ensure each
        repair attempt counts against the circuit breaker budget.
        """
        self._check_day_rollover()
        if not self.can_retry_job(job_id):
            return False
        self._job_retries[job_id] = self._job_retries.get(job_id, 0) + 1
        return True

    def record_tokens(self, count: int) -> None:
        """Accumulate *count* tokens against the daily budget."""
        self._check_day_rollover()
        self._tokens_today += count

    # ── token heuristic ────────────────────────────────────

    @staticmethod
    def estimate_tokens(prompt: str) -> int:
        """Crude token estimator: ``len(prompt) // 4``.

        This is deliberately cheap — we are guarding against orders-of-
        magnitude overspend, not billing precision.  For most English text
        the factor-of-4 heuristic is within 30 % of the tiktoken count.
        """
        return max(1, len(prompt) // 4)

    # ── state serialisation ────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        """Snapshot the current breaker counters (for daemon state persistence)."""
        return {
            "today": self._today,
            "jobs_today": self._jobs_today,
            "tokens_today": self._tokens_today,
        }

    @classmethod
    def from_state(
        cls,
        state: dict[str, Any],
        config: CircuitBreakerConfig | None = None,
    ) -> "CircuitBreaker":
        """Restore a breaker from a previously-saved state snapshot."""
        breaker = cls(config=config or CircuitBreakerConfig())
        saved_date = state.get("today", "")
        if saved_date == breaker._today:
            breaker._jobs_today = int(state.get("jobs_today", 0))
            breaker._tokens_today = int(state.get("tokens_today", 0))
        # _job_retries is always re-built fresh each day
        return breaker


__all__ = ["CircuitBreaker", "CircuitBreakerConfig"]
