use crate::agent::run_agent;
use crate::git;
use crate::types::{BranchWorkResult, Job, Project};
use std::path::Path;

pub async fn branch_work<P: AsRef<Path>>(
    repo_dir: P,
    job: &Job,
    project: &Project,
    config: &crate::types::WorkerConfig,
    logs: &mut Vec<String>,
) -> Result<BranchWorkResult, crate::error::WorkerError> {
    let repo_dir = repo_dir.as_ref();
    let payload = job.payload.as_ref().and_then(|p| p.as_object()).cloned().unwrap_or_default();
    let full_control = config.allow_full_control && payload.get("allow_full_control").and_then(|v| v.as_bool()).unwrap_or(false);
    let branch = payload
        .get("branch_name")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
        .unwrap_or_else(|| format!("idearefinery/{}/{}", slug(&project.repo_full_name), &job.id[..job.id.len().min(8)]));

    git::git_checkout_new_branch(repo_dir, &branch, logs).await.map_err(|e| crate::error::WorkerError::Git(e))?;

    let mut prompt = payload
        .get("prompt")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
        .unwrap_or_else(|| "Implement the queued IdeaRefinery coding task, keep changes scoped, and run tests.".to_string());

    if !full_control {
        prompt.push_str("\n\nAutonomy boundary: create a branch and report results. Do not merge to main or force-push protected branches.");
    }

    let output = run_agent(repo_dir, &prompt, &config.engine, &config.openclaude, logs).await;

    let test_commands: Vec<String> = payload
        .get("test_commands")
        .and_then(|v| v.as_array())
        .map(|arr| arr.iter().filter_map(|v| v.as_str().map(|s| s.to_string())).collect())
        .unwrap_or_default();

    let tests_passed = run_tests(repo_dir, &test_commands, logs).await;

    let status = git::git_status_porcelain(repo_dir, logs).await.unwrap_or_default();
    let mut commit_sha = git::git_rev_parse_head(repo_dir, logs).await.unwrap_or_default();

    if !status.trim().is_empty() {
        git::git_add_all(repo_dir, logs).await.map_err(|e| crate::error::WorkerError::Git(e))?;
        let message = payload
            .get("commit_message")
            .and_then(|v| v.as_str())
            .map(|s| s.to_string())
            .unwrap_or_else(|| format!("feat: idea refinery task {}", &job.id[..job.id.len().min(8)]));
        git::git_commit(repo_dir, &message, logs).await.ok();
        commit_sha = git::git_rev_parse_head(repo_dir, logs).await.unwrap_or_default();
        git::git_push(repo_dir, &branch, "origin", logs).await.ok();
    }

    Ok(BranchWorkResult {
        branch_name: branch,
        commit_sha,
        commit_message: payload.get("commit_message").and_then(|v| v.as_str()).unwrap_or(&format!("IdeaRefinery task {}", &job.id[..job.id.len().min(8)])).to_string(),
        agent_output: output,
        tests_passed,
        full_control_used: full_control,
    })
}

async fn run_tests<P: AsRef<Path>>(repo_dir: P, commands: &[String], logs: &mut Vec<String>) -> bool {
    let repo_dir = repo_dir.as_ref();
    let mut cmds = commands.to_vec();
    if cmds.is_empty() {
        let index = crate::indexing::index_repo(repo_dir).await;
        cmds = index.test_commands;
    }
    let mut ok = true;
    for command in cmds.iter().take(4) {
        let parts: Vec<&str> = command.split_whitespace().collect();
        if parts.is_empty() {
            continue;
        }
        let mut cmd = tokio::process::Command::new(parts[0]);
        cmd.current_dir(repo_dir);
        cmd.args(&parts[1..]);
        logs.push(format!("$ {}", command));
        let output = match cmd.output().await {
            Ok(o) => o,
            Err(e) => {
                logs.push(format!("Failed to run test: {}", e));
                ok = false;
                continue;
            }
        };
        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);
        let combined = format!("{}{}", stdout, stderr);
        if !combined.trim().is_empty() {
            logs.push(combined.trim().to_string());
        }
        logs.push(format!("exit code: {}", output.status.code().unwrap_or(-1)));
        ok = ok && output.status.success();
    }
    ok
}

fn slug(value: &str) -> String {
    value
        .chars()
        .map(|ch| if ch.is_alphanumeric() { ch.to_lowercase().to_string() } else { "-".to_string() })
        .collect::<String>()
        .trim_matches('-')
        .to_string()
}
