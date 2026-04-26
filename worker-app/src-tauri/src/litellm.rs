use reqwest;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use tokio::process::{Child, Command};
use tokio::sync::Mutex;

pub const DEFAULT_LITELLM_PORT: u16 = 4000;
pub const DEFAULT_LITELLM_HOST: &str = "127.0.0.1";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LiteLLMConfig {
    pub port: u16,
    pub config_path: Option<String>,
    pub model_map: serde_json::Value,
}

#[derive(Debug)]
pub enum LiteLLMError {
    NotInstalled,
    StartFailed(String),
    HealthCheckFailed(String),
    ConfigError(String),
}

impl std::fmt::Display for LiteLLMError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            LiteLLMError::NotInstalled => write!(f, "LiteLLM is not installed"),
            LiteLLMError::StartFailed(msg) => write!(f, "LiteLLM start failed: {msg}"),
            LiteLLMError::HealthCheckFailed(msg) => {
                write!(f, "LiteLLM health check failed: {msg}")
            }
            LiteLLMError::ConfigError(msg) => write!(f, "LiteLLM config error: {msg}"),
        }
    }
}

impl std::error::Error for LiteLLMError {}

pub struct LiteLLMProxy {
    process: Arc<Mutex<Option<Child>>>,
    port: u16,
    running: Arc<AtomicBool>,
    client: reqwest::Client,
}

impl LiteLLMProxy {
    pub fn new(port: u16) -> Self {
        Self {
            process: Arc::new(Mutex::new(None)),
            port,
            running: Arc::new(AtomicBool::new(false)),
            client: reqwest::Client::new(),
        }
    }

    pub fn find_executable() -> Option<PathBuf> {
        if let Ok(path) = std::env::var("LITELLM_PROXY_PATH") {
            let p = PathBuf::from(&path);
            if p.exists() {
                return Some(p);
            }
        }

        let relative = std::env::current_dir().ok()?.join("litellm-env").join("Scripts").join("litellm-proxy.exe");
        if relative.exists() {
            return Some(relative);
        }

        which::which("litellm-proxy").ok()
    }

    pub fn generate_config(config: &LiteLLMConfig) -> Result<String, LiteLLMError> {
        let map = config
            .model_map
            .as_object()
            .ok_or_else(|| LiteLLMError::ConfigError("model_map must be a JSON object".into()))?;

        if map.is_empty() {
            return Err(LiteLLMError::ConfigError("model_map is empty".into()));
        }

        let mut model_entries = Vec::new();
        let mut model_names = Vec::new();

        for (name, value) in map {
            let obj = value
                .as_object()
                .ok_or_else(|| LiteLLMError::ConfigError(format!("model '{name}' value must be an object")))?;

            let litellm_model = obj
                .get("litellm_model")
                .and_then(|v| v.as_str())
                .ok_or_else(|| LiteLLMError::ConfigError(format!("model '{name}' missing litellm_model")))?;

            let mut entry = format!(
                "  - model_name: {}\n    litellm_params:\n      model: {}",
                name, litellm_model
            );

            if let Some(api_base) = obj.get("api_base").and_then(|v| v.as_str()) {
                entry.push_str(&format!("\n      api_base: {}", api_base));
            }

            if let Some(api_key_env) = obj.get("api_key_env").and_then(|v| v.as_str()) {
                entry.push_str(&format!("\n      api_key: env({})", api_key_env));
            }

            model_entries.push(entry);
            model_names.push(name.clone());
        }

        let mut yaml = String::from("model_list:\n");
        for entry in &model_entries {
            yaml.push_str(entry);
            yaml.push('\n');
        }

        if model_names.len() > 1 {
            yaml.push_str("\nrouter:\n  fallbacks:\n");
            let primary = &model_names[0];
            let fallbacks: Vec<&str> = model_names[1..].iter().map(|s| s.as_str()).collect();
            yaml.push_str(&format!("    - {}: [{}]\n", primary, fallbacks.join(", ")));
        }

        let config_dir = dirs::data_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join("idearefinery-worker")
            .join("litellm");

        std::fs::create_dir_all(&config_dir)
            .map_err(|e| LiteLLMError::ConfigError(format!("failed to create config dir: {e}")))?;

        let config_file = config_dir.join("config.yaml");
        std::fs::write(&config_file, &yaml)
            .map_err(|e| LiteLLMError::ConfigError(format!("failed to write config: {e}")))?;

        Ok(config_file.to_string_lossy().to_string())
    }

    pub async fn start(&self, config_path: Option<&str>) -> Result<(), LiteLLMError> {
        let exe = Self::find_executable().ok_or(LiteLLMError::NotInstalled)?;

        let mut cmd = Command::new(&exe);
        cmd.arg("--port")
            .arg(self.port.to_string())
            .stdout(std::process::Stdio::null())
            .stderr(std::process::Stdio::null());

        if let Some(path) = config_path {
            cmd.arg("--config").arg(path);
        }

        #[cfg(target_os = "windows")]
        {
            #[allow(unused_imports)]
            use std::os::windows::process::CommandExt;
            cmd.creation_flags(0x08000000);
        }

        let child = cmd
            .spawn()
            .map_err(|e| LiteLLMError::StartFailed(e.to_string()))?;

        *self.process.lock().await = Some(child);
        self.running.store(true, Ordering::SeqCst);

        for _ in 0..10 {
            tokio::time::sleep(std::time::Duration::from_secs(1)).await;
            if self.health_check().await? {
                return Ok(());
            }
        }

        Err(LiteLLMError::HealthCheckFailed(
            "proxy did not become healthy after 10 retries".into(),
        ))
    }

    pub async fn health_check(&self) -> Result<bool, LiteLLMError> {
        let url = format!("http://{}:{}/health", DEFAULT_LITELLM_HOST, self.port);
        let result = self
            .client
            .get(&url)
            .timeout(std::time::Duration::from_secs(5))
            .send()
            .await;

        match result {
            Ok(resp) => Ok(resp.status().is_success()),
            Err(_) => Ok(false),
        }
    }

    pub async fn stop(&self) -> Result<(), LiteLLMError> {
        let mut guard = self.process.lock().await;
        if let Some(ref mut child) = *guard {
            child
                .kill()
                .await
                .map_err(|e| LiteLLMError::StartFailed(format!("failed to kill process: {e}")))?;
            let _ = child.wait().await;
        }
        *guard = None;
        self.running.store(false, Ordering::SeqCst);
        Ok(())
    }

    pub fn is_running(&self) -> bool {
        self.running.load(Ordering::SeqCst)
    }

    pub fn base_url(&self) -> String {
        format!("http://{}:{}", DEFAULT_LITELLM_HOST, self.port)
    }

    pub async fn ensure_running(&self, config_path: Option<&str>) -> Result<(), LiteLLMError> {
        if self.health_check().await? {
            return Ok(());
        }
        self.stop().await.ok();
        self.start(config_path).await
    }
}

impl Drop for LiteLLMProxy {
    fn drop(&mut self) {
        self.running.store(false, Ordering::SeqCst);
    }
}
