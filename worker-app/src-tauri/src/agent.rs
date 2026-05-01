use crate::opencode_session::{
    MessagePart, OpenCodeClient, SendMessageRequest,
};
use std::collections::HashMap;
use std::path::Path;
use tokio::process::Command;

pub enum EngineMode {
    Cli,
    Server { base_url: String },
}

pub async fn run_agent<P: AsRef<Path>>(
    repo_dir: P,
    prompt: &str,
    engine: &str,
    settings: &HashMap<String, serde_json::Value>,
    logs: &mut Vec<String>,
) -> String {
    let repo_dir = repo_dir.as_ref();
    let mode = resolve_engine_mode(engine, settings);

    match mode {
        EngineMode::Server { base_url } => {
            run_server_agent(&base_url, repo_dir, prompt, settings, logs).await
        }
        EngineMode::Cli => run_cli_agent(repo_dir, prompt, engine, settings, logs).await,
    }
}

fn resolve_engine_mode(
    engine: &str,
    settings: &HashMap<String, serde_json::Value>,
) -> EngineMode {
    if let Some(url) = settings
        .get("server_url")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
    {
        return EngineMode::Server { base_url: url };
    }

    if engine == "opencode-server" {
        return EngineMode::Server {
            base_url: "http://127.0.0.1:4096".to_string(),
        };
    }

    EngineMode::Cli
}

async fn run_server_agent<P: AsRef<Path>>(
    base_url: &str,
    _repo_dir: P,
    prompt: &str,
    _settings: &HashMap<String, serde_json::Value>,
    logs: &mut Vec<String>,
) -> String {
    let client = OpenCodeClient::new(base_url);

    match client.health().await {
        Ok(health) if health.healthy => {}
        _ => {
            logs.push("OpenCode server not available, falling back to CLI".to_string());
            return String::new();
        }
    }

    let session = match client.create_session("idearefinery-task").await {
        Ok(s) => s,
        Err(e) => {
            logs.push(format!("Failed to create session: {e}"));
            return String::new();
        }
    };

    let req = SendMessageRequest {
        parts: vec![MessagePart {
            part_type: "text".to_string(),
            text: prompt.to_string(),
        }],
        model: None,
        agent: None,
    };

    match client.send_message(&session.id, &req).await {
        Ok(result) => {
            let text: Vec<String> = result
                .parts
                .iter()
                .filter_map(|p| {
                    p.get("text")
                        .and_then(|v| v.as_str())
                        .map(|s| s.to_string())
                })
                .collect();
            let output = text.join("\n");
            if !output.trim().is_empty() {
                logs.push(output.trim().to_string());
            }
            let _ = client.delete_session(&session.id).await;
            output
        }
        Err(e) => {
            logs.push(format!("Failed to send message: {e}"));
            let _ = client.delete_session(&session.id).await;
            String::new()
        }
    }
}

async fn run_cli_agent<P: AsRef<Path>>(
    repo_dir: P,
    prompt: &str,
    engine: &str,
    settings: &HashMap<String, serde_json::Value>,
    logs: &mut Vec<String>,
) -> String {
    let repo_dir = repo_dir.as_ref();

    if engine == "openclaude" && which::which("openclaude").is_ok() {
        let mut cmd = vec!["openclaude".to_string(), "-p".to_string()];
        if let Some(agent) = settings.get("agent").and_then(|v| v.as_str()) {
            cmd.push("--agent".to_string());
            cmd.push(agent.to_string());
        }
        if let Some(model) = settings.get("model").and_then(|v| v.as_str()) {
            cmd.push("--model".to_string());
            cmd.push(model.to_string());
        }
        if let Some(permission_mode) = settings.get("permission_mode").and_then(|v| v.as_str()) {
            cmd.push("--permission-mode".to_string());
            cmd.push(permission_mode.to_string());
        }
        if let Some(output_format) = settings.get("output_format").and_then(|v| v.as_str()) {
            cmd.push("--output-format".to_string());
            cmd.push(output_format.to_string());
        }
        if let Some(max_budget) = settings.get("max_budget_usd").and_then(|v| v.as_str()) {
            cmd.push("--max-budget-usd".to_string());
            cmd.push(max_budget.to_string());
        }
        if let Some(system_prompt) = settings.get("system_prompt").and_then(|v| v.as_str()) {
            cmd.push("--system-prompt".to_string());
            cmd.push(system_prompt.to_string());
        }
        if let Some(dirs) = settings.get("additional_dirs").and_then(|v| v.as_array()) {
            for d in dirs {
                if let Some(dir) = d.as_str() {
                    cmd.push("--add-dir".to_string());
                    cmd.push(dir.to_string());
                }
            }
        }
        cmd.push(prompt.to_string());
        let args: Vec<&str> = cmd.iter().map(|s| s.as_str()).collect();
        return run_command(&args, repo_dir, logs).await;
    }

    if engine == "opencode" && which::which("opencode").is_ok() {
        return run_command(
            &["opencode", "run", prompt],
            repo_dir,
            logs,
        )
        .await;
    }

    if which::which("codex").is_ok() {
        return run_command(
            &["codex", "exec", "-C", repo_dir.to_str().unwrap_or("."), prompt],
            repo_dir,
            logs,
        )
        .await;
    }

    logs.push(
        "No local coding engine found; returning deterministic fallback.".to_string(),
    );
    String::new()
}

async fn run_command(args: &[&str], cwd: &Path, logs: &mut Vec<String>) -> String {
    let label = args.join(" ");
    logs.push(format!("$ {}", label));

    let mut cmd = Command::new(args[0]);
    cmd.current_dir(cwd);
    cmd.args(&args[1..]);

    let output = match cmd.output().await {
        Ok(o) => o,
        Err(e) => {
            logs.push(format!("Failed to spawn: {}", e));
            return String::new();
        }
    };

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    let combined = format!("{}{}", stdout, stderr);
    if !combined.trim().is_empty() {
        logs.push(combined.trim().to_string());
    }
    logs.push(format!("exit code: {}", output.status.code().unwrap_or(-1)));

    combined
}
