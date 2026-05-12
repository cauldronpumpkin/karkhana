# Karkhana: 7-Day Sprint to Autonomous Operation

> **Model:** Manually triggered by CEO each morning
> **Each day:** CEO asks for status → I report + recommend next phase → CEO greenlights → we execute
> **Completion bar:** Autonomy *working* end-to-end, not just implemented and tested
> **Start:** May 12, 2026 | **Target:** May 18, 2026

---

## Phase A — Day 1: Autonomy Level 2 (Auto-Repair)
**CEO triggers → we build and wire it live**

Karigar handles verification failures automatically instead of just reporting them.

- [ ] Auto-repair engine in Karigar: when verification fails, classify the failure (test/compile/review) and attempt a targeted fix pass
- [ ] Retry logic: max 3 attempts per job, exponential backoff
- [ ] Escalation: after exhausted retries, mark job as `failed` with detailed ledger entry
- [ ] Ledger records: each repair attempt logged (what failed, what was attempted, outcome)
- [ ] Test all paths: pass-first-time, fix-succeeds, fix-exhausted
- [ ] **Working criteria:** Configure a factory run with auto-repair → submit a job with a deliberately failing test → Karigar auto-fixes it and reports success with ledger trail

## Phase B — Day 2: Real-Time WebSocket + Live Dashboard
**CEO triggers → we wire live streaming into the UI**

The existing WebSocket foundation gets connected end-to-end from worker to frontend.

- [ ] Karigar emits WebSocket events during job execution (started, checkpoint, verification, completed/failed)
- [ ] Backend WebSocket manager relays events to subscribed clients by run_id
- [ ] Frontend: live job log viewer in the run detail page (streaming, not polling)
- [ ] Frontend: run status updates in real-time (phase transitions, completion %)
- [ ] Worker heartbeat visible in dashboard (last seen, current job, status)
- [ ] **Working criteria:** Open a run in the browser → start a Karigar job → see live logs appear character-by-character in the UI

## Phase C — Day 3: Worker Daemon Mode
**CEO triggers → we make Karigar run autonomously**

Karigar runs as a persistent background process, not a one-shot CLI.

- [ ] Daemon entry point: `karigar daemon` — polls backend, claims jobs, executes, reports
- [ ] Poll interval configurable (default 20s), with jitter to avoid thundering herd
- [ ] Heartbeat: sends every 15s while job is running
- [ ] Graceful shutdown: finish current job, unregister, save state
- [ ] Windows service wrapper (for the Tauri desktop worker)
- [ ] Daemon health check endpoint (HTTP or signal)
- [ ] Circuit breaker wired: hard cap on LLM token spend per job, per day, per worker
- [ ] **Working criteria:** Start `karigar daemon` → it claims an available job within one poll cycle → executes → reports → polls for next job. Kill it → it stops gracefully with state saved.

## Phase D — Day 4: Auto-Repair + Daemon Integration
**CEO triggers → we marry autonomy with daemon mode**

Autonomy Level 2 repair logic wired into the daemon loop.

- [ ] Daemon runs auto-repair loop on verification failure without exiting
- [ ] Repair attempts counted against circuit breaker budget
- [ ] Escalated jobs (3 failures) trigger notification (Telegram/webhook)
- [ ] Ledger entries include: repair_attempts, repair_outcomes, final_verdict
- [ ] Frontend: "Repairing..." status visible during auto-fix attempts
- [ ] Frontend: job history shows repair trail (attempt 1/3 → fixed, or attempt 3/3 → escalated)
- [ ] **Working criteria:** Configure a run with a flaky test → daemon picks it up → fails verification → auto-fixes → passes → ledger shows full repair history. Run 10 jobs in sequence with various failure modes → daemon handles all without human intervention.

## Phase E — Day 5: Production Hardening + Security
**CEO triggers → we lock it down**

No new features. Safety, security, and stability.

- [ ] Security audit: API auth headers validated on every endpoint
- [ ] Token rotation: worker tokens can be revoked, reissued
- [ ] Error handling audit: every failure mode in the daemon has a recovery path
- [ ] Cost controls: per-run budget hard cap, per-worker daily budget
- [ ] Monitoring: CloudWatch alarms for job failures, worker disconnects, ledger anomalies
- [ ] Worker app: release build with MSI (Windows) — the existing CI produces this on tag
- [ ] Worker app: verify macOS CI build produces a valid .app bundle
- [ ] **Working criteria:** Start daemon → run 20 jobs with random failures → every failure handled (repaired, escalated, or errored gracefully) → no unhandled exceptions. CI produces signed artifacts.

## Phase F — Day 6: Karkhana Builds Karkhana (Dogfood)
**CEO triggers → we eat our own dogfood**

A Karkhana worker claims a real Karkhana development task and delivers.

- [ ] Create a factory run for a concrete Karkhana improvement (e.g., "Add run cancellation API endpoint")
- [ ] Worker claims the job, reads the spec-kit contract, follows spec→plan→tasks→implement
- [ ] Worker creates PR against the karkhana repo with the changes
- [ ] Ledger records the full lifecycle
- [ ] CEO reviews the PR — if it works, autonomy is proven
- [ ] **Working criteria:** A real PR is submitted to karkhana by a karkhana worker, with spec artifacts, implementation, verification, and ledger trail — all autonomously.

## Phase G — Day 7: Buffer + Launch Readiness
**CEO triggers → we polish and ship**

Catch-up day. Anything that slipped gets closed. Final verification of the full pipeline.

- [ ] Any unfinished items from Phases A-F
- [ ] Full integration test: create idea → factory pipeline → worker claims → executes → reports → result visible in UI
- [ ] Documentation: one-page ops guide (how to start worker, create run, monitor)
- [ ] Go/no-go decision with CEO
- [ ] **Working criteria:** Full end-to-end flow works without human intervention. CEO can create an idea, see it get processed by workers, and review results — all autonomously.

---

## Operating Model

Each morning, you ask me for status. I respond with:

```
## Karkhana Status — Day N

**Last phase:** Phase X — [completed / in progress / pending]
**Tests:** 475 passing (419 backend + 56 Karigar)
**Last commit:** <sha> — <date>

**Recommendation:** Phase Y — [what it does, why now]
**Estimated effort:** ~1 day
**Go signal needed:** yes
```

You say "go" (or "skip"), and I execute the phase. If a phase runs long, we push subsequent phases right — no deadline slip beyond the 7-day window.

---

## Success Criteria

1. Autonomy Level 2 **works** — a worker can claim a job, fail verification, auto-repair, and succeed without human intervention
2. The daemon **runs unattended** — polls, claims, executes, reports in a loop
3. The dashboard **shows live** — WebSocket streams job progress to the UI in real-time
4. A Karkhana worker **improves Karkhana** — real PR submitted by the platform itself
7. All phases **fit in 7 days**, CEO-triggered, no build-up of unfinished work

---

## Phase H (Added) — Day 7+: Floci Local Stack + Single Backend Server
**CEO triggers when all coding phases done**

Move from Lambda/API Gateway backend to a single FastAPI server on Floci.

- [ ] Start Floci container (Docker already running)
- [ ] Create DynamoDB tables, SQS queues in Floci
- [ ] Start FastAPI backend directly via Uvicorn (port 8000)
- [ ] Seed local worker registration
- [ ] Verify daemon can claim jobs against local backend
- [ ] Write docs/local-dev.md quick-start guide

**Working criteria:** Floci running → backend on :8000 → daemon claims jobs against it → worker executes → reports. Full local dev loop.
