# Karkhana OpenCode Execution Contract

> **Status:** Verified against OpenCode CLI v1.14.28, worker-app (`src-tauri`), and backend `factory_run.py` / `local_workers.py`.
> **Scope:** This document defines how Karkhana local workers invoke OpenCode, what capabilities are confirmed, what remains unverified, and the execution contract the backend expects from workers regardless of engine internals.

---

## 1. Verified OpenCode Capabilities

### 1.1 CLI Interface (`opencode` v1.14.28)

| Command | Verified? | Notes |
|---------|-----------|-------|
| `opencode serve` | ✅ Yes | Starts headless HTTP server. `--port`, `--hostname`, `--cors` supported. |
| `opencode run [message]` | ✅ Yes | One-shot execution. Supports `--model`, `--agent`, `--format json`, `--title`, `--dir`, `--dangerously-skip-permissions`. |
| `opencode session list/delete` | ✅ Yes | Session management via CLI. |
| `opencode mcp add/list/auth` | ✅ Yes | MCP server management exists as CLI commands. |
| `opencode agent create/list` | ✅ Yes | Agent definitions exist. |
| `opencode providers login/logout` | ✅ Yes | Provider credential management. |
| `opencode attach <url>` | ✅ Yes | Attach to a running server (used for remote). |
| `opencode stats/export` | ✅ Yes | Token usage and session export. |

### 1.2 HTTP Server API (Verified by Worker-App Integration)

The worker-app (`worker-app/src-tauri/src/opencode_session.rs`) implements the following client against a running `opencode serve` instance:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/global/health` | GET | Health check returning `healthy`, `version`. |
| `/session` | POST | Create session with optional `title`. |
| `/session/{id}` | GET | Get session metadata. |
| `/session/{id}` | DELETE | Delete session. |
| `/session/{id}/abort` | POST | Abort active session. |
| `/session/{id}/message` | POST | Send message (`parts`, optional `model`, optional `agent`). |
| `/session/{id}/message` | GET | List messages in session. |
| `/session/{id}/diff` | GET | Retrieve file diffs from session. |
| `/session/{id}/permissions/{perm_id}` | POST | Respond to a permission request (`response`, `remember`). |
| `/session/status` | GET | Get all session statuses. |

**Authentication:** None of the above endpoints currently use authentication in the worker-app integration. The server binds to `127.0.0.1` by default.

### 1.3 LiteLLM Model Routing

The worker-app manages a local `litellm-proxy` process when `engine == "opencode-server"`:

- Reads `WorkerConfig.litellm_config` (JSON `model_map`).
- Generates a LiteLLM `config.yaml` with `model_list` and optional `router.fallbacks`.
- Starts proxy on a configurable port (default `4000`).
- The OpenCode server is expected to consume the LiteLLM proxy as its model provider (configured out-of-band via `~/.claude/settings.json` `agentModels` or equivalent).

### 1.4 Permission System

OpenCode exposes a permission-request flow over HTTP:

1. Agent execution generates `permissionRequest` objects inside message `parts`.
2. Each request has `id`, `tool`, and `input`.
3. The caller must POST `response: "allow" | "deny"` to `/session/{id}/permissions/{perm_id}`.
4. CLI flag `--dangerously-skip-permissions` exists but is **not used** by Karkhana workers.

The worker-app implements a `run_permission_guard` task (`sandbox.rs`) that polls messages every 5 seconds and auto-responds based on a local `PermissionPolicy`:

- `allow_file_edits`: bool
- `allow_shell_commands`: list of command prefixes
- `deny_patterns`: list of forbidden substrings

This guard is **local policy**, not OpenCode-native policy.

### 1.5 Circuit Breaker

The worker-app implements a `CircuitBreaker` (`circuit_breaker.rs`) that polls session messages every 30 seconds and aborts the session if:

- `max_ttl_minutes` exceeded
- `max_llm_tokens` exceeded (reads `usage.input_tokens + usage.output_tokens` from `msg.info`)
- `max_budget_usd` exceeded (reads `usage.cost` from `msg.info`)
- `max_identical_failures` consecutive identical tool errors occur

This is **Karkhana-side** safety logic, not an OpenCode native feature.

---

## 2. Unverified / Unsupported Assumptions

The following capabilities were researched but **could not be confirmed** as stable OpenCode features. The Karkhana contract below does **not** depend on them.

| Capability | Status | Research Notes |
|------------|--------|----------------|
| **System prompts per task** | ❌ Unverified | The HTTP `SendMessageRequest` accepts `parts` and optional `model`/`agent`, but no `system` field. System instructions must be prepended to the user prompt text. |
| **Project-local `SKILL.md` / `.opencode/skills`** | ❌ Not found | No documentation or config files found in OpenCode CLI help, repo, or `~/.opencode`. |
| **`opencode.json` server config** | ❌ Unverified | Found `opencode.json` in `~/.config/kilo/` (Kilo IDE config), not OpenCode server. No evidence the HTTP server reads a local `opencode.json`. |
| **Tool permission settings via API** | ⚠️ Partial | Only `respond_permission` exists. There is no API to pre-seed an allow-list or deny-list. The worker must poll and respond. |
| **Working directory / external dir controls via HTTP API** | ❌ Unverified | CLI `opencode run` has `--dir`, but the HTTP session API has no documented working-directory parameter. The worker-app runs `opencode serve` and sessions operate against the repo directory via AGENTS.md context, not API-level chroot. |
| **MCP integration via HTTP API** | ❌ Unverified | `opencode mcp` is CLI-only in the current version. No MCP endpoints surfaced on the HTTP server. |
| **Structured output / log streaming** | ❌ Unverified | No Server-Sent Events or WebSocket streaming confirmed. `send_message` returns a synchronous `MessageResponse`. `--format json` is a CLI flag only. |
| **Native diff/test capture** | ❌ Unverified | OpenCode does expose `/session/{id}/diff`, but test execution is **not** an OpenCode feature. The worker-app runs tests via `tokio::process::Command` after the agent session completes. |

---

## 3. Karkhana OpenCode Execution Contract

This contract is **independent of uncertain OpenCode internals**. If OpenCode internals change, the contract below remains the stable interface between the Karkhana backend and the local worker.

### 3.1 Request Payload Shape (Worker Contract)

The backend builds a worker contract in `FactoryRunService._build_worker_contract()` and enqueues it as a `WorkItem` payload. The canonical shape is:

```json
{
  "goal": "Human-readable goal for this phase",
  "role": "worker",
  "role_prompt": "<full prompt text built by RolePromptBuilder>",
  "role_prompt_template": "<template identifier>",
  "role_required_inputs": ["field_a", "field_b"],
  "role_output_schema": {"type": "object", "properties": {...}},
  "role_provider": "codex-lb",
  "role_model": "gpt-5.5",
  "messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}],
  "prompt": "<duplicate of role_prompt for backward compatibility>",
  "factory_run_id": "<uuid>",
  "factory_phase_id": "<uuid>",
  "factory_batch_id": "<uuid>",
  "factory_job_type": "factory_phase:scaffold",
  "execution_type": "factory_worker",
  "autonomy_level": "autonomous_development",
  "guardrails": [
    "Never silently deploy to production",
    "Never add paid services or subscriptions",
    "Never commit secrets, API keys, or credentials",
    "Never run destructive database changes (DROP TABLE, DELETE without WHERE, etc.)"
  ],
  "project_twin": {
    "project_id": "<uuid>",
    "idea_id": "<uuid>",
    "provider": "github",
    "owner": "acme",
    "repo": "my-app",
    "repo_full_name": "acme/my-app",
    "clone_url": "https://github.com/acme/my-app.git",
    "default_branch": "main",
    "detected_stack": ["python", "fastapi"]
  },
  "branch": "factory/<run-id-short>/<phase-key>",
  "base_branch": "main",
  "context_files": [
    {"path": "backend/app/main.py", "role": "source"},
    {"path": "graphify-out/GRAPH_REPORT.md", "role": "architecture_context"}
  ],
  "template_docs": [
    {"key": "policies/code-standards.md", "uri": "s3://...", "content_type": "text/markdown", "content": "# Code Standards..."}
  ],
  "template_version": "2.0.0",
  "template_id": "fullstack-saas-v1",
  "constraints": [{"id": "no-secrets", "description": "..."}],
  "quality_gates": [{"phase": "scaffold", "type": "lint", "command": "ruff check ."}],
  "deliverables": [
    "Implementation of the phase goal",
    "Passing test suite",
    "Updated graphify knowledge graph"
  ],
  "verification_commands": ["pytest backend/tests", "graphify update ."],
  "graphify_instructions": {
    "pre_task": [
      "Read graphify-out/GRAPH_REPORT.md for god nodes and community structure",
      "Read graphify-out/wiki/index.md if it exists for codebase navigation"
    ],
    "post_task": [
      "Run 'graphify update .' after all code changes to keep the knowledge graph current"
    ]
  },
  "response_schema": {"type": "object", "properties": {...}},
  "verifier_contract": {"role": "verifier", "prompt": "...", "output_schema": {...}}
}
```

**Key rules:**
- The worker MUST read `prompt` (or `role_prompt`) as the primary instruction.
- The worker MUST respect `guardrails` as hard constraints.
- The worker MUST operate on the repository checked out to `branch` based on `base_branch`.
- The worker SHOULD include `context_files` in the prompt context when possible.
- The worker MUST run `verification_commands` and report `tests_passed`.

### 3.2 Context / Artifact Injection Approach

Because OpenCode's HTTP API does not support per-task system prompts or skill files natively, Karkhana uses the following **injection pattern**:

1. **AGENTS.md Write/Remove:**
   - Before agent execution, the worker writes `AGENTS.md` into the repository root (`sandbox.rs`).
   - `AGENTS.md` contains absolute rules (workspace confinement, no credential access, no destructive git ops, no network egress, no global package installs, no shell escape).
   - After execution, the worker removes `AGENTS.md` so it is not committed.
   - *Rationale:* OpenCode scans the working directory and respects `AGENTS.md` as contextual instructions.

2. **Prompt Prepending:**
   - `graphify_instructions.pre_task` text is prepended to the prompt.
   - `context_files` paths are appended as a "files to consider" block.
   - `constraints` and `guardrails` are appended as a "do not" block.

3. **LiteLLM Proxy:**
   - The worker starts a LiteLLM proxy with a `model_map` from `WorkerConfig.litellm_config`.
   - OpenCode server must be configured out-of-band (e.g., via `~/.claude/settings.json` `agentModels`) to route to `http://127.0.0.1:4000`.
   - This achieves model routing without changing OpenCode internals.

### 3.3 Expected Worker Behavior

1. **Claim**
   - Poll `/api/worker/claim` or listen to SQS `job_available` messages.
   - Match `job_type` against `WorkerConfig.capabilities`.

2. **Setup**
   - Clone or fetch the repository into `workspace_root`.
   - Create the feature branch specified in `payload.branch`.
   - Write `AGENTS.md`.

3. **Execute**
   - If `engine == "opencode-server"`:
     - Ensure `opencode serve` is running (or attach to `opencode_server_url`).
     - Create session via POST `/session`.
     - Send prompt via POST `/session/{id}/message`.
     - Spawn `CircuitBreaker` watcher and `PermissionPolicy` guard as concurrent tasks.
     - On success, GET `/session/{id}/diff` to capture changes.
     - DELETE `/session/{id}` to clean up.
   - If `engine == "opencode"` (CLI fallback):
     - Run `opencode run <prompt>` in repo directory.
     - Capture stdout/stderr.
   - If `engine == "openclaude"` (legacy):
     - Run `openclaude -p <prompt>` with appropriate flags.

4. **Verify**
   - Run `verification_commands` (up to 4 commands) via `tokio::process::Command`.
   - Capture stdout, stderr, and exit codes.
   - Report `tests_passed: bool`.

5. **Commit / Push**
   - If dirty, `git add -A`, `git commit -m "<message>"`, `git push origin <branch>`.
   - Capture final `commit_sha`.

6. **Report**
   - POST `job_completed` or `job_failed` to backend.
   - Include `logs`, `result` (JSON), and `tests_passed`.

### 3.4 Log / Result Capture

| Field | Source | Backend Storage |
|-------|--------|-----------------|
| `logs` | Concatenated stdout/stderr from agent + test commands + git commands | `WorkItem.logs` (truncated if large), full logs optionally in S3 |
| `result` | JSON object with `commit_sha`, `branch_name`, `tests_passed`, `agent_output`, `code_index`, etc. | `WorkItem.result` (DynamoDB) |
| `diff` | `opencode_client.get_diff()` or git diff | Included in `result` or uploaded to S3 URI |

### 3.5 Diff / Test Capture

- **Diff:** Primary source is OpenCode HTTP `/session/{id}/diff`. Fallback is `git diff` if CLI mode or session unavailable.
- **Tests:** Always executed by the worker via subprocess, never by OpenCode directly. The worker appends test output to `logs` and sets `tests_passed`.

### 3.6 Failure Handling

| Failure Mode | Worker Action | Backend Action |
|--------------|---------------|----------------|
| Agent non-zero exit / session error | `job_failed` with `retryable: true` (unless circuit breaker) | `failed_retryable` status; retried up to `IDEAREFINERY_WORKER_MAX_RETRIES` |
| Circuit breaker triggered | `job_failed` with `retryable: false`, `circuit_breaker_triggered` reason | `failed_terminal`; may trigger repair flow if `can_auto_repair` |
| Tests fail | `job_completed` with `tests_passed: false` | `FactoryOrchestrator` runs `process_verification_result`; may block, repair, or advance |
| Permission denied by policy | Worker auto-denies via guard; agent may halt | Treated as agent error, retryable |
| TTL / budget / token limit | Circuit breaker aborts session | Non-retryable failure |

### 3.7 Graphify Read / Update Requirements

Every worker contract includes `graphify_instructions`:

- **Pre-task:**
  - Read `graphify-out/GRAPH_REPORT.md` to understand god nodes and community structure.
  - Read `graphify-out/wiki/index.md` if it exists for navigation.
- **Post-task:**
  - Run `graphify update .` (AST-only, no API cost) after all code changes.

The `verification_commands` array always includes `graphify update .` unless explicitly overridden by the template.

---

## 4. Engine Mode Matrix

| Engine | `opencode_client` | `litellm` | Permission Guard | Circuit Breaker | Diff API |
|--------|-------------------|-----------|------------------|-----------------|----------|
| `opencode-server` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `opencode` (CLI) | ❌ | ❌ | ❌ | ❌ | ❌ (git diff fallback) |
| `openclaude` (CLI) | ❌ | ❌ | ❌ | ❌ | ❌ (git diff fallback) |
| `codex` (CLI fallback) | ❌ | ❌ | ❌ | ❌ | ❌ (git diff fallback) |

**Product direction:** `opencode-server` is the target mode. CLI fallbacks exist for resilience but do not support the full contract (no circuit breaker, no permission guard, no structured diff API).

---

## 5. Security & Sandboxing

### 5.1 Worker-Side Policy (`sandbox.rs`)

The worker implements a **best-effort** permission guard. It is not a true sandbox:

- File edits allowed only within repo directory.
- Shell commands allowed only if prefix-matched to allow-list (`git`, `npm test`, `npm run`, `python -m pytest`, `cargo test`, `go test`).
- Deny-list blocks `rm -rf /`, `format`, `shutdown`, etc.
- Restricted paths: `.env`, `credentials.json`, `*.pem`, `*.key`, `.aws`, `.ssh`, `.config`.

### 5.2 Backend Guardrails

The backend appends universal guardrails to every worker contract:

- Never silently deploy to production.
- Never add paid services or subscriptions.
- Never commit secrets, API keys, or credentials.
- Never run destructive database changes.

These are **instructional**, not enforceable by the backend. Enforcement relies on the worker's `PermissionPolicy` and `AGENTS.md`.

---

## 6. Configuration Reference

### 6.1 Backend Environment Variables

| Variable | Purpose |
|----------|---------|
| `CODEX_LB_API_KEY` | Optional API key for the Codex LB proxy; if unset, local OpenCode config is used |
| `CODEX_LB_API_BASE_URL` | Default: `http://127.0.0.1:2455/v1` |
| `CODEX_LB_MODEL` | Default: `gpt-5.5` |
| `IDEAREFINERY_WORKER_COMMAND_QUEUE_URL` | SQS queue for worker commands |
| `IDEAREFINERY_WORKER_EVENT_QUEUE_URL` | SQS queue for worker events |
| `IDEAREFINERY_WORKER_CLIENT_ROLE_ARN` | AWS STS role for worker credentials |
| `IDEAREFINERY_WORKER_CREDENTIAL_TTL_SECONDS` | Lease TTL (default 3600) |
| `IDEAREFINERY_WORKER_MAX_RETRIES` | Max retries per work item (default 3) |
| `IDEAREFINERY_MAX_REPAIR_ATTEMPTS_PER_TASK` | Repair loop limit (default 3) |
| `IDEAREFINERY_MAX_REPAIR_ATTEMPTS_PER_BATCH` | Batch-level repair limit (default 5) |

### 6.2 Worker Config (`worker-config.json`)

```json
{
  "api_base": "https://api.karkhana.one",
  "display_name": "Build Box",
  "engine": "opencode-server",
  "allow_full_control": false,
  "workspace_root": "~/.idearefinery-worker/repos",
  "poll_seconds": 20,
  "capabilities": ["repo_index", "agent_branch_work", "test_verify"],
  "tenant_id": null,
  "opencode_server_url": "http://127.0.0.1:4096",
  "litellm_port": 4000,
  "litellm_config": {
    "gpt-5.5": {
      "litellm_model": "openai/gpt-5.5",
      "api_base": "http://127.0.0.1:2455/v1",
      "api_key_env": "CODEX_LB_API_KEY"
    }
  }
}
```

### 6.3 OpenCode Server Out-of-Band Config

The OpenCode HTTP server does **not** read `worker-config.json`. Model routing is achieved by ensuring the OpenCode CLI/server is configured via:

- `~/.claude/settings.json` (`agentModels` pointing to LiteLLM proxy URL), **or**
- `opencode providers login` to set credentials, **or**
- Environment variables (`ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`) if using Claude-compatible adapters.

This is a **deployment concern**, not part of the Karkhana contract.

---

## 7. Change Log

| Date | Author | Change |
|------|--------|--------|
| 2026-04-28 | Karkhana Agent | Initial contract documentation based on codebase audit. |

---

## 8. Follow-Up Recommendations

1. **Stabilize `opencode-server` as the only supported engine.** Deprecate CLI fallbacks once `opencode serve` reliability is proven in production.
2. **Add structured streaming.** If OpenCode adds SSE/WebSocket message streaming, update `OpenCodeClient` to stream logs into the backend heartbeat API instead of buffering until session end.
3. **Investigate native OpenCode policy API.** If a future OpenCode version supports pre-seeding permission policies via HTTP, replace the polling `PermissionPolicy` guard with native configuration.
4. **Graphify integration test.** Add an end-to-end test that verifies `graphify update .` is executed and the graph is updated before `job_completed` is sent.
5. **LiteLLM config validation.** Add a health-check endpoint in the worker-app that validates the full chain: worker-app → LiteLLM proxy → upstream provider.
6. **Document `AGENTS.md` format.** Extract the inline `AGENTS_MD_CONTENT` from `sandbox.rs` into a template artifact so it can be versioned per-template.
