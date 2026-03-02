# Karkhana Project Context (Agent Quickstart)

Last updated: 2026-03-01

## 1. Purpose

Karkhana is a local multi-agent software factory. It takes a raw product idea, runs a LangGraph pipeline of agents, and streams progress into a FastAPI dashboard over WebSocket.

Core intent from docs:
- PM generates PRD
- Architect generates stack + file tree
- Taskmaster queues files
- Coder writes files
- Reviewer validates code
- Sandbox executes checks

Important current reality:
- The pipeline currently generates code in memory and emits it to the dashboard.
- It does not persist generated files to `--output-dir`.

## 2. Tech Stack and Runtime

- Language: Python (project package is `src`)
- Orchestration: `langgraph`
- LLM client: `openai.AsyncOpenAI` pointed at LM Studio (`http://localhost:1234/v1`)
- API/UI backend: FastAPI + WebSocket
- CLI: Click
- Logging UI in terminal: Rich
- Packaging: `setup.py` with console entrypoint `karkhana=src.main:main`

Main dependencies (from `requirements.txt` / `setup.py`):
- `langgraph`, `openai`, `pydantic`, `pydantic-settings`
- `fastapi`, `uvicorn[standard]`, `websockets`
- `rich`, `click`
- `psutil`, `aiofiles`, `tiktoken`

## 3. How to Run

Install:
```bash
pip install -e .
```

Run CLI:
```bash
karkhana "Your idea"
```

Run with dashboard:
```bash
karkhana "Your idea" --dashboard
```

Equivalent module run:
```bash
python -m src.main "Your idea" --dashboard
```

Dashboard default URL:
- `http://127.0.0.1:8420`

## 4. Repository Layout (Actual)

Top-level:
- `README.md`: user-facing overview
- `architecture.md`: large design doc (partly aspirational/outdated)
- `setup.py`: package and console script config
- `requirements.txt`: dependency list
- `.env.example`: env template
- `agent_templates.json`: dynamic agent template data store
- `src/`: application code
- `examples/`: sample idea and structure notes
- `tests/`: currently only `__init__.py` (no active test suite)

Core source folders:
- `src/main.py`: CLI entrypoint, optional dashboard startup, workflow invoke
- `src/graph/flow.py`: LangGraph graph definition + nodes
- `src/agents/`: PM, Architect, Coder, Reviewer, dynamic/template helpers
- `src/dashboard/`: FastAPI server, EventBus bridge, static dashboard frontend
- `src/sandbox/`: subprocess sandbox executor + error parser
- `src/utils/`: prompts, parser helpers, logger, start script generator
- `src/types/`: `WorkingState`, project models, error models

## 5. End-to-End Pipeline Flow (Current Code)

Entry:
1. `src/main.py` receives `idea`, starts optional dashboard server thread.
2. Creates `WorkingState(raw_idea=idea, dashboard_mode=...)`.
3. Invokes `src.graph.flow.app.ainvoke(...)`.

Graph nodes (in `src/graph/flow.py`):
1. `start`
2. `pm_agent_1` and `pm_agent_2` (parallel branches)
3. `pm_consensus`
4. `architect_agent`
5. `taskmaster`
6. `coder_agent`
7. `reviewer_agent`
8. `sandbox_executor`
9. `END`

State/event behavior:
- Nodes emit stage events through `EventBus` for live dashboard updates.
- In dashboard mode, PRD and architecture stages block on human approval (`wait_for_approval`).
- Coder output is stored in state (`current_code`) and emitted as `code_generated`.
- Sandbox writes temp file and performs basic checks there.

## 6. Key Data Models

`src/types/state.py` (`WorkingState`):
- Input: `raw_idea`
- Planning fields: `prd_drafts`, `prd`, `tech_stack`, `file_tree`
- Execution fields: `current_file`, `current_code`
- Tracking: `completed_files` (set), `pending_files` (list), `error_log`
- Meta: `dashboard_mode`, timestamps, `llm_calls_count`

`src/types/error.py` (`ErrorLog`):
- `file_path`, `line_number`, `column`, `error_type`, `message`, `traceback_snippet`, `suggested_fix`

`src/types/project.py`:
- `ComponentSpec`, `FileTree`, `TechStack`

## 7. Agent Modules

Static pipeline agents:
- `PMAgent` (`src/agents/pm_agent.py`): generates JSON PRD
- `PMConsensusAgent` (`src/agents/pm_consensus.py`): merges multiple PRD drafts
- `ArchitectAgent` (`src/agents/architect_agent.py`): generates architecture/file tree JSON
- `Taskmaster` (`src/agents/taskmaster.py`): pending-file selection utilities
- `CoderAgent` (`src/agents/coder_agent.py`): generates code text or self-heal attempts
- `ReviewerAgent` (`src/agents/reviewer_agent.py`): LLM code review JSON (`passed`, `issues`)

Dynamic/custom agent system:
- `TemplateManager` uses `agent_templates.json` for CRUD templates
- `DynamicAgent` executes template-driven prompts
- `IdeaManager` persists ideas in `ideas.json`
- `WorkflowManager` persists workflows in `workflows.json`

## 8. Dashboard/API Surface

Server: `src/dashboard/server.py`

Transport:
- WebSocket: `/ws` (events + commands)
- Static dashboard: `/` and `/static/*`

Pipeline controls:
- `POST /api/build`
- `POST /api/build/stop`
- `GET /api/status`
- `POST /api/approve/{stage}`

Template/agent endpoints:
- `GET /api/templates`
- `POST /api/templates`
- `DELETE /api/templates/{template_id}`
- `POST /api/templates/generate`
- `POST /api/templates/{template_id}/run`

Idea/workflow endpoints:
- `GET /api/ideas`
- `POST /api/ideas`
- `DELETE /api/ideas/{idea_id}`
- `GET /api/workflows`
- `POST /api/workflows`
- `DELETE /api/workflows/{workflow_id}`
- `POST /api/workflows/{workflow_id}/run/{idea_id}`

Frontend assets:
- `src/dashboard/static/index.html`
- `src/dashboard/static/app.js`
- `src/dashboard/static/style.css`

## 9. Configuration

Environment template in `.env.example` includes:
- `LM_STUDIO_BASE_URL`
- `LM_STUDIO_MODEL_NAME`
- `MAX_TOKENS`
- `TEMPERATURE_CREATIVE`
- `TEMPERATURE_CODING`
- `TIMEOUT_SECONDS`
- `MAX_RETRIES`
- `SANDBOX_TIMEOUT`
- `MAX_RETRIES_PER_FILE`

Config code:
- `src/config.py` defines `LMStudioConfig`, `SandboxConfig`, `AppConfig`.

Important mismatch:
- `BaseAgent` currently hardcodes LM Studio base URL/model defaults and does not read `src.config.config`.

## 10. Current Known Gaps and Behavioral Notes

High-impact implementation gaps:
- `--output-dir` is logged but not used for actual file writes.
- Generated code is not persisted to a project tree; it is only carried in state and dashboard events.
- `completed_files` is set immediately after code generation, before review/sandbox passes.
- Sandbox for non-Python files currently runs `echo "Syntax check passed"` (no real JS/TS lint/test).
- `extract_json` parser is naive for nested/complex JSON and may fail on rich outputs.
- No substantive tests are currently present in `tests/`.

Operational behavior:
- Base LLM calls are serialized with a class-level async lock to reduce local OOM risk.
- EventBus is a singleton with in-memory event history and approval gates.
- Idea/workflow/template stores are JSON files in repo root; no locking/DB layer.

Repo hygiene observations:
- Working tree is currently dirty with many pre-existing modified/untracked files.
- There is a suspicious zero-byte artifact: `CUserscauldOneDriveDocumentskarkhana.env.example`.

## 11. Quick File Reference

Primary execution files:
- `src/main.py`
- `src/graph/flow.py`
- `src/types/state.py`
- `src/agents/base.py`
- `src/dashboard/server.py`
- `src/dashboard/event_bus.py`

Prompt and parsing behavior:
- `src/utils/prompts.py`
- `src/utils/parser.py`

Sandbox behavior:
- `src/sandbox/executor.py`
- `src/sandbox/reporters.py`

Dynamic systems:
- `src/agents/dynamic_agent.py`
- `src/agents/template_manager.py`
- `src/agents/ideas_manager.py`
- `src/agents/workflow_manager.py`
- `agent_templates.json`

## 12. Suggested Next Work (for Future Agents)

If the goal is "factory outputs real projects", start here:
1. Implement actual file persistence pipeline using `output_dir`.
2. Gate `completed_files` on successful reviewer + sandbox results.
3. Upgrade sandbox checks for JS/TS to real lint/type/test commands.
4. Wire all runtime config to `src/config.py` instead of hardcoded values.
5. Add real test coverage for graph transitions, EventBus gating, and file output.

## 13. Agent Comms Foundation (Week 1)

Week 1 added persistence and read APIs for autonomous inter-agent communication, without changing graph runtime behavior.

Implemented:

- New SQLite table in `src/command_center/db.py`:
  - `agent_messages(id, job_id, from_agent, to_agent, message_type, topic, content_json, status, blocking, created_at, resolved_at)`
- New protocol DTOs in `src/command_center/models.py`:
  - `AgentMessage`
  - `ClarificationRequest`
  - `DependencyApprovalRequest`
  - `FeatureChangeRequest`
  - `AgentDecision`
- New `WorkingState` fields in `src/types/state.py`:
  - `agent_inbox`, `agent_outbox`
  - `pending_agent_requests`, `resolved_agent_requests`
  - `coordination_rounds`, `coordination_budget`, `agent_blocked_reason`
- New Command Center endpoints in `src/dashboard/server.py`:
  - `GET /api/command-center/jobs/{job_id}/agent-messages`
  - `GET /api/command-center/jobs/{job_id}/agent-messages/pending`
  - `POST /api/command-center/jobs/{job_id}/agent-messages/{message_id}/resolve`
- New WebSocket event contracts in `src/dashboard/event_bus.py`:
  - `agent_message_created`
  - `agent_message_resolved`
  - `agent_message_escalated`

Feature flag baseline:

- `AGENT_COMMS_ENABLED=false` default added in `.env.example` and `src/config.py`.

Important Week 1 boundary:

- No orchestration/graph flow behavior changes were introduced for agent-to-agent runtime coordination yet.
- Runtime wiring is deferred to Week 2 and marked with `TODO(agent-comms-w2)` in graph/agent files.

## 14. Agent Comms Runtime (Week 2)

Week 2 enabled runtime inter-agent coordination in the LangGraph flow, gated behind feature flags.

Implemented runtime behavior:

- New graph nodes in `src/graph/flow.py`:
  - `agent_coordinator`
  - `agent_resolution`
  - `agent_escalation`
- New routing:
  - after `architect_agent`
  - before `coder_agent` (from `taskmaster` pending branch)
  - after `reviewer_agent` when reviewer emits requests
- Request dedupe + budget controls:
  - dedupe fingerprinting in `src/graph/agent_comms.py`
  - budget/round tracking via `coordination_budget` + `coordination_rounds`
  - unresolved handling:
    - blocking + budget remaining -> retry coordination
    - blocking + budget exhausted -> escalate
    - non-blocking unresolved -> warn and continue

Feature flags (Week 2):

- `AGENT_COMMS_ENABLED` (default `false`)
- `AGENT_COMMS_MAX_ROUNDS` (default `8`)
- `AGENT_COMMS_ESCALATE_BLOCKING_ONLY` (default `true`)

Runtime emitters/handlers:

- Emitters:
  - `CoderAgent.generate_coordination_requests`
  - `ReviewerAgent.generate_coordination_requests`
  - `ArchitectAgent.generate_coordination_requests`
  - `Taskmaster.generate_coordination_requests`
- Resolvers (rule-based in Week 2 runtime helper):
  - PM scope clarifications
  - Architect dependency approvals
  - Reviewer dependency risk checks
  - Taskmaster sequencing clarifications

Service contract updates:

- `CommandCenterService.create_agent_message(..., round_number=...)`
- `CommandCenterService.resolve_agent_message(..., round_number=...)`
- `CommandCenterService.escalate_agent_message(..., round_number=...)`

WebSocket payload updates:

- `agent_message_*` events now include runtime `round` when available.
