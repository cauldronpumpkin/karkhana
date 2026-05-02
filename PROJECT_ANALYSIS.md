# Idea Refinery - ChatGPT Project Operating Brief

> Purpose: Use this file as the durable knowledge base for a ChatGPT Project that acts as a research partner, product strategist, project manager, and Codex task writer for Idea Refinery.
>
> This is not only an architecture summary. It is an operating manual for helping build the complete app with Codex as the implementation agent.
>
> Snapshot date: 2026-04-27
> Primary repo path: `C:\Users\cauld\Documents\idearefinery`
> Implementation agent: Codex
> Research/planning agent: ChatGPT Project

---

## 0. How ChatGPT Should Use This File

### Role

ChatGPT should act as the user's long-running research and planning partner for Idea Refinery. It should help decide what to build next, refine product direction, write implementation prompts for Codex, review tradeoffs, and keep the project moving toward a complete, useful app.

ChatGPT should not pretend this file is live runtime state. Treat it as a high-quality project snapshot. For current facts, ask Codex to inspect the repo, run tests, or check deployments.

### Working Model

- ChatGPT does product thinking, research, planning, sequencing, architecture review, and Codex prompt generation.
- Codex does code changes, repo inspection, terminal commands, tests, deployment commands, and verification.
- The user wants practical execution, not generic advice. When proposing work, include a Codex-ready task.
- Keep recommendations cost-conscious, privacy-aware, and aligned with serverless/pay-as-you-go infrastructure unless the user explicitly changes direction.

### Default Response Pattern

When the user asks what to do next:

1. Summarize the current project state in 3-6 bullets.
2. Identify the highest-leverage next task.
3. Explain why it matters.
4. Provide a copy-paste-ready Codex prompt.
5. Include verification criteria Codex should run.

When the user asks for implementation guidance:

1. Name the product outcome.
2. Name the affected modules or files if known.
3. State decisions and constraints.
4. Write a Codex prompt with ownership, expected changes, and tests.
5. Add "do not" guardrails for risky or ambiguous areas.

When the user asks for architecture advice:

1. Separate confirmed current design from assumptions.
2. Give 2-3 practical options.
3. Recommend one path.
4. Explain what Codex should inspect before changing code.

### Important: Current-State Refresh Protocol

Before making detailed claims about the current repo, ChatGPT should ask Codex to refresh facts with:

```powershell
cd C:\Users\cauld\Documents\idearefinery
Get-Content graphify-out\GRAPH_REPORT.md -TotalCount 220
git status --short --branch
```

If code changes are made in a Codex session, Codex should run:

```powershell
graphify update .
```

If `graphify-out\wiki\index.md` exists, Codex should prefer it for navigation. If not, `graphify-out\GRAPH_REPORT.md` is the fast map.

---

## 1. Product Vision

Idea Refinery is an AI-powered idea operating system. It helps a founder or team move from vague ideas to structured, researched, scored, and build-ready software projects.

The product should eventually answer:

- What ideas am I working on?
- Which ideas are worth building first?
- What stage is each idea in?
- What do we already know?
- What research is missing?
- What should Codex build next?
- What changed in the real codebase since the last session?
- Which local workers or coding agents can execute the next job?

### Core Product Loops

1. Capture an idea.
2. Clarify the problem, audience, differentiators, and MVP.
3. Research market and competition.
4. Score the idea across objective dimensions.
5. Generate a build-ready plan.
6. Import or connect a GitHub project when implementation already exists.
7. Track project health, work items, agent runs, commits, and progress.
8. Use Codex/local workers to implement the next task.
9. Feed results back into project memory.

### Target Users

- Solo founders with many software ideas.
- Builders who use AI coding agents and need better planning.
- Small teams that want structured ideation, research, and build handoff.
- Users who want a local/private execution model instead of pushing code execution into a hosted sandbox.

---

## 2. Settled Product Decisions

These decisions should be treated as defaults unless the user explicitly revisits them.

### Project Onboarding

- Existing GitHub repositories should be onboarded as first-class project twins, not as simple text-only ideas.
- Private repo access should default to GitHub App installation, not personal access tokens.
- Imported projects should preserve repo metadata, code index artifacts, health status, jobs, agent runs, and commit history.
- Generated changes should default to feature branches so humans can review them.

### Worker Model

- The web app and backend are the control plane.
- Local workers are the execution plane.
- Do not collapse coding execution into Lambda or the web app.
- Heavy code work should run on a user's machine through a local worker bridge.
- Async jobs are preferred for project indexing, worker execution, and long-running AI coding tasks.

### Worker Installer Direction

- The existing script-based worker setup is a baseline, not the final UX.
- The desired UX is a one-click installable app or installer.
- The installer should bootstrap dependencies where possible.
- Startup on reboot is part of done-ness.
- Joining an existing company or tenant should be tenant-scoped and approval-based.
- Separate Windows and macOS installer paths are acceptable if that gives a cleaner UX.
- Installer work should be self-tested on the target OS before being called complete.

### Infrastructure

- Prefer serverless/pay-as-you-go AWS services.
- Prior AWS direction used Lambda, API Gateway, DynamoDB, SQS, Route 53, ACM, and Amplify.
- Default region for Idea Refinery cloud work has been `us-east-1` unless the user changes it.
- Frontend hosting uses Amplify with app root `frontend`, build command `npm run build`, and output `dist`.
- `VITE_API_BASE_URL` is the environment-driven frontend API base URL.

### AI and Handoff

- Idea Refinery plans and instructs; Codex implements.
- Build handoff should generate strong implementation prompts, not vague inspiration.
- Research tasks are prompt-driven and can be executed by humans or external deep research tools.
- Phase advancement should be AI-suggested but human-approved.

---

## 3. Current Project Snapshot

### Graphify Snapshot

As of 2026-04-27, `graphify-out\GRAPH_REPORT.md` reported:

- 168 files and about 116,023 words.
- 1,285 nodes, 2,961 edges, and 110 communities.
- Top god nodes: `FileManager`, `get_repository()`, `DynamoDBRepository`, `MockLLMService`, `InMemoryRepository`, `MemoryService`, `LLMService`, `Repository`, `ScoringService`, and `utcnow()`.
- High-value communities include build handoff, worker orchestration, DynamoDB repository logic, chat, local worker registration, memory, relationships, research, scoring, project twin jobs, GitHub App integration, and web search.

Interpretation: the repo is now broad enough that navigation should begin from graph/community context before deep file reads.

### Git Status Note

At this snapshot, there was an existing uncommitted change in:

```text
worker-app/src-tauri/src/config.rs
```

Codex should not overwrite or revert it unless the user asks.

### Built Areas

The project already contains:

- FastAPI backend with routers for ideas, chat, phases, research, scoring, relationships, reports, memory, build handoff, GitHub, projects, worker jobs, local workers, and AI model listing.
- Repository abstraction with in-memory and DynamoDB implementations.
- Svelte 5 frontend with dashboard, chat, reports, actions, project twin, and local worker UI.
- Project twin backend for importing GitHub repos, indexing, tracking health, queueing jobs, and tracking runs/commits.
- Local worker backend APIs for registration, approval, token rotation, heartbeat, and job lifecycle.
- Legacy Python local worker scripts have been removed; the Tauri worker app is the real local worker, and `workers/karigar` remains the mock readiness harness.
- Tauri v2 worker desktop app in progress.
- CloudFormation infrastructure for Lambda/API Gateway/DynamoDB/SQS.
- Graphify knowledge graph output for code navigation.

### In Progress / Not Finished

- Worker desktop app is not yet the full desired one-click installer experience.
- Tenant/company-scoped worker onboarding needs more explicit UX and backend flow.
- Project indexing can become deeper and more useful.
- Project health checks need stronger real-world validation.
- Product-level progress tracking should become more visible in the app.
- ChatGPT/Idea Refinery/Codex workflow needs to be first-class: the product should know how to suggest and hand off next Codex tasks.

---

## 4. Architecture Overview

```text
Users
  |
  |-- Web App (Svelte 5 SPA)
  |     |-- ideas dashboard
  |     |-- phase-aware chat
  |     |-- research/actions/build queues
  |     |-- project twin status
  |     |-- local worker dashboard
  |
  |-- Worker App / Local Workers
        |-- claim jobs
        |-- run coding agents locally
        |-- push feature branches
        |-- report status and logs

FastAPI Backend
  |
  |-- REST APIs
  |-- WebSocket chat
  |-- services
  |-- repository abstraction
  |-- static frontend serving in production
  |
  |-- Data layer
        |-- in-memory dev/test repository
        |-- DynamoDB production repository
        |-- local filesystem artifacts through FileManager

AWS / Cloud
  |
  |-- Lambda + Mangum
  |-- API Gateway HTTP API
  |-- DynamoDB single table
  |-- SQS FIFO command/event queues
  |-- IAM + STS for worker credential leasing
  |-- Amplify frontend hosting
```

### Backend

- Language: Python 3.11+
- Framework: FastAPI
- Serverless adapter: Mangum
- Settings: Pydantic Settings
- AWS SDK: Boto3
- AI client: OpenAI-compatible APIs
- Auth/security: PyJWT, cryptography, hashed worker tokens

Key backend directories:

```text
backend/app/main.py
backend/app/config.py
backend/app/repository.py
backend/app/lambda_handler.py
backend/app/routers/
backend/app/services/
backend/tests/
```

### Frontend

- Framework: Svelte 5
- Build: Vite
- State: Svelte runes and component-local state
- Routing: lightweight SPA routing
- Markdown: Marked + DOMPurify
- Icons: Lucide Svelte
- Tests: Vitest + Testing Library, with Playwright available for E2E

Key frontend paths:

```text
frontend/src/App.svelte
frontend/src/lib/api.js
frontend/src/lib/components/
frontend/src/routes/
```

### Worker App

- Framework: Tauri v2
- Frontend: Svelte 5
- Backend: Rust
- Goal: installable local worker app that can pair with a tenant, run on startup, claim jobs, execute local coding agents, and report results.

Key worker app paths:

```text
worker-app/
worker-app/src/
worker-app/src-tauri/
scripts/idearefinery_worker.py
scripts/install_idearefinery_worker.ps1
```

### Infrastructure

Key infra paths:

```text
infra/cloudformation/idearefinery-backend.yaml
amplify.yml
```

Known Amplify defaults:

```text
appRoot: frontend
install: npm ci
build: npm run build
artifact output: frontend/dist
API env: VITE_API_BASE_URL
```

---

## 5. Domain Model

### Idea

The central entity.

Core fields include title, slug, description, current phase, status, source type, and timestamps.

### Phase System

Ideas move through 8 phases:

1. Capture
2. Clarify
3. Market Research
4. Competitive Analysis
5. Monetization
6. Feasibility
7. Tech Spec
8. Build

The phase engine should help the user move forward, but the user approves advancement.

### Scoring

Ideas are scored from 0-10 across:

- TAM
- Competition
- Feasibility
- Time-to-MVP
- Revenue
- Uniqueness
- Personal fit

Scores include rationale and can be manually overridden.

### Research

Research tasks contain prompts, topics, status, results, and integration summaries. The system generates targeted prompts and integrates findings, but the actual research may be run outside the app.

### Memory

Memory stores persistent context as global or idea-scoped entries. Categories include stage, issue, bug, note, constraint, and resource.

For the completed app, memory should become more visible and operational: it should help the app know what was decided, what is blocked, and what Codex should do next.

### Project Twin

A project twin is the app's representation of an imported GitHub repository. It tracks:

- GitHub owner/repo metadata.
- Installation and clone URLs.
- Default and active branches.
- Desired outcome and current status.
- Detected stack and test commands.
- Index status and health status.
- Last indexed commit.
- Open queue count.

### Code Index Artifact

Stores project analysis for an imported repo:

- File inventory.
- Manifests.
- Dependency graph.
- Route map.
- Test commands.
- Architecture summary.
- Risks and todos.
- Searchable chunks.

### Work Item

An async job for local workers. It tracks queue status, priority, worker claim, heartbeat, timeout, logs, branch name, results, and errors.

### Agent Run

Represents a specific AI/coding-agent execution tied to a work item. Tracks engine, model, prompt, output, and status.

### Project Commit

Tracks commits produced by workers, including branch, SHA, message, author, and work item.

### Local Worker

Represents a registered machine. Tracks display name, machine name, platform, engine, capabilities, config, token hash, status, and heartbeat.

---

## 6. Service Responsibilities

### Phase Engine

- Manages phase lifecycle.
- Evaluates readiness.
- Generates phase reports.
- Keeps human approval in the loop.

### Scoring Service

- Scores ideas across seven dimensions.
- Stores rationale.
- Computes composite scores.
- Compares ideas.
- Supports manual overrides.

### Research Service

- Generates research prompts.
- Creates tasks.
- Accepts results.
- Integrates research into structured summaries.

### Build Handoff Service

- Collects idea context, reports, research, scores, and memory.
- Generates a comprehensive planning prompt.
- Generates step-by-step build prompts.
- Tracks build progress.

Important product direction: build handoff should become Codex-native. Replace or supplement any "Prometheus" terminology with explicit support for Codex prompts, verification commands, and handoff summaries.

### Chat Service

- Provides phase-aware conversation for each idea.
- Uses current phase and idea context.
- Streams responses through WebSocket.
- Persists chat history.

### Project Twin Service

- Imports GitHub repos.
- Creates project twins.
- Enqueues reindex and worker jobs.
- Manages claim/heartbeat/complete/fail lifecycle.
- Tracks project health and commit history.

### Local Worker Service

- Handles registration and approvals.
- Verifies tokens.
- Rotates credentials.
- Tracks heartbeat.
- Processes worker events.

### Relationship Service

- Links ideas.
- Detects related ideas.
- Supports derive, merge, and split flows.

### Web Search Service

- Uses DuckDuckGo search with rate limiting and caching.
- Fetches readable page text.
- Should fail gracefully.

### LLM Service

- Supports OpenAI-compatible providers.
- Discovers models from `/models`.
- Can read local model/agent configuration.
- Supports sync and streaming completion.

### GitHub App Service

- Handles GitHub App installation metadata.
- Processes webhooks.
- Lists installation repos.
- Creates short-lived tokens.

---

## 7. Current Progress Tracker

Use this as the default "where are we?" view. Codex should refresh it from the repo before major planning sessions.

| Area | Status | Confidence | Notes |
| --- | --- | --- | --- |
| Core idea CRUD | Built | High | Backend and dashboard exist. |
| Phase workflow | Built | Medium | Needs more product polish and real usage validation. |
| Chat | Built | Medium | Phase-aware chat exists; quality depends on LLM prompts/context. |
| Research prompts | Built | Medium | Prompt-driven, not fully autonomous research execution. |
| Scoring | Built | Medium | Seven dimensions exist; scoring quality should be validated with real ideas. |
| Memory | Built | Medium | CRUD exists; product UX for memory-driven progress can improve. |
| Build handoff | Built | Medium | Needs Codex-first wording and stronger task/verification output. |
| GitHub App integration | Built | Medium | Needs live configuration verification before relying on it. |
| Project twin | Built | Medium | Import/status/jobs exist; indexing depth can improve. |
| Worker job lifecycle | Built | Medium | Claim/heartbeat/complete/fail flows exist. |
| Legacy Python worker | Built | Medium | Useful baseline, not final desired UX. |
| Tauri worker app | In progress | Medium | Desktop shell exists; installer/tenant onboarding likely incomplete. |
| One-click installer | Not complete | High | Explicit product requirement. |
| Tenant/company join flow | Not complete | High | Needs scoped approval flow. |
| AWS serverless backend | Implemented/planned | Medium | Verify live AWS before deployment claims. |
| Amplify frontend hosting | Implemented/planned | Medium | `amplify.yml` exists; verify live app/domain before changes. |
| E2E confidence | Partial | Medium | Tests exist, but current pass/fail should be refreshed. |

---

## 8. Best Next Workstreams

### Workstream A: Make ChatGPT-to-Codex Handoff First-Class

Goal: The product should generate Codex-ready tasks, not generic build prompts.

Why this matters: the user's actual implementation agent is Codex. The app should speak that workflow directly.

Likely changes:

- Rename or broaden "Prometheus" handoff language to Codex/agent handoff.
- Add prompt templates that include repo path, target files, constraints, tests, graphify refresh, and summary format.
- Add a UI affordance to copy a Codex task.
- Store Codex task history in memory/work items.

Codex prompt:

```text
In C:\Users\cauld\Documents\idearefinery, update the build handoff flow so it is Codex-first instead of Prometheus-first.

Start by reading graphify-out\GRAPH_REPORT.md and inspecting backend/app/services/build_handoff.py, backend/app/routers/build.py, and the frontend build/action components. Preserve existing API compatibility where practical, but update user-facing language and generated prompts so they produce Codex-ready implementation tasks.

Each generated Codex task should include: goal, repo path, context files to inspect, implementation constraints, expected deliverables, verification commands, graphify update requirement after code changes, and final response format.

Add or update tests for the backend service and any frontend rendering impacted. Do not remove existing build-progress behavior. Do not touch unrelated worker-app changes.

Run relevant backend tests, frontend tests/build if affected, and graphify update . after code changes.
```

Verification:

```powershell
python -m pytest backend/tests
cd frontend; npm test; npm run build
cd ..; graphify update .
```

### Workstream B: Progress Dashboard and "What Should I Do Next?"

Goal: The app should track project progress and suggest the next valuable task.

Why this matters: the user wants ChatGPT Project to track progress and suggest new things to work on. The product itself should eventually support that same loop.

Likely changes:

- Add a progress summary per idea/project.
- Compute blockers from memory, failed jobs, stale index status, missing scores, incomplete phases, and open research tasks.
- Add recommended next actions.
- Generate Codex-ready task prompts from next actions.

Codex prompt:

```text
In C:\Users\cauld\Documents\idearefinery, implement a lightweight "Next Actions" capability for ideas and project twins.

Start by reading graphify-out\GRAPH_REPORT.md and inspecting repository entities, memory service, project twin service, build handoff service, and dashboard/project twin frontend components.

Add backend logic that derives recommended next actions from existing state: incomplete phase, missing scores, pending research tasks, stale project index, failed work items, no worker connected, or incomplete build handoff. Expose this through an API endpoint and render it in the dashboard or project twin view.

Each next action should include title, reason, priority, suggested owner (user, ChatGPT, Codex, local worker), and an optional Codex-ready prompt.

Keep this as a small incremental feature. Do not introduce a new database unless necessary; use existing repository/memory/work item models where possible.

Add tests and run relevant verification. Run graphify update . after code changes.
```

### Workstream C: One-Click Worker Installer and Tenant Join

Goal: Make local worker onboarding feel like installing an app, then requesting to join a specific company/tenant.

Why this matters: local execution is a core differentiator, but script-based onboarding is not enough for non-expert users.

Likely changes:

- Define tenant/company join request model.
- Add UI for entering tenant/company invite or code.
- Route registration requests to the right tenant/admin.
- Package Windows installer path first.
- Ensure startup on reboot.
- Self-test install path.

Codex prompt:

```text
In C:\Users\cauld\Documents\idearefinery, design and implement the first narrow slice of tenant-scoped local worker onboarding.

Start by reading graphify-out\GRAPH_REPORT.md and inspecting backend/app/services/local_workers.py, backend/app/routers/local_workers.py, frontend local worker components, worker-app, and scripts/install_idearefinery_worker.ps1.

Do not treat the existing PowerShell script as the finished one-click installer. Use it as a baseline. Add the smallest backend/frontend model needed for a worker to request joining a specific company/tenant, and for an admin to approve that request in the proper tenant scope. If full auth/tenancy is not present, implement a narrow admin-first placeholder that is explicit and easy to evolve.

Preserve existing worker registration APIs where possible. Add tests. Do not revert existing uncommitted changes in worker-app/src-tauri/src/config.rs.

Run backend tests and relevant frontend tests/build. Run graphify update . after code changes.
```

### Workstream D: Improve Project Twin Indexing and Health

Goal: Make imported GitHub projects useful enough that the app can track real implementation progress.

Why this matters: project twins should tell the user what exists, what is broken, what changed, and what Codex should do next.

Likely changes:

- Capture richer manifests, test commands, routes, package scripts, and deployment hints.
- Track last indexed commit and staleness.
- Add health checks for build/test status.
- Link failed jobs and commits back to recommendations.

Codex prompt:

```text
In C:\Users\cauld\Documents\idearefinery, improve the project twin index and health summary.

Start by reading graphify-out\GRAPH_REPORT.md and inspecting backend/app/services/project_twin.py, repository models for CodeIndexArtifact/ProjectTwin/WorkItem, project routes, worker scripts, and frontend ProjectTwinView.

Implement a narrow enhancement that captures more actionable index metadata from a repository: package manifests, likely test/build commands, route hints, dependency risks, and todo markers. Surface the summary in the project twin UI and use it to flag whether the index is stale relative to the last known commit.

Keep the implementation incremental and testable. Add tests for the index extraction logic. Run relevant tests and graphify update . after code changes.
```

---

## 9. Codex Prompt Template

Use this template whenever ChatGPT writes an implementation task for Codex.

```text
You are working in C:\Users\cauld\Documents\idearefinery.

Goal:
[One clear outcome.]

Context:
- Read graphify-out\GRAPH_REPORT.md first.
- If graphify-out\wiki\index.md exists, use it for navigation.
- Relevant files/modules likely include: [paths].
- Existing decisions/constraints: [list].

Implementation requirements:
- [Requirement 1]
- [Requirement 2]
- [Requirement 3]

Guardrails:
- Do not revert unrelated user changes.
- Do not overwrite worker-app/src-tauri/src/config.rs unless this task explicitly requires it.
- Preserve existing API compatibility unless you explain why it must change.
- Keep AWS/serverless choices pay-as-you-go.
- Keep local worker execution separate from web/backend control plane.

Verification:
- Run: [commands].
- If code files changed, run graphify update .

Final response:
- Summarize what changed.
- List tests/commands run and results.
- Mention any remaining risks or follow-up work.
```

---

## 10. Verification Commands

Codex should choose the smallest relevant set, not always everything.

### Backend

```powershell
python -m pytest backend/tests
```

### Frontend

```powershell
cd frontend
npm test
npm run build
```

### E2E

```powershell
npx playwright test
```

### Worker App

```powershell
cd worker-app
npm run build
```

For Tauri/Rust changes, Codex should inspect available Cargo scripts and run the appropriate cargo checks from `worker-app\src-tauri`.

### Graph Refresh

```powershell
graphify update .
```

---

## 11. Known Risks and Debt

### Product Risks

- The app may have many features but not yet a crisp daily workflow.
- Build handoff language may still be too generic or too tied to older "Prometheus" naming.
- Project twin value depends on indexing quality and next-action recommendations.
- Worker onboarding may be too technical until the installer UX is real.

### Architecture Risks

- Dual local filesystem and DynamoDB persistence means cloud cutover is broader than one database adapter.
- Worker execution must stay separate from the backend to avoid security, cost, and sandboxing problems.
- Full tenancy/auth may not be complete; tenant-scoped worker onboarding needs careful incremental design.
- GitHub App flows require live app credentials and webhook setup; code presence alone does not prove production readiness.

### Implementation Risks

- Existing uncommitted user changes may exist. Codex must check status first.
- `rg.exe` can be blocked in this Windows environment; PowerShell `Get-ChildItem`, `Get-Content`, and `Select-String` are reliable fallbacks.
- Frontend icon imports from `lucide-svelte` should be verified before assuming an icon exists.
- Tests may need assertion updates when new background fetches or queue calls are introduced.

---

## 12. Research Topics for ChatGPT

Use these for strategic planning and product refinement.

### High Priority

- How should a solo-founder "idea operating system" decide the next best action?
- What is the simplest useful project health score for imported GitHub repos?
- What should a Codex-ready implementation prompt always include?
- How should local worker onboarding work for a non-technical teammate?
- How should memory be surfaced so the app feels aware of project history?

### Medium Priority

- Should project twins use AST indexing, vector search, or both?
- What model/provider routing should be used for research, planning, coding, and summarization?
- How should Idea Refinery compare ideas over time as new evidence arrives?
- How should failed worker runs feed into next recommendations?
- What is the minimum viable tenant model?

### Later

- Team collaboration and roles.
- Idea marketplace or reusable project templates.
- Integrations with Notion, Jira, Figma, Linear, Slack, or GitHub Projects.
- Direct PR creation and review loops.
- Automated deployment pipeline tracking.

---

## 13. Suggested ChatGPT Project Instructions

If the ChatGPT Project has a separate instruction field, use this:

```text
You are the research and planning partner for the Idea Refinery app. Use the uploaded project brief as your durable context, but treat it as a snapshot, not live repo state.

Your job is to help the user decide what to build next, refine product and architecture decisions, and write excellent implementation prompts for Codex. Codex is the coding agent and has access to the real repo at C:\Users\cauld\Documents\idearefinery.

When implementation is needed, produce Codex-ready prompts with: goal, repo path, context files, constraints, deliverables, verification commands, graphify refresh requirement, and final response format.

Default decisions: GitHub App for project onboarding, full project twins, feature branches for generated changes, async jobs, local worker execution bridge, serverless/pay-as-you-go AWS, and Codex-first build handoff.

Do not claim current test/deployment status unless Codex has just verified it. Ask Codex to inspect graphify-out\GRAPH_REPORT.md and run relevant tests before relying on current repo facts.

Prefer practical next actions over generic advice. If the user asks what to do next, recommend one highest-leverage task and provide the Codex prompt to execute it.
```

---

## 14. Modification History

| Date | Change |
| --- | --- |
| 2026-04-27 | Reworked from a static architecture report into a ChatGPT Project operating brief with progress tracking, Codex handoff templates, settled decisions, and prioritized workstreams. |
