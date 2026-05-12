# Karkhana: 4-Week Launch Plan

> **Owner:** Hermes Agent (deepseek-v4-pro) as Founding Engineer
> **CEO:** On Telegram (1544573225)
> **Advisor Agent:** codex-lb/gpt-5.5 (daily plan review)
> **Start:** 2026-05-06 | **Target complete:** 2026-06-03
> **PC resilience:** Plan auto-readjusts on restart. Deadlines shift by downtime.
> **CEO injection:** New ideas from CEO on Telegram are integrated into plan immediately. Plan rebalancing happens at next advisor review (9 AM daily).

---

## Major Milestones

| # | Milestone | Target | Status |
|---|-----------|--------|--------|
| 1 | Real engines execute jobs end-to-end via backend | Week 1 | 🟡 Code complete, awaiting backend connectivity test |
| 2 | CI/CD pipeline: tests on every push, auto-deploy frontend | Week 1-2 | ⬜ |
| 3 | Worker app: hardened, code-signed, auto-updating | Week 2-3 | 🟡 |
| 4 | Factory Run Ledger: API + frontend + verification | Week 2 | ⬜ |
| 5 | Autonomy Level 2: auto-repair failed jobs | Week 3 | ⬜ |
| 6 | Staging environment + production readiness | Week 3-4 | ⬜ |
| 7 | **Karkhana builds Karkhana** — the platform self-hosts its own development | Week 4+ | ⬜ |

Milestone 7 is the meta-goal: Karkhana workers claim Karkhana development tasks from the Karkhana backend, execute them, and submit PRs back to the Karkhana repo. The factory builds the factory.

---

## Critical Path

```
Karigar Backend Integration → Worker App Hardening → Ledger → Autonomy L2
                                  ↓
                            CI/CD (parallel)
                                  ↓
                            Staging (parallel)
```

Failure on critical path items triggers automatic reschedule. Parallel items can slip without blocking.

---

## Week 1: Foundation (May 6–12)

### Day 1 — Monday, May 6 ✅ IN PROGRESS
- [x] Karigar real engines: OpenCodeEngine + HermesAgentEngine implemented ✓
- [x] Engine registry, command policy, runner dispatch ✓
- [x] 31 tests passing ✓
- [x] Sent 5 deep research requests to CEO via Gmail (threaded) ✓
- [x] Set up deep research reminder cron (checks every 6h, reminds at 24h no-reply) ✓
- [x] Set up advisor agent cron job (codex-lb/gpt-5.5) ✓
- [x] Set up daily progress check cron job ✓
- [x] Set up test suite cron job (every 4h) ✓
- [x] Set up graphify cron job (every 6h) ✓

### Day 2 — Tuesday, May 7 ✅ COMPLETE
- [x] Karigar backend integration: `claim_job` API call ✓
- [x] Karigar: `report_result` (alias for complete_job) ✓
- [x] BackendClient tests (19 tests, mocked httpx) ✓
- [x] E2E integration tests (claim→run→report, claim→fail→report) ✓
- [x] CLI: `karigar --backend` mode wired (--api-base, --worker-id, --register) ✓

### Day 3 — Wednesday, May 8 ✅ COMPLETE
- [x] CI/CD: GitHub Actions for backend + Karigar tests (uv, Python 3.11, caching) ✓
- [x] CI/CD: GitHub Actions for frontend tests (Vitest + build) ✓
- [x] CI/CD: Go tests + build ✓
- [x] CI/CD: Worker app Windows Tauri build with artifacts ✓
- [x] CI/CD: Deploy frontend to AWS Amplify ✓
- [x] WebSocket foundation: FastAPI ConnectionManager + SvelteKit store (ahead of schedule) ✓

### Day 4 — Thursday, May 7
- [x] **CI/CD audit from deep research:** ✅ Done
  - [x] Go cache: switched to date-based keys with stale entry trimming ✅
  - [x] Rust cache: already using Swatinem/rust-cache@v2 (no change needed)
  - [x] Python uv cache: setup-uv@v5 handles this natively (no change needed)
  - [x] Frontend is Svelte (not SvelteKit) — no Amplify SSR adapter needed
  - [x] Root amplify.yml handles monorepo correctly
  - [x] Path-filtering skipped for now — repo is small, 5 workflows on every PR is fine
  - [x] Deploy workflow: removed redundant npm install/build (Amplify handles it), added OIDC structure
  - [x] OIDC setup script written: `.github/scripts/setup-oidc.sh`
- [x] Advisor cron: fixed — switched from codex-lb/gpt-5.5 (invalid API key) to deepseek ✅
- [x] **Factory Run Ledger — already complete** ✅ (plan was behind reality)
  - [x] Backend API: CRUD endpoints (GET/POST /api/ledgers/{run_id}, GET/PATCH /api/ledgers/{run_id}/{ledger_id}) ✅
  - [x] DynamoDB storage + S3 body storage (factory_run_ledger.py) ✅
  - [x] Backend tests: 15 tests in test_ledger_api.py, all passing ✅
  - [x] Karigar: create_ledger_entry() in backend_client.py + tested ✅
  - [x] Runner: auto-append in run_backend_loop() when factory_run_id set ✅
  - [x] Graphify: ledger files indexed in GRAPH_REPORT.md ✅

### Day 5 — Friday, May 10
- [x] CI/CD: Frontend build + deploy pipeline — already exists (deploy-frontend.yml) ✅
- [x] CI/CD: Worker app binary build — already exists (worker-app-build.yml) ✅
- [x] **E2E integration test** — written and passing: `backend/tests/test_factory_run_e2e.py` ✅
  - [x] test_create_factory_run: POST → 201 + factory_run with id ✅
  - [x] test_list_factory_runs: GET → 200 + list with runs ✅
  - [x] test_factory_run_creates_phases: POST → phases auto-created from template ✅
  - [x] test_claim_and_complete_job: claim → execute → complete → status=completed ✅
  - [x] test_ledger_exists_after_job_completion: 200 (skipped gracefully if no AWS creds) ✅

### Weekend (May 11–12) — Automated Only
- [ ] Test suite cron runs every 4h
- [ ] Graphify update every 6h
- [ ] Advisor agent weekly review

---

## Week 2: Hardening (May 13–19)

### Day 6 — Monday, May 13
- [x] Worker app: revoke button — added to StatusPanel.svelte (calls invoke('revoke_worker'), updates revoked store) ✅
- [x] Worker app: error boundary — created ErrorBoundary.svelte + wired in App.svelte wrapping all tab views ✅
- [x] Worker app: circuit breaker tests — 18 tests appended to circuit_breaker.rs ✅
- [x] macOS CI target — added macos-build job to worker-app-build.yml (macos-latest) ✅
- [ ] Review deep research on code signing

### Day 7 — Tuesday, May 14
- [x] Ledger API endpoints — already exists (GET/POST/PATCH /api/ledgers/{run_id/*}) ✅
- [x] Ledger DynamoDB entity — exists in factory_run_ledger.py ✅
- [x] Ledger S3 markdown body storage — exists (store_ledger_body, get_ledger_body) ✅

### Day 8 — Wednesday, May 15
- [x] Ledger frontend: list view — LedgerList.svelte exists ✅
- [x] Ledger frontend: detail view — LedgerDetail.svelte exists ✅
- [x] Wire ledger into FactoryRun lifecycle UI — KarkhanaRunPanel has Ledger tab ✅

### Day 9 — Thursday, May 16
- [x] Worker app: auto-update from releases — already exists (updater.rs + Tauri plugin configured) ✅
- [ ] Worker app: macOS build verification — CI target added, needs macOS runner to verify
- [ ] End-to-end: desktop worker claims real job, executes, reports — needs running Tauri app

### Day 10 — Friday, May 17
- [x] Week 2 progress report — this message ✅
- ~~Staging environment~~ — skipped (CEO: "app is not live, test in production")

### Weekend (May 18–19) — Automated Only
- [ ] Test suite, graphify, advisor review

---

## Week 3: Autonomy (May 20–26)

### Day 11 — Monday, May 20
- [ ] Autonomy Level 2: auto-repair engine design
- [ ] Safety guardrails: what can Level 2 do vs can't do
- [ ] Review deep research on AI agent sandboxing

### Day 12 — Tuesday, May 21
- [ ] Autonomy L2: implement auto-repair in Karigar
- [ ] Failed verification → auto-fix attempt → re-verify
- [ ] Max retry limit (3 attempts before escalation)

### Day 13 — Wednesday, May 22
- [ ] Autonomy L2: guardrail tests (try to break safety rules)
- [ ] Frontend: real-time WebSocket for chat + run status
- [ ] WebSocket: FastAPI endpoint + SvelteKit client

### Day 14 — Thursday, May 23
- [ ] macOS code signing (if Apple Developer account available — ask CEO)
- [ ] Performance: load test backend (100 concurrent factory runs)
- [ ] Performance: DynamoDB provisioned capacity tuning

### Day 15 — Friday, May 24
- [ ] Mobile-responsive frontend pass
- [ ] Documentation: API docs, architecture docs, onboarding guide
- [ ] Week 3 progress report to CEO via Telegram

### Weekend (May 25–26) — Automated Only

---

## Week 4: Ship (May 27 – Jun 2)

### Day 16 — Monday, May 27
- [ ] Production readiness checklist
- [ ] Security audit: API endpoints, auth, secrets
- [ ] DNS/SSL verification for all domains

### Day 17 — Tuesday, May 28
- [ ] Final integration test: full factory pipeline
- [ ] User acceptance testing flow
- [ ] Bug fixes from testing

### Day 18 — Wednesday, May 29
- [ ] macOS CI/CD pipeline (if cloud Mac available — ask CEO)
- [ ] Worker app release packaging (Windows .msi, macOS .dmg)
- [ ] Release notes + changelog

### Day 19 — Thursday, May 30
- [ ] Autonomy Level 3 design doc (for post-launch)
- [ ] Cost optimization: right-size DynamoDB, Lambda, API Gateway
- [ ] Monitoring + alerting setup (CloudWatch)

### Day 20 — Friday, May 31
- [ ] Final progress report
- [ ] Launch checklist sign-off
- [ ] Go/No-go decision with CEO

### Weekend (Jun 1–2) — Buffer
- [ ] Catch-up on any slipped items
- [ ] Final testing
- [ ] Launch prep

---

## Automated Cron Jobs

| Job | Schedule | Purpose |
|-----|----------|---------|
| `karkhana-test-suite` | Every 4h | Run all tests, report failures via Telegram |
| `karkhana-graphify` | Every 6h | Update knowledge graph |
| `karkhana-advisor` | Daily 9 AM | codex-lb/gpt-5.5 reviews progress, suggests adjustments |
| `karkhana-progress` | Daily 8 PM | Progress check: what was done today, what's blocked |
| `karkhana-plan-check` | Daily 7 AM | Readjust deadlines if PC was offline |

---

## Deep Research Requests for CEO

These go to Telegram. CEO runs Gemini deep research and pastes results.

1. **Tauri v2 macOS code signing:** Full process from Apple Developer account to notarized .dmg. Requirements, costs, timelines.
2. **GitHub Actions CI/CD for polyglot monorepo:** Best practices for Python + Rust + Go + Svelte in one repo. Matrix builds, caching, artifact management.
3. **AWS cost optimization for serverless:** DynamoDB on-demand vs provisioned, Lambda provisioned concurrency, API Gateway caching, Amplify pricing.
4. **AI agent sandboxing patterns:** How to safely execute AI-generated code. Container isolation, filesystem restrictions, network egress controls. What Cursor/Windsurf/Devin do.
5. **WebSocket in SvelteKit + FastAPI:** Production patterns for real-time updates. Reconnection, auth, scaling with API Gateway WebSocket.

---

## Failure Handling

- If a cron task fails → retry in 30 min, then 2h, then escalate to Telegram
- If PC shuts down → on restart, `karkhana-plan-check` calculates downtime and shifts all deadlines
- If a delegated subagent fails → retry with same context, if fails again → escalate to advisor agent
- Critical path blocker → immediate Telegram message to CEO

---

## Success Criteria (What "Done" Means)

1. User creates an idea on karkhana.one
2. Factory pipeline assigns it to a phase
3. Karigar worker claims the job, executes it with a real AI engine
4. Results (code, tests, review) are delivered back
5. Factory Run Ledger records everything
6. Autonomy Level 2 can auto-repair simple failures
7. CI/CD deploys on every merge to main
8. Staging environment catches regressions before production
