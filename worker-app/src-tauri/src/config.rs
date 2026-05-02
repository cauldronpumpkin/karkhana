use crate::types::WorkerConfig;
use serde_json;
use std::env;
use std::path::Path;
use std::path::PathBuf;

const WORKER_DIR: &str = "idearefinery-worker";
const LEGACY_WORKER_DIR: &str = "openclaude-local";
const CONFIG_FILE: &str = "worker-config.json";

pub fn config_path() -> PathBuf {
    config_path_in(dirs::config_dir().unwrap_or_else(|| PathBuf::from(".")))
}

pub fn config_path_in(base_dir: impl AsRef<Path>) -> PathBuf {
    base_dir.as_ref().join(WORKER_DIR).join(CONFIG_FILE)
}

fn legacy_config_paths_in(base_dir: impl AsRef<Path>) -> [PathBuf; 2] {
    let base = base_dir.as_ref();
    [
        base.join(LEGACY_WORKER_DIR).join(CONFIG_FILE),
        base.join(WORKER_DIR).join(LEGACY_WORKER_DIR).join(CONFIG_FILE),
    ]
}

fn read_config_value(path: &Path) -> Option<serde_json::Value> {
    let content = std::fs::read_to_string(path).ok()?;
    serde_json::from_str(&content).ok()
}

fn write_config_value(path: &Path, value: &serde_json::Value) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let content = serde_json::to_string_pretty(value).map_err(|e| e.to_string())?;
    std::fs::write(path, content).map_err(|e| e.to_string())
}

pub fn load_config_from_dir(base_dir: impl AsRef<Path>) -> WorkerConfig {
    let current_path = config_path_in(base_dir.as_ref());
    let legacy_paths = legacy_config_paths_in(base_dir);

    let current_value = read_config_value(&current_path);
    let legacy_value = if current_value.is_none() {
        legacy_paths.iter().find_map(|path| read_config_value(path))
    } else {
        None
    };

    let mut data = current_value
        .clone()
        .or(legacy_value.clone())
        .unwrap_or_else(|| serde_json::Value::Object(Default::default()));

    if current_value.is_none() {
        if let Some(legacy) = legacy_value.as_ref() {
            let _ = write_config_value(&current_path, legacy);
        }
    }

    if let Ok(env_api_base) = env::var("IDEAREFINERY_API_BASE_URL") {
        data["api_base"] = serde_json::Value::String(env_api_base);
    }
    if data.get("api_base").is_none() {
        data["api_base"] = serde_json::Value::String("https://api.karkhana.one".to_string());
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
        api_base: "https://api.karkhana.one".to_string(),
        ..Default::default()
    })
}

pub fn load_config() -> WorkerConfig {
    load_config_from_dir(dirs::config_dir().unwrap_or_else(|| PathBuf::from(".")))
}

pub fn save_config(config: &WorkerConfig) -> Result<(), String> {
    save_config_to_dir(dirs::config_dir().unwrap_or_else(|| PathBuf::from(".")), config)
}

pub fn save_config_to_dir(base_dir: impl AsRef<Path>, config: &WorkerConfig) -> Result<(), String> {
    let path = config_path_in(base_dir);
    let value = serde_json::to_value(config).map_err(|e| e.to_string())?;
    write_config_value(&path, &value)
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
            api_base: "https://api.karkhana.one".to_string(),
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
