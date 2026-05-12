use crate::types::WorkerFailure;
use std::path::Path;
use tokio::process::Command;

fn emit_git_log(app: Option<&tauri::AppHandle>, logs: &mut Vec<String>, line: String) {
    if let Some(app) = app {
        crate::worker::emit_log_event(app, logs, line);
    } else {
        logs.push(line);
    }
}

pub async fn git_run<P: AsRef<Path>>(
    app: Option<&tauri::AppHandle>,
    repo_dir: P,
    args: &[&str],
    logs: &mut Vec<String>,
) -> Result<String, String> {
    let repo_dir = repo_dir.as_ref();
    let mut cmd = Command::new("git");
    cmd.current_dir(repo_dir);
    cmd.args(args);

    let label = format!("git {}", args.join(" "));
    emit_git_log(app, logs, format!("$ {}", label));

    let output = cmd
        .output()
        .await
        .map_err(|e| format!("Failed to run git: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    let combined = format!("{}{}", stdout, stderr);
    if !combined.trim().is_empty() {
        emit_git_log(app, logs, combined.trim().to_string());
    }
    emit_git_log(app, logs, format!("exit code: {}", output.status.code().unwrap_or(-1)));

    if !output.status.success() {
        return Err(format!("Git command failed: {}", label));
    }

    Ok(combined)
}

pub async fn ensure_repo<P: AsRef<Path>>(
    repo_dir: P,
    clone_url: &str,
    branch: &str,
    logs: &mut Vec<String>,
) -> Result<(), WorkerFailure> {
    ensure_repo_with_app(None, repo_dir, clone_url, branch, logs).await
}

pub async fn ensure_repo_with_app<P: AsRef<Path>>(
    app: Option<&tauri::AppHandle>,
    repo_dir: P,
    clone_url: &str,
    branch: &str,
    logs: &mut Vec<String>,
) -> Result<(), WorkerFailure> {
    let repo_dir = repo_dir.as_ref();
    if repo_dir.exists() {
        let status = git_status_porcelain(app, repo_dir, logs)
            .await
            .map_err(|message| WorkerFailure {
                code: "repo_status_check_failed".to_string(),
                stage: "preflight".to_string(),
                message,
                branch_name: Some(branch.to_string()),
                repo_status: None,
                details: None,
            })?;
        if !status.trim().is_empty() {
            return Err(WorkerFailure {
                code: "repo_dirty_preflight".to_string(),
                stage: "branch_checkout".to_string(),
                message: "Repository has uncommitted changes before branch checkout".to_string(),
                branch_name: Some(branch.to_string()),
                repo_status: Some(status),
                details: None,
            });
        }
        git_run(app, repo_dir, &["fetch", "--all", "--prune"], logs)
            .await
            .map_err(|message| WorkerFailure {
                code: "repo_fetch_failed".to_string(),
                stage: "repo_sync".to_string(),
                message,
                branch_name: Some(branch.to_string()),
                repo_status: None,
                details: None,
            })?;
        git_run(app, repo_dir, &["checkout", branch], logs)
            .await
            .map_err(|message| WorkerFailure {
                code: "repo_checkout_failed".to_string(),
                stage: "repo_sync".to_string(),
                message,
                branch_name: Some(branch.to_string()),
                repo_status: None,
                details: None,
            })?;
        git_run(app, repo_dir, &["pull", "--ff-only"], logs)
            .await
            .map_err(|message| WorkerFailure {
                code: "repo_pull_failed".to_string(),
                stage: "repo_sync".to_string(),
                message,
                branch_name: Some(branch.to_string()),
                repo_status: None,
                details: None,
            })?;
        return Ok(());
    }
    let parent = repo_dir.parent();
    if let Some(p) = parent {
        let _ = tokio::fs::create_dir_all(p).await;
    }
    let _ = git_run(
        app,
        parent.unwrap_or(std::path::Path::new(".")),
        &["clone", "--branch", branch, clone_url, repo_dir.to_str().unwrap_or("")],
        logs,
    )
    .await
    .map_err(|message| WorkerFailure {
        code: "repo_clone_failed".to_string(),
        stage: "repo_clone".to_string(),
        message,
        branch_name: Some(branch.to_string()),
        repo_status: None,
        details: None,
    })?;
    Ok(())
}

pub async fn git_clone<P: AsRef<Path>>(
    app: Option<&tauri::AppHandle>,
    target_dir: P,
    clone_url: &str,
    branch: &str,
    logs: &mut Vec<String>,
) -> Result<(), String> {
    let target_dir = target_dir.as_ref();
    if let Some(parent) = target_dir.parent() {
        let _ = tokio::fs::create_dir_all(parent).await;
    }
    git_run(
        app,
        target_dir.parent().unwrap_or(std::path::Path::new(".")),
        &["clone", "--branch", branch, clone_url, target_dir.to_str().unwrap_or("")],
        logs,
    )
    .await?;
    Ok(())
}

pub async fn git_fetch_all<P: AsRef<Path>>(app: Option<&tauri::AppHandle>, repo_dir: P, logs: &mut Vec<String>) -> Result<String, String> {
    git_run(app, repo_dir.as_ref(), &["fetch", "--all", "--prune"], logs).await
}

pub async fn git_checkout<P: AsRef<Path>>(app: Option<&tauri::AppHandle>, repo_dir: P, branch: &str, logs: &mut Vec<String>) -> Result<String, String> {
    git_run(app, repo_dir.as_ref(), &["checkout", branch], logs).await
}

pub async fn git_pull_ff<P: AsRef<Path>>(app: Option<&tauri::AppHandle>, repo_dir: P, logs: &mut Vec<String>) -> Result<String, String> {
    git_run(app, repo_dir.as_ref(), &["pull", "--ff-only"], logs).await
}

pub async fn git_add_all<P: AsRef<Path>>(app: Option<&tauri::AppHandle>, repo_dir: P, logs: &mut Vec<String>) -> Result<String, String> {
    git_run(app, repo_dir.as_ref(), &["add", "."], logs).await
}

pub async fn git_commit<P: AsRef<Path>>(app: Option<&tauri::AppHandle>, repo_dir: P, message: &str, logs: &mut Vec<String>) -> Result<String, String> {
    git_run(app, repo_dir.as_ref(), &["commit", "-m", message], logs).await
}

pub async fn git_push<P: AsRef<Path>>(
    app: Option<&tauri::AppHandle>,
    repo_dir: P,
    branch: &str,
    remote: &str,
    logs: &mut Vec<String>,
) -> Result<String, String> {
    git_run(app, repo_dir.as_ref(), &["push", "-u", remote, branch], logs).await
}

pub async fn git_status_porcelain<P: AsRef<Path>>(app: Option<&tauri::AppHandle>, repo_dir: P, logs: &mut Vec<String>) -> Result<String, String> {
    git_run(app, repo_dir.as_ref(), &["status", "--porcelain"], logs).await
}

pub async fn git_rev_parse_head<P: AsRef<Path>>(app: Option<&tauri::AppHandle>, repo_dir: P, logs: &mut Vec<String>) -> Result<String, String> {
    let out = git_run(app, repo_dir.as_ref(), &["rev-parse", "HEAD"], logs).await?;
    Ok(out.trim().to_string())
}

pub async fn git_checkout_new_branch<P: AsRef<Path>>(
    app: Option<&tauri::AppHandle>,
    repo_dir: P,
    branch: &str,
    logs: &mut Vec<String>,
) -> Result<String, String> {
    git_run(app, repo_dir.as_ref(), &["checkout", "-B", branch], logs).await
}
