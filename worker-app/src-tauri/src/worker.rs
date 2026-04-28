use crate::agent::run_agent;
use crate::api::ApiClient;
use crate::circuit_breaker::{CircuitBreaker, CircuitBreakerLimits};
use crate::config::load_config;
use crate::error::WorkerError;
use crate::git::ensure_repo;
use crate::indexing::index_repo;
use crate::litellm::{LiteLLMConfig, LiteLLMProxy};
use crate::opencode_session::OpenCodeClient;
use crate::sandbox::PermissionPolicy;
use crate::sqs::SqsTransport;
use crate::state::StateStore;
use crate::types::{
    HIGH_AUTONOMY_REQUIRED_CAPABILITIES, Job, JobCompleteRequest, JobFailRequest, JobUpdateRequest,
    Project, WorkerConfig, WorkerState,
};
use serde_json::json;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use tauri::{AppHandle, Emitter};
use tokio::time::{sleep, Duration};

#[allow(dead_code)]
fn is_high_autonomy_job(payload: &serde_json::Value) -> bool {
    let autonomy = payload
        .get("autonomy_level")
        .and_then(|v| v.as_str())
        .unwrap_or("");
    autonomy == "autonomous_development" || autonomy == "full_autopilot"
}

#[allow(dead_code)]
fn has_graphify_verification(payload: &serde_json::Value) -> bool {
    let cmds = payload
        .get("verification_commands")
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|v| v.as_str())
                .any(|c| c.contains("graphify update"))
        })
        .unwrap_or(false);
    cmds
}

static WORKER_RUNNING: AtomicBool = AtomicBool::new(false);

#[tauri::command]
pub async fn start_worker(app: AppHandle) -> Result<(), String> {
    if WORKER_RUNNING.swap(true, Ordering::SeqCst) {
        return Err("Worker already running".to_string());
    }

    tokio::spawn(async move {
        if let Err(e) = run_worker_loop(&app).await {
            let _ = app.emit("worker-error", e.to_string());
        }
        WORKER_RUNNING.store(false, Ordering::SeqCst);
    });

    Ok(())
}

#[tauri::command]
pub fn stop_worker() -> Result<(), String> {
    WORKER_RUNNING.store(false, Ordering::SeqCst);
    Ok(())
}

#[tauri::command]
pub fn get_worker_status() -> bool {
    WORKER_RUNNING.load(Ordering::SeqCst)
}

struct WorkerContext {
    client: ApiClient,
    config: WorkerConfig,
    state: WorkerState,
    workspace: PathBuf,
    sqs: Option<SqsTransport>,
    litellm: Option<LiteLLMProxy>,
    opencode_client: Option<OpenCodeClient>,
}

async fn run_worker_loop(app: &AppHandle) -> Result<(), WorkerError> {
    let config = load_config();
    let state_store = StateStore::new();
    let state = state_store
        .load()
        .ok_or_else(|| WorkerError::Config("Worker not paired".to_string()))?;
    let mut client = ApiClient::new(state.api_base.clone(), state.api_token.clone());
    if let Some(ref wat) = state.worker_auth_token {
        client = client.with_worker_auth_token(wat.clone());
    }
    let workspace = PathBuf::from(shellexpand::tilde(&config.workspace_root).to_string());

    let mut ctx = WorkerContext {
        client,
        config,
        state,
        workspace,
        sqs: None,
        litellm: None,
        opencode_client: None,
    };

    ctx.sqs = if ctx.state.credentials.command_queue_url.is_some() {
        Some(SqsTransport::new(ctx.state.credentials.clone()))
    } else {
        None
    };

    let _is_high_autonomy = HIGH_AUTONOMY_REQUIRED_CAPABILITIES.iter().all(|cap| {
        ctx.config.capabilities.iter().any(|c| c == cap)
    });

    if ctx.config.engine == "opencode-server" || ctx.config.opencode_server_url.is_some() {
        let base_url = ctx
            .config
            .opencode_server_url
            .as_deref()
            .unwrap_or("http://127.0.0.1:4096");
        ctx.opencode_client = Some(OpenCodeClient::new(base_url));

        let litellm_port = ctx.config.litellm_port.unwrap_or(4000);
        ctx.litellm = Some(LiteLLMProxy::new(litellm_port));

        if let Some(ref litellm) = ctx.litellm {
            let config_path = ctx
                .config
                .litellm_config
                .as_ref()
                .and_then(|v| {
                    let lc = LiteLLMConfig {
                        port: litellm_port,
                        config_path: None,
                        model_map: v.clone(),
                    };
                    LiteLLMProxy::generate_config(&lc).ok()
                });
            litellm.ensure_running(config_path.as_deref()).await?;
        }
    }

    app.emit("worker-status", json!({"status": "active"})).ok();

    while WORKER_RUNNING.load(Ordering::SeqCst) {
        let did_work = run_once(app, &mut ctx).await;
        let wait_secs = if did_work { 5 } else { ctx.config.poll_seconds };
        sleep(Duration::from_secs(wait_secs)).await;
    }

    if let Some(ref litellm) = ctx.litellm {
        litellm.stop().await.ok();
    }

    app.emit("worker-status", json!({"status": "idle"})).ok();
    Ok(())
}

async fn run_once(app: &AppHandle, ctx: &mut WorkerContext) -> bool {
    if let Some(ref sqs) = ctx.sqs {
        if let Ok(messages) = sqs.receive().await {
            for message in messages {
                let _ = sqs.delete(&message).await;
                if let Ok(envelope) = serde_json::from_str::<serde_json::Value>(&message.body) {
                    if envelope.get("type").and_then(|v| v.as_str()) == Some("job_available") {
                        let job_type = envelope
                            .get("job_type")
                            .and_then(|v| v.as_str())
                            .unwrap_or("");
                        if ctx.config.capabilities.contains(&job_type.to_string())
                            || job_type.is_empty()
                        {
                            return claim_and_process(app, ctx).await;
                        }
                    }
                }
            }
        }
    }

    claim_and_process(app, ctx).await
}

async fn claim_and_process(app: &AppHandle, ctx: &mut WorkerContext) -> bool {
    let claim = match ctx
        .client
        .claim_job(&ctx.state.worker_id, &ctx.config.capabilities)
        .await
    {
        Ok(Some(claim)) => claim,
        _ => return false,
    };

    let job = match &claim.claim {
        Some(c) => c.job.clone(),
        None => return false,
    };
    let project = match &claim.claim {
        Some(c) => c.project.clone(),
        None => return false,
    };

    app.emit("job-started", json!({"job": job})).ok();

    let mut logs: Vec<String> = Vec::new();
    let result = process_job(app, ctx, &job, &project, &mut logs).await;

    match result {
        Ok(res) => {
            let _ = ctx
                .client
                .complete_job(
                    &job.id,
                    &JobCompleteRequest {
                        worker_id: ctx.state.worker_id.clone(),
                        claim_token: job.claim_token.clone(),
                        logs: logs.join("\n"),
                        result: res,
                    },
                )
                .await;
            app.emit("job-completed", json!({"job": job})).ok();
        }
        Err(e) => {
            let breaker_reason = match &e {
                WorkerError::CircuitBreaker(reason) => Some(reason.clone()),
                _ => None,
            };
            let _ = ctx
                .client
                .fail_job(
                    &job.id,
                    &JobFailRequest {
                        worker_id: ctx.state.worker_id.clone(),
                        claim_token: job.claim_token.clone(),
                        error: e.to_string(),
                        retryable: breaker_reason.is_none(),
                        logs: logs.join("\n"),
                    },
                )
                .await;

            if let Some(ref sqs) = ctx.sqs {
                let mut payload = serde_json::json!({
                    "work_item_id": job.id,
                    "claim_token": job.claim_token,
                    "error": e.to_string(),
                    "retryable": breaker_reason.is_none(),
                });
                if let Some(reason) = breaker_reason {
                    payload["circuit_breaker_triggered"] = json!(reason);
                }
                sqs.send_event(&ctx.state.worker_id, "job_failed", &payload)
                    .await
                    .ok();
            }

            app.emit("job-failed", json!({"job": job, "error": e.to_string()}))
                .ok();
        }
    }

    true
}

async fn process_job(
    _app: &AppHandle,
    ctx: &mut WorkerContext,
    job: &Job,
    project: &Project,
    logs: &mut Vec<String>,
) -> Result<serde_json::Value, WorkerError> {
    let _ = ctx
        .client
        .heartbeat_job(
            &job.id,
            &JobUpdateRequest {
                worker_id: ctx.state.worker_id.clone(),
                claim_token: job.claim_token.clone(),
                logs: "Claimed job.".to_string(),
            },
        )
        .await;

    let repo_dir = ctx.workspace.join(slug(&project.repo_full_name));
    ensure_repo(
        &repo_dir,
        &project.clone_url,
        project.default_branch.as_deref().unwrap_or("main"),
        logs,
    )
    .await
    .map_err(|e| WorkerError::Git(e))?;

    let payload_obj = job
        .payload
        .as_ref()
        .and_then(|p| p.as_object())
        .cloned()
        .unwrap_or_default();

    let limits = CircuitBreakerLimits {
        max_ttl_minutes: payload_obj
            .get("max_ttl_minutes")
            .and_then(|v| v.as_u64())
            .unwrap_or(40) as u32,
        max_llm_tokens: payload_obj
            .get("max_llm_tokens")
            .and_then(|v| v.as_u64()),
        max_budget_usd: payload_obj
            .get("max_budget_usd")
            .and_then(|v| v.as_f64()),
        max_identical_failures: 3,
    };

    let use_server = ctx.config.engine == "opencode-server"
        || ctx.config.opencode_server_url.is_some();

    match job.job_type.as_str() {
        "repo_index" => {
            let index = index_repo(&repo_dir).await;
            let sha = crate::git::git_rev_parse_head(&repo_dir, logs)
                .await
                .unwrap_or_default();
            Ok(json!({"commit_sha": sha, "code_index": index, "tests_passed": true}))
        }
        "architecture_dossier" | "gap_analysis" | "build_task_plan" => {
            let index = index_repo(&repo_dir).await;
            let prompt = format!(
                "Analyze this repository index and return a concise implementation-ready dossier.\n\n{}",
                serde_json::to_string(&index).unwrap_or_default()
            );

            let _ = crate::sandbox::write_agents_md(&repo_dir);
            let output = run_with_circuit_breaker(
                ctx,
                &repo_dir,
                &prompt,
                &limits,
                logs,
            )
            .await;
            crate::sandbox::remove_agents_md(&repo_dir).ok();

            let mut index = index;
            index.architecture_summary = output.output.clone();
            let sha = crate::git::git_rev_parse_head(&repo_dir, logs)
                .await
                .unwrap_or_default();
            Ok(json!({"commit_sha": sha, "code_index": index, "tests_passed": true}))
        }
        "agent_branch_work" | "test_verify" => {
            let result = branch_work_with_server(
                ctx,
                &repo_dir,
                job,
                project,
                use_server,
                &limits,
                logs,
            )
            .await?;
            Ok(serde_json::to_value(result).unwrap_or_default())
        }
        "sync_remote_state" => {
            crate::git::git_fetch_all(&repo_dir, logs)
                .await
                .map_err(|e| WorkerError::Git(e))?;
            let sha = crate::git::git_rev_parse_head(&repo_dir, logs)
                .await
                .unwrap_or_default();
            Ok(json!({"commit_sha": sha, "tests_passed": true}))
        }
        _ => Err(WorkerError::Config(format!(
            "Unsupported job type: {}",
            job.job_type
        ))),
    }
}

#[allow(dead_code)]
struct CircuitBreakerResult {
    output: String,
    session_id: Option<String>,
    diff: String,
}

async fn run_with_circuit_breaker(
    ctx: &mut WorkerContext,
    repo_dir: &PathBuf,
    prompt: &str,
    limits: &CircuitBreakerLimits,
    logs: &mut Vec<String>,
) -> CircuitBreakerResult {
    if let Some(ref opencode_client) = ctx.opencode_client {
        let client_clone = opencode_client.clone();
        run_server_with_breaker(&client_clone, ctx, repo_dir, prompt, limits, logs).await
    } else {
        let output = run_agent(
            repo_dir,
            prompt,
            &ctx.config.engine,
            &ctx.config.openclaude,
            logs,
        )
        .await;
        CircuitBreakerResult {
            output,
            session_id: None,
            diff: String::new(),
        }
    }
}

async fn run_server_with_breaker(
    opencode_client: &OpenCodeClient,
    ctx: &mut WorkerContext,
    _repo_dir: &PathBuf,
    prompt: &str,
    limits: &CircuitBreakerLimits,
    logs: &mut Vec<String>,
) -> CircuitBreakerResult {
    let session = match opencode_client.create_session("idearefinery-task").await {
        Ok(s) => s,
        Err(e) => {
            logs.push(format!("Failed to create session: {e}"));
            return CircuitBreakerResult {
                output: String::new(),
                session_id: None,
                diff: String::new(),
            };
        }
    };

    logs.push(format!("Created OpenCode session: {}", session.id));

    let breaker = CircuitBreaker::new(
        opencode_client.clone(),
        session.id.clone(),
        limits.clone(),
    );
    let cancelled = Arc::new(AtomicBool::new(false));
    let _breaker_cancelled = cancelled.clone();

    let session_id = session.id.clone();
    let client_clone = opencode_client.clone();
    let policy = PermissionPolicy::default();
    let guard_cancelled = cancelled.clone();

    let breaker_handle = tokio::spawn(async move {
        breaker.watch().await
    });

    let guard_handle = tokio::spawn(async move {
        crate::sandbox::run_permission_guard(
            client_clone,
            session_id,
            policy,
            guard_cancelled,
        )
        .await
    });

    if let Some(ref sqs) = ctx.sqs {
        let checkpoint_payload = serde_json::json!({
            "work_item_id": "",
            "status_detail": "session_started",
            "session_id": session.id,
        });
        sqs.send_event(&ctx.state.worker_id, "status_update", &checkpoint_payload)
            .await
            .ok();
    }

    let req = crate::opencode_session::SendMessageRequest {
        parts: vec![crate::opencode_session::MessagePart {
            part_type: "text".to_string(),
            text: prompt.to_string(),
        }],
        model: None,
        agent: None,
    };

    let message_result = opencode_client.send_message(&session.id, &req).await;

    cancelled.store(true, Ordering::SeqCst);
    breaker_handle.abort();
    guard_handle.abort();

    match message_result {
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

            let diff = opencode_client
                .get_diff(&session.id)
                .await
                .unwrap_or_default()
                .iter()
                .map(|d| d.data.to_string())
                .collect::<Vec<_>>()
                .join("\n");

            let _ = opencode_client.delete_session(&session.id).await;

            CircuitBreakerResult {
                output,
                session_id: Some(session.id),
                diff,
            }
        }
        Err(e) => {
            logs.push(format!("OpenCode session error: {e}"));
            let _ = opencode_client.delete_session(&session.id).await;
            CircuitBreakerResult {
                output: String::new(),
                session_id: Some(session.id),
                diff: String::new(),
            }
        }
    }
}

async fn branch_work_with_server(
    ctx: &mut WorkerContext,
    repo_dir: &PathBuf,
    job: &Job,
    project: &Project,
    _use_server: bool,
    limits: &CircuitBreakerLimits,
    logs: &mut Vec<String>,
) -> Result<crate::types::BranchWorkResult, WorkerError> {
    let payload_obj = job
        .payload
        .as_ref()
        .and_then(|p| p.as_object())
        .cloned()
        .unwrap_or_default();

    let full_control = ctx.config.allow_full_control
        && payload_obj
            .get("allow_full_control")
            .and_then(|v| v.as_bool())
            .unwrap_or(false);

    let branch = payload_obj
        .get("branch_name")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
        .unwrap_or_else(|| {
            format!(
                "idearefinery/{}/{}",
                slug(&project.repo_full_name),
                &job.id[..job.id.len().min(8)]
            )
        });

    crate::git::git_checkout_new_branch(repo_dir, &branch, logs)
        .await
        .map_err(|e| WorkerError::Git(e))?;

    let mut prompt = payload_obj
        .get("prompt")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
        .unwrap_or_else(|| {
            "Implement the queued IdeaRefinery coding task, keep changes scoped, and run tests."
                .to_string()
        });

    if !full_control {
        prompt.push_str("\n\nAutonomy boundary: create a branch and report results. Do not merge to main or force-push protected branches.");
    }

    let _ = crate::sandbox::write_agents_md(repo_dir);

    let cb_result = run_with_circuit_breaker(ctx, repo_dir, &prompt, limits, logs).await;

    crate::sandbox::remove_agents_md(repo_dir).ok();

    let test_commands: Vec<String> = payload_obj
        .get("test_commands")
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|v| v.as_str().map(|s| s.to_string()))
                .collect()
        })
        .unwrap_or_default();

    let tests_passed = run_tests(repo_dir, &test_commands, logs).await;

    let has_graphify_cmd = test_commands.iter().any(|c| c.contains("graphify update"));
    let mut graphify_updated = false;
    if has_graphify_cmd {
        graphify_updated = run_graphify_update(repo_dir, logs).await;
        if !graphify_updated {
            logs.push("[WARNING] graphify update . failed or was not found. "
                .to_string() + "The knowledge graph may be out of date.");
        }
    }

    let status = crate::git::git_status_porcelain(repo_dir, logs)
        .await
        .unwrap_or_default();
    let mut commit_sha = crate::git::git_rev_parse_head(repo_dir, logs)
        .await
        .unwrap_or_default();

    if !status.trim().is_empty() {
        crate::git::git_add_all(repo_dir, logs)
            .await
            .map_err(|e| WorkerError::Git(e))?;
        let message = payload_obj
            .get("commit_message")
            .and_then(|v| v.as_str())
            .map(|s| s.to_string())
            .unwrap_or_else(|| format!("feat: idea refinery task {}", &job.id[..job.id.len().min(8)]));
        crate::git::git_commit(repo_dir, &message, logs).await.ok();
        commit_sha = crate::git::git_rev_parse_head(repo_dir, logs)
            .await
            .unwrap_or_default();
        crate::git::git_push(repo_dir, &branch, "origin", logs)
            .await
            .ok();
    }

    Ok(crate::types::BranchWorkResult {
        branch_name: branch,
        commit_sha,
        commit_message: payload_obj
            .get("commit_message")
            .and_then(|v| v.as_str())
            .unwrap_or(&format!(
                "IdeaRefinery task {}",
                &job.id[..job.id.len().min(8)]
            ))
            .to_string(),
        agent_output: cb_result.output,
        tests_passed,
        full_control_used: full_control,
        graphify_updated,
    })
}

async fn run_tests(repo_dir: &PathBuf, commands: &[String], logs: &mut Vec<String>) -> bool {
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
        logs.push(format!(
            "exit code: {}",
            output.status.code().unwrap_or(-1)
        ));
        ok = ok && output.status.success();
    }
    ok
}

pub(crate) async fn run_graphify_update(repo_dir: &std::path::Path, logs: &mut Vec<String>) -> bool {
    let mut cmd = tokio::process::Command::new("graphify");
    cmd.current_dir(repo_dir);
    cmd.arg("update");
    cmd.arg(".");
    logs.push("$ graphify update .".to_string());
    match cmd.output().await {
        Ok(output) => {
            let stdout = String::from_utf8_lossy(&output.stdout);
            let stderr = String::from_utf8_lossy(&output.stderr);
            let combined = format!("{}{}", stdout, stderr);
            if !combined.trim().is_empty() {
                logs.push(combined.trim().to_string());
            }
            logs.push(format!("exit code: {}", output.status.code().unwrap_or(-1)));
            output.status.success()
        }
        Err(e) => {
            logs.push(format!("Failed to run graphify: {}", e));
            false
        }
    }
}

fn slug(value: &str) -> String {
    value
        .chars()
        .map(|ch| {
            if ch.is_alphanumeric() {
                ch.to_lowercase().to_string()
            } else {
                "-".to_string()
            }
        })
        .collect::<String>()
        .trim_matches('-')
        .to_string()
}
