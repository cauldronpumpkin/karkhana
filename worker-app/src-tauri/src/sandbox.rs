use crate::opencode_session::OpenCodeClient;
use serde::{Deserialize, Serialize};
use std::path::Path;

pub const AGENTS_MD_CONTENT: &str = r#"# IdeaRefinery Worker Constraints

## Absolute Rules (violation = immediate session termination)

1. **Workspace confinement**: All file operations MUST be within the repository
   directory. Never read, write, or traverse outside this directory.
2. **No credential access**: NEVER read files named `.env`, `credentials.json`,
   `*.pem`, `*.key`, or any file under `~/.aws/`, `~/.ssh/`, `~/.config/`.
   NEVER print or log environment variables.
3. **No destructive git operations**: No `git push --force`, `git reset --hard`,
   `git clean -fd`, or `git branch -D` on the default branch.
4. **No network egress**: Do not run `curl`, `wget`, `Invoke-WebRequest`, or any
   HTTP client commands. No `npm publish`, `docker push`, or similar.
5. **No package installation**: Do not run `npm install -g`, `pip install --system`,
   or any global/system-level package manager commands. Local installs
   (`npm install`, `pip install -e .`) are allowed only if specified in the task.
6. **No shell escape**: Do not run `bash -i`, `python -c "import os; os.system(...)"`,
   or any command intended to spawn interactive shells.
7. **No process management**: Do not run `kill`, `taskkill`, `pkill`, or similar.

## Behavioral Guidelines

- Create a feature branch for all changes. Never commit directly to
  the default branch (main/master).
- Keep commits atomic and well-described.
- Run the test suite before reporting completion.
- If tests fail and you cannot fix them within 3 attempts, report failure
  with the test output rather than continuing to loop.
- Report the diff summary and list of changed files when done.
"#;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PermissionPolicy {
    pub allow_file_edits: bool,
    pub allow_shell_commands: Vec<String>,
    pub deny_patterns: Vec<String>,
}

impl Default for PermissionPolicy {
    fn default() -> Self {
        PermissionPolicy {
            allow_file_edits: true,
            allow_shell_commands: vec![
                "git".to_string(),
                "npm test".to_string(),
                "npm run".to_string(),
                "python -m pytest".to_string(),
                "cargo test".to_string(),
                "go test".to_string(),
            ],
            deny_patterns: vec![
                "rm -rf /".to_string(),
                "del /s /q C:\\".to_string(),
                "format ".to_string(),
                "shutdown".to_string(),
                "reboot".to_string(),
            ],
        }
    }
}

pub fn write_agents_md(workspace: &Path) -> Result<std::path::PathBuf, String> {
    let agents_path = workspace.join("AGENTS.md");
    let backup_path = workspace.join("AGENTS.md.bak");
    if agents_path.exists() && !backup_path.exists() {
        let existing = std::fs::read(&agents_path)
            .map_err(|e| format!("Failed to back up existing AGENTS.md: {}", e))?;
        std::fs::write(&backup_path, existing)
            .map_err(|e| format!("Failed to create AGENTS.md backup: {}", e))?;
    }
    std::fs::write(&agents_path, AGENTS_MD_CONTENT)
        .map_err(|e| format!("Failed to write AGENTS.md: {}", e))?;
    Ok(agents_path)
}

pub fn remove_agents_md(workspace: &Path) -> Result<(), String> {
    let agents_path = workspace.join("AGENTS.md");
    let backup_path = workspace.join("AGENTS.md.bak");
    if backup_path.exists() {
        let backup = std::fs::read(&backup_path)
            .map_err(|e| format!("Failed to read AGENTS.md backup: {}", e))?;
        std::fs::write(&agents_path, backup)
            .map_err(|e| format!("Failed to restore AGENTS.md from backup: {}", e))?;
        std::fs::remove_file(&backup_path)
            .map_err(|e| format!("Failed to remove AGENTS.md backup: {}", e))?;
    } else if agents_path.exists() {
        std::fs::remove_file(&agents_path)
            .map_err(|e| format!("Failed to remove AGENTS.md: {}", e))?;
    }
    Ok(())
}

pub fn evaluate_permission(policy: &PermissionPolicy, tool_name: &str, input: &serde_json::Value) -> String {
    match tool_name {
        "write" | "edit" | "create" | "multiEdit" => {
            if !policy.allow_file_edits {
                return "deny".to_string();
            }
            if let Some(path) = input.get("file_path").and_then(|v| v.as_str()).or_else(|| input.get("path").and_then(|v| v.as_str())) {
                if is_restricted_path(path) {
                    return "deny".to_string();
                }
            }
            "allow".to_string()
        }
        "bash" | "shell" | "exec" | "command" => {
            let cmd = input.get("command")
                .and_then(|v| v.as_str())
                .or_else(|| input.get("input").and_then(|v| v.as_str()))
                .unwrap_or("");

            if is_deny_listed(cmd, &policy.deny_patterns) {
                return "deny".to_string();
            }

            if is_allow_listed(cmd, &policy.allow_shell_commands) {
                return "allow".to_string();
            }

            "deny".to_string()
        }
        "read" | "grep" | "glob" | "list" | "search" => {
            if let Some(path) = input.get("path").and_then(|v| v.as_str()).or_else(|| input.get("file_path").and_then(|v| v.as_str())) {
                if is_restricted_path(path) {
                    return "deny".to_string();
                }
            }
            "allow".to_string()
        }
        _ => "allow".to_string(),
    }
}

fn is_restricted_path(path: &str) -> bool {
    let lower = path.to_lowercase();
    let restricted = [
        ".env",
        "credentials.json",
        ".pem",
        ".key",
        ".aws",
        ".ssh",
        ".config",
    ];
    restricted.iter().any(|r| lower.contains(r))
}

fn is_deny_listed(cmd: &str, patterns: &[String]) -> bool {
    let lower = cmd.to_lowercase();
    patterns.iter().any(|p| lower.contains(&p.to_lowercase()))
}

fn is_allow_listed(cmd: &str, allowed: &[String]) -> bool {
    let cmd_trimmed = cmd.trim();
    allowed.iter().any(|a| {
        cmd_trimmed.starts_with(a.as_str()) || cmd_trimmed == a.as_str()
    })
}

pub async fn run_permission_guard(
    client: OpenCodeClient,
    session_id: String,
    policy: PermissionPolicy,
    cancelled: std::sync::Arc<std::sync::atomic::AtomicBool>,
) {
    use std::sync::atomic::Ordering;
    use std::time::Duration;

    loop {
        if cancelled.load(Ordering::SeqCst) {
            return;
        }

        if let Ok(messages) = client.list_messages(&session_id).await {
            for msg in &messages {
                for part in &msg.parts {
                    if let Some(perm) = part.get("permissionRequest") {
                        if let (Some(id), Some(tool)) = (
                            perm.get("id").and_then(|v| v.as_str()),
                            perm.get("tool").and_then(|v| v.as_str()),
                        ) {
                            if perm.get("response").is_some() {
                                continue;
                            }
                            let input = perm.get("input").cloned().unwrap_or(serde_json::Value::Null);
                            let response = evaluate_permission(&policy, tool, &input);
                            let _ = client.respond_permission(&session_id, id, &response).await;
                        }
                    }
                }
            }
        }

        tokio::time::sleep(Duration::from_secs(5)).await;
    }
}
