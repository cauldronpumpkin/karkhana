use crate::opencode_session::OpenCodeClient;
use serde::{Deserialize, Serialize};
use std::sync::atomic::{AtomicBool, AtomicU32, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::Mutex;

/// Global canary-mode state for the worker process.
static CANARY_MODE: AtomicBool = AtomicBool::new(false);
static CONSECUTIVE_FAILURES_GLOBAL: AtomicU32 = AtomicU32::new(0);
const CANARY_THRESHOLD: u32 = 5;

/// Enter canary mode when consecutive failures exceed threshold.
pub fn enter_canary_mode() -> bool {
    let prev = CANARY_MODE.swap(true, Ordering::SeqCst);
    log_canary_state(true);
    !prev // returns true if this call actually toggled canary on
}

/// Exit canary mode and reset the failure counter.
pub fn exit_canary_mode() {
    CONSECUTIVE_FAILURES_GLOBAL.store(0, Ordering::SeqCst);
    CANARY_MODE.store(false, Ordering::SeqCst);
    log_canary_state(false);
}

/// Returns true if the worker is currently in canary mode.
pub fn is_canary() -> bool {
    CANARY_MODE.load(Ordering::SeqCst)
}

/// Returns an optional warning message when in canary mode.
pub fn canary_warning() -> Option<String> {
    if is_canary() {
        let failures = CONSECUTIVE_FAILURES_GLOBAL.load(Ordering::SeqCst);
        Some(format!(
            "CANARY MODE: {} consecutive failures (threshold {}) — worker is degraded. \
             No new jobs will be claimed until the failure count resets.",
            failures, CANARY_THRESHOLD
        ))
    } else {
        None
    }
}

/// Increment the global failure counter.  If it crosses the threshold the
/// worker enters canary mode automatically.
pub fn record_failure() {
    let count = CONSECUTIVE_FAILURES_GLOBAL.fetch_add(1, Ordering::SeqCst) + 1;
    if count >= CANARY_THRESHOLD && !CANARY_MODE.load(Ordering::SeqCst) {
        enter_canary_mode();
    }
}

/// Reset the global failure counter (e.g. after a successful job).
pub fn reset_failures() {
    CONSECUTIVE_FAILURES_GLOBAL.store(0, Ordering::SeqCst);
}

/// Returns the current consecutive failure count.
pub fn failure_count() -> u32 {
    CONSECUTIVE_FAILURES_GLOBAL.load(Ordering::SeqCst)
}

/// Persist canary state to the worker config file on disk.
fn log_canary_state(canary: bool) {
    if let Ok(mut config) = crate::config::load_config_as_value() {
        if let Some(obj) = config.as_object_mut() {
            obj.insert(
                "canary_mode".to_string(),
                serde_json::Value::Bool(canary),
            );
            obj.insert(
                "canary_since".to_string(),
                serde_json::Value::String(chrono_now()),
            );
        }
        let _ = crate::config::save_config_value(&config);
    }
}

/// Quick ISO-8601 timestamp helper (no extra crate needed).
fn chrono_now() -> String {
    use std::time::SystemTime;
    let dur = SystemTime::now()
        .duration_since(SystemTime::UNIX_EPOCH)
        .unwrap_or_default();
    let secs = dur.as_secs();
    // Simple UTC ISO rendering
    let days = secs / 86400;
    let time = secs % 86400;
    let hours = time / 3600;
    let mins = (time % 3600) / 60;
    let secs = time % 60;
    // Compute year/month/day from epoch (approximate but good enough for logging)
    let (year, month, day) = civil_from_days(days as i64);
    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}Z",
        year, month, day, hours, mins, secs
    )
}

fn civil_from_days(days: i64) -> (i64, u32, u32) {
    // Algorithm from Howard Hinnant
    let z = days + 719468;
    let era = if z >= 0 { z } else { z - 146096 } / 146097;
    let doe = (z - era * 146097) as u32;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y = yoe as i64 + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if m <= 2 { y + 1 } else { y };
    (y, m, d)
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CircuitBreakerLimits {
    pub max_ttl_minutes: u32,
    pub max_llm_tokens: Option<u64>,
    pub max_budget_usd: Option<f64>,
    pub max_identical_failures: u32,
}

impl Default for CircuitBreakerLimits {
    fn default() -> Self {
        CircuitBreakerLimits {
            max_ttl_minutes: 40,
            max_llm_tokens: Some(500_000),
            max_budget_usd: Some(2.0),
            max_identical_failures: 3,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum BreakerTrigger {
    Ttl,
    TokenLimit,
    BudgetLimit,
    IdenticalFailures,
}

impl std::fmt::Display for BreakerTrigger {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            BreakerTrigger::Ttl => write!(f, "ttl"),
            BreakerTrigger::TokenLimit => write!(f, "token_limit"),
            BreakerTrigger::BudgetLimit => write!(f, "budget_limit"),
            BreakerTrigger::IdenticalFailures => write!(f, "identical_failures"),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BreakerStatus {
    pub triggered: Option<BreakerTrigger>,
    pub elapsed_minutes: f64,
    pub tokens_used: u64,
    pub budget_used: f64,
    pub consecutive_failures: u32,
}

pub struct CircuitBreaker {
    client: OpenCodeClient,
    session_id: String,
    limits: CircuitBreakerLimits,
    start_time: Instant,
    triggered: Arc<Mutex<Option<BreakerTrigger>>>,
    cancelled: Arc<AtomicBool>,
    tokens_used: Arc<Mutex<u64>>,
    budget_used: Arc<Mutex<f64>>,
    last_error_hashes: Arc<Mutex<Vec<String>>>,
}

impl CircuitBreaker {
    pub fn new(
        client: OpenCodeClient,
        session_id: String,
        limits: CircuitBreakerLimits,
    ) -> Self {
        CircuitBreaker {
            client,
            session_id,
            limits,
            start_time: Instant::now(),
            triggered: Arc::new(Mutex::new(None)),
            cancelled: Arc::new(AtomicBool::new(false)),
            tokens_used: Arc::new(Mutex::new(0)),
            budget_used: Arc::new(Mutex::new(0.0)),
            last_error_hashes: Arc::new(Mutex::new(Vec::new())),
        }
    }

    pub fn status(&self) -> BreakerStatus {
        let elapsed = self.start_time.elapsed().as_secs_f64() / 60.0;
        let tokens = *self.tokens_used.blocking_lock();
        let budget = *self.budget_used.blocking_lock();
        let triggered = self.triggered.blocking_lock().clone();
        let error_hashes = self.last_error_hashes.blocking_lock().clone();
        let consecutive = count_consecutive_identical(&error_hashes);
        BreakerStatus {
            triggered,
            elapsed_minutes: elapsed,
            tokens_used: tokens,
            budget_used: budget,
            consecutive_failures: consecutive,
        }
    }

    pub fn cancel(&self) {
        self.cancelled.store(true, Ordering::SeqCst);
    }

    pub fn is_cancelled(&self) -> bool {
        self.cancelled.load(Ordering::SeqCst)
    }

    pub async fn watch(&self) -> Option<BreakerTrigger> {
        loop {
            if self.cancelled.load(Ordering::SeqCst) {
                return None;
            }

            let elapsed = self.start_time.elapsed().as_secs() / 60;
            if elapsed >= self.limits.max_ttl_minutes as u64 {
                let _ = self.client.abort_session(&self.session_id).await;
                *self.triggered.lock().await = Some(BreakerTrigger::Ttl);
                return Some(BreakerTrigger::Ttl);
            }

            if let Ok(messages) = self.client.list_messages(&self.session_id).await {
                let mut total_tokens: u64 = 0;
                let mut total_budget: f64 = 0.0;
                let mut error_hashes: Vec<String> = Vec::new();

                for msg in &messages {
                    if let Some(usage) = msg.info.get("usage") {
                        let input: u64 =
                            usage.get("input_tokens").and_then(|v| v.as_u64()).unwrap_or(0);
                        let output: u64 =
                            usage.get("output_tokens").and_then(|v| v.as_u64()).unwrap_or(0);
                        total_tokens += input + output;

                        if let Some(cost) = usage.get("cost").and_then(|v| v.as_f64()) {
                            total_budget += cost;
                        }
                    }

                    for part in &msg.parts {
                        if let Some(tool_result) = part.get("toolResult") {
                            if let Some(error) = tool_result.get("error") {
                                let error_str = error.to_string();
                                let hash = simple_hash(&error_str);
                                error_hashes.push(hash);
                            }
                        }
                    }
                }

                *self.tokens_used.lock().await = total_tokens;
                *self.budget_used.lock().await = total_budget;
                *self.last_error_hashes.lock().await = error_hashes.clone();

                if let Some(max_tokens) = self.limits.max_llm_tokens {
                    if total_tokens >= max_tokens {
                        let _ = self.client.abort_session(&self.session_id).await;
                        *self.triggered.lock().await = Some(BreakerTrigger::TokenLimit);
                        return Some(BreakerTrigger::TokenLimit);
                    }
                }

                if let Some(max_budget) = self.limits.max_budget_usd {
                    if total_budget >= max_budget {
                        let _ = self.client.abort_session(&self.session_id).await;
                        *self.triggered.lock().await = Some(BreakerTrigger::BudgetLimit);
                        return Some(BreakerTrigger::BudgetLimit);
                    }
                }

                if error_hashes.len() >= self.limits.max_identical_failures as usize {
                    let last_n: Vec<String> = error_hashes
                        .iter()
                        .rev()
                        .take(self.limits.max_identical_failures as usize)
                        .cloned()
                        .collect();
                    if last_n.windows(2).all(|w| w[0] == w[1]) {
                        let _ = self.client.abort_session(&self.session_id).await;
                        *self.triggered.lock().await = Some(BreakerTrigger::IdenticalFailures);
                        return Some(BreakerTrigger::IdenticalFailures);
                    }
                }
            }

            tokio::time::sleep(Duration::from_secs(30)).await;
        }
    }
}

fn count_consecutive_identical(hashes: &[String]) -> u32 {
    if hashes.is_empty() {
        return 0;
    }
    let last = &hashes[hashes.len() - 1];
    let mut count: u32 = 1;
    for h in hashes.iter().rev().skip(1) {
        if h == last {
            count += 1;
        } else {
            break;
        }
    }
    count
}

fn simple_hash(s: &str) -> String {
    let truncated: String = s.chars().take(64).collect();
    let mut hash: u64 = 5381;
    for byte in truncated.bytes() {
        hash = hash.wrapping_mul(33).wrapping_add(byte as u64);
    }
    format!("{:016x}", hash)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    static TEST_LOCK: Mutex<()> = Mutex::new(());
struct CanaryStateGuard;

impl Drop for CanaryStateGuard {
    fn drop(&mut self) {
        reset_failures();
        exit_canary_mode();
    }
}

fn take_canary_state_guard() -> CanaryStateGuard {
    reset_failures();
    exit_canary_mode();
    CanaryStateGuard
}

    // --- Canary mode tests ---

    #[test]
    fn test_circuit_breaker_starts_closed() {
        let _guard = TEST_LOCK.lock().unwrap();
        let _state_guard = take_canary_state_guard();
        // Canary mode starts disabled (analogous to circuit breaker "Closed")
        exit_canary_mode();
        assert!(!is_canary());
        assert_eq!(failure_count(), 0);
    }

    #[test]
    fn test_circuit_breaker_trips_on_threshold() {
        let _guard = TEST_LOCK.lock().unwrap();
        let _state_guard = take_canary_state_guard();
        // After N (CANARY_THRESHOLD = 5) consecutive failures, canary mode activates
        // analogous to circuit breaker "Open"
        exit_canary_mode();
        for _ in 0..CANARY_THRESHOLD - 1 {
            record_failure();
        }
        // Threshold not yet reached
        assert!(!is_canary());
        // One more triggers canary mode
        record_failure();
        assert!(is_canary());
        assert!(failure_count() >= CANARY_THRESHOLD);
    }

    #[test]
    fn test_circuit_breaker_recovers() {
        let _guard = TEST_LOCK.lock().unwrap();
        let _state_guard = take_canary_state_guard();
        // After exiting canary mode and resetting, state goes back to normal
        // analogous to circuit breaker HalfOpen -> Closed on success
        exit_canary_mode();
        assert!(!is_canary());
        // Trip the breaker
        for _ in 0..CANARY_THRESHOLD {
            record_failure();
        }
        assert!(is_canary());
        // "Recovery" — reset failures and exit canary mode
        reset_failures();
        exit_canary_mode();
        assert!(!is_canary());
        assert_eq!(failure_count(), 0);
    }

    #[test]
    fn test_circuit_breaker_stays_open_on_half_open_failure() {
        let _guard = TEST_LOCK.lock().unwrap();
        let _state_guard = take_canary_state_guard();
        // When canary is active and new failures arrive, it stays in canary mode
        // analogous to HalfOpen -> failure -> Open
        exit_canary_mode();
        // Trip the breaker
        for _ in 0..CANARY_THRESHOLD {
            record_failure();
        }
        assert!(is_canary());
        // Record more failures — stays in canary mode
        let _prev = is_canary();
        record_failure();
        assert!(is_canary());
        // The canary warning should still indicate degraded state
        let warning = canary_warning();
        assert!(warning.is_some());
        assert!(warning.unwrap().contains("CANARY MODE"));
    }

    #[test]
    fn test_circuit_breaker_resets_on_success() {
        let _guard = TEST_LOCK.lock().unwrap();
        let _state_guard = take_canary_state_guard();
        // Reset clears the failure count - analogous to success resetting the breaker
        exit_canary_mode();
        record_failure();
        record_failure();
        assert_eq!(failure_count(), 2);
        reset_failures();
        assert_eq!(failure_count(), 0);
    }

    #[test]
    fn test_circuit_breaker_limits_configurable() {
        // Custom CircuitBreakerLimits can be constructed and have expected defaults
        let default_limits = CircuitBreakerLimits::default();
        assert_eq!(default_limits.max_ttl_minutes, 40);
        assert_eq!(default_limits.max_llm_tokens, Some(500_000));
        assert_eq!(default_limits.max_budget_usd, Some(2.0));
        assert_eq!(default_limits.max_identical_failures, 3);

        // Custom limits work
        let custom = CircuitBreakerLimits {
            max_ttl_minutes: 10,
            max_llm_tokens: Some(100_000),
            max_budget_usd: None,
            max_identical_failures: 5,
        };
        assert_eq!(custom.max_ttl_minutes, 10);
        assert_eq!(custom.max_llm_tokens, Some(100_000));
        assert_eq!(custom.max_budget_usd, None);
        assert_eq!(custom.max_identical_failures, 5);
    }

    // --- Utility function tests ---

    #[test]
    fn test_count_consecutive_identical_empty() {
        assert_eq!(count_consecutive_identical(&[]), 0);
    }

    #[test]
    fn test_count_consecutive_identical_single() {
        assert_eq!(count_consecutive_identical(&["a".into()]), 1);
    }

    #[test]
    fn test_count_consecutive_identical_all_same() {
        let hashes: Vec<String> =
            vec!["x".into(), "x".into(), "x".into()];
        assert_eq!(count_consecutive_identical(&hashes), 3);
    }

    #[test]
    fn test_count_consecutive_identical_last_different() {
        let hashes: Vec<String> =
            vec!["a".into(), "a".into(), "b".into()];
        assert_eq!(count_consecutive_identical(&hashes), 1);
    }

    #[test]
    fn test_count_consecutive_identical_trailing_run() {
        let hashes: Vec<String> =
            vec!["a".into(), "b".into(), "b".into(), "b".into()];
        assert_eq!(count_consecutive_identical(&hashes), 3);
    }

    #[test]
    fn test_simple_hash_deterministic() {
        let h1 = simple_hash("hello world");
        let h2 = simple_hash("hello world");
        assert_eq!(h1, h2);
        assert_eq!(h1.len(), 16);
    }

    #[test]
    fn test_simple_hash_different_inputs() {
        let h1 = simple_hash("error type A");
        let h2 = simple_hash("error type B");
        assert_ne!(h1, h2);
    }

    #[test]
    fn test_simple_hash_long_input_truncated() {
        let long = "x".repeat(128);
        let hash = simple_hash(&long);
        assert_eq!(hash.len(), 16);
    }

    // --- BreakerTrigger Display ---

    #[test]
    fn test_breaker_trigger_display() {
        assert_eq!(BreakerTrigger::Ttl.to_string(), "ttl");
        assert_eq!(BreakerTrigger::TokenLimit.to_string(), "token_limit");
        assert_eq!(BreakerTrigger::BudgetLimit.to_string(), "budget_limit");
        assert_eq!(
            BreakerTrigger::IdenticalFailures.to_string(),
            "identical_failures"
        );
    }

    // --- Entry / exit idempotency ---

    #[test]
    fn test_enter_canary_mode_idempotent() {
        let _guard = TEST_LOCK.lock().unwrap();
        let _state_guard = take_canary_state_guard();
        exit_canary_mode();
        assert!(enter_canary_mode()); // first entry returns true
        assert!(!enter_canary_mode()); // already in canary mode — returns false
        exit_canary_mode();
    }

    #[test]
    fn test_canary_warning_when_not_canary() {
        let _guard = TEST_LOCK.lock().unwrap();
        let _state_guard = take_canary_state_guard();
        exit_canary_mode();
        assert!(canary_warning().is_none());
    }

    #[test]
    fn test_canary_warning_when_canary() {
        let _guard = TEST_LOCK.lock().unwrap();
        let _state_guard = take_canary_state_guard();
        exit_canary_mode();
        enter_canary_mode();
        let warning = canary_warning();
        assert!(warning.is_some());
        let msg = warning.unwrap();
        assert!(msg.contains("CANARY MODE"));
        assert!(msg.contains(&CANARY_THRESHOLD.to_string()));
    }
}



