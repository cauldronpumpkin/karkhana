# Worker Desktop App — Tauri v2 + Svelte 5

## TL;DR

> **Quick Summary**: Build a standalone desktop worker app using Tauri v2 + Svelte 5 that rewrites the existing Python worker in Rust. Lives in system tray, opens a monitoring dashboard on click.
>
> **Deliverables**:
> - `worker-app/` directory at repo root with complete Tauri v2 project
> - Rust-native worker logic (HTTP client, SQS, git ops, agent spawning, repo indexing)
> - Svelte 5 dashboard UI matching existing web app design system
> - System tray with status dot + menu
> - Auto-start on boot, auto-update support
> - Windows (.exe/.msi) and macOS (.dmg) installers
>
> **Estimated Effort**: XL (20+ tasks, significant Rust + Svelte work)
> **Parallel Execution**: YES - 4 waves
> **Critical Path**: Task 1 → Task 3 → Task 9 → Task 15 → Task 22 → Final

---

## Context

### Original Request
User wants an Electron-like desktop app for Windows and macOS that serves as a one-click install for the IdeaRefinery local worker. Should register as startup service, allow joining a company/tenant, and install any needed dependencies.

### Interview Summary
**Key Discussions**:
- **Framework choice**: Tauri v2 chosen over Electron (3-12 MB vs 80-200 MB, official tray/autostart/updater plugins)
- **Worker logic**: Full Rust rewrite — no Python dependency. Rewrite worker.py natively
- **UI mode**: System tray + hidden window (like Docker Desktop). No dock/taskbar icon when minimized
- **Features**: Full monitoring dashboard — status, job queue, live logs, job history, health, config editor, pairing flow
- **Design**: Reuse existing web app CSS variables, component patterns, lucide-svelte icons
- **Location**: `worker-app/` at repo root
- **Notifications**: No native OS notifications

**Research Findings**:
- Tauri v2 + Svelte 5 proven in production (c9watch, Peek, Knative Explorer)
- Existing web app design system: CSS variables in `app.css`, 5 UI components (Button/Badge/Modal/Input/Card), Svelte 5 runes ($state/$derived/$props)
- Worker.py has 7 capabilities: repo_index, architecture_dossier, gap_analysis, build_task_plan, agent_branch_work, test_verify, sync_remote_state
- Backend API surface: `/api/local-workers/register`, `/api/worker/claim`, `/api/worker/jobs/{id}/heartbeat|complete|fail`

### Metis Review
Skipped per user request.

---

## Work Objectives

### Core Objective
Build a standalone Tauri v2 desktop application that serves as the IdeaRefinery local worker — handling pairing, job processing, and monitoring — with zero Python dependency.

### Concrete Deliverables
- `worker-app/` with `src-tauri/` (Rust) and `src/` (Svelte 5)
- System tray app with status indicator
- Dashboard window with: status panel, job history, live logs, pairing flow, config editor
- Rust modules: HTTP client, SQS transport, git ops, repo indexing, agent spawning
- Auto-start on boot, auto-update support
- Windows and macOS build pipelines

### Definition of Done
- [ ] `cargo build` succeeds in `worker-app/src-tauri/`
- [ ] `npm run build` succeeds in `worker-app/`
- [ ] App launches, shows system tray icon, opens dashboard on click
- [ ] Pairing flow works: register → poll → approved → credentials saved
- [ ] Job processing works: claim → process → report
- [ ] Dashboard shows live status, job history, streaming logs
- [ ] Auto-start registers on both Windows and macOS
- [ ] Build produces Windows .exe and macOS .dmg

### Must Have
- Tauri v2 with Svelte 5 frontend
- System tray with status dot (green/yellow/red)
- Dashboard window: status, current job, job history, live logs
- Pairing flow UI (API URL, tenant ID, display name → register → waiting → approved)
- Config editor (API base, tenant, capabilities, workspace path)
- Rust HTTP client for all karkhana API endpoints
- Rust SQS client for job queue
- Git operations (clone, fetch, checkout, push, add, commit)
- Repo indexing (walk filesystem, read manifests, detect tests)
- Agent spawning (openclaude/opencode/codex via tokio::process)
- Auto-start on boot (tauri-plugin-autostart)
- Auto-update (tauri-plugin-updater)
- Dark theme matching existing web app design system (CSS variables, colors, typography)

### Must NOT Have (Guardrails)
- NO Python dependency — all worker logic in Rust
- NO ideas, chat, scoring, phases, reports features (that's the web app)
- NO native OS notifications
- NO light mode (dark theme only, matching web app)
- NO admin/elevation requirements
- NO hardcoded API URLs
- NO AI slop: excessive comments, over-abstraction, generic variable names
- NO scope creep into web app territory

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: NO (new project)
- **Automated tests**: YES (tests-after — Rust unit tests + Svelte component tests)
- **Framework**: Rust built-in `#[cfg(test)]` + Vitest for Svelte
- **Test location**: `worker-app/src-tauri/src/` (inline Rust tests) + `worker-app/src/lib/**/*.test.js`

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Rust modules**: Use Bash — `cargo test` in worker-app/src-tauri/
- **Svelte components**: Use Playwright or Bash — `npm run build` + visual verification
- **Tauri commands**: Use Bash — `cargo build` + verify IPC layer
- **Integration**: Use Bash — `cargo tauri build` + verify output artifacts

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — 6 tasks, ALL parallel):
├── Task 1: Tauri project scaffolding + Cargo.toml + tauri.conf.json + package.json [quick]
├── Task 2: Svelte 5 frontend scaffold with design system [visual-engineering]
├── Task 3: Rust core types + config + state management [quick]
├── Task 4: Rust HTTP client module [unspecified-high]
├── Task 5: System tray setup [unspecified-high]
└── Task 6: Svelte UI components (Button, Badge, Modal, Input, Card) [visual-engineering]

Wave 2 (Core logic — 7 tasks, MAX PARALLEL):
├── Task 7: Pairing flow (Rust backend + Svelte UI) [deep]
├── Task 8: SQS transport module [unspecified-high]
├── Task 9: Job processor framework (claim → dispatch → report) [deep]
├── Task 10: Git operations module [unspecified-high]
├── Task 11: Dashboard: Status panel + health metrics [visual-engineering]
├── Task 12: Dashboard: Job history + current job view [visual-engineering]
└── Task 13: Dashboard: Live logs viewer [visual-engineering]

Wave 3 (Advanced features — 6 tasks):
├── Task 14: Repo indexing (walkdir, manifests, TODOs, test detection) [deep]
├── Task 15: Agent spawning (openclaude/opencode/codex) [unspecified-high]
├── Task 16: Branch work handler (git checkout, agent, tests, push) [deep]
├── Task 17: Dashboard: Configuration editor [visual-engineering]
├── Task 18: Auto-start plugin integration [quick]
└── Task 19: Auto-update setup [unspecified-high]

Wave 4 (Build + Polish — 4 tasks):
├── Task 20: Error handling & reconnection logic [deep]
├── Task 21: Windows build pipeline (.exe/.msi) [unspecified-high]
├── Task 22: macOS build pipeline (.dmg + signing) [unspecified-high]
└── Task 23: Integration test (full flow: pair → claim → process → report) [deep]

Wave FINAL (4 parallel reviews):
├── F1: Plan compliance audit (oracle)
├── F2: Code quality review (unspecified-high)
├── F3: Real manual QA (unspecified-high)
└── F4: Scope fidelity check (deep)
-> Present results -> Get explicit user okay

Critical Path: Task 1 → Task 3 → Task 9 → Task 15 → Task 23 → F1-F4 → user okay
Parallel Speedup: ~65% faster than sequential
Max Concurrent: 7 (Waves 1 & 2)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | - | 2-6, 7-23 | 1 |
| 2 | 1 | 6, 7, 11-13, 17 | 1 |
| 3 | 1 | 4, 5, 7-10, 14-16 | 1 |
| 4 | 1, 3 | 7, 8, 9 | 1 |
| 5 | 1, 3 | 18 | 1 |
| 6 | 2 | 7, 11-13, 17 | 1 |
| 7 | 2, 3, 4, 6 | 9 | 2 |
| 8 | 3, 4 | 9 | 2 |
| 9 | 3, 4, 7, 8 | 14-16, 23 | 2 |
| 10 | 1, 3 | 14-16 | 2 |
| 11 | 2, 6 | 13 | 2 |
| 12 | 2, 6 | - | 2 |
| 13 | 2, 6, 11 | - | 2 |
| 14 | 3, 10 | 15 | 3 |
| 15 | 9, 10 | 16 | 3 |
| 16 | 9, 10, 14, 15 | 23 | 3 |
| 17 | 2, 6 | - | 3 |
| 18 | 5 | - | 3 |
| 19 | 1 | 21, 22 | 3 |
| 20 | 4, 8, 9 | 23 | 4 |
| 21 | 19 | - | 4 |
| 22 | 19 | - | 4 |
| 23 | 9, 14-16, 20 | F1-F4 | 4 |

### Agent Dispatch Summary

- **Wave 1**: **6** — T1 → `quick`, T2 → `visual-engineering`, T3 → `quick`, T4 → `unspecified-high`, T5 → `unspecified-high`, T6 → `visual-engineering`
- **Wave 2**: **7** — T7 → `deep`, T8 → `unspecified-high`, T9 → `deep`, T10 → `unspecified-high`, T11-T13 → `visual-engineering`
- **Wave 3**: **6** — T14 → `deep`, T15 → `unspecified-high`, T16 → `deep`, T17 → `visual-engineering`, T18 → `quick`, T19 → `unspecified-high`
- **Wave 4**: **4** — T20 → `deep`, T21-T22 → `unspecified-high`, T23 → `deep`
- **FINAL**: **4** — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

> Implementation + Test = ONE Task. Never separate.
> EVERY task MUST have: Recommended Agent Profile + Parallelization info + QA Scenarios.

- [ ] 1. Tauri Project Scaffolding

  **What to do**:
  - Create `worker-app/` directory at repo root
  - Initialize Tauri v2 project: `npm create tauri-app@latest` or manual setup
  - `worker-app/package.json` with: svelte 5.55+, @sveltejs/vite-plugin-svelte 7+, vite 8+, @tauri-apps/api 2+, @tauri-apps/cli 2+
  - `worker-app/src-tauri/Cargo.toml` with: tauri 2 (with tray-icon feature), tauri-plugin-autostart, tauri-plugin-updater, tauri-plugin-shell, tauri-plugin-fs, reqwest (json, rustls-tls), serde/serde_json, tokio (full), aws-sdk-sqs, walkdir, ignore
  - `worker-app/src-tauri/tauri.conf.json` with: app name "IdeaRefinery Worker", window hidden by default (visible: false), system tray config, permissions for shell/fs/autostart/updater
  - `worker-app/src-tauri/capabilities/default.json` with required permissions
  - `worker-app/vite.config.js` for Svelte 5
  - `worker-app/src-tauri/src/main.rs` with minimal Tauri app entry (empty setup, system tray placeholder)
  - `worker-app/src-tauri/src/lib.rs` as Tauri lib entry
  - `worker-app/index.html` entry point
  - Verify: `cargo build` and `npm install` both succeed

  **Must NOT do**:
  - Do NOT implement any business logic yet
  - Do NOT configure code signing yet
  - Do NOT add Python-related anything

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Mechanical scaffolding, well-defined structure
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO — blocks everything
  - **Parallel Group**: Wave 1 (foundation)
  - **Blocks**: Tasks 2-23
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `frontend/package.json` — Svelte/Vite dependency versions to match
  - `frontend/vite.config.js` — Vite configuration pattern for Svelte

  **API/Type References**:
  - `workers/openclaude-local/worker.py:18-29` — DEFAULT_CAPABILITIES and config patterns
  - `backend/app/config.py` — Settings pattern (env vars, field names)

  **External References**:
  - Tauri v2 project setup: `https://v2.tauri.app/start/create-project/`
  - Tauri v2 Cargo.toml reference: `https://v2.tauri.app/reference/config/`
  - Tauri plugins registry: `https://v2.tauri.app/plugin/`

  **WHY Each Reference Matters**:
  - `frontend/package.json`: Must match exact Svelte/Vite versions for component reuse
  - `worker.py:18-29`: Capability names must be identical strings for API compatibility
  - Tauri docs: Correct plugin feature flags and config format are critical

  **Acceptance Criteria**:
  - [ ] `worker-app/package.json` exists with Svelte 5 + Vite 8 + Tauri 2 deps
  - [ ] `worker-app/src-tauri/Cargo.toml` exists with all required crates
  - [ ] `worker-app/src-tauri/tauri.conf.json` configured with hidden window + tray
  - [ ] `cd worker-app && npm install` succeeds
  - [ ] `cd worker-app/src-tauri && cargo build` succeeds

  **QA Scenarios:**

  ```
  Scenario: Fresh build succeeds
    Tool: Bash
    Preconditions: worker-app/ directory exists with all config files
    Steps:
      1. cd worker-app && npm install
      2. Assert exit code 0
      3. cd src-tauri && cargo check
      4. Assert exit code 0
    Expected Result: Both npm install and cargo check exit cleanly
    Failure Indicators: Missing dependency, version conflict, compilation error
    Evidence: .sisyphus/evidence/task-1-fresh-build.txt

  Scenario: Config files are valid JSON/TOML
    Tool: Bash
    Preconditions: All config files created
    Steps:
      1. node -e "JSON.parse(require('fs').readFileSync('worker-app/src-tauri/tauri.conf.json'))" 
      2. Assert no parse errors
      3. node -e "JSON.parse(require('fs').readFileSync('worker-app/package.json'))"
      4. Assert no parse errors
    Expected Result: All config files parse without errors
    Evidence: .sisyphus/evidence/task-1-config-valid.txt
  ```

  **Commit**: YES
  - Message: `feat(worker-app): scaffold Tauri v2 project with Svelte 5`
  - Files: `worker-app/` (all new files)
  - Pre-commit: `cd worker-app/src-tauri && cargo check`

- [ ] 2. Svelte 5 Frontend Scaffold with Design System

  **What to do**:
  - Create `worker-app/src/` structure: `App.svelte`, `main.js`, `app.css`
  - Copy CSS variables from `frontend/src/app.css` into `worker-app/src/app.css` (all `:root` variables: colors, spacing, typography, borders, shadows)
  - Copy grid/scanline visual effects from web app (`body::before`, `body::after`)
  - Set up Svelte 5 with runes ($state, $derived, $props)
  - Create `worker-app/src/lib/stores.js` with core state stores:
    - `workerStatus`: 'idle' | 'pairing' | 'active' | 'error'
    - `currentJob`: current job object or null
    - `jobHistory`: array of recent jobs
    - `logs`: array of log lines
    - `workerConfig`: config object
    - `connectionHealth`: { connected, lastHeartbeat, uptime }
  - Create `worker-app/src/App.svelte` with basic layout shell (header bar + main content area)
  - Verify: `npm run build` produces working output

  **Must NOT do**:
  - Do NOT copy web app components that aren't needed (Chat, Ideas, etc.)
  - Do NOT create a router — single-page app with tab navigation
  - Do NOT add light mode

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: CSS/design system porting and Svelte component creation
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: Design system replication and component craftsmanship

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Task 1)
  - **Parallel Group**: Wave 1 (with Tasks 3-6)
  - **Blocks**: Tasks 6, 7, 11-13, 17
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `frontend/src/app.css:1-80` — Complete CSS variables block to copy
  - `frontend/src/App.svelte` — App shell pattern
  - `frontend/src/lib/components/Layout/AppShell.svelte` — Layout structure

  **API/Type References**:
  - `workers/openclaude-local/worker.py:159-168` — LocalWorker state shape (what the UI needs to display)

  **WHY Each Reference Matters**:
  - `app.css`: Exact variable values ensure pixel-perfect design consistency
  - `worker.py LocalWorker`: State fields the stores must mirror

  **Acceptance Criteria**:
  - [ ] `worker-app/src/app.css` contains all CSS variables from web app
  - [ ] `worker-app/src/lib/stores.js` exports all 6 stores
  - [ ] `worker-app/src/App.svelte` renders without errors
  - [ ] `cd worker-app && npm run build` succeeds

  **QA Scenarios:**

  ```
  Scenario: Build produces output
    Tool: Bash
    Preconditions: Task 1 complete, Svelte files created
    Steps:
      1. cd worker-app && npm run build
      2. Assert exit code 0
      3. Check dist/ or build/ directory exists with index.html
    Expected Result: Vite build completes, HTML output exists
    Failure Indicators: Build error, missing import, Svelte compile error
    Evidence: .sisyphus/evidence/task-2-svelte-build.txt

  Scenario: CSS variables match web app
    Tool: Bash (grep)
    Preconditions: app.css created
    Steps:
      1. grep "--color-bg:" worker-app/src/app.css
      2. grep "--color-primary:" worker-app/src/app.css
      3. grep "--font-sans:" worker-app/src/app.css
      4. Assert all present
    Expected Result: All core design tokens present in worker-app CSS
    Evidence: .sisyphus/evidence/task-2-css-variables.txt
  ```

  **Commit**: YES
  - Message: `feat(worker-app): add Svelte 5 frontend with design system`
  - Files: `worker-app/src/`
  - Pre-commit: `cd worker-app && npm run build`

- [ ] 3. Rust Core Types + Config + State Management

  **What to do**:
  - Create `worker-app/src-tauri/src/config.rs`:
    - `WorkerConfig` struct (api_base, display_name, engine, workspace_root, poll_seconds, capabilities, tenant_id, openclaude settings) with serde Serialize/Deserialize
    - `load_config()` function: reads from worker-config.json, falls back to env vars (IDEAREFINERY_API_BASE_URL, etc.)
    - Match exact field names from Python WorkerConfig for API compatibility
  - Create `worker-app/src-tauri/src/state.rs`:
    - `WorkerState` struct (api_base, worker_id, api_token, credentials with SQS info)
    - `StateStore` with load/save to `~/.idearefinery-worker/openclaude-local/state.json`
    - Match exact JSON format from Python state file for migration compatibility
  - Create `worker-app/src-tauri/src/types.rs`:
    - API request/response types: `RegisterRequest`, `RegisterResponse`, `PairingResponse`, `ClaimRequest`, `ClaimResponse`, `JobUpdateRequest`, `JobCompleteRequest`, `JobFailRequest`
    - `Job`, `Project`, `WorkerCredentialLease` structs
    - All with serde derives, matching exact JSON shapes from Python worker
  - Add unit tests for config loading and state serialization round-trip

  **Must NOT do**:
  - Do NOT implement HTTP calls yet (just types)
  - Do NOT change any Python worker code
  - Do NOT use any crate not already in Cargo.toml from Task 1

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Struct definitions and serde plumbing, well-defined contracts
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Task 1)
  - **Parallel Group**: Wave 1 (with Tasks 2, 4-6)
  - **Blocks**: Tasks 4, 5, 7-10, 14-16
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `workers/openclaude-local/worker.py:32-41` — WorkerConfig dataclass (exact fields)
  - `workers/openclaude-local/worker.py:44-55` — StateStore pattern (load/save JSON)
  - `workers/openclaude-local/worker.py:351-362` — load_config() env var handling

  **API/Type References**:
  - `workers/openclaude-local/worker.py:365-376` — pair() payload shape (what gets sent to /register)
  - `workers/openclaude-local/worker.py:385` — State file JSON shape (worker_id, api_token, credentials)
  - `backend/app/routers/local_workers.py:20-27` — WorkerRegisterRequest Pydantic model
  - `backend/app/routers/worker.py:36-53` — ClaimRequest, JobUpdateRequest, JobCompleteRequest, JobFailRequest

  **Test References**:
  - `workers/openclaude-local/worker-config.example.json` — Example config to validate against

  **WHY Each Reference Matters**:
  - `WorkerConfig dataclass`: Every field must match for API compatibility
  - `pair() payload`: Registration request shape must be identical
  - `State file JSON`: Must be backwards-compatible with existing state files
  - `Pydantic models`: These define the exact JSON shapes the API expects/returns

  **Acceptance Criteria**:
  - [ ] `config.rs` compiles with WorkerConfig struct matching Python fields
  - [ ] `state.rs` compiles with StateStore load/save round-trip test passing
  - [ ] `types.rs` has all API request/response types
  - [ ] `cargo test` passes with config and state unit tests
  - [ ] JSON serialization of types matches Python shapes (verified by test)

  **QA Scenarios:**

  ```
  Scenario: Config loads from JSON
    Tool: Bash
    Preconditions: config.rs with load_config() implemented
    Steps:
      1. cd worker-app/src-tauri && cargo test config
      2. Assert all config tests pass
      3. Verify test creates temp JSON, loads it, asserts field values
    Expected Result: Config loads from JSON file with correct types
    Failure Indicators: Deserialization error, missing field, type mismatch
    Evidence: .sisyphus/evidence/task-3-config-test.txt

  Scenario: State round-trip matches Python format
    Tool: Bash
    Preconditions: state.rs with WorkerState implemented
    Steps:
      1. cd worker-app/src-tauri && cargo test state
      2. Assert state save → load produces identical struct
      3. Verify JSON output matches Python state file format
    Expected Result: State serialization is backwards-compatible
    Evidence: .sisyphus/evidence/task-3-state-test.txt
  ```

  **Commit**: YES
  - Message: `feat(worker-app): add Rust core types, config, and state management`
  - Files: `worker-app/src-tauri/src/{config,state,types}.rs`
  - Pre-commit: `cd worker-app/src-tauri && cargo test`

- [ ] 4. Rust HTTP Client Module

  **What to do**:
  - Create `worker-app/src-tauri/src/api.rs`:
    - `ApiClient` struct with reqwest::Client, api_base URL, optional bearer token
    - `get(path) -> Result<Value>` and `post(path, body) -> Result<Value>` methods
    - Typed methods: `register(req) -> RegisterResponse`, `get_registration(id, pairing_token) -> RegistrationStatus`, `claim_job(worker_id, capabilities) -> Option<ClaimResponse>`, `heartbeat_job(job_id, ...) -> Job`, `complete_job(job_id, ...) -> Job`, `fail_job(job_id, ...) -> Job`
    - All methods use typed request/response structs from types.rs
    - Proper error handling with custom error types (ApiError enum: Network, Http { status }, Json, Auth)
  - Add unit tests with mock server (or just compilation + type safety tests)

  **Must NOT do**:
  - Do NOT add retry logic yet (Task 20)
  - Do NOT implement SQS client here (Task 8)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: reqwest API surface, async Rust, error type design
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Task 1 + Task 3)
  - **Parallel Group**: Wave 1
  - **Blocks**: Tasks 7, 8, 9
  - **Blocked By**: Tasks 1, 3

  **References**:

  **Pattern References**:
  - `workers/openclaude-local/worker.py:58-80` — ApiClient class (exact HTTP patterns to replicate)

  **API/Type References**:
  - `backend/app/routers/local_workers.py:38-101` — All local-workers API endpoints
  - `backend/app/routers/worker.py:56-86` — All worker job API endpoints
  - `worker-app/src-tauri/src/types.rs` — Request/response types from Task 3

  **WHY Each Reference Matters**:
  - `worker.py ApiClient`: Shows exact URL patterns, headers, auth token handling
  - Backend routers: Define the exact HTTP methods, paths, and request/response shapes

  **Acceptance Criteria**:
  - [ ] `api.rs` compiles with ApiClient and all typed methods
  - [ ] `cargo test` passes (compilation + type safety tests)
  - [ ] Auth header pattern matches Python: `Authorization: Bearer {token}`
  - [ ] Content-Type: application/json on all requests

  **QA Scenarios:**

  ```
  Scenario: Module compiles and types align
    Tool: Bash
    Preconditions: Task 3 types complete, api.rs written
    Steps:
      1. cd worker-app/src-tauri && cargo check
      2. Assert exit code 0
      3. cargo test api
      4. Assert tests pass
    Expected Result: ApiClient compiles, all methods type-check against types.rs
    Evidence: .sisyphus/evidence/task-4-api-client.txt

  Scenario: Request shapes match Python
    Tool: Bash (grep)
    Preconditions: api.rs written
    Steps:
      1. grep "register" worker-app/src-tauri/src/api.rs — assert register method exists
      2. grep "claim" worker-app/src-tauri/src/api.rs — assert claim method exists
      3. grep "heartbeat" worker-app/src-tauri/src/api.rs — assert heartbeat method exists
      4. grep "complete" worker-app/src-tauri/src/api.rs — assert complete method exists
      5. grep "fail" worker-app/src-tauri/src/api.rs — assert fail method exists
    Expected Result: All 5 API operations implemented as typed methods
    Evidence: .sisyphus/evidence/task-4-api-methods.txt
  ```

  **Commit**: YES
  - Message: `feat(worker-app): add Rust HTTP client for karkhana API`
  - Files: `worker-app/src-tauri/src/api.rs`
  - Pre-commit: `cd worker-app/src-tauri && cargo test`

- [ ] 5. System Tray Setup

  **What to do**:
  - Create `worker-app/src-tauri/src/tray.rs`:
    - System tray with status icon (use built-in Tauri tray-icon feature)
    - Status indicator: green (active), yellow (pairing), red (error), gray (idle)
    - Menu items: "Status: ..." (dynamic), separator, "Open Dashboard", "Start/Stop Worker", separator, "Quit"
    - Click handler: "Open Dashboard" shows/focuses the main window
    - "Start/Stop Worker" toggles the worker loop
    - "Quit" exits the app
  - Update `main.rs` to initialize tray on startup
  - Create minimal app icons (PNG) for tray: `worker-app/src-tauri/icons/tray-icon.png`
  - Window should be hidden on launch, only visible via tray "Open Dashboard"
  - On macOS: no dock icon when window is hidden (`LSUIElement` in tauri.conf.json or programmatic)

  **Must NOT do**:
  - Do NOT implement actual worker start/stop logic (just the tray commands/hooks)
  - Do NOT create elaborate icons — simple colored circles are fine

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Tauri tray API, platform-specific behavior, menu system
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Task 1 + Task 3)
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 18
  - **Blocked By**: Tasks 1, 3

  **References**:

  **Pattern References**:
  - Tauri v2 tray example: `https://v2.tauri.app/learn/system-tray/`

  **API/Type References**:
  - `worker-app/src-tauri/tauri.conf.json` — Tray config section

  **WHY Each Reference Matters**:
  - Tauri tray docs: Correct API for tray icon, menu items, and click handlers in v2

  **Acceptance Criteria**:
  - [ ] `tray.rs` compiles with tray initialization, menu items, and click handlers
  - [ ] `cargo build` succeeds
  - [ ] App launches with tray icon visible (manual or automated test)
  - [ ] Clicking tray menu items compiles (even if worker logic not wired yet)

  **QA Scenarios:**

  ```
  Scenario: Tray module compiles
    Tool: Bash
    Preconditions: tray.rs written, Tauri tray-icon feature enabled
    Steps:
      1. cd worker-app/src-tauri && cargo check
      2. Assert exit code 0
      3. grep "tray" src/tray.rs | head -5 — verify menu items defined
    Expected Result: Tray module compiles with all menu items
    Evidence: .sisyphus/evidence/task-5-tray-compile.txt

  Scenario: Tray config in tauri.conf.json
    Tool: Bash (grep)
    Preconditions: tauri.conf.json updated
    Steps:
      1. grep "trayIcon" worker-app/src-tauri/tauri.conf.json — or tray config
      2. Assert tray configuration exists
      3. Verify icon path points to existing file
    Expected Result: Tray properly configured in Tauri config
    Evidence: .sisyphus/evidence/task-5-tray-config.txt
  ```

  **Commit**: YES
  - Message: `feat(worker-app): add system tray with status icon and menu`
  - Files: `worker-app/src-tauri/src/tray.rs`, icons, main.rs updates
  - Pre-commit: `cd worker-app/src-tauri && cargo check`

- [ ] 6. Svelte UI Components (Button, Badge, Modal, Input, Card)

  **What to do**:
  - Port the 5 core UI components from `frontend/src/lib/components/UI/` to `worker-app/src/lib/components/UI/`:
    - `Button.svelte` — variants: primary, secondary, ghost, danger, warning; sizes: sm, md, lg
    - `Badge.svelte` — variants: primary, accent, success, warning, error, muted
    - `Modal.svelte` — with backdrop blur, header, close button, content slot
    - `Input.svelte` — with label, bindable value, placeholder, mono uppercase label
    - `Card.svelte` — with optional header, title, subtitle, gradient background
  - Use Svelte 5 runes ($props, $bindable, {@render children()})
  - Import lucide-svelte icons where needed (matching web app usage)
  - Style using the CSS variables from app.css (no hardcoded values)
  - Each component should be a 1:1 port of the web app version with identical props API

  **Must NOT do**:
  - Do NOT invent new components beyond the 5 listed
  - Do NOT add light mode variants
  - Do NOT change prop names from web app versions

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Direct component porting with design fidelity
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: Ensures pixel-perfect component replication

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Task 2)
  - **Parallel Group**: Wave 1
  - **Blocks**: Tasks 7, 11-13, 17
  - **Blocked By**: Task 2

  **References**:

  **Pattern References**:
  - `frontend/src/lib/components/UI/Button.svelte` — Exact component to port (all variants, styles, hover effects)
  - `frontend/src/lib/components/UI/Badge.svelte` — Status badge with color variants
  - `frontend/src/lib/components/UI/Modal.svelte` — Backdrop blur dialog
  - `frontend/src/lib/components/UI/Input.svelte` — Form input with mono labels
  - `frontend/src/lib/components/UI/Card.svelte` — Gradient card container
  - `frontend/src/app.css` — CSS variables the components reference

  **WHY Each Reference Matters**:
  - These are 1:1 ports — every prop, variant, CSS class, and hover effect must match exactly

  **Acceptance Criteria**:
  - [ ] All 5 components exist in `worker-app/src/lib/components/UI/`
  - [ ] `npm run build` succeeds with all components imported
  - [ ] Each component accepts same props as web app version
  - [ ] No hardcoded colors — all via CSS variables

  **QA Scenarios:**

  ```
  Scenario: All components compile
    Tool: Bash
    Preconditions: All 5 Svelte components created
    Steps:
      1. cd worker-app && npm run build
      2. Assert exit code 0
      3. Verify no Svelte compiler warnings
    Expected Result: Clean build with all 5 components
    Evidence: .sisyphus/evidence/task-6-components-build.txt

  Scenario: Component props match web app
    Tool: Bash (grep)
    Preconditions: Components written
    Steps:
      1. grep "variant" worker-app/src/lib/components/UI/Button.svelte — assert variant prop exists
      2. grep "variant" worker-app/src/lib/components/UI/Badge.svelte — assert variant prop exists
      3. grep "title" worker-app/src/lib/components/UI/Modal.svelte — assert title prop exists
      4. grep "label" worker-app/src/lib/components/UI/Input.svelte — assert label prop exists
      5. grep "title" worker-app/src/lib/components/UI/Card.svelte — assert title prop exists
    Expected Result: All component APIs match web app versions
    Evidence: .sisyphus/evidence/task-6-component-props.txt
  ```

  **Commit**: YES
  - Message: `feat(worker-app): port UI components (Button, Badge, Modal, Input, Card)`
  - Files: `worker-app/src/lib/components/UI/*.svelte`
  - Pre-commit: `cd worker-app && npm run build`

- [ ] 7. Pairing Flow (Rust Backend + Svelte UI)

  **What to do**:
  - **Rust side** (`worker-app/src-tauri/src/pairing.rs`):
    - `start_pairing(config, state_store, tenant_id)` async function
    - POST /api/local-workers/register with display_name, machine_name, platform, engine, capabilities, tenant_id
    - Store pairing_token and request_id
    - Poll loop: GET /api/local-workers/registrations/{id}?pairing_token=... every 5 seconds
    - On approved: extract api_token + credentials, save to state via StateStore
    - On denied: return error with reason
    - Expose as Tauri command: `#[tauri::command] fn start_pairing(...)` that emits events to frontend
    - Emit Tauri events: `pairing-status-changed` with status payload
  - **Svelte side** (`worker-app/src/lib/components/Dashboard/PairingFlow.svelte`):
    - Form fields: API Base URL, Display Name, Tenant ID (optional)
    - Submit button → invokes Tauri command
    - Waiting screen with animated status: "Waiting for approval in Local Workers page..."
    - Success screen: "Worker paired! Worker ID: ..." with green badge
    - Error screen: denial reason or connection error
    - Uses Button, Input, Badge, Card components from Task 6

  **Must NOT do**:
  - Do NOT start the worker loop after pairing (that's Task 9)
  - Do NOT hardcode API base URL

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Cross-cutting Rust+Svelte integration, async polling, Tauri IPC events
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: Pairing flow UI with animations and state transitions

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Wave 1)
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 9
  - **Blocked By**: Tasks 2, 3, 4, 6

  **References**:

  **Pattern References**:
  - `workers/openclaude-local/worker.py:365-392` — pair() function (exact API calls, polling logic, status transitions)
  - `frontend/src/lib/components/LocalWorkers/LocalWorkers.svelte:45-50` — Approve UI pattern

  **API/Type References**:
  - `worker-app/src-tauri/src/api.rs` — register() and get_registration() methods
  - `worker-app/src-tauri/src/types.rs` — RegisterRequest, RegisterResponse types
  - `worker-app/src-tauri/src/state.rs` — StateStore save

  **WHY Each Reference Matters**:
  - `worker.py pair()`: Exact flow — register → poll → extract credentials → save state
  - `api.rs`: Already-built HTTP methods this task calls into

  **Acceptance Criteria**:
  - [ ] `pairing.rs` compiles with start_pairing function
  - [ ] Tauri command exposed for frontend invocation
  - [ ] `PairingFlow.svelte` renders form, waiting, success, and error states
  - [ ] `cargo test` passes for pairing unit tests
  - [ ] `npm run build` succeeds

  **QA Scenarios:**

  ```
  Scenario: Pairing module compiles with Tauri commands
    Tool: Bash
    Preconditions: pairing.rs written
    Steps:
      1. cd worker-app/src-tauri && cargo check
      2. Assert exit code 0
      3. grep "tauri::command" src/pairing.rs — verify Tauri command attribute
    Expected Result: Pairing module compiles with proper Tauri integration
    Evidence: .sisyphus/evidence/task-7-pairing-compile.txt

  Scenario: Svelte pairing form renders
    Tool: Bash
    Preconditions: PairingFlow.svelte created
    Steps:
      1. cd worker-app && npm run build
      2. Assert exit code 0
      3. grep "API Base" src/lib/components/Dashboard/PairingFlow.svelte — assert form fields
      4. grep "Tenant" src/lib/components/Dashboard/PairingFlow.svelte — assert tenant field
    Expected Result: Pairing form builds with API Base, Display Name, Tenant ID fields
    Evidence: .sisyphus/evidence/task-7-pairing-ui.txt
  ```

  **Commit**: YES
  - Message: `feat(worker-app): add pairing flow with Rust backend and Svelte UI`
  - Files: `worker-app/src-tauri/src/pairing.rs`, `worker-app/src/lib/components/Dashboard/PairingFlow.svelte`
  - Pre-commit: `cd worker-app/src-tauri && cargo test`

- [ ] 8. SQS Transport Module

  **What to do**:
  - Create `worker-app/src-tauri/src/sqs.rs`:
    - `SqsTransport` struct with AWS credentials (access_key_id, secret_access_key, session_token, region)
    - `receive_messages(queue_url, wait_seconds) -> Vec<Message>` — long-poll receive from command queue
    - `delete_message(queue_url, receipt_handle)` — acknowledge processed message
    - `send_event(queue_url, worker_id, event_type, payload)` — send to event queue
    - Handle message parsing: JSON body → envelope with type, job_type, work_item_id
    - Use aws-sdk-sqs crate for actual SQS operations
    - Fall back to API-based polling when SQS credentials are not configured (match Python behavior)
  - Add tests for message parsing (use mock JSON envelopes)

  **Must NOT do**:
  - Do NOT implement the job processing loop (Task 9)
  - Do NOT add credential refresh logic (that's a config concern)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: AWS SDK integration, async message handling, error recovery
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Wave 1)
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 9
  - **Blocked By**: Tasks 3, 4

  **References**:

  **Pattern References**:
  - `workers/openclaude-local/worker.py:83-132` — SqsTransport class (exact message handling, delete, send_event patterns)

  **API/Type References**:
  - `worker-app/src-tauri/src/types.rs` — Credential types, message envelope types

  **WHY Each Reference Matters**:
  - `worker.py SqsTransport`: Shows exact FIFO queue patterns, visibility timeout, deduplication IDs

  **Acceptance Criteria**:
  - [ ] `sqs.rs` compiles with receive, delete, send methods
  - [ ] Message parsing handles JSON envelopes correctly
  - [ ] `cargo test` passes for SQS message parsing tests
  - [ ] Falls back to API polling when no SQS credentials

  **QA Scenarios:**

  ```
  Scenario: SQS module compiles and tests pass
    Tool: Bash
    Preconditions: sqs.rs written
    Steps:
      1. cd worker-app/src-tauri && cargo check
      2. cargo test sqs
      3. Assert tests pass
    Expected Result: SQS module compiles, message parsing tests pass
    Evidence: .sisyphus/evidence/task-8-sqs-module.txt
  ```

  **Commit**: YES
  - Message: `feat(worker-app): add SQS transport module`
  - Files: `worker-app/src-tauri/src/sqs.rs`
  - Pre-commit: `cd worker-app/src-tauri && cargo test`

- [ ] 9. Job Processor Framework (claim → dispatch → report)

  **What to do**:
  - Create `worker-app/src-tauri/src/worker.rs`:
    - `Worker` struct holding config, state, api client, sqs transport
    - `run_once()` method: try SQS receive → handle_envelope → claim_and_process
    - `handle_envelope()`: parse message type, check job_type in capabilities
    - `claim_and_process()`: POST /api/worker/claim → dispatch by job_type → report result
    - Dispatch table for 7 job types → individual handler methods (stubs for now, implemented in Tasks 14-16):
      - `repo_index` → stub returning empty index
      - `architecture_dossier` → stub
      - `gap_analysis` → stub
      - `build_task_plan` → stub
      - `agent_branch_work` → stub
      - `test_verify` → stub
      - `sync_remote_state` → stub
    - `_submit_update()` method: send heartbeat/completed/failed via SQS or API fallback (matching Python _submit_update)
    - Main loop: `run()` async method with configurable poll interval, random jitter
    - Expose worker state as Tauri events: `job-started`, `job-completed`, `job-failed`, `worker-heartbeat`
  - Register all Tauri commands in main.rs

  **Must NOT do**:
  - Do NOT implement actual job handlers (Tasks 14-16)
  - Do NOT add retry/reconnection logic (Task 20)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Core async event loop, job dispatch architecture, Tauri event bridge
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Tasks 7, 8)
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 14-16, 20, 23
  - **Blocked By**: Tasks 3, 4, 7, 8

  **References**:

  **Pattern References**:
  - `workers/openclaude-local/worker.py:159-216` — LocalWorker class with run_once(), handle_envelope(), claim_and_process(), _submit_update()
  - `workers/openclaude-local/worker.py:416-425` — Main loop with poll interval and jitter

  **API/Type References**:
  - `worker-app/src-tauri/src/api.rs` — claim, heartbeat, complete, fail methods
  - `worker-app/src-tauri/src/sqs.rs` — SQS receive/send methods

  **WHY Each Reference Matters**:
  - `worker.py LocalWorker`: Exact dispatch table, claim flow, and result reporting pattern
  - Main loop: Configurable poll seconds with random jitter to avoid thundering herd

  **Acceptance Criteria**:
  - [ ] `worker.rs` compiles with Worker struct, run_once, dispatch table
  - [ ] All 7 job type stubs exist in dispatch table
  - [ ] Tauri events emitted for job lifecycle
  - [ ] `cargo test` passes for worker dispatch tests
  - [ ] Tauri commands registered in main.rs

  **QA Scenarios:**

  ```
  Scenario: Worker module compiles with dispatch table
    Tool: Bash
    Preconditions: worker.rs written
    Steps:
      1. cd worker-app/src-tauri && cargo check
      2. Assert exit code 0
      3. grep "repo_index\|architecture_dossier\|gap_analysis\|build_task_plan\|agent_branch_work\|test_verify\|sync_remote_state" src/worker.rs
      4. Assert all 7 job types present
    Expected Result: Worker dispatch table has all 7 capabilities
    Evidence: .sisyphus/evidence/task-9-worker-dispatch.txt

  Scenario: Tauri commands registered
    Tool: Bash
    Preconditions: main.rs updated with worker commands
    Steps:
      1. grep "invoke_handler" worker-app/src-tauri/src/main.rs — or lib.rs
      2. Assert worker commands are in the handler list
    Expected Result: Worker Tauri commands accessible from frontend
    Evidence: .sisyphus/evidence/task-9-tauri-commands.txt
  ```

  **Commit**: YES
  - Message: `feat(worker-app): add job processor framework with dispatch table`
  - Files: `worker-app/src-tauri/src/worker.rs`, updates to main.rs/lib.rs
  - Pre-commit: `cd worker-app/src-tauri && cargo test`

- [ ] 10. Git Operations Module

  **What to do**:
  - Create `worker-app/src-tauri/src/git.rs`:
    - `git_run(repo_dir, args, logs) -> Result<String>` — shell out to git CLI with tokio::process::Command
    - Helper methods wrapping common operations:
      - `ensure_repo(repo_dir, clone_url, branch)` — clone if missing, else fetch+checkout+pull
      - `git_clone(clone_url, branch, target_dir)` — `git clone --branch {branch} {url} {dir}`
      - `git_fetch_all(repo_dir)` — `git fetch --all --prune`
      - `git_checkout(repo_dir, branch)` — `git checkout {branch}`
      - `git_pull_ff(repo_dir)` — `git pull --ff-only`
      - `git_add_all(repo_dir)` — `git add .`
      - `git_commit(repo_dir, message)` — `git commit -m {message}`
      - `git_push(repo_dir, branch, remote)` — `git push -u {remote} {branch}`
      - `git_status_porcelain(repo_dir)` — `git status --porcelain`
      - `git_rev_parse_head(repo_dir)` — `git rev-parse HEAD`
      - `git_checkout_new_branch(repo_dir, branch)` — `git checkout -B {branch}`
    - All methods capture stdout+stderr, append to logs Vec, return output
    - Optional `check` parameter — some git commands are non-critical (e.g., checkout on existing branch might fail)

  **Must NOT do**:
  - Do NOT use git2 crate — shell out to git CLI for simplicity and exact parity with Python
  - Do NOT implement git authentication — rely on system git credentials

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: tokio::process, async command execution, output capture
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Wave 1)
  - **Parallel Group**: Wave 2
  - **Blocks**: Tasks 14-16
  - **Blocked By**: Tasks 1, 3

  **References**:

  **Pattern References**:
  - `workers/openclaude-local/worker.py:301-313` — _git() and _run() helper methods (exact command patterns, output capture, error handling)
  - `workers/openclaude-local/worker.py:238-245` — _ensure_repo() (clone vs fetch+pull logic)

  **WHY Each Reference Matters**:
  - `worker.py _git/_run`: Exact git commands, output handling, exit code behavior, and log capture pattern

  **Acceptance Criteria**:
  - [ ] `git.rs` compiles with all helper methods
  - [ ] `cargo test` passes for git module
  - [ ] Command output capture matches Python pattern (stdout+stderr, exit code)

  **QA Scenarios:**

  ```
  Scenario: Git module compiles
    Tool: Bash
    Preconditions: git.rs written
    Steps:
      1. cd worker-app/src-tauri && cargo check
      2. Assert exit code 0
    Expected Result: Git module compiles without errors
    Evidence: .sisyphus/evidence/task-10-git-compile.txt

  Scenario: All git operations defined
    Tool: Bash (grep)
    Preconditions: git.rs written
    Steps:
      1. grep "clone\|fetch\|checkout\|pull\|add\|commit\|push\|status\|rev_parse" worker-app/src-tauri/src/git.rs
      2. Assert all 9+ git operations present
    Expected Result: All git operations from worker.py are available
    Evidence: .sisyphus/evidence/task-10-git-ops.txt
  ```

  **Commit**: YES
  - Message: `feat(worker-app): add git operations module`
  - Files: `worker-app/src-tauri/src/git.rs`
  - Pre-commit: `cd worker-app/src-tauri && cargo check`

- [ ] 11. Dashboard: Status Panel + Health Metrics

  **What to do**:
  - Create `worker-app/src/lib/components/Dashboard/StatusPanel.svelte`:
    - Status card showing: worker status (idle/pairing/active/error) with color-coded Badge
    - Connection info: API base URL, worker ID, tenant ID
    - Health metrics row (4-column grid matching web app pattern):
      - "Jobs completed" count
      - "Current job" type or "Idle"
      - "Uptime" formatted as Xh Xm
      - "Last heartbeat" timestamp
    - Machine info: display name, platform, engine
    - Capabilities list as Badge components
    - Subscribes to Tauri events for real-time status updates
    - Uses Card, Badge, Button components

  **Must NOT do**:
  - Do NOT implement live logs (Task 13)
  - Do NOT implement job history (Task 12)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Dashboard UI matching existing web app design patterns
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: Status dashboard with health metrics layout

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Tasks 2, 6)
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 13
  - **Blocked By**: Tasks 2, 6

  **References**:

  **Pattern References**:
  - `frontend/src/lib/components/LocalWorkers/LocalWorkers.svelte:134-155` — Status grid pattern (4-column, article cards with span/strong/small)
  - `frontend/src/lib/components/LocalWorkers/LocalWorkers.svelte:216-242` — Worker detail row pattern

  **WHY Each Reference Matters**:
  - LocalWorkers status grid: Exact same 4-column card layout with label/value/description pattern

  **Acceptance Criteria**:
  - [ ] `StatusPanel.svelte` renders status, connection info, health metrics
  - [ ] `npm run build` succeeds
  - [ ] Uses Card, Badge, Button from Task 6
  - [ ] Grid layout matches web app pattern

  **QA Scenarios:**

  ```
  Scenario: Status panel builds
    Tool: Bash
    Preconditions: StatusPanel.svelte created
    Steps:
      1. cd worker-app && npm run build
      2. Assert exit code 0
    Expected Result: StatusPanel compiles without Svelte errors
    Evidence: .sisyphus/evidence/task-11-status-build.txt
  ```

  **Commit**: YES (groups with Task 12)
  - Message: `feat(worker-app): add dashboard status panel and job history`
  - Files: `worker-app/src/lib/components/Dashboard/StatusPanel.svelte`

- [ ] 12. Dashboard: Job History + Current Job View

  **What to do**:
  - Create `worker-app/src/lib/components/Dashboard/JobHistory.svelte`:
    - Current job card (if active): job type, idea ID, project name, elapsed time
    - Progress indicator (simple: "Running..." with elapsed timer, no percentage unless available)
    - Job history list: last 20 jobs with:
      - Status icon (✅ completed / ❌ failed) as Badge
      - Job type
      - Timestamp (relative: "2m ago", "1h ago")
      - Duration
    - Empty state: "No jobs processed yet" message
    - Subscribes to Tauri events: `job-started`, `job-completed`, `job-failed`
    - Uses Card, Badge components

  **Must NOT do**:
  - Do NOT show job logs (that's Task 13)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: List UI, event-driven updates, relative timestamps
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: Job history list with status indicators

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Tasks 2, 6)
  - **Parallel Group**: Wave 2
  - **Blocks**: None
  - **Blocked By**: Tasks 2, 6

  **References**:

  **Pattern References**:
  - `frontend/src/lib/components/LocalWorkers/LocalWorkers.svelte:186-208` — Request list row pattern (status + details + actions)
  - `frontend/src/lib/components/LocalWorkers/LocalWorkers.svelte:245-263` — Event list pattern

  **WHY Each Reference Matters**:
  - LocalWorkers rows: Same row pattern with strong/small/span layout for list items

  **Acceptance Criteria**:
  - [ ] `JobHistory.svelte` renders current job + history list
  - [ ] `npm run build` succeeds
  - [ ] Subscribes to Tauri events for live updates
  - [ ] Empty state shown when no jobs

  **QA Scenarios:**

  ```
  Scenario: Job history builds
    Tool: Bash
    Preconditions: JobHistory.svelte created
    Steps:
      1. cd worker-app && npm run build
      2. Assert exit code 0
    Expected Result: JobHistory compiles without errors
    Evidence: .sisyphus/evidence/task-12-job-history.txt
  ```

  **Commit**: YES (groups with Task 11)
  - Message: `feat(worker-app): add dashboard status panel and job history`
  - Files: `worker-app/src/lib/components/Dashboard/JobHistory.svelte`

- [ ] 13. Dashboard: Live Logs Viewer

  **What to do**:
  - Create `worker-app/src/lib/components/Dashboard/LiveLogs.svelte`:
    - Scrolling terminal-style log viewer
    - Auto-scrolls to bottom as new logs arrive
    - Each log line formatted as: `[HH:MM:SS] $ command` or `[HH:MM:SS] output text`
    - Color coding: commands in cyan (`--color-primary-2`), errors in red (`--color-error`), normal in secondary text color
    - Max buffer: last 500 lines (oldest dropped)
    - Clear button to reset logs
    - Subscribes to Tauri event: `worker-log` with { line, level } payload
    - Uses monospace font (`--font-mono`)
    - Matches the web app's `<code>` styling pattern (dark background, border, overflow scroll)

  **Must NOT do**:
  - Do NOT implement log file persistence (logs live in memory only)
  - Do NOT add search/filter (out of scope for v1)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Terminal-style UI, auto-scroll, color formatting
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: Terminal-style log viewer with auto-scroll

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Tasks 2, 6, 11)
  - **Parallel Group**: Wave 2
  - **Blocks**: None
  - **Blocked By**: Tasks 2, 6

  **References**:

  **Pattern References**:
  - `frontend/src/lib/components/LocalWorkers/LocalWorkers.svelte:362-373` — `<code>` styling pattern (dark bg, border, monospace, overflow)
  - `frontend/src/lib/components/Layout/Sidebar.svelte` — Command log section pattern

  **WHY Each Reference Matters**:
  - LocalWorkers code styling: Exact same visual treatment for log output
  - Sidebar command log: Shows how the web app already renders live command output

  **Acceptance Criteria**:
  - [ ] `LiveLogs.svelte` renders scrolling log viewer
  - [ ] Auto-scrolls to bottom
  - [ ] Monospace font, dark background, colored output
  - [ ] `npm run build` succeeds

  **QA Scenarios:**

  ```
  Scenario: Live logs component builds
    Tool: Bash
    Preconditions: LiveLogs.svelte created
    Steps:
      1. cd worker-app && npm run build
      2. Assert exit code 0
    Expected Result: LiveLogs compiles without errors
    Evidence: .sisyphus/evidence/task-13-live-logs.txt
  ```

  **Commit**: YES (groups with Tasks 11-12)
  - Message: `feat(worker-app): add dashboard live logs viewer`
  - Files: `worker-app/src/lib/components/Dashboard/LiveLogs.svelte`

- [ ] 14. Repo Indexing (walkdir, manifests, TODOs, test detection)

  **What to do**:
  - Create `worker-app/src-tauri/src/indexing.rs`:
    - `index_repo(repo_dir) -> RepoIndex` function
    - Use `walkdir` + `ignore` crates to walk filesystem (respecting .gitignore, skipping SKIP_DIRS: .git, node_modules, .venv, __pycache__, dist, build, .next, .svelte-kit)
    - `FileEntry` struct: path, size, kind (source/manifest/doc/asset) — match Python's _kind()
    - Detect manifests: package.json, pyproject.toml, requirements.txt, pnpm-lock.yaml, etc.
    - Read manifest contents (capped at 24KB per file)
    - Scan source files for TODO/FIXME lines (capped at 200 entries)
    - Scan for route patterns: @app., APIRouter, router.
    - `detect_tests(manifests) -> Vec<String>` — extract test commands from package.json scripts and pyproject.toml
    - `RepoIndex` struct: file_inventory, manifests, route_map, test_commands, risks, todos, searchable_chunks
    - Register as the `repo_index` handler in the worker dispatch table (Task 9)

  **Must NOT do**:
  - Do NOT implement architecture_dossier (that's agent-driven, Task 15)
  - Do NOT read files larger than 250KB

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Filesystem traversal, pattern matching, manifest parsing
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Tasks 3, 10)
  - **Parallel Group**: Wave 3
  - **Blocks**: Task 15
  - **Blocked By**: Tasks 3, 10

  **References**:

  **Pattern References**:
  - `workers/openclaude-local/worker.py:247-265` — _index_repo() (exact file classification, manifest names, source suffixes, skip dirs, caps)
  - `workers/openclaude-local/worker.py:316-330` — _detect_tests() (exact test command detection logic)
  - `workers/openclaude-local/worker.py:332-345` — _kind() and _read() helpers
  - `workers/openclaude-local/worker.py:27-29` — SKIP_DIRS, SOURCE_SUFFIXES, MANIFEST_NAMES constants

  **WHY Each Reference Matters**:
  - These functions define exact file classification logic that must be replicated identically

  **Acceptance Criteria**:
  - [ ] `indexing.rs` compiles with index_repo function
  - [ ] Walks filesystem respecting skip dirs and size limits
  - [ ] Detects manifests, TODOs, routes, test commands
  - [ ] `cargo test` passes with indexing tests
  - [ ] Registered as repo_index handler in dispatch table

  **QA Scenarios:**

  ```
  Scenario: Indexing module compiles and tests pass
    Tool: Bash
    Preconditions: indexing.rs written
    Steps:
      1. cd worker-app/src-tauri && cargo test indexing
      2. Assert tests pass
    Expected Result: Indexing tests pass (file classification, manifest detection)
    Evidence: .sisyphus/evidence/task-14-indexing.txt
  ```

  **Commit**: YES
  - Message: `feat(worker-app): add repo indexing module`
  - Files: `worker-app/src-tauri/src/indexing.rs`

- [ ] 15. Agent Spawning (openclaude/opencode/codex)

  **What to do**:
  - Create `worker-app/src-tauri/src/agent.rs`:
    - `run_agent(repo_dir, prompt, engine, settings, logs) -> Result<String>` function
    - Agent discovery: check `which openclaude`, `which opencode`, `which codex` in order
    - Build command based on engine type:
      - openclaude: `openclaude -p [--agent X] [--model X] [--permission-mode X] [--output-format X] [--max-budget-usd X] [--system-prompt X] [--add-dir X]... {prompt}`
      - opencode: `opencode run {prompt}`
      - codex: `codex exec -C {repo_dir} {prompt}`
    - If no engine found: return empty string + log "No local coding engine found"
    - Use tokio::process::Command for async execution
    - Capture stdout+stderr, append to logs Vec
    - Stream output lines as Tauri events: `worker-log`
    - Timeout: configurable, default 30 minutes

  **Must NOT do**:
  - Do NOT implement branch work logic (Task 16)
  - Do NOT install agents — just detect and use them

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Process management, async command execution, output streaming
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Tasks 9, 10)
  - **Parallel Group**: Wave 3
  - **Blocks**: Task 16
  - **Blocked By**: Tasks 9, 10

  **References**:

  **Pattern References**:
  - `workers/openclaude-local/worker.py:135-156` — OpenClaudeAdapter class (exact command building with all flags)
  - `workers/openclaude-local/worker.py:267-275` — _run_agent() (engine discovery, fallback chain)

  **WHY Each Reference Matters**:
  - `OpenClaudeAdapter`: Exact CLI flags and argument ordering for each engine
  - `_run_agent()`: Fallback chain logic (openclaude → opencode → codex → empty)

  **Acceptance Criteria**:
  - [ ] `agent.rs` compiles with run_agent function
  - [ ] Detects all 3 agent engines
  - [ ] Streams output as Tauri events
  - [ ] `cargo test` passes

  **QA Scenarios:**

  ```
  Scenario: Agent module compiles
    Tool: Bash
    Preconditions: agent.rs written
    Steps:
      1. cd worker-app/src-tauri && cargo check
      2. Assert exit code 0
    Expected Result: Agent module compiles
    Evidence: .sisyphus/evidence/task-15-agent.txt
  ```

  **Commit**: YES
  - Message: `feat(worker-app): add agent spawning module`
  - Files: `worker-app/src-tauri/src/agent.rs`

- [ ] 16. Branch Work Handler (git checkout, agent, tests, push)

  **What to do**:
  - Create `worker-app/src-tauri/src/branch_work.rs`:
    - `branch_work(repo_dir, job, project, config, logs) -> BranchWorkResult` function
    - Extract payload from job: prompt, branch_name (or generate one), allow_full_control
    - `git checkout -B {branch_name}`
    - Build prompt (append autonomy boundary unless full_control)
    - Call `run_agent()` from agent.rs
    - Call `run_tests()` — detect test commands, run up to 4
    - Check `git status --porcelain` for changes
    - If changes: `git add .` → `git commit -m {message}` → `git push -u origin {branch}`
    - Return: { branch_name, commit_sha, commit_message, agent_output, tests_passed, full_control_used }
    - Register as handler for: `agent_branch_work`, `test_verify` in dispatch table
  - Also implement handlers for `architecture_dossier`, `gap_analysis`, `build_task_plan`:
    - Index repo → build prompt with index → run_agent → return result with commit_sha

  **Must NOT do**:
  - Do NOT implement full_control safety checks beyond what Python does
  - Do NOT merge to main

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex multi-step git operations, agent integration, test execution
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on Tasks 14, 15)
  - **Parallel Group**: Wave 3 (sequential within group)
  - **Blocks**: Task 23
  - **Blocked By**: Tasks 9, 10, 14, 15

  **References**:

  **Pattern References**:
  - `workers/openclaude-local/worker.py:218-236` — _branch_work() (exact flow: checkout, prompt, agent, tests, add, commit, push)
  - `workers/openclaude-local/worker.py:199-216` — process_job() dispatch for all types
  - `workers/openclaude-local/worker.py:277-284` — _run_tests() (detect tests, run up to 4, check exit code)

  **WHY Each Reference Matters**:
  - `_branch_work()`: Exact sequence of git + agent + test operations
  - `process_job()`: Shows how different job types map to different processing paths

  **Acceptance Criteria**:
  - [ ] `branch_work.rs` compiles with branch_work function
  - [ ] All job type handlers registered in dispatch table
  - [ ] `cargo test` passes

  **QA Scenarios:**

  ```
  Scenario: Branch work module compiles
    Tool: Bash
    Preconditions: branch_work.rs written
    Steps:
      1. cd worker-app/src-tauri && cargo check
      2. Assert exit code 0
    Expected Result: Branch work module compiles
    Evidence: .sisyphus/evidence/task-16-branch-work.txt
  ```

  **Commit**: YES
  - Message: `feat(worker-app): add branch work handler for all job types`
  - Files: `worker-app/src-tauri/src/branch_work.rs`

- [ ] 17. Dashboard: Configuration Editor

  **What to do**:
  - Create `worker-app/src/lib/components/Dashboard/ConfigEditor.svelte`:
    - Form with fields: API Base URL, Display Name, Tenant ID, Workspace Root, Poll Seconds, Engine (dropdown)
    - Capabilities as checkboxes: repo_index, architecture_dossier, gap_analysis, build_task_plan, agent_branch_work, test_verify, sync_remote_state
    - OpenClaude settings: model, agent, permission_mode, output_format, max_budget_usd, system_prompt
    - Save button → invokes Tauri command to write config to worker-config.json
    - Load current config on mount
    - Uses Card, Input, Button, Badge components
    - Sections separated by Card components matching web app panel pattern

  **Must NOT do**:
  - Do NOT save config to backend (only local file)
  - Do NOT add validation beyond required fields

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
    - Reason: Form layout with design system consistency
  - **Skills**: [`frontend-ui-ux`]
    - `frontend-ui-ux`: Settings form with proper layout and grouping

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Tasks 2, 6)
  - **Parallel Group**: Wave 3
  - **Blocks**: None
  - **Blocked By**: Tasks 2, 6

  **References**:

  **Pattern References**:
  - `frontend/src/lib/components/UI/Input.svelte` — Form input pattern with mono labels
  - `workers/openclaude-local/worker-config.example.json` — Exact config shape to edit

  **WHY Each Reference Matters**:
  - `worker-config.example.json`: Defines every field the editor must support

  **Acceptance Criteria**:
  - [ ] `ConfigEditor.svelte` renders all config fields
  - [ ] Save invokes Tauri command
  - [ ] `npm run build` succeeds

  **QA Scenarios:**

  ```
  Scenario: Config editor builds
    Tool: Bash
    Preconditions: ConfigEditor.svelte created
    Steps:
      1. cd worker-app && npm run build
      2. Assert exit code 0
    Expected Result: ConfigEditor compiles
    Evidence: .sisyphus/evidence/task-17-config-editor.txt
  ```

  **Commit**: YES
  - Message: `feat(worker-app): add configuration editor dashboard`
  - Files: `worker-app/src/lib/components/Dashboard/ConfigEditor.svelte`

- [ ] 18. Auto-Start Plugin Integration

  **What to do**:
  - Add `tauri-plugin-autostart` to Cargo.toml (if not already)
  - Register autostart plugin in Tauri builder
  - Add tray menu item: "Start at Login" (toggle)
  - Persist autostart preference in app config
  - On macOS: creates LaunchAgent via SMAppService or tauri-plugin-autostart
  - On Windows: registers via registry (handled by plugin)
  - Verify: autostart toggle appears in tray menu

  **Must NOT do**:
  - Do NOT require admin elevation
  - Do NOT create custom launchd/plist files (use the plugin)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Plugin integration, minimal code
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Task 5)
  - **Parallel Group**: Wave 3
  - **Blocks**: None
  - **Blocked By**: Task 5

  **References**:

  **External References**:
  - Tauri autostart plugin: `https://v2.tauri.app/plugin/autostart/`

  **Acceptance Criteria**:
  - [ ] Autostart plugin registered in Cargo.toml and Tauri builder
  - [ ] Tray menu has "Start at Login" toggle
  - [ ] `cargo build` succeeds

  **QA Scenarios:**

  ```
  Scenario: Autostart plugin compiles
    Tool: Bash
    Steps:
      1. cd worker-app/src-tauri && cargo check
      2. Assert exit code 0
    Expected Result: Plugin integration compiles
    Evidence: .sisyphus/evidence/task-18-autostart.txt
  ```

  **Commit**: YES
  - Message: `feat(worker-app): add auto-start on boot via tauri plugin`
  - Files: `worker-app/src-tauri/` (Cargo.toml, main.rs/lib.rs, tray.rs)

- [ ] 19. Auto-Update Setup

  **What to do**:
  - Add `tauri-plugin-updater` to Cargo.toml (if not already)
  - Register updater plugin in Tauri builder
  - Configure update endpoint in tauri.conf.json (GitHub Releases URL pattern)
  - Create `worker-app/src-tauri/src/updater.rs`:
    - Check for updates on app launch (async, non-blocking)
    - If update found: emit Tauri event `update-available` with version info
    - Svelte dashboard shows update notification in status bar
    - Install on next restart (default Tauri updater behavior)
  - Add tray menu item: "Check for Updates"
  - Generate signing key: `cargo tauri signer generate` (store public key in tauri.conf.json)

  **Must NOT do**:
  - Do NOT implement custom update server (use GitHub Releases)
  - Do NOT force updates silently

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Tauri updater plugin, signing, release workflow
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Task 1)
  - **Parallel Group**: Wave 3
  - **Blocks**: Tasks 21, 22
  - **Blocked By**: Task 1

  **References**:

  **External References**:
  - Tauri updater plugin: `https://v2.tauri.app/plugin/updater/`

  **Acceptance Criteria**:
  - [ ] Updater plugin registered
  - [ ] Update check runs on launch
  - [ ] "Check for Updates" in tray menu
  - [ ] Signing key generated, public key in config

  **QA Scenarios:**

  ```
  Scenario: Updater plugin compiles
    Tool: Bash
    Steps:
      1. cd worker-app/src-tauri && cargo check
      2. Assert exit code 0
    Expected Result: Updater integration compiles
    Evidence: .sisyphus/evidence/task-19-updater.txt
  ```

  **Commit**: YES
  - Message: `feat(worker-app): add auto-update support via tauri plugin`
  - Files: `worker-app/src-tauri/` (Cargo.toml, config, updater.rs)

- [ ] 20. Error Handling & Reconnection Logic

  **What to do**:
  - Enhance `worker-app/src-tauri/src/api.rs`:
    - Retry failed HTTP requests with exponential backoff (max 3 retries)
    - Handle: connection refused, DNS failure, timeout, 5xx server errors
    - Don't retry: 4xx client errors (except 429 rate limit)
  - Enhance `worker-app/src-tauri/src/worker.rs`:
    - Wrap run_once() in error handler: catch network errors, log, continue loop
    - On connection failure: emit `worker-status` event with "reconnecting"
    - Back off poll interval during sustained failures (5s → 30s → 60s → 120s)
    - Reset poll interval on successful connection
  - Enhance `worker-app/src-tauri/src/sqs.rs`:
    - Handle SQS throttling, credential expiration
    - Fall back to API-based polling when SQS credentials expire
  - Create `worker-app/src-tauri/src/error.rs`:
    - `WorkerError` enum: Api(ApiError), Io(std::io::Error), Config(String), Git(String), Agent(String)
    - Implement std::error::Error and Display for all variants

  **Must NOT do**:
  - Do NOT retry infinitely — cap at max retries then back off
  - Do NOT panic on any error — always gracefully handle

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Error architecture, retry strategies, reconnection state machine
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (enhances existing modules)
  - **Parallel Group**: Wave 4
  - **Blocks**: Task 23
  - **Blocked By**: Tasks 4, 8, 9

  **References**:

  **Pattern References**:
  - `workers/openclaude-local/worker.py:416-425` — Main loop error handling (catches URLError/TimeoutError, logs, continues)

  **Acceptance Criteria**:
  - [ ] `error.rs` defines WorkerError enum with all variants
  - [ ] HTTP retries with backoff for transient errors
  - [ ] Worker loop survives network errors without crashing
  - [ ] Poll interval backs off during failures
  - [ ] `cargo test` passes

  **QA Scenarios:**

  ```
  Scenario: Error module compiles
    Tool: Bash
    Steps:
      1. cd worker-app/src-tauri && cargo check
      2. cargo test error
      3. Assert tests pass
    Expected Result: Error handling compiles and tests pass
    Evidence: .sisyphus/evidence/task-20-error-handling.txt
  ```

  **Commit**: YES
  - Message: `feat(worker-app): add error handling, retry, and reconnection logic`
  - Files: `worker-app/src-tauri/src/error.rs`, updates to api.rs, worker.rs, sqs.rs

- [ ] 21. Windows Build Pipeline (.exe/.msi)

  **What to do**:
  - Create `worker-app/.github/workflows/build-worker-app.yml` (or document manual build):
    - Steps: install Rust, install Node, npm install, cargo tauri build
    - Output: .exe installer + .msi in target/release/bundle/
  - Configure `tauri.conf.json` for Windows:
    - `bundle.windows` section: installer language, NSIS or WiX settings
    - App icon: .ico format
    - File associations: none needed
    - Window: no menu bar, no titlebar decorations if using custom chrome
  - Create `worker-app/src-tauri/icons/icon.ico` (Windows app icon)
  - Document build command: `cd worker-app && cargo tauri build`
  - Verify: build produces `target/release/bundle/msi/*.msi` or `nsis/*.exe`

  **Must NOT do**:
  - Do NOT set up code signing yet (can be added later)
  - Do NOT create CI/CD pipeline — just document the build process

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Tauri build configuration, Windows bundling
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Task 19)
  - **Parallel Group**: Wave 4
  - **Blocks**: None
  - **Blocked By**: Task 19

  **References**:

  **External References**:
  - Tauri Windows build: `https://v2.tauri.app/distribute/windows/`

  **Acceptance Criteria**:
  - [ ] `cargo tauri build` produces Windows installer
  - [ ] `tauri.conf.json` has Windows bundle config
  - [ ] Build documented in worker-app/README.md (or similar)

  **QA Scenarios:**

  ```
  Scenario: Windows build produces artifacts
    Tool: Bash
    Steps:
      1. cd worker-app && cargo tauri build --target x86_64-pc-windows-msvc 2>&1 | tail -5
      2. Check target/release/bundle/ directory for .msi or .exe
    Expected Result: Build completes, installer file exists
    Evidence: .sisyphus/evidence/task-21-windows-build.txt
  ```

  **Commit**: YES
  - Message: `feat(worker-app): add Windows build pipeline`
  - Files: `worker-app/src-tauri/tauri.conf.json`, icons, workflow/docs

- [ ] 22. macOS Build Pipeline (.dmg + signing)

  **What to do**:
  - Configure `tauri.conf.json` for macOS:
    - `bundle.macOS` section: minimum system version, category
    - LSUIElement: true (no dock icon — system tray only)
    - App icon: .icns format
  - Create `worker-app/src-tauri/icons/icon.icns` (macOS app icon)
  - Document code signing steps (not required for local dev, required for distribution):
    - `codesign --sign "Developer ID Application: ..." target/release/bundle/macos/*.app`
    - `xcrun notarytool submit ...`
  - Document build command: `cd worker-app && cargo tauri build --target aarch64-apple-darwin`
  - Note: Actual macOS build requires macOS machine (cannot cross-compile from Windows)
  - Provide instructions for building on macOS

  **Must NOT do**:
  - Do NOT require code signing for development builds
  - Do NOT attempt to cross-compile from Windows

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: macOS-specific bundling, signing documentation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Task 19)
  - **Parallel Group**: Wave 4
  - **Blocks**: None
  - **Blocked By**: Task 19

  **References**:

  **External References**:
  - Tauri macOS build: `https://v2.tauri.app/distribute/macos/`
  - macOS signing: `https://v2.tauri.app/distribute/macos/#signing-and-notarizing`

  **Acceptance Criteria**:
  - [ ] `tauri.conf.json` has macOS bundle config with LSUIElement
  - [ ] Build documentation provided
  - [ ] macOS icon exists

  **QA Scenarios:**

  ```
  Scenario: macOS config is valid
    Tool: Bash
    Steps:
      1. grep "LSUIElement" worker-app/src-tauri/tauri.conf.json — assert true
      2. Verify macOS bundle section exists
    Expected Result: macOS config properly set for tray-only app
    Evidence: .sisyphus/evidence/task-22-macos-config.txt
  ```

  **Commit**: YES
  - Message: `feat(worker-app): add macOS build configuration`
  - Files: `worker-app/src-tauri/tauri.conf.json`, icons, docs

- [ ] 23. Integration Test (full flow: pair → claim → process → report)

  **What to do**:
  - Create `worker-app/src-tauri/tests/integration_test.rs`:
    - Test: config loads from file
    - Test: state save/load round-trip
    - Test: API client constructs correct URLs and headers
    - Test: SQS message parsing
    - Test: worker dispatch routes to correct handler
    - Test: git module commands are correct (mock or real git repo)
    - Test: indexing produces valid RepoIndex from test fixture
    - Test: pairing flow constructs correct register payload
  - Create test fixtures:
    - `worker-app/src-tauri/tests/fixtures/worker-config.json`
    - `worker-app/src-tauri/tests/fixtures/state.json`
    - `worker-app/src-tauri/tests/fixtures/sample-repo/` (minimal git repo for indexing test)
  - All tests must pass: `cargo test`

  **Must NOT do**:
  - Do NOT make network calls to real API (mock or unit-test level)
  - Do NOT require AWS credentials for SQS tests

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Integration testing across all modules, test fixture creation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on all implementation)
  - **Parallel Group**: Wave 4
  - **Blocks**: F1-F4
  - **Blocked By**: Tasks 9, 14, 15, 16, 20

  **References**:

  **Pattern References**:
  - `workers/openclaude-local/tests/test_worker.py` — Existing Python worker tests (what to test)

  **API/Type References**:
  - All Rust modules in `worker-app/src-tauri/src/`

  **Acceptance Criteria**:
  - [ ] Integration test file exists with 8+ test cases
  - [ ] Test fixtures exist
  - [ ] `cargo test` passes all tests
  - [ ] No tests make real network calls

  **QA Scenarios:**

  ```
  Scenario: All integration tests pass
    Tool: Bash
    Preconditions: All implementation tasks complete
    Steps:
      1. cd worker-app/src-tauri && cargo test --test integration_test
      2. Assert exit code 0
      3. Assert all test cases pass
    Expected Result: Full integration test suite passes
    Failure Indicators: Missing module, broken import, test fixture missing
    Evidence: .sisyphus/evidence/task-23-integration.txt
  ```

  **Commit**: YES
  - Message: `test(worker-app): add integration tests for full worker flow`
  - Files: `worker-app/src-tauri/tests/`, fixtures

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, check module). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `cargo clippy` + `cargo test` + `npm run build`. Review all changed files for: unwrap() in production, empty error catches, debug prints, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names.
  Output: `Build [PASS/FAIL] | Clippy [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high` (+ `playwright` skill if UI)
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration. Test edge cases: no network, invalid config, missing git. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1 — everything in spec was built, nothing beyond spec was built. Check "Must NOT do" compliance. Detect cross-task contamination. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **Wave 1**: `feat(worker-app): scaffold Tauri v2 project with Svelte 5 frontend`
- **Wave 2**: `feat(worker-app): add pairing flow, job processing, SQS transport, dashboard`
- **Wave 3**: `feat(worker-app): add repo indexing, agent spawning, config editor, autostart`
- **Wave 4**: `feat(worker-app): add error handling, build pipelines, integration tests`

---

## Success Criteria

### Verification Commands
```bash
cd worker-app && cargo build          # Expected: Compiles successfully
cd worker-app && cargo test           # Expected: All tests pass
cd worker-app && npm run build        # Expected: Svelte builds successfully
cd worker-app && cargo tauri build    # Expected: Produces .exe (Win) or .app (macOS)
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] `cargo test` passes
- [ ] `npm run build` succeeds
- [ ] App launches with system tray icon
- [ ] Pairing flow completes end-to-end
- [ ] Dashboard shows live status, jobs, logs
