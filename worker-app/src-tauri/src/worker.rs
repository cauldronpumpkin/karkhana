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
    DraftPullRequestMetadata, HIGH_AUTONOMY_REQUIRED_CAPABILITIES, Job, JobCompleteRequest,
    JobFailRequest, JobUpdateRequest, Project, VerificationResult, WorkerConfig, WorkerFailure,
    WorkerState,
};
use serde_json::json;
use serde_json::{Map, Value};
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Instant;
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
                .any(is_graphify_update_command)
        })
        .unwrap_or(false);
    cmds
}

fn is_graphify_update_command(command: &str) -> bool {
    let mut parts = command.split_whitespace();
    matches!(parts.next(), Some("graphify")) && matches!(parts.next(), Some("update"))
}

pub fn is_protected_branch_name(branch_name: &str, default_branch: Option<&str>) -> bool {
    let normalized = branch_name.trim();
    if normalized.is_empty() {
        return true;
    }
    let lowered = normalized.to_ascii_lowercase();
    matches!(lowered.as_str(), "main" | "master")
        || default_branch
            .map(|default_branch| lowered == default_branch.trim().to_ascii_lowercase())
            .unwrap_or(false)
}

pub fn resolve_work_branch_name(job: &Job, project: &Project, payload_obj: &Map<String, Value>) -> String {
    let mut candidates = Vec::new();
    if let Some(branch_name) = job.branch_name.as_deref() {
        candidates.push(branch_name.trim().to_string());
    }
    if let Some(branch_name) = payload_obj.get("branch_name").and_then(Value::as_str) {
        candidates.push(branch_name.trim().to_string());
    }

    for candidate in candidates {
        if !candidate.is_empty() && !is_protected_branch_name(&candidate, project.default_branch.as_deref()) {
            return candidate;
        }
    }

    let mut fallback = format!(
        "idearefinery/{}/{}",
        slug(&project.repo_full_name),
        &job.id[..job.id.len().min(8)]
    );
    if is_protected_branch_name(&fallback, project.default_branch.as_deref()) {
        fallback.push_str("-work");
    }
    fallback
}

pub fn resolve_verification_commands(
    payload_obj: &Map<String, Value>,
    legacy_test_commands: &[String],
) -> Vec<String> {
    let mut commands = string_list(payload_obj.get("verification_commands"));
    if commands.is_empty() {
        if let Some(bundle) = payload_obj.get("worker_context_bundle").and_then(Value::as_object) {
            commands = string_list(bundle.get("verification_commands"));
        }
    }
    if commands.is_empty() {
        commands = legacy_test_commands
            .iter()
            .map(|command| command.trim().to_string())
            .filter(|command| !command.is_empty())
            .collect();
    }
    commands
}

pub fn resolve_draft_pull_request_metadata(
    payload_obj: &Map<String, Value>,
) -> Option<DraftPullRequestMetadata> {
    if let Some(metadata) = payload_obj
        .get("draft_pull_request")
        .and_then(Value::as_object)
        .or_else(|| payload_obj.get("draft_pr").and_then(Value::as_object))
    {
        return Some(DraftPullRequestMetadata {
            url: metadata.get("url").and_then(Value::as_str).map(|s| s.to_string()),
            html_url: metadata
                .get("html_url")
                .and_then(Value::as_str)
                .map(|s| s.to_string()),
            number: metadata.get("number").and_then(Value::as_u64),
            draft: metadata.get("draft").and_then(Value::as_bool),
        });
    }

    let url = string_value(payload_obj.get("draft_pr_url"))
        .or_else(|| string_value(payload_obj.get("pull_request_url")))
        .or_else(|| string_value(payload_obj.get("pr_url")));
    let html_url = string_value(payload_obj.get("draft_pr_html_url"))
        .or_else(|| string_value(payload_obj.get("pull_request_html_url")))
        .or_else(|| string_value(payload_obj.get("pr_html_url")));
    let number = payload_obj
        .get("draft_pr_number")
        .or_else(|| payload_obj.get("pull_request_number"))
        .or_else(|| payload_obj.get("pr_number"))
        .and_then(Value::as_u64);
    let draft = payload_obj
        .get("draft_pr_draft")
        .or_else(|| payload_obj.get("pull_request_draft"))
        .and_then(Value::as_bool);

    if url.is_none() && html_url.is_none() && number.is_none() && draft.is_none() {
        None
    } else {
        Some(DraftPullRequestMetadata {
            url,
            html_url,
            number,
            draft,
        })
    }
}

fn string_value(value: Option<&Value>) -> Option<String> {
    value.and_then(Value::as_str).map(|value| value.trim().to_string()).filter(|value| !value.is_empty())
}

fn string_list(value: Option<&Value>) -> Vec<String> {
    value
        .and_then(Value::as_array)
        .map(|items| {
            items
                .iter()
                .filter_map(Value::as_str)
                .map(|command| command.trim().to_string())
                .filter(|command| !command.is_empty())
                .collect()
        })
        .unwrap_or_default()
}

fn tail_text(value: &str, max_chars: usize) -> String {
    let chars: Vec<char> = value.chars().collect();
    if chars.len() <= max_chars {
        return value.to_string();
    }
    chars[chars.len() - max_chars..].iter().collect()
}

fn structured_failure(
    code: &str,
    stage: &str,
    message: impl Into<String>,
    branch_name: Option<String>,
    repo_status: Option<String>,
    details: Option<Value>,
) -> WorkerFailure {
    WorkerFailure {
        code: code.to_string(),
        stage: stage.to_string(),
        message: message.into(),
        branch_name,
        repo_status,
        details,
    }
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
    .map_err(WorkerError::from)?;

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
    error: Option<WorkerFailure>,
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
            error: None,
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
                error: Some(structured_failure(
                    "opencode_session_create_failed",
                    "opencode_session",
                    e.to_string(),
                    None,
                    None,
                    None,
                )),
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
            "session_id": session.id.clone(),
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
            let empty_output_error = if output.trim().is_empty() {
                Some(structured_failure(
                    "opencode_empty_output",
                    "opencode_message",
                    "OpenCode returned empty output for branch work",
                    Some(session.id.clone()),
                    None,
                    None,
                ))
            } else {
                None
            };

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
                session_id: Some(session.id.clone()),
                diff,
                error: empty_output_error,
            }
        }
        Err(e) => {
            logs.push(format!("OpenCode session error: {e}"));
            let _ = opencode_client.delete_session(&session.id).await;
            CircuitBreakerResult {
                output: String::new(),
                session_id: Some(session.id.clone()),
                diff: String::new(),
                error: Some(structured_failure(
                    "opencode_message_failed",
                    "opencode_message",
                    e.to_string(),
                    Some(session.id.clone()),
                    None,
                    None,
                )),
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

    let branch = resolve_work_branch_name(job, project, &payload_obj);

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

    if let Some(failure) = cb_result.error {
        return Err(WorkerError::from(failure));
    }

    if cb_result.output.trim().is_empty() {
        return Err(WorkerError::from(structured_failure(
            "agent_output_empty",
            "agent_execution",
            "Branch work produced no OpenCode output",
            Some(branch.clone()),
            None,
            Some(json!({
                "session_id": cb_result.session_id,
                "diff": cb_result.diff,
            })),
        )));
    }

    let legacy_test_commands: Vec<String> = payload_obj
        .get("test_commands")
        .and_then(|v| v.as_array())
        .map(|arr| {
            arr.iter()
                .filter_map(|v| v.as_str().map(|s| s.to_string()))
                .collect()
        })
        .unwrap_or_default();

    let verification_commands = resolve_verification_commands(&payload_obj, &legacy_test_commands);
    if verification_commands.is_empty() {
        return Err(WorkerError::from(structured_failure(
            "missing_verification_commands",
            "verification",
            "No verification commands were provided",
            Some(branch.clone()),
            None,
            None,
        )));
    }

    let (verification_results, tests_passed, graphify_updated) =
        run_verification_commands(repo_dir, &verification_commands, logs).await;

    if !tests_passed {
        return Err(WorkerError::from(structured_failure(
            "verification_failed",
            "verification",
            "One or more verification commands failed",
            Some(branch.clone()),
            None,
            Some(json!({ "verification_results": verification_results })),
        )));
    }

    let status = crate::git::git_status_porcelain(repo_dir, logs)
        .await
        .map_err(WorkerError::Git)?;
    let mut commit_sha = crate::git::git_rev_parse_head(repo_dir, logs)
        .await
        .map_err(WorkerError::Git)?;

    if !status.trim().is_empty() {
        crate::git::git_add_all(repo_dir, logs)
            .await
            .map_err(WorkerError::Git)?;
        let commit_message = payload_obj
            .get("commit_message")
            .and_then(|v| v.as_str())
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .unwrap_or_else(|| format!("feat: idea refinery task {}", &job.id[..job.id.len().min(8)]));
        crate::git::git_commit(repo_dir, &commit_message, logs)
            .await
            .map_err(WorkerError::Git)?;
        commit_sha = crate::git::git_rev_parse_head(repo_dir, logs)
            .await
            .map_err(WorkerError::Git)?;
        crate::git::git_push(repo_dir, &branch, "origin", logs)
            .await
            .map_err(WorkerError::Git)?;
    }

    let draft_pull_request = resolve_draft_pull_request_metadata(&payload_obj);
    let draft_pull_request_todo = draft_pull_request.is_none().then(|| {
        "TODO: integrate draft pull request creation via backend/app/services/github_app.py and surface the returned metadata here.".to_string()
    });

    Ok(crate::types::BranchWorkResult {
        branch_name: branch,
        commit_sha,
        commit_message: payload_obj
            .get("commit_message")
            .and_then(|v| v.as_str())
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty())
            .unwrap_or_else(|| format!("IdeaRefinery task {}", &job.id[..job.id.len().min(8)])),
        agent_output: cb_result.output,
        tests_passed,
        full_control_used: full_control,
        verification_results,
        graphify_updated,
        ledger_updated: false,
        ledger_sections_updated: Vec::new(),
        draft_pull_request,
        draft_pull_request_todo,
    })
}

async fn run_verification_commands(
    repo_dir: &PathBuf,
    commands: &[String],
    logs: &mut Vec<String>,
) -> (Vec<VerificationResult>, bool, bool) {
    let mut results = Vec::new();
    let mut all_passed = true;
    let mut graphify_updated = false;

    for command in commands {
        let command = command.trim();
        if command.is_empty() {
            continue;
        }

        let start = Instant::now();
        let parts: Vec<&str> = command.split_whitespace().collect();
        if parts.is_empty() {
            continue;
        }

        logs.push(format!("$ {}", command));
        let output = match tokio::process::Command::new(parts[0])
            .current_dir(repo_dir)
            .args(&parts[1..])
            .output()
            .await
        {
            Ok(output) => output,
            Err(error) => {
                let result = VerificationResult {
                    command: command.to_string(),
                    status: "error".to_string(),
                    exit_code: None,
                    stdout_tail: String::new(),
                    stderr_tail: tail_text(&error.to_string(), 1000),
                    duration_seconds: start.elapsed().as_secs_f64(),
                };
                logs.push(result.stderr_tail.clone());
                results.push(result);
                all_passed = false;
                continue;
            }
        };

        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        let stdout_tail = tail_text(&stdout, 1000);
        let stderr_tail = tail_text(&stderr, 1000);
        if !stdout_tail.trim().is_empty() {
            logs.push(stdout_tail.clone());
        }
        if !stderr_tail.trim().is_empty() {
            logs.push(stderr_tail.clone());
        }

        let exit_code = output.status.code();
        let status = if output.status.success() {
            "passed"
        } else {
            all_passed = false;
            "failed"
        };
        if is_graphify_update_command(command) && output.status.success() {
            graphify_updated = true;
        }

        results.push(VerificationResult {
            command: command.to_string(),
            status: status.to_string(),
            exit_code,
            stdout_tail,
            stderr_tail,
            duration_seconds: start.elapsed().as_secs_f64(),
        });
    }

    (results, all_passed && !commands.is_empty(), graphify_updated)
}

#[cfg(test)]
mod tests {
    use super::is_graphify_update_command;

    #[test]
    fn graphify_update_detection_is_exact() {
        assert!(is_graphify_update_command("graphify update ."));
        assert!(is_graphify_update_command("graphify update"));
        assert!(!is_graphify_update_command("echo graphify update ."));
        assert!(!is_graphify_update_command("graphify status"));
        assert!(!is_graphify_update_command("graphify-update ."));
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
