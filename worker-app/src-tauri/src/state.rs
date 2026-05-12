use crate::types::WorkerState;
use serde::{Deserialize, Serialize};
use serde_json;
use std::path::Path;
use std::path::PathBuf;
use std::sync::{Arc, OnceLock, RwLock};

const WORKER_DIR: &str = "idearefinery-worker";
const LEGACY_WORKER_DIR: &str = "openclaude-local";
const STATE_FILE: &str = "state.json";

pub fn state_path() -> PathBuf {
    state_path_in(dirs::data_dir().unwrap_or_else(|| PathBuf::from(".")))
}

pub fn state_path_in(base_dir: impl AsRef<Path>) -> PathBuf {
    base_dir.as_ref().join(WORKER_DIR).join(STATE_FILE)
}

fn legacy_state_paths_in(base_dir: impl AsRef<Path>) -> [PathBuf; 2] {
    let base = base_dir.as_ref();
    [
        base.join(WORKER_DIR).join(LEGACY_WORKER_DIR).join(STATE_FILE),
        base.join(LEGACY_WORKER_DIR).join(STATE_FILE),
    ]
}

fn read_state(path: &Path) -> Option<WorkerState> {
    let content = std::fs::read_to_string(path).ok()?;
    serde_json::from_str(&content).ok()
}

fn migrate_state(path: &Path, state: &WorkerState) {
    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    if let Ok(content) = serde_json::to_string_pretty(state) {
        let _ = std::fs::write(path, content);
    }
}

fn write_state(path: &Path, state: &WorkerState) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let content = serde_json::to_string_pretty(state).map_err(|e| e.to_string())?;
    std::fs::write(path, content).map_err(|e| e.to_string())
}

pub struct StateStore {
    path: PathBuf,
    legacy_paths: [PathBuf; 2],
}

impl StateStore {
    pub fn new() -> Self {
        Self::from_data_dir(dirs::data_dir().unwrap_or_else(|| PathBuf::from(".")))
    }

    pub fn from_data_dir(base_dir: impl AsRef<Path>) -> Self {
        let path = state_path_in(base_dir.as_ref());
        if let Some(parent) = path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        StateStore {
            path,
            legacy_paths: legacy_state_paths_in(base_dir),
        }
    }

    pub fn load(&self) -> Option<WorkerState> {
        if let Some(state) = read_state(&self.path) {
            return Some(state);
        }

        for legacy_path in &self.legacy_paths {
            if let Some(state) = read_state(legacy_path) {
                if !self.path.exists() {
                    migrate_state(&self.path, &state);
                }
                return Some(state);
            }
        }

        None
    }

    pub fn save(&self, state: &WorkerState) -> Result<(), String> {
        write_state(&self.path, state)
    }
}

impl Default for StateStore {
    fn default() -> Self {
        Self::new()
    }
}

// ── AppHealth ──────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppHealth {
    pub api_connected: bool,
    pub sqs_messages_waiting: u64,
    pub opencode_session_count: u32,
    pub last_successful_job: Option<String>,
    pub error_count_last_hour: u32,
}

impl Default for AppHealth {
    fn default() -> Self {
        AppHealth {
            api_connected: false,
            sqs_messages_waiting: 0,
            opencode_session_count: 0,
            last_successful_job: None,
            error_count_last_hour: 0,
        }
    }
}

/// Thread-safe global health tracker.
static GLOBAL_HEALTH: OnceLock<Arc<RwLock<AppHealth>>> = OnceLock::new();

fn global_health() -> &'static Arc<RwLock<AppHealth>> {
    GLOBAL_HEALTH.get_or_init(|| Arc::new(RwLock::new(AppHealth::default())))
}

#[tauri::command]
pub fn get_app_health() -> Result<AppHealth, String> {
    global_health()
        .read()
        .map(|h| h.clone())
        .map_err(|e| format!("Failed to read app health: {}", e))
}

/// Update a single field of the global AppHealth by name.
/// Supported fields: `api_connected` (bool), `sqs_messages_waiting` (u64),
/// `opencode_session_count` (u32), `last_successful_job` (String),
/// `error_count_last_hour` (u32).
pub fn update_app_health(field: &str, value: serde_json::Value) -> Result<(), String> {
    let mut health = global_health()
        .write()
        .map_err(|e| format!("Failed to write app health: {}", e))?;
    match field {
        "api_connected" => {
            health.api_connected = value.as_bool().unwrap_or(false);
        }
        "sqs_messages_waiting" => {
            health.sqs_messages_waiting = value.as_u64().unwrap_or(0);
        }
        "opencode_session_count" => {
            health.opencode_session_count = value.as_u64().unwrap_or(0) as u32;
        }
        "last_successful_job" => {
            health.last_successful_job = value.as_str().map(|s| s.to_string());
        }
        "error_count_last_hour" => {
            health.error_count_last_hour = value.as_u64().unwrap_or(0) as u32;
        }
        _ => return Err(format!("Unknown health field: {}", field)),
    }
    Ok(())
}

/// Convenience: mark API connectivity status.
pub fn set_api_connected(connected: bool) {
    if let Ok(mut h) = global_health().write() {
        h.api_connected = connected;
    }
}

/// Convenience: increment error count (auto‑trims on read, caller can
/// call `decay_errors()` periodically).
pub fn increment_error_count() {
    if let Ok(mut h) = global_health().write() {
        h.error_count_last_hour = h.error_count_last_hour.saturating_add(1);
    }
}

/// Convenience: record a successful job timestamp.
pub fn record_successful_job(timestamp: &str) {
    if let Ok(mut h) = global_health().write() {
        h.last_successful_job = Some(timestamp.to_string());
    }
}

/// Convenience: set SQS messages waiting.
pub fn set_sqs_messages_waiting(count: u64) {
    if let Ok(mut h) = global_health().write() {
        h.sqs_messages_waiting = count;
    }
}

/// Convenience: set opencode session count.
pub fn set_opencode_session_count(count: u32) {
    if let Ok(mut h) = global_health().write() {
        h.opencode_session_count = count;
    }
}
