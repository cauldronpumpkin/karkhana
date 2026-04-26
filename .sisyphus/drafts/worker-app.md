# Draft: Tauri v2 Worker Desktop App

## Requirements (confirmed)
- One-click desktop app for Windows and macOS
- Follows exact same design pattern as webapp (Svelte 5 + dark theme + lucide icons + CSS variables)
- UI is worker-only (no ideas, chat, scoring, phases)
- System tray + hidden window (like Docker Desktop / ngrok)
- Full monitoring dashboard: status, job queue, live logs, job history, health metrics, config editor, pairing flow
- No native OS notifications
- Rust-native rewrite — no Python dependency
- Project location: `worker-app/` at repo root

## Technical Decisions
- **Framework**: Tauri v2 + Svelte 5
- **UI mode**: System tray (menu bar) + hidden window for dashboard
- **Worker logic**: Rewrite in Rust (reqwest for HTTP, serde for JSON, aws-sdk-sqs for SQS, shell out to git CLI)
- **System tray**: Tauri built-in tray-icon feature
- **Auto-start**: tauri-plugin-autostart
- **Auto-update**: tauri-plugin-updater (signed updates)
- **Subprocess**: tokio::process for spawning agents (openclaude, opencode, codex)
- **No Python dependency**: All worker logic in Rust
- **No notifications**: User checks dashboard manually

## Research Findings
- Tauri v2: 3-12 MB bundle, 30-70 MB idle RAM, official plugins for tray/autostart/updater
- Existing web app design system: CSS variables in app.css, 5 UI components (Button/Badge/Modal/Input/Card), lucide-svelte icons, Svelte 5 runes
- Real-world Tauri 2 + Svelte 5 + system tray apps: c9watch, Peek, Knative Explorer
- Code signing: Azure Trusted Signing ($9.99/mo) for Windows, Apple Dev Program ($99/yr) for macOS

## What the app does (from worker.py analysis)
1. **Pair**: POST /api/local-workers/register with tenant_id → poll until approved → store credentials
2. **Run**: Long-poll SQS command queue OR poll /api/worker/claim for jobs
3. **Process jobs**: repo_index, architecture_dossier, gap_analysis, build_task_plan, agent_branch_work, test_verify, sync_remote_state
4. **Report**: heartbeat, job_completed, job_failed via API or SQS events
5. **Git ops**: clone, fetch, checkout, pull, add, commit, push, status
6. **Agent spawning**: openclaude, opencode, or codex CLI
7. **Repo indexing**: Walk filesystem, read manifests, find TODOs, detect test commands

## Scope Boundaries
- INCLUDE: Worker app only (pairing, job processing, monitoring dashboard)
- INCLUDE: System tray, autostart on boot, auto-update
- INCLUDE: Full Rust rewrite of worker.py logic
- INCLUDE: Svelte 5 dashboard matching existing web app design system
- EXCLUDE: Ideas, chat, scoring, phases, reports (that's the web app)
- EXCLUDE: Native OS notifications
- EXCLUDE: Python dependency

## Open Questions
- Auto-update source: GitHub Releases or custom karkhana server endpoint?
- First release scope: MVP (pair + run + basic dashboard) or full feature set?
- macOS code signing: Apple Developer Program ($99/yr) required for distribution?
