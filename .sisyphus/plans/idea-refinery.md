# Idea Refinery — Collaborative AI-Human Idea Pipeline

## TL;DR

> **Quick Summary**: Build a localhost-first web application (FastAPI + Svelte + SQLite) that enables collaborative AI-human idea refinement. Users chat with an AI agent through codex-lb/OpenCode, asks questions, does research, delegates Gemini Deep Research tasks, scores ideas, and generates step-by-step Prometheus prompts when ideas are ready to build.
> 
> **Deliverables**:
> - FastAPI backend with REST API + WebSocket chat
> - Svelte frontend (Vite-built, served by FastAPI)
> - SQLite database + per-idea folder structure
> - LLM integration (codex-lb/OpenCode, OpenAI-compatible)
> - Web search (OpenAI-compatible tools → DuckDuckGo fallback)
> - Per-idea chat sessions with AI-driven phase progression
> - Gemini Deep Research prompt generation + result upload
> - 7-dimension numeric scoring system
> - Rich idea relationships (merge, split, derive)
> - Reports viewer + Actions panel
> - Desktop shortcut for one-click launch
> - Global + per-idea project memory (stage, issues, bugs)
> 
> **Estimated Effort**: XL (full-stack web application with LLM integration)
> **Parallel Execution**: YES - 4 waves
> **Critical Path**: Project scaffolding → SQLite models → LLM service → Chat API → Chat UI → Phase engine → Build handoff

---

## Context

### Original Request
User wanted a collaborative pipeline where AI and human collaborate to refine ideas before building software. Initially conceived as an Oh My OpenCode skill, pivoted to a full standalone GUI web application with FastAPI backend + Svelte frontend.

### Interview Summary
**Key Discussions**:
- **Direction pivot**: OMC skill → full web app with dedicated chat interface
- **Human role**: Copy-paster and Gemini DR doer ONLY. AI orchestrates everything.
- **Phase progression**: AI suggests advancement, human approves
- **Scoring**: All 7 dimensions (TAM, Competition, Feasibility, Time-to-MVP, Revenue, Uniqueness, Personal Fit)
- **Idea relationships**: Rich — merge, split, derive from each other
- **Build handoff**: Step-by-step prompts for Prometheus, human copies manually
- **Project memory**: Both global + per-idea tracking

**Research Findings**:
- codex-lb is OpenAI-compatible at `http://127.0.0.1:2455/v1`
- codex-lb/OpenCode is the configured model path for local development
- Svelte with Vite builds to static files servable by FastAPI
- Oh My OpenCode graphify skill provided pattern reference (multi-step pipeline, file-based state)

### Self-Performed Gap Analysis (Metis timeout compensation)
**Identified Gaps** (addressed):
- **LLM streaming**: Chat requires streaming responses (SSE or WebSocket) — included in plan
- **Error handling for LLM failures**: API timeout, rate limits, invalid responses — included as guardrail
- **Chat history persistence**: Need to store full conversation per idea in SQLite — included in DB design
- **System prompt design**: The AI needs a carefully crafted system prompt that knows the idea context — included as a task
- **Markdown rendering in chat**: User specifically requested correct MD formatting — included in frontend task
- **File upload security**: Validate uploaded files, size limits — included as guardrail
- **Concurrent chat sessions**: Multiple ideas might be chatted with simultaneously — WebSocket design addresses this
- **Desktop shortcut on Windows**: .bat file that starts FastAPI + opens browser — included as task
- **Phase state machine**: Need clear rules for phase transitions — included in phase engine task

---

## Work Objectives

### Core Objective
Build a localhost web application where a human collaborates with an AI agent to take vague ideas through a structured refinement pipeline (8 phases) ending with step-by-step build prompts for Prometheus.

### Concrete Deliverables
- `backend/` — FastAPI application with all API endpoints
- `frontend/` — Svelte application built by Vite to static files
- `data/` — SQLite database + per-idea folder structure
- `start.bat` — Desktop shortcut for one-click launch
- `.env.example` — Template for API key configuration

### Definition of Done
- [ ] `start.bat` launches app and opens browser at localhost:8000
- [ ] User can create a new idea with vague description
- [ ] Chat interface sends messages to AI and receives streamed responses with correct markdown rendering
- [ ] AI asks clarifying questions and recognizes when to advance phases
- [ ] Gemini DR prompts are generated and saved to idea's research folder
- [ ] User can upload markdown/text research results
- [ ] AI reads uploaded research and integrates findings
- [ ] Ideas are scored on all 7 dimensions
- [ ] Ideas can reference, merge, split from each other
- [ ] Reports are generated per phase and viewable in Reports section
- [ ] Build phase generates step-by-step Prometheus prompts
- [ ] Project memory (stage, issues, bugs) tracked globally and per-idea

### Must Have
- Per-idea chat sessions with streaming LLM responses
- Phase progression engine (8 phases) with AI-suggested, human-approved advancement
- Gemini DR prompt generation + result upload + AI integration
- 7-dimension numeric scoring
- Idea relationships (merge, split, derive)
- Reports section with per-phase markdown documents
- Actions section showing pending Gemini DR tasks
- Desktop shortcut for one-click launch
- Global + per-idea project memory

### Must NOT Have (Guardrails)
- **No CLI interface** — GUI only
- **No OMC skill format** — standalone app
- **No authentication system** — localhost only, single user
- **No paid external APIs** — ZAI API key is the user's existing plan, web search uses free tier
- **No Docker/Kubernetes** — simple localhost execution
- **No multi-user support** — single user
- **No CI/CD pipeline** — development tool, not production deployment
- **No PDF/DOCX parsing** — markdown/text only for Gemini DR uploads
- **No mobile responsive design** — desktop browser only
- **No auto-invocation of Prometheus** — human copies prompts manually
- **AI slop patterns to avoid**: Over-abstracted services, unnecessary middleware layers, excessive error handling for happy paths, generic variable names (data/result/item), excessive comments explaining obvious code

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** - ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: NO (new project)
- **Automated tests**: YES (tests after implementation)
- **Framework**: pytest (FastAPI) + vitest (Svelte)
- **Test setup included as a task**: YES

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Frontend/UI**: Use Playwright — Navigate, interact, assert DOM, screenshot
- **API/Backend**: Use Bash (curl) — Send requests, assert status + response fields
- **Integration**: Use Playwright — Full user workflows through the GUI

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Foundation — start immediately):
├── Task 1: Project scaffolding + config [quick]
├── Task 2: SQLite database models + migrations [quick]
├── Task 3: Svelte project setup + design system [visual-engineering]
├── Task 4: LLM service layer (OpenAI-compatible client) [quick]
└── Task 5: File structure + idea folder management [quick]

Wave 2 (Core services — after Wave 1):
├── Task 6: Chat API + WebSocket streaming (depends: 2, 4) [deep]
├── Task 7: Phase engine + state machine (depends: 2) [deep]
├── Task 8: Web search service (depends: 4) [unspecified-high]
├── Task 9: Gemini DR prompt generator (depends: 2, 5) [quick]
├── Task 10: Scoring engine — 7 dimensions (depends: 2) [unspecified-high]
├── Task 11: Chat UI component (depends: 3, 6) [visual-engineering]
└── Task 12: Ideas dashboard + management UI (depends: 3, 2) [visual-engineering]

Wave 3 (Integration + advanced features — after Wave 2):
├── Task 13: Research upload + integration service (depends: 5, 9) [unspecified-high]
├── Task 14: Idea relationships service (depends: 2) [unspecified-high]
├── Task 15: Reports section UI (depends: 12, 7) [visual-engineering]
├── Task 16: Actions panel UI (depends: 12, 9) [visual-engineering]
├── Task 17: Project memory service (depends: 2, 7) [unspecified-high]
├── Task 18: Build handoff — Prometheus prompt generator (depends: 7, 10) [deep]
└── Task 19: Desktop shortcut + launch script (depends: all backend+frontend) [quick]

Wave 4 (Testing + polish — after Wave 3):
├── Task 20: Backend test suite (depends: 6, 7, 8, 9, 10, 13, 14, 17, 18) [unspecified-high]
├── Task 21: Frontend test suite (depends: 11, 12, 15, 16) [unspecified-high]
├── Task 22: Integration/E2E tests (depends: 20, 21) [unspecified-high]
└── Task 23: Desktop shortcut + launch script (depends: 19, 22) [quick]

Wave FINAL (After ALL tasks — 4 parallel reviews):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high + playwright)
└── Task F4: Scope fidelity check (deep)
→ Present results → Get explicit user okay

Critical Path: Task 1 → Task 2 → Task 6 → Task 11 → Wave 3 → Wave 4 → FINAL
Parallel Speedup: ~60% faster than sequential
Max Concurrent: 7 (Wave 2)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | - | 2, 3, 4, 5 | 1 |
| 2 | 1 | 6, 7, 9, 10, 12, 14, 17 | 1 |
| 3 | 1 | 11, 12, 15, 16 | 1 |
| 4 | 1 | 6, 8 | 1 |
| 5 | 1 | 9, 13 | 1 |
| 6 | 2, 4 | 11, 20 | 2 |
| 7 | 2 | 15, 17, 18, 20 | 2 |
| 8 | 4 | 20 | 2 |
| 9 | 2, 5 | 13, 16, 20 | 2 |
| 10 | 2 | 18, 20 | 2 |
| 11 | 3, 6 | 21 | 2 |
| 12 | 3, 2 | 15, 16, 21 | 2 |
| 13 | 5, 9 | 20 | 3 |
| 14 | 2 | 20 | 3 |
| 15 | 12, 7 | 21 | 3 |
| 16 | 12, 9 | 21 | 3 |
| 17 | 2, 7 | 20 | 3 |
| 18 | 7, 10 | 20 | 3 |
| 19 | all | 23 | 3 |
| 20 | 6,7,8,9,10,13,14,17,18 | 22 | 4 |
| 21 | 11,12,15,16 | 22 | 4 |
| 22 | 20, 21 | 23 | 4 |
| 23 | 19, 22 | - | 4 |

### Agent Dispatch Summary

- **Wave 1**: **5** — T1 → `quick`, T2 → `quick`, T3 → `visual-engineering`, T4 → `quick`, T5 → `quick`
- **Wave 2**: **7** — T6 → `deep`, T7 → `deep`, T8 → `unspecified-high`, T9 → `quick`, T10 → `unspecified-high`, T11 → `visual-engineering`, T12 → `visual-engineering`
- **Wave 3**: **7** — T13 → `unspecified-high`, T14 → `unspecified-high`, T15 → `visual-engineering`, T16 → `visual-engineering`, T17 → `unspecified-high`, T18 → `deep`, T19 → `quick`
- **Wave 4**: **4** — T20 → `unspecified-high`, T21 → `unspecified-high`, T22 → `unspecified-high`, T23 → `quick`
- **FINAL**: **4** — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 1. Project Scaffolding + Configuration

  **What to do**:
  - Create project directory structure: `backend/`, `frontend/`, `data/`, `data/ideas/`
  - Initialize Python project with `pyproject.toml` (FastAPI, uvicorn, openai, python-dotenv, httpx, sqlalchemy, aiosqlite)
  - Create `.env.example` with `CODEX_LB_API_KEY=`, `CODEX_LB_API_BASE_URL=http://127.0.0.1:2455/v1`, `CODEX_LB_MODEL=gpt-5.5`
  - Create FastAPI app skeleton in `backend/app/main.py` with CORS middleware (localhost:5173 for dev, localhost:8000 for prod)
  - Create `backend/app/config.py` that loads settings from `.env` using pydantic-settings
  - Create `requirements.txt` or use pyproject.toml deps
  - Initialize Svelte project in `frontend/` using `npm create vite@latest frontend -- --template svelte`
  - Create `start.bat` placeholder (will be completed in Task 23)
  - Create `.gitignore` (node_modules, __pycache__, data/*.db, .env, frontend/dist/)

  **Must NOT do**:
  - No Docker setup
  - No CI/CD pipeline
  - No authentication middleware

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4, 5)
  - **Blocks**: Tasks 2, 3, 4, 5
  - **Blocked By**: None

  **References**:
  - FastAPI project structure: standard `backend/app/main.py` pattern
  - codex-lb API config: `http://127.0.0.1:2455/v1`
  - Vite Svelte template: `npm create vite@latest frontend -- --template svelte`

  **Acceptance Criteria**:
  - [ ] `backend/app/main.py` exists and starts with `uvicorn backend.app.main:app`
  - [ ] `frontend/` contains a working Svelte project (npm install + npm run build succeeds)
  - [ ] `.env.example` exists with CODEX_LB_API_KEY, CODEX_LB_API_BASE_URL, CODEX_LB_MODEL
  - [ ] `.gitignore` covers node_modules, __pycache__, data/*.db, .env, frontend/dist/

  **QA Scenarios**:

  ```
  Scenario: Backend starts successfully
    Tool: Bash
    Preconditions: .env file exists with CODEX_LB_API_KEY when proxy auth is enabled
    Steps:
      1. Run: uvicorn backend.app.main:app --port 8000 (start in background)
      2. Run: curl http://localhost:8000/api/health
      3. Assert: response contains {"status": "ok"}
      4. Kill the uvicorn process
    Expected Result: FastAPI responds with health check
    Failure Indicators: Connection refused, import errors, module not found
    Evidence: .sisyphus/evidence/task-1-backend-start.txt

  Scenario: Frontend builds to static files
    Tool: Bash
    Preconditions: frontend/ directory exists with package.json
    Steps:
      1. Run: cd frontend && npm install
      2. Run: cd frontend && npm run build
      3. Assert: frontend/dist/ directory exists with index.html
    Expected Result: Static files generated in frontend/dist/
    Failure Indicators: Build errors, missing dist/ directory
    Evidence: .sisyphus/evidence/task-1-frontend-build.txt
  ```

  **Commit**: YES
  - Message: `feat(scaffold): project scaffolding with FastAPI + Svelte + SQLite config`
  - Files: `backend/`, `frontend/`, `.env.example`, `.gitignore`, `pyproject.toml`

- [x] 2. SQLite Database Models + Migrations

  **What to do**:
  - Create `backend/app/database.py` with SQLAlchemy async engine + session factory for SQLite
  - Define models in `backend/app/models/`:
    - `idea.py`: Idea model (id UUID, title, slug, description, current_phase enum, created_at, updated_at, status active/archived/killed)
    - `phase.py`: PhaseRecord model (id, idea_id FK, phase enum [capture/clarify/market_research/competitive_analysis/monetization/feasibility/tech_spec/build], started_at, completed_at, notes JSON)
    - `score.py`: Score model (id, idea_id FK, dimension enum [tam/competition/feasibility/time_to_mvp/revenue/uniqueness/personal_fit], value float 0-10, rationale text, scored_at)
    - `message.py`: Message model (id, idea_id FK, role enum [user/assistant/system], content text, timestamp, metadata JSON)
    - `relationship.py`: IdeaRelationship model (id, source_idea_id FK, target_idea_id FK, relation_type enum [merge/split/derive/reference], description, created_at)
    - `research.py`: ResearchTask model (id, idea_id FK, prompt_text, status enum [pending/submitted/completed], result_file_path, created_at, completed_at)
    - `memory.py`: ProjectMemory model (id, idea_id FK nullable, key, value text, category enum [stage/issue/bug/note], created_at, updated_at)
    - `report.py`: Report model (id, idea_id FK, phase, title, content_path markdown file, generated_at)
  - Create `backend/app/models/__init__.py` that exports all models
  - Create `backend/app/init_db.py` script to initialize DB with tables
  - Database file location: `data/idearefinery.db`
  - Use Alembic or simple create_all() for migrations (simple create_all is fine for localhost-first)

  **Must NOT do**:
  - No PostgreSQL/MySQL — SQLite only
  - No complex migration framework — keep it simple

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4, 5)
  - **Blocks**: Tasks 6, 7, 9, 10, 12, 14, 17
  - **Blocked By**: Task 1

  **References**:
  - SQLAlchemy async with aiosqlite: standard pattern for FastAPI + SQLite
  - Phase enum values: capture, clarify, market_research, competitive_analysis, monetization, feasibility, tech_spec, build
  - Score dimensions: tam, competition, feasibility, time_to_mvp, revenue, uniqueness, personal_fit

  **Acceptance Criteria**:
  - [ ] All models defined with correct fields and relationships
  - [ ] `python backend/app/init_db.py` creates `data/idearefinery.db` with all tables
  - [ ] Foreign keys correctly reference ideas table
  - [ ] Enums use string values for readability

  **QA Scenarios**:

  ```
  Scenario: Database initializes with all tables
    Tool: Bash
    Preconditions: Python dependencies installed
    Steps:
      1. Run: python backend/app/init_db.py
      2. Run: sqlite3 data/idearefinery.db ".tables"
      3. Assert: output contains ideas, phase_records, scores, messages, idea_relationships, research_tasks, project_memories, reports
    Expected Result: All 8 tables created
    Failure Indicators: Missing tables, foreign key errors, SQL errors
    Evidence: .sisyphus/evidence/task-2-db-tables.txt

  Scenario: Model CRUD operations work
    Tool: Bash
    Preconditions: Database initialized
    Steps:
      1. Run Python script that creates an idea, adds a phase record, adds a score, adds a message
      2. Query back all records and verify they exist
      3. Assert: idea has title, phase record linked, score value 7.5, message content matches
    Expected Result: All CRUD operations succeed
    Failure Indicators: Integrity errors, foreign key violations
    Evidence: .sisyphus/evidence/task-2-crud-test.txt
  ```

  **Commit**: YES
  - Message: `feat(db): SQLite models for ideas, phases, scores, messages, relationships`
  - Files: `backend/app/database.py`, `backend/app/models/`, `backend/app/init_db.py`

- [x] 3. Svelte Project Setup + Design System

  **What to do**:
  - Set up Svelte project in `frontend/` with Vite
  - Install dependencies: `svelte`, `@sveltejs/vite-plugin-svelte`, `marked` (markdown rendering), `dompurify` (sanitize HTML)
  - Create base layout in `frontend/src/lib/components/Layout/`:
    - `AppShell.svelte` — sidebar navigation + main content area
    - `Sidebar.svelte` — navigation links (Dashboard, Chat, Reports, Actions, Settings placeholder)
  - Create base UI components in `frontend/src/lib/components/UI/`:
    - `Button.svelte`, `Input.svelte`, `Card.svelte`, `Badge.svelte`, `Modal.svelte`
  - Create global CSS with design tokens (colors, spacing, typography) in `frontend/src/app.css`
  - Dark theme as default (developer tool aesthetic)
  - Configure Vite to build to `frontend/dist/` (FastAPI will serve these)
  - Set up API client in `frontend/src/lib/api.js` with base URL from environment
  - Create page stubs: `Dashboard.svelte`, `ChatView.svelte`, `Reports.svelte`, `Actions.svelte`

  **Must NOT do**:
  - No Tailwind CSS — keep it lightweight with custom CSS
  - No component library (MUI, etc.) — hand-roll minimal components
  - No SSR — pure SPA
  - No mobile responsive design — desktop only

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: [`/frontend-ui-ux`]
    - `/frontend-ui-ux`: Domain overlap — building UI components and design system from scratch

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4, 5)
  - **Blocks**: Tasks 11, 12, 15, 16
  - **Blocked By**: Task 1

  **References**:
  - Vite Svelte config: standard `vite.config.js` with `@sveltejs/vite-plugin-svelte`
  - `marked` library for markdown rendering: `https://marked.js.org/`
  - `dompurify` for HTML sanitization: `https://github.com/cure53/DOMPurify`
  - Design aesthetic: developer tool (dark theme, monospace accents, clean layout)

  **Acceptance Criteria**:
  - [ ] `npm run build` produces `frontend/dist/index.html`
  - [ ] Sidebar navigation renders with all 4 sections
  - [ ] Base UI components (Button, Input, Card, Badge, Modal) render correctly
  - [ ] Global CSS establishes consistent design tokens
  - [ ] API client configured with correct base URL

  **QA Scenarios**:

  ```
  Scenario: Frontend builds and renders correctly
    Tool: Playwright
    Preconditions: frontend/dist/ built, FastAPI serving static files
    Steps:
      1. Navigate to http://localhost:8000
      2. Assert: sidebar is visible with navigation items (Dashboard, Chat, Reports, Actions)
      3. Assert: dark theme applied (background is dark color)
      4. Click each nav item and verify page stub loads
    Expected Result: App loads with dark theme, sidebar navigation works
    Failure Indicators: White screen, missing sidebar, 404 on navigation
    Evidence: .sisyphus/evidence/task-3-frontend-render.png

  Scenario: UI components render correctly
    Tool: Playwright
    Preconditions: App running
    Steps:
      1. Navigate to dashboard page
      2. Assert: Button component visible and clickable
      3. Assert: Card component renders with content
      4. Assert: Badge component shows text
    Expected Result: All base UI components render correctly
    Failure Indicators: Missing components, styling broken
    Evidence: .sisyphus/evidence/task-3-components.png
  ```

  **Commit**: YES
  - Message: `feat(ui): Svelte project setup with design system and base layout`
  - Files: `frontend/`

- [x] 4. LLM Service Layer (OpenAI-Compatible Client)

  **What to do**:
  - Create `backend/app/services/llm.py` with `LLMService` class
  - Use the `openai` Python package (OpenAI-compatible)
  - Initialize with `base_url=http://127.0.0.1:2455/v1` and API key from `.env` or OpenCode config
  - Model: `gpt-5.5` (configurable via env)
  - Implement methods:
    - `async chat_completion(messages: list[dict], stream: bool = True) -> AsyncGenerator[str, None]` — streaming chat
    - `async chat_completion_sync(messages: list[dict]) -> str` — non-streaming for quick tasks
  - Create `backend/app/services/system_prompts.py` with system prompt templates:
    - `IDEA_REFINERY_SYSTEM`: Base system prompt explaining the AI's role as idea refiner
    - `PHASE_PROMPTS`: Dict mapping each phase to specific instructions for that phase
    - `SCORING_PROMPT`: Instructions for scoring an idea on 7 dimensions
    - `RESEARCH_INTEGRATION_PROMPT`: Instructions for integrating uploaded research
  - Handle errors: API timeout (30s default), rate limits (retry with backoff), invalid response
  - Create `backend/app/services/__init__.py`

  **Must NOT do**:
  - No custom HTTP client — use the official `openai` package
  - No prompt caching — keep it simple
  - No function calling / tool use — just chat completions

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 5)
  - **Blocks**: Tasks 6, 8
  - **Blocked By**: Task 1

  **References**:
  - OpenAI Python client: `pip install openai` — use `OpenAI(base_url=..., api_key=...)`
  - codex-lb API endpoint: `http://127.0.0.1:2455/v1`
  - Streaming: `client.chat.completions.create(..., stream=True)` returns async iterator of chunks
  - System prompt should know: idea context, current phase, research findings, scores, relationships

  **Acceptance Criteria**:
  - [ ] `LLMService` initializes with ZAI API config
  - [ ] `chat_completion` streams response chunks as AsyncGenerator
  - [ ] `chat_completion_sync` returns complete string response
  - [ ] System prompt templates cover all 8 phases + scoring + research integration
  - [ ] Error handling for timeout, rate limit, invalid response

  **QA Scenarios**:

  ```
  Scenario: LLM service returns streaming response
    Tool: Bash (curl + Python)
    Preconditions: .env or OpenCode config with valid codex-lb credentials
    Steps:
      1. Run Python script: create LLMService, call chat_completion with [{"role": "user", "content": "Hello"}]
      2. Collect all chunks and verify non-empty response
      3. Assert: response contains text content
    Expected Result: Streaming response received with content
    Failure Indicators: API error, empty response, connection refused
    Evidence: .sisyphus/evidence/task-4-llm-stream.txt

  Scenario: LLM service handles API error gracefully
    Tool: Bash (Python)
    Preconditions: .env with INVALID_API_KEY
    Steps:
      1. Run Python script with invalid API key
      2. Call chat_completion_sync
      3. Assert: raises appropriate error (AuthenticationError or similar)
    Expected Result: Error is caught and handled gracefully
    Failure Indicators: Unhandled exception, crash
    Evidence: .sisyphus/evidence/task-4-llm-error.txt
  ```

  **Commit**: YES
  - Message: `feat(llm): OpenAI-compatible LLM client for codex-lb`
  - Files: `backend/app/services/llm.py`, `backend/app/services/system_prompts.py`, `backend/app/services/__init__.py`

- [x] 5. File Structure + Idea Folder Management

  **What to do**:
  - Create `backend/app/services/file_manager.py` with `FileManager` class
  - Define idea folder structure:
    ```
    data/ideas/
    └── {idea-slug}/
        ├── state.json          # Phase, scores, metadata
        ├── chat_history.jsonl  # Append-only chat messages
        ├── research/
        │   ├── prompts/        # Gemini DR prompts generated by AI
        │   │   └── {NNN}-{slug}.md
        │   └── results/        # Uploaded Gemini DR results
        │       └── {NNN}-{slug}.md
        └── reports/
            ├── 01-capture.md
            ├── 02-clarify.md
            ├── 03-market-research.md
            ├── 04-competitive-analysis.md
            ├── 05-monetization.md
            ├── 06-feasibility.md
            ├── 07-tech-spec.md
            └── 08-build-plan.md
    ```
  - Implement methods:
    - `create_idea_folder(slug: str) -> Path`
    - `get_idea_folder(slug: str) -> Path`
    - `write_state(slug: str, state: dict)`
    - `read_state(slug: str) -> dict`
    - `save_research_prompt(slug: str, prompt: str, topic: str) -> str` (returns filename)
    - `save_research_result(slug: str, filename: str, content: str) -> Path`
    - `get_pending_research(slug: str) -> list[dict]` (prompts without matching results)
    - `get_completed_research(slug: str) -> list[dict]` (prompts WITH matching results)
    - `write_report(slug: str, phase: str, content: str)`
    - `read_report(slug: str, phase: str) -> str`
    - `append_chat_message(slug: str, message: dict)`
    - `read_chat_history(slug: str) -> list[dict]`
  - Create `data/ideas/` directory on init if not exists

  **Must NOT do**:
  - No cloud storage — local filesystem only
  - No file encryption
  - No binary file support (markdown/text only)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 4)
  - **Blocks**: Tasks 9, 13
  - **Blocked By**: Task 1

  **References**:
  - Idea folder structure as defined above
  - state.json format: `{"phase": "capture", "scores": {...}, "metadata": {...}}`
  - chat_history.jsonl: one JSON object per line (role, content, timestamp, metadata)

  **Acceptance Criteria**:
  - [ ] `create_idea_folder("ai-cooking-app")` creates full directory tree
  - [ ] `write_state` + `read_state` round-trip correctly
  - [ ] `save_research_prompt` creates numbered file in prompts/
  - [ ] `save_research_result` saves file in results/
  - [ ] `get_pending_research` returns prompts without results
  - [ ] `append_chat_message` + `read_chat_history` work correctly

  **QA Scenarios**:

  ```
  Scenario: Full idea folder lifecycle
    Tool: Bash (Python)
    Preconditions: data/ directory exists
    Steps:
      1. Create idea folder for "test-idea"
      2. Write state, save research prompt, append 3 chat messages, write report
      3. Read back state, chat history, and report
      4. Assert: all data matches what was written
    Expected Result: Full round-trip file operations succeed
    Failure Indicators: FileNotFoundError, data mismatch
    Evidence: .sisyphus/evidence/task-5-file-lifecycle.txt

  Scenario: Pending vs completed research detection
    Tool: Bash (Python)
    Preconditions: Idea folder exists
    Steps:
      1. Save 2 research prompts (001-market, 002-competition)
      2. Upload result for 001-market only
      3. Call get_pending_research() — assert returns 002-competition
      4. Call get_completed_research() — assert returns 001-market
    Expected Result: Correct classification of pending vs completed
    Failure Indicators: Both returned as pending, or both as completed
    Evidence: .sisyphus/evidence/task-5-research-detection.txt
  ```

  **Commit**: YES
  - Message: `feat(storage): idea folder structure and file management service`
  - Files: `backend/app/services/file_manager.py`

- [x] 6. Chat API + WebSocket Streaming

  **What to do**:
  - Create `backend/app/routers/chat.py` with FastAPI router
  - Implement WebSocket endpoint: `WS /api/ideas/{idea_id}/ws/chat`
    - Accept WebSocket connection
    - Receive JSON messages: `{"message": "user text"}`
    - Build message context: system prompt (with phase context, idea state, research findings) + chat history
    - Stream LLM response chunks back as: `{"type": "chunk", "content": "..."}`
    - On completion, send: `{"type": "done", "message_id": "..."}`
    - On error, send: `{"type": "error", "message": "..."}`
    - Save both user message and assistant response to chat_history.jsonl and SQLite messages table
  - Implement REST endpoint for chat history: `GET /api/ideas/{idea_id}/chat/history`
  - Create `backend/app/routers/__init__.py` to register all routers
  - Mount router in main.py

  **Must NOT do**:
  - No SSE (Server-Sent Events) — WebSocket only for chat
  - No multi-user WebSocket management — single user
  - No message queuing — direct LLM call per message

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 7, 8, 9, 10, 11, 12)
  - **Blocks**: Tasks 11, 20
  - **Blocked By**: Tasks 2, 4

  **References**:
  - `backend/app/services/llm.py`: LLMService.chat_completion() for streaming
  - `backend/app/services/system_prompts.py`: Phase-aware system prompts
  - `backend/app/models/message.py`: Message model for persistence
  - `backend/app/services/file_manager.py`: append_chat_message() for file-based history
  - FastAPI WebSocket: `https://fastapi.tiangolo.com/advanced/websockets/`
  - WebSocket message protocol: JSON with type field (chunk/done/error)

  **Acceptance Criteria**:
  - [ ] WebSocket endpoint accepts connections and receives messages
  - [ ] LLM responses stream back in chunks
  - [ ] Chat history persisted to both SQLite and JSONL file
  - [ ] System prompt includes current phase context
  - [ ] Error responses sent on LLM failure
  - [ ] Chat history endpoint returns all messages for an idea

  **QA Scenarios**:

  ```
  Scenario: WebSocket chat streams response
    Tool: Bash (Python websockets or wscat)
    Preconditions: Backend running, idea exists in DB
    Steps:
      1. Connect WebSocket to ws://localhost:8000/api/ideas/{idea_id}/ws/chat
      2. Send: {"message": "I want to build an AI cooking app"}
      3. Receive chunks and verify type="chunk" messages
      4. Verify final type="done" message
      5. Call GET /api/ideas/{idea_id}/chat/history
      6. Assert: 2 messages (1 user, 1 assistant) in history
    Expected Result: Streaming response received, history saved
    Failure Indicators: No chunks, connection dropped, empty history
    Evidence: .sisyphus/evidence/task-6-ws-chat.txt

  Scenario: Chat handles LLM error gracefully
    Tool: Bash (Python)
    Preconditions: Backend running with invalid LLM config
    Steps:
      1. Connect WebSocket
      2. Send message
      3. Assert: receive type="error" message
      4. Verify WebSocket stays open (not crashed)
    Expected Result: Error message sent, connection maintained
    Failure Indicators: WebSocket closes, unhandled exception
    Evidence: .sisyphus/evidence/task-6-chat-error.txt
  ```

  **Commit**: YES
  - Message: `feat(chat): WebSocket chat API with LLM streaming`
  - Files: `backend/app/routers/chat.py`, `backend/app/routers/__init__.py`

- [x] 7. Phase Engine + State Machine

  **What to do**:
  - Create `backend/app/services/phase_engine.py` with `PhaseEngine` class
  - Define phase enum and transition rules:
    ```
    CAPTURE → CLARIFY → MARKET_RESEARCH → COMPETITIVE_ANALYSIS → MONETIZATION → FEASIBILITY → TECH_SPEC → BUILD
    ```
  - Implement phase transition logic:
    - `get_current_phase(idea_id) -> Phase`
    - `suggest_advancement(idea_id) -> dict`: AI evaluates if idea is ready for next phase, returns reasoning + recommendation
    - `approve_advancement(idea_id) -> Phase`: Human approves, transition to next phase
    - `reject_advancement(idea_id, reason: str)`: Human rejects with reason, stay in current phase
    - `get_phase_requirements(phase: Phase) -> list[str]`: What should be accomplished in this phase
    - `generate_phase_report(idea_id, phase: Phase) -> str`: AI generates summary of phase accomplishments
  - Each phase transition triggers:
    1. AI generates phase report → saved to reports/
    2. Phase record created in SQLite
    3. state.json updated with new phase
    4. AI re-evaluates scores based on new information
  - Build the phase-aware system prompt that changes instructions based on current phase
  - The system prompt should instruct the AI to:
    - Ask relevant questions for the current phase
    - Assess when enough information is gathered
    - Suggest advancing to next phase with reasoning
    - NOT auto-advance without human approval

  **Must NOT do**:
  - No auto-advancement — AI suggests, human approves
  - No skipping phases — must go in order
  - No phase regression (going back) — forward only (can be added later)

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 8, 9, 10, 11, 12)
  - **Blocks**: Tasks 15, 17, 18, 20
  - **Blocked By**: Task 2

  **References**:
  - `backend/app/models/phase.py`: PhaseRecord model
  - `backend/app/services/llm.py`: LLMService for AI evaluation
  - `backend/app/services/system_prompts.py`: PHASE_PROMPTS dict
  - `backend/app/services/file_manager.py`: write_report(), write_state()
  - Phase enum values: capture, clarify, market_research, competitive_analysis, monetization, feasibility, tech_spec, build
  - Phase-specific AI behavior:
    - CAPTURE: Ask "what is this idea? what problem does it solve? who is it for?"
    - CLARIFY: Ask detailed questions about features, target user, value proposition
    - MARKET_RESEARCH: Focus on TAM, target audience, demand signals, market trends
    - COMPETITIVE_ANALYSIS: Focus on competitors, differentiation, positioning
    - MONETIZATION: Revenue model, pricing strategy, unit economics
    - FEASIBILITY: Technical stack, resources needed, risks, timeline
    - TECH_SPEC: Architecture, components, MVP scope, data models
    - BUILD: Generate step-by-step Prometheus prompts

  **Acceptance Criteria**:
  - [ ] Phase enum with all 8 phases defined
  - [ ] `suggest_advancement()` returns AI evaluation with reasoning
  - [ ] `approve_advancement()` transitions phase and generates report
  - [ ] Phase-aware system prompt changes behavior per phase
  - [ ] Each transition creates PhaseRecord in SQLite

  **QA Scenarios**:

  ```
  Scenario: Phase advancement cycle
    Tool: Bash (curl)
    Preconditions: Backend running, idea in CAPTURE phase
    Steps:
      1. POST /api/ideas/{id}/phase/suggest — assert: returns recommendation with reasoning
      2. POST /api/ideas/{id}/phase/approve — assert: phase changes to CLARIFY
      3. GET /api/ideas/{id} — assert: current_phase is "clarify"
      4. Verify report file exists in reports/01-capture.md
    Expected Result: Phase transitions correctly with report generated
    Failure Indicators: Phase doesn't change, no report generated
    Evidence: .sisyphus/evidence/task-7-phase-cycle.txt

  Scenario: Rejection keeps phase unchanged
    Tool: Bash (curl)
    Preconditions: Idea in CLARIFY phase, suggestion pending
    Steps:
      1. POST /api/ideas/{id}/phase/reject with {"reason": "Need more details"}
      2. GET /api/ideas/{id} — assert: current_phase is still "clarify"
    Expected Result: Phase stays the same after rejection
    Failure Indicators: Phase changed despite rejection
    Evidence: .sisyphus/evidence/task-7-phase-reject.txt
  ```

  **Commit**: YES
  - Message: `feat(phases): 8-phase state machine with AI-driven progression`
  - Files: `backend/app/services/phase_engine.py`

- [x] 8. Web Search Service

  **What to do**:
  - Create `backend/app/services/web_search.py` with `WebSearchService` class
  - Strategy: Try ZAI API's web search capability first, fall back to DuckDuckGo
  - ZAI web search: Use the OpenAI function calling / tool use mechanism if ZAI supports it, or use their Web Search MCP endpoint
  - DuckDuckGo fallback: Use `duckduckgo-search` Python package (`pip install duckduckgo-search`)
  - Implement methods:
    - `async search(query: str, max_results: int = 5) -> list[dict]`: Returns list of {title, url, snippet}
    - `async fetch_page(url: str) -> str`: Fetch and extract text from a URL (use `httpx` + `html2text` or `readability-lxml`)
  - Rate limiting: Simple in-memory rate limiter (max 10 requests per minute)
  - Cache search results in SQLite or simple file cache to avoid repeated queries

  **Must NOT do**:
  - No paid search APIs — free tier only
  - No headless browser for scraping — httpx + html2text only
  - No persistent search index

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 7, 9, 10, 11, 12)
  - **Blocks**: Task 20
  - **Blocked By**: Task 4

  **References**:
  - codex-lb API web search: Check if the configured codex-lb route supports function calling or has a web search endpoint
  - `duckduckgo-search` package: `https://pypi.org/project/duckduckgo-search/`
  - `html2text` package: `https://pypi.org/project/html2text/`
  - Rate limiting: Simple token bucket in-memory

  **Acceptance Criteria**:
  - [ ] `search()` returns results with title, url, snippet
  - [ ] DuckDuckGo fallback works when ZAI search unavailable
  - [ ] `fetch_page()` extracts readable text from URLs
  - [ ] Rate limiter prevents excessive API calls
  - [ ] Results cached to avoid duplicate queries

  **QA Scenarios**:

  ```
  Scenario: Web search returns results
    Tool: Bash (Python)
    Preconditions: Backend services available
    Steps:
      1. Call search("AI cooking app market size 2024")
      2. Assert: returns list with at least 1 result
      3. Assert: each result has title, url, snippet
    Expected Result: Search returns relevant results
    Failure Indicators: Empty list, missing fields, exception
    Evidence: .sisyphus/evidence/task-8-search.txt

  Scenario: Fallback to DuckDuckGo works
    Tool: Bash (Python)
    Preconditions: ZAI search disabled (simulate failure)
    Steps:
      1. Mock ZAI search to raise exception
      2. Call search("test query")
      3. Assert: DuckDuckGo results returned
    Expected Result: Graceful fallback to DuckDuckGo
    Failure Indicators: Exception propagated, no results
    Evidence: .sisyphus/evidence/task-8-fallback.txt
  ```

  **Commit**: YES
  - Message: `feat(search): web search service with ZAI MCP + DuckDuckGo fallback`
  - Files: `backend/app/services/web_search.py`

- [x] 9. Gemini Deep Research Prompt Generator

  **What to do**:
  - Create `backend/app/services/research.py` with `ResearchService` class
  - Implement methods:
    - `async generate_research_prompts(idea_id: UUID) -> list[dict]`: AI analyzes idea context and generates specific Gemini DR prompts for knowledge gaps
    - `async create_research_task(idea_id: UUID, prompt: str, topic: str) -> ResearchTask`: Create a new research task
    - `async upload_research_result(idea_id: UUID, task_id: UUID, content: str) -> Path`: Save uploaded markdown/text
    - `async integrate_research(idea_id: UUID, task_id: UUID) -> dict`: AI reads the research result and produces a summary + insights
    - `async get_pending_tasks(idea_id: UUID) -> list[ResearchTask]`: Get all pending research tasks
    - `async get_completed_tasks(idea_id: UUID) -> list[ResearchTask]`: Get all completed research tasks
  - AI generates prompts that are:
    - Specific and actionable (not vague "research X")
    - Include context about what we already know and what's missing
    - Formatted for Gemini Deep Research (clear scope, expected deliverables)
  - Save prompts to `ideas/{slug}/research/prompts/` via FileManager
  - Save results to `ideas/{slug}/research/results/` via FileManager
  - Research task workflow: PENDING → SUBMITTED (human acknowledged) → COMPLETED (result uploaded)

  **Must NOT do**:
  - No auto-submission to Gemini — human copies prompt manually
  - No PDF/DOCX parsing — markdown/text only
  - No external API calls for research (that's what Gemini DR is for)

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 7, 8, 10, 11, 12)
  - **Blocks**: Tasks 13, 16, 20
  - **Blocked By**: Tasks 2, 5

  **References**:
  - `backend/app/models/research.py`: ResearchTask model
  - `backend/app/services/file_manager.py`: save_research_prompt(), save_research_result()
  - `backend/app/services/llm.py`: LLMService for prompt generation and research integration
  - `backend/app/services/system_prompts.py`: RESEARCH_INTEGRATION_PROMPT

  **Acceptance Criteria**:
  - [ ] AI generates context-aware Gemini DR prompts
  - [ ] Prompts saved to filesystem with proper naming
  - [ ] File upload endpoint accepts markdown/text
  - [ ] AI integrates research results and produces insights
  - [ ] Research task status tracked correctly (pending/submitted/completed)

  **QA Scenarios**:

  ```
  Scenario: Research prompt generation and upload cycle
    Tool: Bash (curl)
    Preconditions: Backend running, idea exists in market_research phase
    Steps:
      1. POST /api/ideas/{id}/research/generate — assert: returns list of prompts
      2. Verify prompt files exist in research/prompts/
      3. POST /api/ideas/{id}/research/{task_id}/upload with markdown content
      4. POST /api/ideas/{id}/research/{task_id}/integrate
      5. Assert: integration returns summary + insights
    Expected Result: Full research cycle from generation to integration
    Failure Indicators: Empty prompts, upload fails, integration error
    Evidence: .sisyphus/evidence/task-9-research-cycle.txt

  Scenario: Upload rejects non-markdown/text files
    Tool: Bash (curl)
    Preconditions: Research task exists
    Steps:
      1. POST /api/ideas/{id}/research/{task_id}/upload with Content-Type: application/pdf and binary data
      2. Assert: 400 Bad Request with error about unsupported format
    Expected Result: Rejection of unsupported file types
    Failure Indicators: File accepted despite wrong format
    Evidence: .sisyphus/evidence/task-9-upload-reject.txt
  ```

  **Commit**: YES
  - Message: `feat(research): Gemini DR prompt generation service`
  - Files: `backend/app/services/research.py`

- [x] 10. Scoring Engine — 7 Dimensions

  **What to do**:
  - Create `backend/app/services/scoring.py` with `ScoringService` class
  - Define scoring dimensions with rubrics:
    - **TAM (Market Size)**: 1=tiny niche, 5=moderate market, 10=massive global market
    - **Competition Level**: 1=saturated/no room, 5=some players, 10=blue ocean
    - **Technical Feasibility**: 1=impossible with current tech, 5=challenging, 10=straightforward
    - **Time to MVP**: 1=years, 5=months, 10=days/weeks
    - **Revenue Potential**: 1=no clear monetization, 5=some paths, 10=clear high-revenue model
    - **Uniqueness**: 1=exact copies exist, 5=some differentiation, 10=completely novel
    - **Personal Fit**: 1=no skills/interest, 5=some alignment, 10=perfect match
  - Implement methods:
    - `async score_idea(idea_id: UUID) -> dict[str, float]`: AI evaluates idea on all 7 dimensions
    - `async rescore_dimension(idea_id: UUID, dimension: str, value: float, rationale: str)`: Manual override
    - `async get_scores(idea_id: UUID) -> list[Score]`: Get all scores for an idea
    - `async get_composite_score(idea_id: UUID) -> float`: Weighted average (all dimensions equal weight for now)
    - `async compare_ideas(idea_ids: list[UUID]) -> dict`: Side-by-side comparison
  - AI scoring uses a carefully crafted prompt that:
    - Considers all available context (chat history, research, phase data)
    - Provides rationale for each score
    - Suggests what information is missing to improve confidence
  - Store scores in SQLite Score table with rationale text

  **Must NOT do**:
  - No external scoring APIs — AI generates scores
  - No ML models for scoring — prompt-based only
  - No weighted scoring formula — equal weights (user can customize later)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 7, 8, 9, 11, 12)
  - **Blocks**: Tasks 18, 20
  - **Blocked By**: Task 2

  **References**:
  - `backend/app/models/score.py`: Score model with dimension, value, rationale
  - `backend/app/services/llm.py`: LLMService for AI scoring
  - `backend/app/services/system_prompts.py`: SCORING_PROMPT
  - Dimensions: tam, competition, feasibility, time_to_mvp, revenue, uniqueness, personal_fit
  - Score range: 0.0 to 10.0

  **Acceptance Criteria**:
  - [ ] `score_idea()` returns all 7 dimension scores with rationale
  - [ ] Scores stored in SQLite with value and rationale
  - [ ] `get_composite_score()` returns weighted average
  - [ ] `compare_ideas()` returns side-by-side comparison
  - [ ] Manual override works for individual dimensions

  **QA Scenarios**:

  ```
  Scenario: Full scoring cycle
    Tool: Bash (curl)
    Preconditions: Backend running, idea exists with some chat history
    Steps:
      1. POST /api/ideas/{id}/score — assert: returns 7 scores, each 0-10 with rationale
      2. GET /api/ideas/{id}/scores — assert: all 7 stored
      3. GET /api/ideas/{id}/scores/composite — assert: single float value
    Expected Result: All dimensions scored with rationale
    Failure Indicators: Missing dimensions, scores out of range, no rationale
    Evidence: .sisyphus/evidence/task-10-scoring.txt

  Scenario: Manual score override
    Tool: Bash (curl)
    Preconditions: Idea has existing scores
    Steps:
      1. PUT /api/ideas/{id}/scores/competition with {"value": 8.5, "rationale": "Found niche gap"}
      2. GET /api/ideas/{id}/scores — assert: competition score is 8.5 with new rationale
    Expected Result: Override persists correctly
    Failure Indicators: Old value still present
    Evidence: .sisyphus/evidence/task-10-override.txt
  ```

  **Commit**: YES
  - Message: `feat(scoring): 7-dimension numeric scoring engine`
  - Files: `backend/app/services/scoring.py`

- [x] 11. Chat UI Component

  **What to do**:
  - Create `frontend/src/lib/components/Chat/` directory:
    - `ChatView.svelte` — Main chat page component
    - `MessageList.svelte` — Scrollable message list with auto-scroll
    - `MessageBubble.svelte` — Individual message (user vs assistant styling)
    - `ChatInput.svelte` — Input field with send button (Enter to send)
    - `MarkdownRenderer.svelte` — Renders markdown content using `marked` + `dompurify`
    - `PhaseIndicator.svelte` — Shows current phase with advancement button
  - WebSocket connection management:
    - Connect to `ws://localhost:8000/api/ideas/{id}/ws/chat` on mount
    - Handle reconnection on disconnect
    - Display typing indicator while streaming
  - Message rendering:
    - User messages: right-aligned, simple background
    - Assistant messages: left-aligned, rendered markdown (headers, lists, code blocks, bold/italic, links)
    - Streaming: show content as it arrives (append chunks)
  - Phase advancement UI:
    - Show current phase badge
    - When AI suggests advancement: show suggestion card with "Approve" / "Reject" buttons
    - After approval: animate phase change, show new phase
  - Load chat history on mount via REST API

  **Must NOT do**:
  - No rich text editor for input — plain text only
  - No message editing or deletion
  - No file upload in chat (that's in Actions)
  - No syntax highlighting for code blocks (basic styling only)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: [`/frontend-ui-ux`]
    - `/frontend-ui-ux`: Domain overlap — building chat UI with markdown rendering, WebSocket streaming, and interactive components

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 7, 8, 9, 10, 12)
  - **Blocks**: Task 21
  - **Blocked By**: Tasks 3, 6

  **References**:
  - `frontend/src/lib/components/UI/`: Base UI components (Button, Card, Badge)
  - `frontend/src/lib/api.js`: API client for REST endpoints
  - WebSocket API: `ws://localhost:8000/api/ideas/{id}/ws/chat`
  - Message format: `{"type": "chunk"|"done"|"error", "content": "..."}`
  - `marked` library: `https://marked.js.org/` for markdown rendering
  - `dompurify`: `https://github.com/cure53/DOMPurify` for HTML sanitization

  **Acceptance Criteria**:
  - [ ] Chat messages render with correct markdown formatting
  - [ ] WebSocket streaming shows content as it arrives
  - [ ] User and assistant messages visually distinct
  - [ ] Phase indicator shows current phase
  - [ ] Phase advancement buttons work (approve/reject)
  - [ ] Chat history loads on page mount
  - [ ] Auto-scroll to latest message

  **QA Scenarios**:

  ```
  Scenario: Chat sends message and receives streaming response
    Tool: Playwright
    Preconditions: App running, idea selected, WebSocket connected
    Steps:
      1. Navigate to chat page for an idea
      2. Type "Tell me about the AI cooking app market" in input
      3. Press Enter
      4. Wait for response to complete
      5. Assert: assistant message appears with rendered markdown
      6. Assert: markdown includes headers, bullet points (not raw **text**)
    Expected Result: User message sent, AI response rendered as formatted markdown
    Failure Indicators: No response, raw markdown shown, WebSocket disconnected
    Evidence: .sisyphus/evidence/task-11-chat-stream.png

  Scenario: Phase advancement works in chat
    Tool: Playwright
    Preconditions: Idea in CAPTURE phase, AI has suggested advancement
    Steps:
      1. Look for phase indicator showing "CAPTURE"
      2. Look for advancement suggestion card
      3. Click "Approve" button
      4. Assert: phase indicator changes to "CLARIFY"
      5. Assert: success notification appears
    Expected Result: Phase transitions with visual feedback
    Failure Indicators: Button doesn't work, phase doesn't change
    Evidence: .sisyphus/evidence/task-11-phase-advance.png
  ```

  **Commit**: YES
  - Message: `feat(ui): chat interface component with markdown rendering`
  - Files: `frontend/src/lib/components/Chat/`

- [x] 12. Ideas Dashboard + Management UI

  **What to do**:
  - Create `frontend/src/lib/components/Dashboard/` directory:
    - `Dashboard.svelte` — Main dashboard page
    - `IdeaCard.svelte` — Card showing idea title, phase badge, composite score, quick stats
    - `CreateIdea.svelte` — Modal form for new idea (title + description textarea)
    - `IdeaDetail.svelte` — Detailed view with all scores, phase history, relationships
    - `ScoreBar.svelte` — Visual score bar (0-10 scale) for each dimension
  - Dashboard features:
    - Grid of IdeaCards showing all active ideas
    - "New Idea" button opens CreateIdea modal
    - Click IdeaCard → navigate to Chat view for that idea
    - Show composite score prominently on each card
    - Color-code ideas by health: green (high scores), yellow (mixed), red (low scores)
    - Show phase badge on each card
  - Create idea API calls:
    - `POST /api/ideas` — Create new idea
    - `GET /api/ideas` — List all ideas with scores and phases
    - `GET /api/ideas/{id}` — Get idea detail
    - `PATCH /api/ideas/{id}` — Update idea
    - `DELETE /api/ideas/{id}` — Archive/kill idea
  - Create corresponding backend router: `backend/app/routers/ideas.py`

  **Must NOT do**:
  - No drag-and-drop ordering
  - No filtering/sorting (only 1-3 ideas)
  - No bulk operations

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: [`/frontend-ui-ux`]
    - `/frontend-ui-ux`: Domain overlap — dashboard layout, card grid, modal forms, score visualization

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 7, 8, 9, 10, 11)
  - **Blocks**: Tasks 15, 16, 21
  - **Blocked By**: Tasks 3, 2

  **References**:
  - `frontend/src/lib/components/UI/`: Button, Card, Badge, Modal, Input components
  - `frontend/src/lib/api.js`: API client
  - `backend/app/models/idea.py`: Idea model
  - `backend/app/models/score.py`: Score model
  - Score dimensions: tam, competition, feasibility, time_to_mvp, revenue, uniqueness, personal_fit
  - Color coding: green >= 7, yellow 4-6.9, red < 4

  **Acceptance Criteria**:
  - [ ] Dashboard shows all ideas as cards
  - [ ] Each card shows title, phase, composite score
  - [ ] "New Idea" modal creates idea with title + description
  - [ ] Clicking card navigates to chat
  - [ ] Score bars visualize all 7 dimensions
  - [ ] Color coding by score health

  **QA Scenarios**:

  ```
  Scenario: Create idea and see it on dashboard
    Tool: Playwright
    Preconditions: App running
    Steps:
      1. Navigate to dashboard
      2. Click "New Idea" button
      3. Fill title: "AI Cooking App"
      4. Fill description: "An app that suggests recipes based on what's in your fridge"
      5. Click "Create"
      6. Assert: new card appears on dashboard with title "AI Cooking App"
      7. Assert: phase badge shows "CAPTURE"
    Expected Result: Idea created and visible on dashboard
    Failure Indicators: Card doesn't appear, modal doesn't close, error message
    Evidence: .sisyphus/evidence/task-12-create-idea.png

  Scenario: Idea card shows correct score visualization
    Tool: Playwright
    Preconditions: Idea exists with scores
    Steps:
      1. Navigate to dashboard
      2. Find idea card
      3. Assert: composite score visible
      4. Click card to open detail
      5. Assert: all 7 score bars visible with values
      6. Assert: color coding correct (green/yellow/red)
    Expected Result: Scores correctly visualized
    Failure Indicators: Missing bars, wrong colors, no scores
    Evidence: .sisyphus/evidence/task-12-scores.png
  ```

  **Commit**: YES
  - Message: `feat(ui): ideas dashboard with list, create, manage`
  - Files: `frontend/src/lib/components/Dashboard/`, `backend/app/routers/ideas.py`

- [x] 13. Research Upload + Integration Service

  **What to do**:
  - Create `backend/app/routers/research.py` with REST endpoints:
    - `POST /api/ideas/{id}/research/generate` — AI generates research prompts for knowledge gaps
    - `GET /api/ideas/{id}/research/tasks` — List all research tasks (pending + completed)
    - `POST /api/ideas/{id}/research/{task_id}/upload` — Upload markdown/text research result
    - `POST /api/ideas/{id}/research/{task_id}/integrate` — AI reads and integrates research findings
  - File upload handling:
    - Accept `multipart/form-data` with file field
    - Validate: file extension is .md, .txt, or .markdown
    - Validate: file size < 5MB
    - Save to `ideas/{slug}/research/results/` with proper naming
    - Update research task status to COMPLETED in SQLite
  - Research integration:
    - AI reads the uploaded research file
    - Produces structured summary: key findings, relevant data, implications for the idea
    - Updates chat context so future conversations reference the research
    - May trigger score re-evaluation if research changes market/competitive understanding

  **Must NOT do**:
  - No PDF parsing
  - No OCR
  - No automatic web scraping of research URLs

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 14, 15, 16, 17, 18, 19)
  - **Blocks**: Task 20
  - **Blocked By**: Tasks 5, 9

  **References**:
  - `backend/app/services/research.py`: ResearchService for prompt generation and integration
  - `backend/app/services/file_manager.py`: save_research_result(), get_completed_research()
  - `backend/app/models/research.py`: ResearchTask model
  - FastAPI file upload: `https://fastapi.tiangolo.com/tutorial/request-files/`
  - File validation: extension in [.md, .txt, .markdown], size < 5MB

  **Acceptance Criteria**:
  - [ ] Upload endpoint accepts .md/.txt files
  - [ ] Upload rejects binary/unsupported formats with clear error
  - [ ] Research integration produces structured summary
  - [ ] Chat context updated after integration
  - [ ] Research task status transitions correctly

  **QA Scenarios**:

  ```
  Scenario: Upload markdown research and integrate
    Tool: Bash (curl)
    Preconditions: Idea exists, research task in PENDING state
    Steps:
      1. Create test markdown file with market research content
      2. curl -X POST -F "file=@research.md" http://localhost:8000/api/ideas/{id}/research/{task_id}/upload
      3. Assert: 200 OK, file saved
      4. curl -X POST http://localhost:8000/api/ideas/{id}/research/{task_id}/integrate
      5. Assert: returns structured summary with key_findings
    Expected Result: File uploaded and integrated
    Failure Indicators: Upload rejected, integration fails, empty summary
    Evidence: .sisyphus/evidence/task-13-upload-integrate.txt

  Scenario: Reject oversized or wrong format file
    Tool: Bash (curl)
    Preconditions: Research task exists
    Steps:
      1. Create a 6MB markdown file
      2. Upload — assert: 413 Payload Too Large
      3. Upload a .pdf file — assert: 400 Bad Request
    Expected Result: Proper rejection of invalid uploads
    Failure Indicators: Oversized file accepted
    Evidence: .sisyphus/evidence/task-13-upload-reject.txt
  ```

  **Commit**: YES
  - Message: `feat(research): research file upload and AI integration`
  - Files: `backend/app/routers/research.py`

- [x] 14. Idea Relationships Service

  **What to do**:
  - Create `backend/app/services/relationships.py` with `RelationshipService` class
  - Implement methods:
    - `async create_relationship(source_id: UUID, target_id: UUID, type: str, description: str) -> IdeaRelationship`
    - `async get_relationships(idea_id: UUID) -> list[IdeaRelationship]` (both directions)
    - `async merge_ideas(source_id: UUID, target_id: UUID, merged_title: str, merged_description: str) -> Idea` — Merge two ideas into one, combining chat history, scores, research
    - `async split_idea(idea_id: UUID, split_data: dict) -> tuple[Idea, Idea]` — Split one idea into two
    - `async derive_idea(source_id: UUID, new_title: str, new_description: str) -> Idea` — Create derivative idea with reference to original
    - `async detect_related_ideas(idea_id: UUID) -> list[dict]` — AI suggests potential relationships with other ideas
  - Create `backend/app/routers/relationships.py` with REST endpoints:
    - `POST /api/ideas/{id}/relationships` — Create relationship
    - `GET /api/ideas/{id}/relationships` — Get all relationships for an idea
    - `POST /api/ideas/{id}/merge` — Merge with another idea
    - `POST /api/ideas/{id}/split` — Split into two ideas
    - `POST /api/ideas/{id}/derive` — Create derivative idea
    - `POST /api/ideas/{id}/suggest-relationships` — AI suggests related ideas

  **Must NOT do**:
  - No circular relationship detection (keep simple for 1-3 ideas)
  - No relationship graph visualization (text-based only)
  - No auto-merging — human initiates all relationships

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 13, 15, 16, 17, 18, 19)
  - **Blocks**: Task 20
  - **Blocked By**: Task 2

  **References**:
  - `backend/app/models/relationship.py`: IdeaRelationship model
  - `backend/app/models/idea.py`: Idea model
  - `backend/app/services/llm.py`: LLMService for AI relationship detection
  - Relationship types: merge, split, derive, reference

  **Acceptance Criteria**:
  - [ ] Create and retrieve relationships works
  - [ ] Merge combines chat history and scores from both ideas
  - [ ] Split creates two new ideas with divided content
  - [ ] Derive creates new idea with reference link
  - [ ] AI suggests relationships between existing ideas

  **QA Scenarios**:

  ```
  Scenario: Merge two ideas
    Tool: Bash (curl)
    Preconditions: Two ideas exist
    Steps:
      1. POST /api/ideas/{id_a}/merge {"target_id": id_b, "title": "Merged Cooking App", "description": "..."}
      2. Assert: new idea created with merged title
      3. Assert: old ideas archived
      4. Assert: chat history from both available in merged idea
    Expected Result: Ideas merged with combined history
    Failure Indicators: Old ideas still active, missing history
    Evidence: .sisyphus/evidence/task-14-merge.txt

  Scenario: AI detects related ideas
    Tool: Bash (curl)
    Preconditions: Two similar ideas exist
    Steps:
      1. POST /api/ideas/{id}/suggest-relationships
      2. Assert: returns list suggesting relationship with the similar idea
      3. Assert: includes relationship type suggestion and reasoning
    Expected Result: AI identifies related ideas
    Failure Indicators: Empty list, no suggestions
    Evidence: .sisyphus/evidence/task-14-detect.txt
  ```

  **Commit**: YES
  - Message: `feat(ideas): idea relationships — merge, split, derive`
  - Files: `backend/app/services/relationships.py`, `backend/app/routers/relationships.py`

- [x] 15. Reports Section UI

  **What to do**:
  - Create `frontend/src/lib/components/Reports/` directory:
    - `Reports.svelte` — Main reports page
    - `ReportViewer.svelte` — Renders a single markdown report with proper formatting
    - `ReportList.svelte` — List of reports grouped by phase
  - Features:
    - Show list of all generated reports for the selected idea
    - Group by phase (Capture, Clarify, Market Research, etc.)
    - Click a report → render full markdown in ReportViewer
    - Phase badges showing which reports exist
    - Empty state: "No reports yet — advance through phases to generate reports"
  - Fetch reports from `GET /api/ideas/{id}/reports` API endpoint
  - Create backend endpoint in `backend/app/routers/reports.py`:
    - `GET /api/ideas/{id}/reports` — List all reports
    - `GET /api/ideas/{id}/reports/{phase}` — Get specific report

  **Must NOT do**:
  - No report editing in UI
  - No report export/download (files exist on disk)
  - No PDF generation

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: [`/frontend-ui-ux`]
    - `/frontend-ui-ux`: Domain overlap — report viewing, markdown rendering, list/grid layout

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 13, 14, 16, 17, 18, 19)
  - **Blocks**: Task 21
  - **Blocked By**: Tasks 12, 7

  **References**:
  - `frontend/src/lib/components/Chat/MarkdownRenderer.svelte`: Reuse markdown rendering
  - `backend/app/models/report.py`: Report model
  - `backend/app/services/file_manager.py`: read_report()
  - Phase names: capture, clarify, market_research, competitive_analysis, monetization, feasibility, tech_spec, build

  **Acceptance Criteria**:
  - [ ] Reports page shows all reports for selected idea
  - [ ] Reports grouped by phase with badges
  - [ ] Clicking report renders full markdown content
  - [ ] Empty state shown when no reports exist

  **QA Scenarios**:

  ```
  Scenario: View phase reports
    Tool: Playwright
    Preconditions: Idea exists with reports from multiple phases
    Steps:
      1. Navigate to Reports page
      2. Select an idea
      3. Assert: list of reports shown grouped by phase
      4. Click "Market Research" report
      5. Assert: full markdown content rendered correctly
    Expected Result: Reports listed and viewable with correct formatting
    Failure Indicators: Empty list, markdown not rendering
    Evidence: .sisyphus/evidence/task-15-reports.png
  ```

  **Commit**: YES
  - Message: `feat(ui): reports section with per-phase document viewer`
  - Files: `frontend/src/lib/components/Reports/`, `backend/app/routers/reports.py`

- [x] 16. Actions Panel UI

  **What to do**:
  - Create `frontend/src/lib/components/Actions/` directory:
    - `Actions.svelte` — Main actions page
    - `ResearchTaskCard.svelte` — Card showing a Gemini DR task with prompt + status
    - `FileUpload.svelte` — Drag-and-drop file upload component for research results
  - Features:
    - Show all research tasks for selected idea
    - Each task card shows:
      - Topic/title
      - Generated prompt text (expandable/collapsible)
      - Copy button to copy prompt to clipboard
      - Status badge (PENDING / SUBMITTED / COMPLETED)
      - Upload button (opens FileUpload dialog when PENDING or SUBMITTED)
    - FileUpload component:
      - Drag-and-drop zone
      - Accept .md, .txt, .markdown files only
      - Show upload progress
      - Show success/error feedback
    - "Generate New Research Tasks" button — triggers AI to analyze knowledge gaps
    - Completed tasks show "View Integration" button to see AI summary

  **Must NOT do**:
  - No auto-submission to Gemini — copy button only
  - No multi-file upload — one file per task
  - No progress tracking for Gemini DR (manual status update)

  **Recommended Agent Profile**:
  - **Category**: `visual-engineering`
  - **Skills**: [`/frontend-ui-ux`]
    - `/frontend-ui-ux`: Domain overlap — action cards, file upload, status indicators

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 13, 14, 15, 17, 18, 19)
  - **Blocks**: Task 21
  - **Blocked By**: Tasks 12, 9

  **References**:
  - `frontend/src/lib/components/UI/`: Card, Badge, Button, Modal components
  - `backend/app/routers/research.py`: Research API endpoints
  - `backend/app/models/research.py`: ResearchTask model with status enum
  - File upload: FastAPI UploadFile with multipart/form-data

  **Acceptance Criteria**:
  - [ ] Actions page lists all research tasks
  - [ ] Each task shows prompt with copy-to-clipboard button
  - [ ] File upload accepts .md/.txt via drag-and-drop
  - [ ] Upload triggers research integration
  - [ ] Status badges show correct state

  **QA Scenarios**:

  ```
  Scenario: Copy prompt and upload research result
    Tool: Playwright
    Preconditions: Idea exists with research tasks
    Steps:
      1. Navigate to Actions page, select idea
      2. Find a PENDING research task
      3. Click copy button on prompt — assert: text copied to clipboard
      4. Upload a .md file via drag-and-drop
      5. Assert: status changes to COMPLETED
      6. Assert: "View Integration" button appears
    Expected Result: Full research task lifecycle works in UI
    Failure Indicators: Copy fails, upload fails, status stuck
    Evidence: .sisyphus/evidence/task-16-actions.png
  ```

  **Commit**: YES
  - Message: `feat(ui): actions panel for Gemini DR tasks`
  - Files: `frontend/src/lib/components/Actions/`

- [x] 17. Project Memory Service

  **What to do**:
  - Create `backend/app/services/memory.py` with `MemoryService` class
  - Two scopes:
    - **Global memory**: Key-value pairs accessible across all ideas (e.g., "user_skills", "available_tools", "constraints")
    - **Per-idea memory**: Stage tracking, issues, bugs, notes specific to one idea
  - Implement methods:
    - `async set_memory(key: str, value: str, category: str, idea_id: UUID = None) -> ProjectMemory`
    - `async get_memory(key: str, idea_id: UUID = None) -> ProjectMemory`
    - `async get_all_memory(idea_id: UUID = None) -> list[ProjectMemory]`
    - `async delete_memory(key: str, idea_id: UUID = None) -> bool`
    - `async get_by_category(category: str, idea_id: UUID = None) -> list[ProjectMemory]`
  - Categories: stage, issue, bug, note, constraint, resource
  - Auto-update mechanisms:
    - When phase changes → auto-set memory "stage" = new phase
    - When build prompt generated → track "current_build_step"
    - When issue found in chat → AI can create memory entry
  - Create REST endpoints in `backend/app/routers/memory.py`:
    - `GET /api/memory` — Get all global memory
    - `GET /api/ideas/{id}/memory` — Get all memory for idea
    - `POST /api/ideas/{id}/memory` — Create/update memory entry
    - `DELETE /api/ideas/{id}/memory/{key}` — Delete memory entry
  - Memory is included in LLM context when building system prompts

  **Must NOT do**:
  - No memory expiration or TTL
  - No memory versioning
  - No vector search — simple key-value

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 13, 14, 15, 16, 18, 19)
  - **Blocks**: Task 20
  - **Blocked By**: Tasks 2, 7

  **References**:
  - `backend/app/models/memory.py`: ProjectMemory model with idea_id nullable
  - `backend/app/services/phase_engine.py`: Phase transitions trigger memory updates
  - Categories: stage, issue, bug, note, constraint, resource

  **Acceptance Criteria**:
  - [ ] Global memory works without idea_id
  - [ ] Per-idea memory works with idea_id
  - [ ] Phase transitions auto-set stage memory
  - [ ] Memory included in LLM system prompt context

  **QA Scenarios**:

  ```
  Scenario: Memory CRUD operations
    Tool: Bash (curl)
    Preconditions: Backend running
    Steps:
      1. POST /api/ideas/{id}/memory {"key": "tech_stack", "value": "FastAPI+Svelte", "category": "note"}
      2. GET /api/ideas/{id}/memory — assert: entry present
      3. POST /api/memory {"key": "user_skills", "value": "Python,JS", "category": "resource"} — global
      4. GET /api/memory — assert: global entry present
    Expected Result: Both scopes work correctly
    Failure Indicators: Entries missing, wrong scope
    Evidence: .sisyphus/evidence/task-17-memory.txt
  ```

  **Commit**: YES
  - Message: `feat(memory): project memory service — global + per-idea tracking`
  - Files: `backend/app/services/memory.py`, `backend/app/routers/memory.py`

- [x] 18. Build Handoff — Prometheus Prompt Generator

  **What to do**:
  - Create `backend/app/services/build_handoff.py` with `BuildHandoffService` class
  - When idea reaches BUILD phase:
    - `async generate_prometheus_prompt(idea_id: UUID) -> dict`:
      1. Compile all idea context: title, description, all phase reports, scores, research findings, memory
      2. Generate a structured Prometheus planning prompt
      3. The prompt should guide Prometheus through the exact project setup needed
    - `async generate_step_prompts(idea_id: UUID) -> list[dict]`:
      1. Break the build into step-by-step prompts
      2. Each prompt is a complete instruction for one step (copy-paste to Prometheus)
      3. Steps: Project setup → Database → Backend → Frontend → Integration → Testing
    - `async get_current_build_state(idea_id: UUID) -> dict`:
      1. Check memory for current build step
      2. Return current step, completed steps, remaining steps
    - `async mark_step_complete(idea_id: UUID, step: str)`:
      1. Update memory with completed step
      2. Generate next step prompt
  - Create REST endpoints in `backend/app/routers/build.py`:
    - `GET /api/ideas/{id}/build/prompts` — Get all build prompts
    - `GET /api/ideas/{id}/build/current-step` — Get current step + prompt
    - `POST /api/ideas/{id}/build/step-complete` — Mark step done, get next
    - `POST /api/ideas/{id}/build/regenerate` — Regenerate all prompts
  - Add "Build" tab in UI that shows when idea is in BUILD phase

  **Must NOT do**:
  - No auto-invocation of Prometheus
  - No code generation — only prompt generation
  - No build execution — human copies to Prometheus

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 13, 14, 15, 16, 17, 19)
  - **Blocks**: Task 20
  - **Blocked By**: Tasks 7, 10

  **References**:
  - `backend/app/services/phase_engine.py`: BUILD phase triggers
  - `backend/app/services/memory.py`: Build step tracking
  - `backend/app/services/llm.py`: LLMService for prompt generation
  - `backend/app/services/file_manager.py`: read all reports for context
  - Prometheus planning: The generated prompts should follow Prometheus's planning interview format

  **Acceptance Criteria**:
  - [ ] Generate complete Prometheus planning prompt from all idea context
  - [ ] Break build into step-by-step prompts
  - [ ] Track current build step in memory
  - [ ] Mark step complete and generate next prompt
  - [ ] Build tab appears only when idea is in BUILD phase

  **QA Scenarios**:

  ```
  Scenario: Generate and step through build prompts
    Tool: Bash (curl)
    Preconditions: Idea in BUILD phase with full context
    Steps:
      1. GET /api/ideas/{id}/build/prompts — assert: returns list of prompts
      2. GET /api/ideas/{id}/build/current-step — assert: shows step 1
      3. POST /api/ideas/{id}/build/step-complete {"step": "project_setup"}
      4. GET /api/ideas/{id}/build/current-step — assert: shows step 2
    Expected Result: Build prompts generated and stepped through correctly
    Failure Indicators: Empty prompts, step doesn't advance
    Evidence: .sisyphus/evidence/task-18-build-prompts.txt
  ```

  **Commit**: YES
  - Message: `feat(handoff): Prometheus build prompt generator`
  - Files: `backend/app/services/build_handoff.py`, `backend/app/routers/build.py`

- [x] 19. Desktop Shortcut + Launch Script

  **What to do**:
  - Create `start.bat` in project root:
    ```bat
    @echo off
    echo Starting Idea Refinery...
    start /b python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
    timeout /t 3 /nobreak >nul
    start http://localhost:8000
    echo Idea Refinery is running at http://localhost:8000
    echo Press Ctrl+C to stop
    pause
    ```
  - Also create `start.ps1` as PowerShell alternative
  - Ensure FastAPI serves static files from `frontend/dist/` in production mode
  - Configure FastAPI to serve `frontend/dist/index.html` as the root route
  - Handle SPA routing: all non-API routes should serve index.html (for Svelte client-side routing)
  - Create `README.md` with setup instructions:
    1. Copy `.env.example` to `.env` and add ZAI API key
    2. Run `pip install -r requirements.txt`
    3. Run `cd frontend && npm install && npm run build`
    4. Run `start.bat`
  - Verify the entire app starts and works with the shortcut

  **Must NOT do**:
  - No Docker
  - No systemd/launchd services
  - No npm global installs

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 13, 14, 15, 16, 17, 18)
  - **Blocks**: Task 23
  - **Blocked By**: All Wave 1-2 tasks must be complete

  **References**:
  - FastAPI static files: `https://fastapi.tiangolo.com/tutorial/static-files/`
  - SPA routing: Catch-all route that serves index.html for non-API paths
  - `frontend/dist/`: Svelte build output directory

  **Acceptance Criteria**:
  - [ ] `start.bat` launches FastAPI and opens browser
  - [ ] App accessible at http://localhost:8000
  - [ ] SPA routing works (refresh on any route returns app, not 404)
  - [ ] Static files served correctly

  **QA Scenarios**:

  ```
  Scenario: Start app via batch file
    Tool: Bash
    Preconditions: All dependencies installed, frontend built
    Steps:
      1. Run: start.bat
      2. Wait 5 seconds
      3. curl http://localhost:8000 — assert: returns HTML
      4. curl http://localhost:8000/api/health — assert: {"status": "ok"}
    Expected Result: App starts and serves both static and API
    Failure Indicators: Batch file fails, browser shows error
    Evidence: .sisyphus/evidence/task-19-launch.txt
  ```

  **Commit**: YES
  - Message: `feat(launch): desktop shortcut and start script`
  - Files: `start.bat`, `start.ps1`, `README.md`

- [x] 20. Backend Test Suite

  **What to do**:
  - Set up pytest in `backend/tests/`
  - Create `backend/tests/conftest.py` with:
    - In-memory SQLite fixture (test DB)
    - Test client fixture (httpx AsyncClient)
    - Mock LLM service fixture (returns canned responses)
    - Sample idea fixture
  - Write test files:
    - `test_ideas_api.py` — CRUD for ideas, listing, archiving
    - `test_chat_api.py` — WebSocket chat, history retrieval
    - `test_phase_engine.py` — Phase transitions, suggestions, approval/rejection
    - `test_scoring.py` — Score generation, manual override, composite calculation
    - `test_research.py` — Prompt generation, file upload, integration
    - `test_relationships.py` — Create, merge, split, derive, detect
    - `test_memory.py` — Global and per-idea memory CRUD
    - `test_build_handoff.py` — Prompt generation, step tracking
    - `test_file_manager.py` — Folder creation, file I/O
  - Target: at least 3 tests per module (happy path + 2 edge cases)
  - Mock the LLM service to avoid API calls during testing

  **Must NOT do**:
  - No real LLM API calls in tests
  - No external network calls in tests
  - No flaky tests dependent on timing

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 21, 22, 23)
  - **Blocks**: Task 22
  - **Blocked By**: Tasks 6, 7, 8, 9, 10, 13, 14, 17, 18

  **References**:
  - `backend/app/` — All service and router modules
  - pytest-asyncio for async test functions
  - httpx for async test client
  - Mock pattern: create a MockLLMService that returns fixed responses

  **Acceptance Criteria**:
  - [ ] `pytest backend/tests/` runs with 0 failures
  - [ ] At least 3 tests per module
  - [ ] All tests use mocked LLM (no real API calls)
  - [ ] Tests cover happy path + edge cases

  **QA Scenarios**:

  ```
  Scenario: Test suite passes
    Tool: Bash
    Preconditions: All backend code complete
    Steps:
      1. Run: pytest backend/tests/ -v
      2. Assert: 0 failures, 0 errors
      3. Assert: coverage shows at least 70% of backend/app/
    Expected Result: All tests pass
    Failure Indicators: Test failures, import errors
    Evidence: .sisyphus/evidence/task-20-backend-tests.txt
  ```

  **Commit**: YES
  - Message: `test(backend): pytest suite for all backend services`
  - Files: `backend/tests/`

- [x] 21. Frontend Test Suite

  **What to do**:
  - Set up vitest in `frontend/`
  - Install: `vitest`, `@testing-library/svelte`, `jsdom`
  - Create test files:
    - `frontend/src/lib/components/Chat/ChatView.test.js` — Message rendering, input handling
    - `frontend/src/lib/components/Dashboard/Dashboard.test.js` — Idea listing, creation
    - `frontend/src/lib/components/Reports/Reports.test.js` — Report listing, viewing
    - `frontend/src/lib/components/Actions/Actions.test.js` — Research tasks, file upload
    - `frontend/src/lib/components/UI/Button.test.js` — Base component test
  - Mock WebSocket and API calls
  - Target: at least 2 tests per component

  **Must NOT do**:
  - No real WebSocket connections in tests
  - No real API calls in tests

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 20, 22, 23)
  - **Blocks**: Task 22
  - **Blocked By**: Tasks 11, 12, 15, 16

  **References**:
  - `frontend/src/lib/components/` — All component directories
  - vitest: `https://vitest.dev/`
  - @testing-library/svelte: `https://testing-library.com/docs/svelte-testing-library/intro`

  **Acceptance Criteria**:
  - [ ] `npm run test` in frontend/ passes with 0 failures
  - [ ] At least 2 tests per major component
  - [ ] All API/WebSocket calls mocked

  **QA Scenarios**:

  ```
  Scenario: Frontend test suite passes
    Tool: Bash
    Preconditions: All frontend code complete
    Steps:
      1. Run: cd frontend && npm run test
      2. Assert: 0 failures, 0 errors
    Expected Result: All tests pass
    Failure Indicators: Test failures, import errors
    Evidence: .sisyphus/evidence/task-21-frontend-tests.txt
  ```

  **Commit**: YES
  - Message: `test(frontend): vitest suite for Svelte components`
  - Files: `frontend/src/**/*.test.js`

- [x] 22. Integration/E2E Tests

  **What to do**:
  - Set up Playwright for E2E testing
  - Install: `@playwright/test`
  - Create `e2e/` directory with test files:
    - `e2e/idea-lifecycle.spec.js` — Full idea lifecycle: create → chat → advance phases → score → build prompts
    - `e2e/research-flow.spec.js` — Research tasks: generate prompts → upload result → integration
    - `e2e/idea-relationships.spec.js` — Create related ideas, merge, split
  - Each test starts the backend with test DB
  - Tests run against the full application (frontend + backend)

  **Must NOT do**:
  - No real LLM calls — mock the LLM at the backend level
  - No flaky timing-dependent assertions

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 4 (with Tasks 20, 21, 23)
  - **Blocks**: Task 23
  - **Blocked By**: Tasks 20, 21

  **References**:
  - Playwright: `https://playwright.dev/`
  - Full application endpoints documented in prior tasks

  **Acceptance Criteria**:
  - [ ] `npx playwright test` passes with 0 failures
  - [ ] At least 3 E2E test scenarios
  - [ ] Tests cover cross-feature workflows

  **QA Scenarios**:

  ```
  Scenario: E2E test suite passes
    Tool: Bash
    Preconditions: All code complete, backend + frontend running
    Steps:
      1. Run: npx playwright test
      2. Assert: 0 failures
    Expected Result: All E2E tests pass
    Failure Indicators: Test failures, timeout errors
    Evidence: .sisyphus/evidence/task-22-e2e-tests.txt
  ```

  **Commit**: YES
  - Message: `test(e2e): end-to-end integration tests`
  - Files: `e2e/`

- [x] 23. Final Desktop Shortcut Verification

  **What to do**:
  - Verify `start.bat` works end-to-end:
    1. Double-click start.bat
    2. FastAPI starts
    3. Browser opens at http://localhost:8000
    4. App loads with dashboard
  - Verify full user journey:
    1. Create new idea
    2. Chat with AI, get responses
    3. AI suggests phase advancement
    4. Approve advancement, see report generated
    5. Generate research prompt
    6. Upload research result
    7. View reports
    8. Score idea
    9. Advance to BUILD phase
    10. Generate Prometheus prompts
  - Fix any issues found during verification

  **Must NOT do**:
  - No new features — only fixes

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: [`/playwright`]
    - `/playwright`: Domain overlap — full E2E browser verification

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (final task before verification wave)
  - **Blocks**: FINAL wave
  - **Blocked By**: Tasks 19, 22

  **References**:
  - `start.bat` — Desktop shortcut
  - All prior task acceptance criteria

  **Acceptance Criteria**:
  - [ ] start.bat launches app in one click
  - [ ] Full user journey works without errors
  - [ ] All features accessible and functional

  **QA Scenarios**:

  ```
  Scenario: Full user journey end-to-end
    Tool: Playwright
    Preconditions: App running via start.bat
    Steps:
      1. Navigate to http://localhost:8000
      2. Create idea: "AI Recipe Generator"
      3. Open chat, send "I want to build an app that generates recipes"
      4. Assert: AI responds with clarifying questions
      5. Generate research prompt via Actions
      6. Assert: prompt appears with copy button
      7. View reports — assert: capture report exists
      8. View scores — assert: 7 dimensions scored
    Expected Result: Complete user journey succeeds
    Failure Indicators: Any step fails, page crashes, features broken
    Evidence: .sisyphus/evidence/task-23-full-journey.png
  ```

  **Commit**: YES
  - Message: `feat(launch): final desktop shortcut with tested app`
  - Files: `start.bat`, any fixes

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Present consolidated results to user and get explicit "okay" before completing.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, curl endpoint, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run linter + type checker + tests. Review all changed files for: bare excepts, print statements in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names.
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high` (+ playwright)
  Start from clean state. Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration (features working together, not isolation). Test edge cases: empty state, invalid input, rapid actions. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **Wave 1**: `feat(scaffold): project scaffolding with FastAPI + Svelte + SQLite config`
- **Wave 1**: `feat(db): SQLite models for ideas, phases, scores, messages, relationships`
- **Wave 1**: `feat(ui): Svelte project setup with design system and base layout`
- **Wave 1**: `feat(llm): OpenAI-compatible LLM client for codex-lb`
- **Wave 1**: `feat(storage): idea folder structure and file management service`
- **Wave 2**: `feat(chat): WebSocket chat API with LLM streaming`
- **Wave 2**: `feat(phases): 8-phase state machine with AI-driven progression`
- **Wave 2**: `feat(search): web search service with ZAI MCP + DuckDuckGo fallback`
- **Wave 2**: `feat(research): Gemini DR prompt generation service`
- **Wave 2**: `feat(scoring): 7-dimension numeric scoring engine`
- **Wave 2**: `feat(ui): chat interface component with markdown rendering`
- **Wave 2**: `feat(ui): ideas dashboard with list, create, manage`
- **Wave 3**: `feat(research): research file upload and AI integration`
- **Wave 3**: `feat(ideas): idea relationships — merge, split, derive`
- **Wave 3**: `feat(ui): reports section with per-phase document viewer`
- **Wave 3**: `feat(ui): actions panel for Gemini DR tasks`
- **Wave 3**: `feat(memory): project memory service — global + per-idea tracking`
- **Wave 3**: `feat(handoff): Prometheus build prompt generator`
- **Wave 3**: `feat(launch): desktop shortcut and start script`
- **Wave 4**: `test(backend): pytest suite for all backend services`
- **Wave 4**: `test(frontend): vitest suite for Svelte components`
- **Wave 4**: `test(e2e): end-to-end integration tests`
- **Wave 4**: `feat(launch): final desktop shortcut with tested app`

---

## Success Criteria

### Verification Commands
```bash
# Start the app
start.bat
# Expected: Browser opens at http://localhost:8000

# Backend health
curl http://localhost:8000/api/health
# Expected: {"status": "ok"}

# Create an idea
curl -X POST http://localhost:8000/api/ideas -H "Content-Type: application/json" -d '{"title": "AI Cooking App", "description": "An app that suggests recipes based on fridge contents"}'
# Expected: 201 with idea object including id, slug, phase="capture"

# List ideas
curl http://localhost:8000/api/ideas
# Expected: Array of ideas with scores and phases

# Send chat message (WebSocket test via curl)
curl -X POST http://localhost:8000/api/ideas/{id}/chat -H "Content-Type: application/json" -d '{"message": "I want to build an AI cooking app"}'
# Expected: 200 with AI response containing clarifying questions
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass (pytest + vitest)
- [ ] Desktop shortcut launches app in one click
- [ ] Chat streams responses with correct markdown
- [ ] Ideas progress through all 8 phases
- [ ] Scoring works on all 7 dimensions
- [ ] Gemini DR prompts generated and results uploaded
- [ ] Prometheus build prompts generated at final phase
