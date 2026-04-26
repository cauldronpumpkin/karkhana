use crate::opencode_session::OpenCodeClient;
use serde::{Deserialize, Serialize};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::sync::Mutex;

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
