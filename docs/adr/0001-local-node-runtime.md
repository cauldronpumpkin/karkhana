# ADR-0001: Local node runtime foundation

## Status

Accepted

## Context

Karkhana needs a local tenant node runtime that can execute product/business orchestration on the user's machine while the hosted website remains a dashboard and control plane. The current repository has a Python local worker and a Tauri worker app direction, but this decision establishes a new additive foundation rather than expanding either of those implementations as the long-term core runtime.

The intended product shape is closer to a headless background app such as Tailscale than to a dashboard app installed on every worker machine. OpenCode CLI is expected to become the primary coding execution engine used by the local runtime.

## Decision

Use a **Go daemon** for the long-running local node runtime and an **npm launcher** as the install/distribution entrypoint.

Specifically:

- The website is **dashboard only**.
- The backend/Lambda layer should mostly expose dashboard/control APIs: authentication, tenant registration, node registration, master lease, high-level job/event state, and later audit/billing.
- The local tenant node runtime will increasingly own product/business orchestration.
- A node can eventually run as `worker`, `master`, or `master-worker`.
- Each tenant should eventually have exactly one active master node.
- Worker nodes execute jobs.
- Master nodes eventually coordinate tenant-specific orchestration such as project decomposition, repo indexing, scheduling, retry policy, and OpenCode job planning.
- OpenCode CLI is the primary execution engine for coding work.
- The Tauri worker app is not the core runtime for this architecture. It may remain as reference code or a future tray/status UI, but it should not be expanded as the main local runtime.
- Broad direct database access by all workers is avoided. Workers should receive scoped job context and report results/events. Any master-side state access must be tenant-scoped and mediated by control-plane APIs.
- Auth will eventually use a modern CLI browser login flow with PKCE and a loopback callback.
- Local state will eventually use SQLite for durable daemon-local cache/state, plus a user-level config/data directory.
- This slice is additive scaffolding only. It does not replace the existing backend APIs, Tauri worker, Python worker, or dashboard.

## Consequences

### Positive

- Go provides a small, efficient, cross-platform daemon with simpler deployment and lower idle resource use than a long-running Node.js process.
- npm remains useful as a familiar installer/launcher without making Node.js the runtime architecture.
- Headless runtime keeps worker machines operationally simple and avoids duplicating dashboard UI locally.
- Local business orchestration reduces backend token waste and limits cloud-side coupling.

### Negative

- The Go runtime must eventually port or reimplement useful behavior from the Tauri/Rust worker app, including repo indexing, OpenCode execution, git workflow, job reporting, and safety controls.
- npm-based distribution still needs careful platform-specific binary handling in a later slice.
- Master lease semantics require backend-enforced fencing before real master orchestration can be safe.
- Existing paired workers will need an explicit migration path in a future slice.

## Deferred work

- Real browser/PKCE auth.
- Real daemon service installation/autostart.
- Real node registration/heartbeat APIs.
- Real master lease acquisition/renewal/release.
- Real OpenCode job execution.
- Local SQLite migrations.
- Migration from existing Python/Tauri worker credentials.

## Current foundation slice

This ADR accompanies an additive scaffold only:

- `cli/` npm launcher package.
- `node/` Go module foundation.
- `karkhana version`.
- `karkhana doctor`.
- `karkhana install --mode worker|master|master-worker` as a safe stub.
- `karkhana status` as a safe stub.

No real auth, OpenCode execution, master lease, service install, backend API change, or frontend change is implemented in this slice.
