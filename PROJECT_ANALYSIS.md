# Idea Refinery - Project Analysis & Research Document

> **Purpose**: This document provides a comprehensive, non-technical analysis of the Idea Refinery project for research and strategic planning discussions. It contains no source code — only architecture, decisions, frameworks, and intentions.
> 
> **Version**: 1.0
> **Date**: 2026-04-27
> **Last Updated By**: OpenCode Agent

---

## 1. Project Vision & Core Purpose

**Idea Refinery** is an AI-powered idea development platform designed to take vague concepts and systematically refine them into well-defined, market-ready software projects. The platform acts as a structured "idea operating system" that guides users through a multi-phase refinement process, scores ideas against objective criteria, conducts automated research, and ultimately generates build-ready specifications for AI coding assistants.

### Primary Goals
- **Structured Idea Development**: Guide ideas through 8 distinct phases from initial capture to build-ready specification
- **Objective Evaluation**: Score ideas on 7 dimensions (TAM, Competition, Feasibility, Time-to-MVP, Revenue, Uniqueness, Personal Fit) using AI
- **Automated Research**: Generate targeted research prompts and integrate findings into the idea context
- **Build Handoff**: Produce comprehensive planning prompts and step-by-step build instructions for AI coding agents (specifically "Prometheus")
- **Project Twinning**: Import existing GitHub projects and maintain a "digital twin" with automated indexing, health monitoring, and worker-driven development
- **Local Worker Ecosystem**: Support local AI workers that can claim jobs, execute tasks, and push code back to repositories

### Target Users
- Solo developers and founders with many ideas who need help prioritizing and refining them
- Teams who want structured ideation before committing engineering resources
- Users who want to leverage AI coding assistants but need proper planning and context first

---

## 2. High-Level Architecture

The project follows a **three-tier architecture** with clear separation between frontend, backend, and worker systems.

### 2.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENTS                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Web App    │  │ Worker App   │  │ Local Workers    │  │
│  │  (Browser)   │  │  (Desktop)   │  │  (CLI/Scripts)   │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└────────────────────┬──────────────────┬─────────────────────┘
                     │                  │
                     ▼                  ▼
          ┌─────────────────┐  ┌──────────────┐
          │   REST API      │  │    SQS       │
          │   WebSocket     │  │   Queues     │
          └────────┬────────┘  └──────┬───────┘
                   │                   │
                   ▼                   ▼
          ┌─────────────────────────────────────┐
          │           BACKEND (FastAPI)          │
          │  ┌─────────┐ ┌─────────┐ ┌────────┐ │
          │  │  Ideas  │ │ Scoring │ │  Chat  │ │
          │  │  Mgmt   │ │ Engine  │ │  AI    │ │
          │  └─────────┘ └─────────┘ └────────┘ │
          │  ┌─────────┐ ┌─────────┐ ┌────────┐ │
          │  │ Research│ │  Phase  │ │ Project│ │
          │  │  Mgmt   │ │ Engine  │ │  Twin  │ │
          │  └─────────┘ └─────────┘ └────────┘ │
          │  ┌─────────┐ ┌─────────┐ ┌────────┐ │
          │  │  Build  │ │  Local  │ │ GitHub │ │
          │  │ Handoff │ │ Workers │ │  App   │ │
          │  └─────────┘ └─────────┘ └────────┘ │
          └─────────────────────────────────────┘
                     │
                     ▼
          ┌─────────────────────────────────────┐
          │         DATA LAYER                   │
          │  ┌─────────┐      ┌──────────────┐  │
          │  │DynamoDB │      │  File System │  │
          │  │(Cloud)  │      │  (Local)     │  │
          │  └─────────┘      └──────────────┘  │
          └─────────────────────────────────────┘
```

### 2.2 Deployment Targets

The backend is designed to run in **three modes**:

1. **Local Development**: In-memory repository, local file system, no external dependencies
2. **Self-Hosted**: DynamoDB-backed, can run on EC2 or similar with environment configuration
3. **Serverless (AWS Lambda)**: Fully managed, pay-per-use, with API Gateway, DynamoDB, and SQS queues

---

## 3. Technology Stack & Frameworks

### 3.1 Backend

| Component | Technology | Decision Rationale |
|-----------|-----------|-------------------|
| **Framework** | FastAPI (Python 3.11+) | Modern async Python, automatic OpenAPI docs, WebSocket support |
| **API Style** | REST + WebSocket | REST for CRUD, WebSocket for streaming AI chat responses |
| **AI Integration** | OpenAI-compatible API | Uses `openai` Python client with configurable base URLs |
| **Data Models** | Python Dataclasses | Lightweight, no ORM overhead, easy serialization |
| **Persistence** | In-Memory / DynamoDB | In-memory for dev/testing; DynamoDB for production (single-table design) |
| **Configuration** | Pydantic Settings | Type-safe env var loading with `.env` support |
| **Serverless** | Mangum | ASGI adapter for AWS Lambda |
| **AWS SDK** | Boto3 | DynamoDB, SQS, STS for worker credential leasing |
| **Auth** | PyJWT + Cryptography | Token-based worker authentication |
| **Web Search** | DuckDuckGo Search + HTML2Text | Free, no API key required for research augmentation |
| **HTTP Client** | HTTPX | Modern async HTTP client for model discovery and page fetching |

### 3.2 Frontend

| Component | Technology | Decision Rationale |
|-----------|-----------|-------------------|
| **Framework** | Svelte 5 | Reactive, compile-time framework, smaller bundle than React |
| **Build Tool** | Vite | Fast HMR, modern ES modules, easy configuration |
| **Routing** | Hash-based (custom) | No routing library dependency; simple `#/route/params` pattern |
| **State** | Svelte Runes (`$state`) | Native Svelte 5 reactivity, no external state library |
| **Styling** | Custom CSS | No CSS framework; component-scoped styles |
| **Icons** | Lucide Svelte | Lightweight, consistent icon set |
| **Markdown** | Marked + DOMPurify | Client-side markdown rendering with XSS protection |
| **Testing** | Vitest + Testing Library | Unit testing for components and logic |
| **E2E Testing** | Playwright | Cross-browser end-to-end testing |

### 3.3 Worker Desktop App

| Component | Technology | Decision Rationale |
|-----------|-----------|-------------------|
| **Framework** | Tauri v2 | Rust-based, lightweight alternative to Electron, smaller bundle |
| **Frontend** | Svelte 5 (same as web) | Code reuse, consistent UI patterns |
| **Backend** | Rust | System-level operations, git, HTTP client, SQS consumer |
| **Build** | Cargo + esbuild | Rust compilation with JS bundling |

### 3.4 Infrastructure (AWS)

| Component | Service | Decision Rationale |
|-----------|---------|-------------------|
| **Compute** | AWS Lambda (ARM64) | Cost-effective, scales to zero, Python 3.11 runtime |
| **API Gateway** | API Gateway v2 (HTTP API) | Cheaper than REST API, native CORS support |
| **Database** | DynamoDB (Single Table) | Pay-per-request billing, scales automatically |
| **Messaging** | SQS (FIFO Queues) | Ordered job delivery, dead-letter queues for reliability |
| **Auth** | IAM + STS AssumeRole | Scoped credential leasing for workers without long-term keys |
| **Deployment** | CloudFormation | Infrastructure as code, reproducible stacks |

---

## 4. Core Domain & Data Model

The application centers around several key domain concepts:

### 4.1 Idea
The central entity. Every idea has:
- Title, slug, description
- Current phase (one of 8 phases)
- Status (active, archived)
- Source type (manual entry, imported from GitHub)
- Timestamps for creation and updates

### 4.2 Phase System
Ideas progress through **8 structured phases**:

1. **Capture** — Document the core concept, problem, and target audience
2. **Clarify** — Define features, value proposition, user personas, differentiators
3. **Market Research** — Estimate TAM, analyze trends, validate demand
4. **Competitive Analysis** — Map competitors, define positioning and advantages
5. **Monetization** — Select revenue model, define pricing, estimate unit economics
6. **Feasibility** — Choose tech stack, estimate resources, assess risks and timeline
7. **Tech Spec** — Design architecture, define components, finalize MVP scope
8. **Build** — Generate implementation prompts and plan

### 4.3 Scoring
Ideas are scored on **7 dimensions** (0-10 scale):
- **TAM** — Total Addressable Market size
- **Competition** — Blue ocean potential (less competition = higher score)
- **Feasibility** — Technical feasibility
- **Time-to-MVP** — Speed to minimum viable product (faster = higher)
- **Revenue** — Clarity of revenue model
- **Uniqueness** — Novelty and differentiation
- **Personal Fit** — Alignment with builder's skills

### 4.4 Project Twin
A representation of an imported GitHub repository linked to an idea:
- Repository metadata (owner, repo, URLs, branches)
- Detected technology stack
- Test commands
- Index status and health status
- Open work queue count
- Code index artifacts (file inventory, dependency graph, architecture summary)

### 4.5 Work Items & Agent Runs
Jobs queued for local workers:
- **Work Items** — Queued tasks with status tracking (queued, claimed, running, completed, failed)
- **Agent Runs** — Specific AI agent executions tied to work items
- **Project Commits** — Commits made by workers tracked against work items

### 4.6 Local Workers
Machines that connect to execute jobs:
- Registration and approval workflow
- Capability-based job claiming
- Heartbeat and timeout management
- Credential leasing via AWS STS
- Event logging and status reporting

### 4.7 Memory System
Key-value storage for project context:
- Categories: stage, issue, bug, note, constraint, resource
- Scoped globally or per-idea
- Used to persist build state, prompts, and project context

---

## 5. Key Services & Responsibilities

### 5.1 Phase Engine
- Manages the 8-phase lifecycle of ideas
- Evaluates readiness for phase advancement using AI
- Generates phase summary reports
- **Decision**: Phase advancement is AI-suggested but **human-approved** — never automatic

### 5.2 Scoring Service
- Triggers AI scoring on all 7 dimensions
- Stores individual dimension scores with rationale
- Computes composite (weighted average) scores
- Supports manual override of any dimension
- Enables comparison across multiple ideas

### 5.3 Research Service
- Analyzes idea context and generates targeted research prompts
- Creates research tasks with topics and prompts
- Accepts research results (intended for Gemini Deep Research or similar)
- Integrates completed research into structured summaries
- **Decision**: Research is prompt-driven, not automated execution — human or external AI executes the research

### 5.4 Build Handoff Service
- Collects all idea context (reports, research, scores, memory)
- Generates a comprehensive "Prometheus planning prompt" — a single document for AI coding agents
- Creates step-by-step build prompts for 6 build phases:
  1. Project Setup
  2. Database
  3. Backend
  4. Frontend
  5. Integration
  6. Testing
- Tracks build progress through memory system

### 5.5 Chat Service
- Provides conversational AI interface for each idea
- Uses system prompts tailored to the current phase
- Streams responses via WebSocket
- Persists message history
- **Decision**: Chat is context-aware — the AI knows the current phase and asks appropriate questions

### 5.6 Project Twin Service
- Imports GitHub repositories and links them to ideas
- Manages code indexing jobs
- Job queue management with claim/heartbeat/complete/fail lifecycle
- Requeue expired claims based on heartbeat timeouts
- Tracks project health and commit history

### 5.7 Local Worker Service
- Registration request workflow with pairing tokens
- Approve/deny/revoke worker management
- Credential rotation and leasing
- Token verification and heartbeat tracking
- SQS event processing for worker events

### 5.8 Relationship Service
- Links ideas together (reference, derive, merge, split)
- AI-powered detection of related ideas
- Merging: Combines two ideas into one, archiving originals
- Splitting: Divides one idea into two distinct ideas
- Deriving: Creates a new idea based on an existing one

### 5.9 Memory Service
- CRUD operations for project memory
- Context assembly for AI prompts
- Used extensively by Build Handoff to track build state

### 5.10 Web Search Service
- DuckDuckGo search with rate limiting (10 req/min)
- In-memory caching (1-hour TTL)
- Page fetching and text extraction
- **Decision**: Free search, no API keys required, graceful failure handling

### 5.11 LLM Service
- Multi-provider support (OpenCode Go, Z.ai)
- Auto-discovery of models from `/models` endpoint
- Reads Claude Desktop settings for agent model configuration
- Streaming and synchronous completion modes
- Configurable via environment variables

### 5.12 GitHub App Service
- GitHub App integration for repository access
- Webhook handling for installation events
- Installation token management
- Repository listing

---

## 6. Implementation Decisions & Philosophy

### 6.1 Storage Strategy

**Decision**: Dual storage approach — in-memory for dev/test, DynamoDB for production.

**Rationale**:
- Enables rapid local development without AWS credentials
- Single-table DynamoDB design minimizes cost and complexity
- Repository pattern abstracts storage implementation
- Easy testing with in-memory fixtures

**DynamoDB Design**:
- Single table with PK/SK partition/sort keys
- GSI1 for status-based queries (active ideas, project twins, work items)
- GSI2 for relationship queries (idea-centric lookups, project-centric lookups)
- Entity type stored in each item for deserialization

### 6.2 AI Provider Strategy

**Decision**: OpenAI-compatible API with multiple provider support.

**Rationale**:
- Avoids vendor lock-in
- Can switch between providers (OpenCode Go, Z.ai, OpenAI, etc.)
- Reads Claude Desktop's `settings.json` to discover configured agent models
- Falls back to environment variables if no Claude config found

### 6.3 Worker Architecture

**Decision**: Local workers with SQS-based job distribution.

**Rationale**:
- Workers run on user's machines (privacy, cost control)
- SQS provides reliable job delivery and ordering (FIFO queues)
- STS credential leasing gives temporary, scoped AWS access
- Workers claim jobs; backend doesn't push — reduces complexity
- One job per project at a time to prevent conflicts

### 6.4 Frontend Architecture

**Decision**: SPA with hash-based routing, no meta-framework.

**Rationale**:
- Svelte 5 runes provide sufficient reactivity without stores
- Hash routing avoids server-side configuration for SPA fallback
- Simple component hierarchy: AppShell → Route Components
- API client is a thin wrapper around `fetch`

### 6.5 Build Handoff Philosophy

**Decision**: Generate prompts, not code.

**Rationale**:
- The platform doesn't build — it plans and instructs
- Prometheus (or other AI coding agents) executes the build
- Step-by-step prompts allow human review at each stage
- Memory system tracks progress across sessions

### 6.6 Testing Strategy

**Decision**: Comprehensive test coverage with mocked AI.

**Backend Tests**:
- Async test client using HTTPX and ASGI transport
- In-memory repository fixtures
- Mock LLM service with canned responses
- Tests cover all routers and services

**Frontend Tests**:
- Vitest for unit testing components
- Testing Library Svelte for component interaction
- Playwright for E2E testing

### 6.7 Security Decisions

- **Worker Auth**: SHA-256 hashed tokens, not stored plaintext
- **Credential Leasing**: AWS STS AssumeRole with scoped policies, 1-hour TTL
- **GitHub Integration**: App-based (not OAuth), private key authentication
- **CORS**: Configured for local development origins

---

## 7. What Has Been Built

### 7.1 Backend (Complete)

**API Endpoints** (Routers):
- **Ideas** — CRUD, list active, archive
- **Chat** — Send messages, get history, WebSocket streaming
- **Phases** — Get current phase, suggest advancement, approve/reject
- **Research** — Generate prompts, create tasks, upload results, integrate
- **Scoring** — Score idea, get scores, composite score, compare ideas, manual override
- **Relationships** — Create, list, merge, split, derive, detect related
- **Reports** — Get phase reports
- **Memory** — Set, get, delete, list by category
- **Build** — Generate Prometheus prompt, generate step prompts, get build state, mark complete
- **GitHub** — App webhook, list installations, list repos
- **Projects** — Import GitHub project, get status, enqueue reindex
- **Workers** — Claim job, heartbeat, complete, fail, list jobs
- **Local Workers** — Register, approve, deny, revoke, rotate, dashboard, verify

**Services**:
- Phase Engine, Scoring, Research, Build Handoff, Chat, Memory, Relationships
- Project Twin, Local Worker, Web Search, LLM, GitHub App, File Manager
- Worker SQS Publisher

**Data Layer**:
- Repository abstraction with InMemory and DynamoDB implementations
- 15+ entity types with full CRUD

### 7.2 Frontend (Complete)

**Pages/Routes**:
- **Dashboard** — Idea cards, create idea, import project, score visualization
- **Chat** — Phase-aware chat interface with markdown rendering
- **Reports** — Phase report viewer and list
- **Actions** — Research tasks, build queue, file upload
- **Project Twin** — Project status, jobs, agent runs, commits
- **Workers** — Local worker dashboard, registration, approval

**Components**:
- Layout: AppShell, Sidebar
- UI: Button, Card, Input, Modal, Badge
- Dashboard: IdeaCard, IdeaDetail, CreateIdea, ImportProject, ScoreBar
- Chat: ChatView, ChatInput, MessageBubble, MessageList, MarkdownRenderer, PhaseIndicator
- Actions: Actions, BuildQueue, FileUpload, ResearchTaskCard
- Reports: Reports, ReportList, ReportViewer
- ProjectTwin: ProjectTwinView
- LocalWorkers: LocalWorkers

### 7.3 Worker Desktop App (In Progress)

**Tauri v2 Application**:
- Svelte 5 frontend for worker dashboard
- Rust backend for HTTP client, SQS operations, git operations
- Cross-platform builds (Windows .exe/.msi, macOS .dmg planned)

### 7.4 Infrastructure (Complete)

**CloudFormation Template**:
- Lambda function (ARM64, Python 3.11)
- API Gateway v2 with CORS
- DynamoDB single-table with 2 GSIs
- SQS FIFO queues (commands + events) with dead-letter queues
- IAM roles for backend and worker clients
- Environment variable configuration for all services

### 7.5 Workers (Legacy + New)

**openclaude-local** (Python CLI worker):
- Deprecated in favor of Tauri desktop app
- Basic job claiming and execution
- Install scripts for PowerShell and Bash

---

## 8. Project Structure

```
idearefinery/
├── backend/                 # FastAPI Python backend
│   ├── app/
│   │   ├── main.py          # FastAPI app, CORS, static files, routers
│   │   ├── config.py        # Pydantic settings from env
│   │   ├── repository.py    # Data models + InMemory + DynamoDB repos
│   │   ├── lambda_handler.py # AWS Lambda entry point
│   │   ├── test_server.py   # Test server with mocked LLM
│   │   ├── init_db.py       # Database initialization
│   │   ├── database.py      # Database connection utilities
│   │   ├── routers/         # API route handlers (13 routers)
│   │   ├── services/        # Business logic (12 services)
│   │   └── models/          # Model re-exports
│   └── tests/               # Pytest test suite (12 test files)
├── frontend/                # Svelte 5 SPA
│   ├── src/
│   │   ├── App.svelte       # Root component, routing
│   │   ├── main.js          # Entry point
│   │   ├── app.css          # Global styles
│   │   ├── lib/
│   │   │   ├── api.js       # API client utilities
│   │   │   └── components/  # Svelte components organized by feature
│   │   ├── routes/          # Page components
│   │   └── mocks/           # Test mocks
│   └── package.json         # Vite, Svelte 5, Vitest dependencies
├── worker-app/              # Tauri v2 desktop application
│   ├── src/                 # Svelte frontend
│   └── src-tauri/           # Rust backend, build config
├── workers/                 # Legacy and current worker implementations
│   └── openclaude-local/    # Python CLI worker (deprecated)
├── infra/                   # Infrastructure as Code
│   └── cloudformation/
│       └── idearefinery-backend.yaml
├── e2e/                     # Playwright end-to-end tests
├── data/                    # Local data storage (gitignored)
├── graphify-out/            # Knowledge graph output
├── package.json             # Root package.json (Playwright)
├── pyproject.toml           # Python project config
└── AGENTS.md                # AI agent instructions
```

---

## 9. Development Workflow

### Local Development
1. Install Python 3.11+ and Node.js 18+
2. Create virtual environment and install Python dependencies
3. Install frontend dependencies with npm
4. Run backend with uvicorn (port 8000)
5. Run frontend with Vite dev server (port 5173)
6. Backend serves frontend static files in production

### Testing
- Backend: `pytest` with async fixtures and mocked LLM
- Frontend: `vitest run` for unit tests
- E2E: Playwright tests across browsers

### Deployment
- **CloudFormation**: Deploy stack to AWS, upload Lambda package
- **Environment Variables**: Configure AI providers, GitHub App, worker queues
- **Frontend Build**: `vite build` produces static files in `frontend/dist/`

---

## 10. Current Intentions & Future Directions

### 10.1 Immediate Goals
- Complete the Tauri v2 worker desktop app to replace the Python CLI worker
- Improve build handoff prompts based on real-world usage with Prometheus
- Enhance project twin code indexing with deeper AST analysis
- Add more sophisticated health checking for imported projects

### 10.2 Research Areas
- **Multi-Provider AI**: Better model selection per task type (reasoning vs coding vs research)
- **Vector Search**: Semantic search across idea history and research findings
- **Automated Testing**: Self-healing tests for worker-driven code changes
- **Deployment Integration**: Connect project twins to actual deployment pipelines

### 10.3 Long-Term Vision
- **Idea Marketplace**: Share refined ideas and project templates
- **Team Collaboration**: Multi-user support with roles and permissions
- **Integration Ecosystem**: Plugins for Jira, Notion, Figma, etc.
- **Autonomous Refinement**: More autonomous phase advancement with human checkpoints
- **Code Generation**: Direct code generation and PR creation via workers

### 10.4 Known Technical Debt
- Frontend uses hash-based routing; may migrate to SvelteKit for SSR/features
- Worker app is early stage; needs robust error handling and reconnection
- Code indexing is basic; needs deeper analysis for complex codebases
- No real-time updates; polling used for job status

---

## 11. Key Constraints & Assumptions

### Constraints
- **Cost-conscious**: Designed for personal use; AWS resources use pay-per-use billing
- **Privacy-first**: Local workers keep code on user's machine
- **AI-agnostic**: Works with any OpenAI-compatible API
- **Offline-friendly**: Core functionality works without internet (except AI and search)

### Assumptions
- Users have AWS accounts if using cloud features
- Users have GitHub accounts for project import
- AI providers are configured with valid API keys
- Local workers have git and appropriate language tooling installed

---

## 12. How to Use This Document

This document is designed to be uploaded to ChatGPT (or any AI research partner) to enable deep architectural discussions without exposing source code.

### Suggested Discussion Topics
1. "Given this architecture, how would you implement [feature]?"
2. "What are the trade-offs of the current [technology] choice vs [alternative]?"
3. "How would you scale the [component] for team usage?"
4. "What security improvements would you recommend for the worker system?"
5. "How would you design [new feature] within these constraints?"

### Modification History
| Date | Changes |
|------|---------|
| 2026-04-27 | Initial document creation |

---

*This document was generated by analyzing the Idea Refinery codebase using graphify knowledge graph extraction. It intentionally excludes all source code, function signatures, and implementation details in favor of architectural context and strategic decision-making.*
