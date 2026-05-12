from __future__ import annotations

from datetime import datetime, timezone

import pytest

from karigar.circuit_breaker import CircuitBreaker, CircuitBreakerConfig


# ── helpers ────────────────────────────────────────────────────

def _make_breaker(**overrides) -> CircuitBreaker:
    config = CircuitBreakerConfig(**overrides)
    return CircuitBreaker(config=config)


def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ======================================================================
# can_claim
# ======================================================================

def test_can_claim_returns_true_when_under_limits() -> None:
    cb = _make_breaker(max_jobs_per_day=10, token_budget_per_day=1000)
    assert cb.can_claim() is True


def test_can_claim_returns_false_when_daily_jobs_exceeded() -> None:
    cb = _make_breaker(max_jobs_per_day=3, token_budget_per_day=1000)
    cb.record_claim("j1")
    cb.record_claim("j2")
    cb.record_claim("j3")
    assert cb.can_claim() is False


def test_can_claim_returns_false_when_token_budget_exceeded() -> None:
    cb = _make_breaker(max_jobs_per_day=100, token_budget_per_day=50)
    cb.record_tokens(60)
    assert cb.can_claim() is False


def test_can_claim_returns_true_when_token_budget_not_exceeded() -> None:
    cb = _make_breaker(max_jobs_per_day=100, token_budget_per_day=50)
    cb.record_tokens(49)
    assert cb.can_claim() is True


# ======================================================================
# can_retry_job
# ======================================================================

def test_can_retry_job_returns_true_under_limit() -> None:
    cb = _make_breaker(max_retries_per_job=3)
    cb.record_claim("job-1")
    assert cb.can_retry_job("job-1") is True


def test_can_retry_job_returns_false_when_limit_exceeded() -> None:
    cb = _make_breaker(max_retries_per_job=3)
    cb.record_claim("job-1")
    cb.record_claim("job-1")
    cb.record_claim("job-1")
    assert cb.can_retry_job("job-1") is False


def test_can_retry_job_unknown_job_returns_true() -> None:
    cb = _make_breaker(max_retries_per_job=3)
    assert cb.can_retry_job("never-seen") is True


# ======================================================================
# record_claim
# ======================================================================

def test_record_claim_increments_daily_jobs() -> None:
    cb = _make_breaker(max_jobs_per_day=10)
    cb.record_claim("j1")
    cb.record_claim("j2")
    assert cb._jobs_today == 2


def test_record_claim_increments_job_retry_count() -> None:
    cb = _make_breaker()
    cb.record_claim("job-a")
    cb.record_claim("job-a")
    assert cb._job_retries["job-a"] == 2


# ======================================================================
# record_tokens
# ======================================================================

def test_record_tokens_accumulates() -> None:
    cb = _make_breaker()
    cb.record_tokens(100)
    cb.record_tokens(50)
    assert cb._tokens_today == 150


# ======================================================================
# estimate_tokens
# ======================================================================

def test_estimate_tokens_uses_chars_div_4() -> None:
    # 400 chars → 100 tokens
    assert CircuitBreaker.estimate_tokens("x" * 400) == 100


def test_estimate_tokens_short_string_minimum_1() -> None:
    assert CircuitBreaker.estimate_tokens("ab") == 1     # 2 // 4 = 0 → max(1, 0) = 1


def test_estimate_tokens_empty_string_minimum_1() -> None:
    assert CircuitBreaker.estimate_tokens("") == 1


# ======================================================================
# get_state / from_state
# ======================================================================

def test_get_state_returns_snapshot() -> None:
    cb = _make_breaker()
    cb.record_claim("j1")
    cb.record_tokens(42)
    state = cb.get_state()
    assert state["today"] == _today_str()
    assert state["jobs_today"] == 1
    assert state["tokens_today"] == 42


def test_from_state_restores_same_day_counters() -> None:
    cb = _make_breaker()
    cb.record_claim("j1")
    cb.record_tokens(100)
    saved = cb.get_state()

    cb2 = CircuitBreaker.from_state(saved)
    assert cb2._jobs_today == 1
    assert cb2._tokens_today == 100
    assert cb2._today == _today_str()


def test_from_state_ignores_stale_date() -> None:
    saved = {"today": "2020-01-01", "jobs_today": 50, "tokens_today": 999}
    cb = CircuitBreaker.from_state(saved)
    # Stale date means counters reset to 0
    assert cb._jobs_today == 0
    assert cb._tokens_today == 0


def test_from_state_default_config() -> None:
    cb = CircuitBreaker.from_state({})
    assert cb.config.max_jobs_per_day == 100
    assert cb.config.token_budget_per_day == 1_000_000


def test_from_state_accepts_custom_config() -> None:
    config = CircuitBreakerConfig(max_jobs_per_day=5)
    cb = CircuitBreaker.from_state({"jobs_today": 3}, config=config)
    assert cb.config.max_jobs_per_day == 5


# ======================================================================
# day rollover
# ======================================================================

def test_check_day_rollover_resets_counters_on_new_day() -> None:
    """Simulate a day change by setting _today to an old date."""
    cb = _make_breaker()
    cb.record_claim("j1")
    cb.record_tokens(500)
    assert cb._jobs_today == 1

    # Set _today to an old date to trigger rollover on next check
    cb._today = "2000-01-01"

    # Trigger rollover check
    cb._check_day_rollover()

    assert cb._jobs_today == 0
    assert cb._tokens_today == 0
    assert cb._job_retries == {}
    # _today should be updated to today's date
    assert cb._today != "2000-01-01"


def test_check_day_rollover_noop_same_day() -> None:
    cb = _make_breaker()
    cb.record_claim("j1")
    cb._check_day_rollover()
    # Should not reset — same day
    assert cb._jobs_today == 1


# ======================================================================
# default config
# ======================================================================

def test_default_config_values() -> None:
    config = CircuitBreakerConfig()
    assert config.max_retries_per_job == 3
    assert config.max_jobs_per_day == 100
    assert config.token_budget_per_day == 1_000_000
