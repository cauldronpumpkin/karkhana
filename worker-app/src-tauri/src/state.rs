use crate::types::WorkerState;
use serde_json;
use std::path::Path;
use std::path::PathBuf;

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
