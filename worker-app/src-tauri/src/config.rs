use crate::types::WorkerConfig;
use serde_json;
use std::env;
use std::path::PathBuf;

pub fn config_path() -> PathBuf {
    dirs::config_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join("idearefinery-worker")
        .join("worker-config.json")
}

pub fn load_config() -> WorkerConfig {
    let path = config_path();
    let mut data: serde_json::Value = if path.exists() {
        let content = std::fs::read_to_string(&path).unwrap_or_default();
        serde_json::from_str(&content).unwrap_or_default()
    } else {
        serde_json::Value::Object(Default::default())
    };

    if let Ok(env_api_base) = env::var("IDEAREFINERY_API_BASE_URL") {
        data["api_base"] = serde_json::Value::String(env_api_base);
    }
    if data.get("api_base").is_none() {
        data["api_base"] = serde_json::Value::String("http://localhost:8000".to_string());
    }

    if let Ok(env_engine) = env::var("IDEAREFINERY_WORKER_ENGINE") {
        data["engine"] = serde_json::Value::String(env_engine);
    }
    if let Ok(env_workspace) = env::var("IDEAREFINERY_WORKER_WORKSPACE") {
        data["workspace_root"] = serde_json::Value::String(env_workspace);
    }
    if let Ok(env_full_control) = env::var("IDEAREFINERY_WORKER_ALLOW_FULL_CONTROL") {
        data["allow_full_control"] = serde_json::Value::Bool(
            matches!(env_full_control.to_lowercase().as_str(), "1" | "true" | "yes"),
        );
    }

    serde_json::from_value(data).unwrap_or_else(|_| WorkerConfig {
        api_base: "http://localhost:8000".to_string(),
        ..Default::default()
    })
}

pub fn save_config(config: &WorkerConfig) -> Result<(), String> {
    let path = config_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let content = serde_json::to_string_pretty(config).map_err(|e| e.to_string())?;
    std::fs::write(&path, content).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn load_config_command() -> Result<WorkerConfig, String> {
    Ok(load_config())
}

#[tauri::command]
pub fn save_config_command(config: WorkerConfig) -> Result<(), String> {
    save_config(&config)
}

impl Default for WorkerConfig {
    fn default() -> Self {
        WorkerConfig {
            api_base: "http://localhost:8000".to_string(),
            display_name: "OpenClaude local worker".to_string(),
            engine: "opencode-server".to_string(),
            allow_full_control: false,
            workspace_root: "~/.idearefinery-worker/repos".to_string(),
            poll_seconds: 20,
            capabilities: crate::types::DEFAULT_CAPABILITIES
                .iter()
                .map(|s| s.to_string())
                .collect(),
            tenant_id: None,
            openclaude: Default::default(),
            opencode_server_url: Some("http://127.0.0.1:4096".to_string()),
            litellm_port: Some(4000),
            litellm_config: None,
        }
    }
}
