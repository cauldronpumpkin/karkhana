use crate::types::WorkerState;
use serde_json;
use std::path::PathBuf;

pub fn state_path() -> PathBuf {
    dirs::data_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("idearefinery-worker")
        .join("openclaude-local")
        .join("state.json")
}

pub struct StateStore {
    path: PathBuf,
}

impl StateStore {
    pub fn new() -> Self {
        let path = state_path();
        if let Some(parent) = path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        StateStore { path }
    }

    pub fn load(&self) -> Option<WorkerState> {
        if !self.path.exists() {
            return None;
        }
        let content = std::fs::read_to_string(&self.path).ok()?;
        serde_json::from_str(&content).ok()
    }

    pub fn save(&self, state: &WorkerState) -> Result<(), String> {
        let content = serde_json::to_string_pretty(state).map_err(|e| e.to_string())?;
        std::fs::write(&self.path, content).map_err(|e| e.to_string())
    }
}

impl Default for StateStore {
    fn default() -> Self {
        Self::new()
    }
}
