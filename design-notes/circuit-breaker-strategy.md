# Circuit Breaker: Smarter Backoff & Retry (Rust)

**Source:** GPT-5.5 via codex-lb, 2026-05-05 | **5,683 tokens**

## Architecture

Separates four concerns:
1. **Retry/backoff** — handles individual transient failures
2. **Jitter** — prevents retry storms across workers
3. **Circuit breaking** — stops requests when dependency is unhealthy
4. **Rate-limit handling** — honors Retry-After, backs off differently

## Failure Classification

| Kind | Examples | Strategy |
|:---|:---|:---|
| Permanent | 400, 401, 404 | Fail fast, no retry |
| TransientNetwork | timeout, ECONNRESET, DNS | Decorrelated jitter |
| ServerError | 500, 502, 503, 504 | Exponential backoff + full jitter |
| RateLimited | 429 | Honor Retry-After, open circuit briefly |

## Jitter Strategy

- **Full jitter** (`sleep = random(0, cap)`) — for 5xx, server overload
- **Decorrelated jitter** (`sleep = min(cap, random(base, prev*3))`) — for network instability
- Both prevent synchronized retry storms across workers

## Circuit States

```
Closed → Open (after 5 consecutive failures)
Open → HalfOpen (after duration expires, min 2s max 60s)
HalfOpen → Closed (after 2 successful probes)
HalfOpen → Open (any failure in half-open)
```

Additional: open_duration escalates with repeated openings to avoid flapping.

## vs AWS SDK

Closest to AWS **Standard** mode with explicit circuit breaker. Missing retry budget — suggested future addition. Partial approximation of **Adaptive** mode for 429 handling.

## Full Code

See original GPT-5.5 output for complete Rust implementation of `CircuitBreaker` with `ClassifyFailure` trait, `CircuitBreakerConfig`, and `WorkerHttpError` classifier.
