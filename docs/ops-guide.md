# Operations Guide: Idea Refinery

This guide covers day-to-day operations: starting the backend, running the Karigar worker daemon, creating factory runs, and monitoring the system.

## Architecture

```
┌──────────────────────┐     HTTP Worker API     ┌───────────────────────┐
│  Backend (FastAPI)   │◄──────────────────────►│  Karigar Worker        │
│  port 8000           │  claim / complete / fail │  daemon or CLI mode   │
│  DynamoDB via Floci  │  heartbeat / register    │                        │
│  localhost:4566      │                          │  Runs engines,          │
│                      │                          │  verifications,         │
└──────────────────────┘                          │  writes artifacts       │
                                                  └───────────────────────┘
```

- **Backend** — FastAPI app serving the API, SPA frontend, and worker endpoints.
- **Karigar** — Worker daemon that polls the backend for jobs, executes them via OpenCode/engines, and reports results.
- **Floci** — Local AWS emulator providing DynamoDB, SQS, S3, STS at `http://localhost:4566`.

## Prerequisites

- Python 3.11+ with `uv` or pip
- Node.js (for frontend build)
- Docker (for Floci)
- PowerShell (for Windows automation scripts; Linux users use direct commands below)
- AWS CLI configured with fake local credentials (see Environment Variables)

### Environment Variables

For local development (`local_stack.ps1` sets these automatically):

```bash
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=ap-south-1
export AWS_REGION=ap-south-1
export AWS_ENDPOINT_URL=http://localhost:4566
export IDEAREFINERY_WORKER_AUTH_TOKEN=local-worker-token
export IDEAREFINERY_STORAGE=dynamodb
export DYNAMODB_TABLE_NAME=idearefinery-prod
```

These variables are required for all local operations. The `local_stack.ps1` script sets them; if running manually, export them first.

## 1. Starting the Backend

### Option A: One-Command Full Stack (Windows/PowerShell)

From the repo root:

```powershell
# Full startup: Floci → infra → Lambda → frontend → backend
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-up

# Or via Makefile:
make local-up
```

This single command:
1. Starts the Floci Docker container (port 4566)
2. Applies CloudFormation infrastructure (DynamoDB table, SQS queues)
3. Deploys local Lambda (optional)
4. Builds the frontend (`npm run build` in `frontend/`)
5. Starts the FastAPI backend on `http://127.0.0.1:8000`

### Option B: Manual Backend Start (Linux, or without full stack)

If Floci is already running and infra is applied, build the frontend and start the backend:

```bash
# Build frontend (required for serving the SPA)
npm --prefix frontend run build

# From repo root, with environment variables set:
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

# Or with system python:
python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

The backend serves static files from `frontend/dist/`. If the frontend has not been built, the API will still work but the root path will return 404.

### Option C: Floci + Backend (no frontend)

```bash
# Start Floci
docker compose -f docker-compose.floci.yml up -d

# Wait for Floci health
curl -s http://localhost:4566/_localstack/health

# Apply infrastructure
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_floci.ps1 -Command infra-apply

# Start backend
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

### Health Check

```bash
curl http://127.0.0.1:8000/api/health
# Expected: {"status":"ok"}
```

## 2. Starting the Karigar Daemon

The Karigar daemon polls the backend for available jobs, claims them, executes them, and reports results.

### Daemon Mode (Recommended)

```bash
python -m workers.karigar daemon \
  --worker-id "my-local-worker" \
  --worker-token "local-worker-token" \
  --api-base "http://127.0.0.1:8000" \
  --poll-interval 20 \
  --heartbeat-interval 15 \
  --factory-run-id "" \
  --register
```

**Key flags:**

| Flag | Default | Description |
|---|---|---|
| `--worker-id` | (required) | Unique worker identifier |
| `--worker-token` | (required) | Auth token matching `IDEAREFINERY_WORKER_AUTH_TOKEN` |
| `--api-base` | `https://api.karkhana.one` | Backend base URL |
| `--poll-interval` | `20` | Seconds between job polls when idle |
| `--heartbeat-interval` | `15` | Seconds between heartbeat pings for in-flight jobs |
| `--run-once` | off | Execute one cycle and exit (for Windows service / Tauri) |
| `--register` | off | Register worker with backend before starting |
| `--state-dir` | `~/.karigar` | Directory for persistent state file |
| `--factory-run-id` | (empty) | Factory run ID for auto-ledger entries |

**Circuit breaker flags:**

| Flag | Default | Description |
|---|---|---|
| `--max-jobs-per-day` | `100` | Hard cap on jobs per UTC day |
| `--max-retries-per-job` | `3` | Max retries per failed job before giving up |
| `--token-budget-per-day` | `1,000,000` | Estimated token budget cap per day |

### Daemon Status

```bash
python -m workers.karigar daemon --state-dir ~/.karigar status
```

Output shows the persistent state: `worker_id`, `jobs_completed_today`, `jobs_failed_today`, `total_spend`, `last_heartbeat_utc`.

### Legacy Backend Mode

```bash
python -m workers.karigar \
  --backend \
  --worker-id "my-worker" \
  --worker-token "local-worker-token" \
  --api-base "http://127.0.0.1:8000" \
  --poll-interval 5 \
  --max-jobs 0 \
  --register
```

This is the simpler poll-claim-execute loop without daemon features (no state persistence, no circuit breaker, no heartbeat, no graceful shutdown). Use `--max-jobs 0` for an infinite loop, or set a positive number to exit after N jobs.

### Local Single-Job Mode (no backend)

```bash
python -m workers.karigar --job-json workers/karigar/examples/mock-job.json
```

Useful for testing engines and execution outside of the backend loop.

### Graceful Shutdown

Send `SIGTERM` or `SIGINT` (Ctrl+C) to the daemon. It will:
- Allow the current job to complete
- Report the result to the backend
- Save state to `daemon.json`
- Exit cleanly

## 3. Creating Factory Runs

Factory runs are the primary work unit. They bind a project to a template and define the autonomy level and configuration.

### API Endpoints

```
POST   /api/projects/{project_id}/factory-runs     Create a factory run
GET    /api/projects/{project_id}/factory-runs     List factory runs for a project
GET    /api/factory-runs/{factory_run_id}           Get a single factory run
POST   /api/factory-runs/{id}/research-artifacts    Add research artifacts
POST   /api/factory-runs/{id}/research-handoff      Create research handoff (review packet)
```

### Creating a Run via cURL

```bash
curl -s -X POST http://127.0.0.1:8000/api/projects/my-project/factory-runs \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "full-stack-feature",
    "autonomy_level": "autonomous_development",
    "config": {
      "feature_name": "user-profiles",
      "branch": "feature/user-profiles"
    },
    "intent": {
      "description": "Add user profile management to the application"
    }
  }' | python3 -m json.tool
```

**Response example:**
```json
{
  "factory_run_id": "run-abc123",
  "project_id": "my-project",
  "template_id": "full-stack-feature",
  "autonomy_level": "autonomous_development",
  "status": "pending",
  "phases": [...],
  "created_at": "2026-05-12T10:00:00Z"
}
```

### Listing Runs

```bash
curl -s http://127.0.0.1:8000/api/projects/my-project/factory-runs | python3 -m json.tool
```

### Getting a Single Run

```bash
curl -s http://127.0.0.1:8000/api/factory-runs/run-abc123 | python3 -m json.tool
```

### Worker Registration

Workers must be registered before they can claim jobs. The `--register` flag handles this during daemon startup. Registration can also be done via the API:

```bash
curl -s -X POST http://127.0.0.1:8000/api/local-workers/register \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer local-worker-token" \
  -d '{
    "machine_name": "dev-machine",
    "platform": "linux",
    "engine": "opencode",
    "display_name": "My Local Worker"
  }' | python3 -m json.tool
```

### Worker Job Lifecycle

1. **Claim** — `POST /api/worker/claim` — Worker polls and claims a pending job
2. **Heartbeat** — `POST /api/worker/jobs/{id}/heartbeat` — Sent every 15s during execution
3. **Complete** — `POST /api/worker/jobs/{id}/complete` — Job succeeded, includes artifacts and test results
4. **Fail** — `POST /api/worker/jobs/{id}/fail` — Job failed, includes error and retry info

## 4. Monitoring

### Backend Health

```bash
# Basic health check
curl -s http://127.0.0.1:8000/api/health

# CORS test
curl -s -I -H "Origin: http://localhost:5173" http://127.0.0.1:8000/api/health
```

### Smoke Test (Full Stack)

```powershell
# PowerShell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-smoke-test

# Or via Makefile
make local-smoke-test
```

The smoke test checks:
- Floci health endpoint
- DynamoDB table existence
- SQS queue listing
- Backend health endpoint
- Worker auth (rejects missing token, accepts valid token)
- Frontend serving

### Stack Status

```powershell
# PowerShell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-status

# Or via Makefile
make local-status
```

Reports: Floci status, backend health, autostart configuration, process info.

### Daemon State Monitoring

```bash
# View persistent daemon state
cat ~/.karigar/daemon.json | python3 -m json.tool

# Or via daemon CLI
python -m workers.karigar daemon status

# Watch daemon state in real-time
watch -n 5 'cat ~/.karigar/daemon.json | python3 -m json.tool'
```

**State fields:**
| Field | Description |
|---|---|
| `worker_id` | Worker identifier |
| `last_seen_job` | ID of most recently processed job |
| `jobs_completed_today` | Successful + failed today (UTC) |
| `jobs_failed_today` | Only failures today |
| `total_spend` | Running estimated token spend in USD |
| `today` | ISO date for daily counters |
| `last_heartbeat_utc` | Last heartbeat timestamp |

### Logs

```powershell
# PowerShell (local stack logs)
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-logs

# Or via Makefile
make local-logs
```

Backend process output and Floci container logs are captured in `.local/logs/`.

### Key API Endpoints for Monitoring

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/health` | GET | Backend liveness |
| `/api/projects/{id}/factory-runs` | GET | List active runs |
| `/api/factory-runs/{id}` | GET | Run detail with phase status |
| `/api/local-workers/register` | POST | Register a worker |
| `/api/local-workers/{worker_id}/events` | POST | Push worker events |
| `/api/worker/claim` | POST | Worker claims pending job |
| `/api/ledgers/{run_id}` | GET | Factory run ledger |

### Restarting

```powershell
# Restart just the backend (Floci stays running)
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-restart

# Or via Makefile
make local-restart
```

### Shutting Down

```powershell
# Stop backend and Floci
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-down

# Or via Makefile
make local-down
```

For the Karigar daemon: send SIGTERM (Ctrl+C in terminal) or `kill <pid>`.

## 5. Troubleshooting

### Floci Not Starting

```bash
# Check Docker is running
docker info

# Check Floci container status
docker ps -a --filter "name=floci"

# Restart Floci
docker compose -f docker-compose.floci.yml down
docker compose -f docker-compose.floci.yml up -d
```

### Backend Fails to Start

```bash
# Check port availability
lsof -i :8000

# Check environment variables
echo $AWS_ENDPOINT_URL
echo $IDEAREFINERY_WORKER_AUTH_TOKEN

# Start with verbose logging
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --log-level debug
```

### Worker Can't Claim Jobs

1. Verify backend is healthy: `curl http://127.0.0.1:8000/api/health`
2. Check worker token matches: `$IDEAREFINERY_WORKER_AUTH_TOKEN` must match `--worker-token`
3. Register the worker: use `--register` flag or POST to `/api/local-workers/register`
4. Verify factory runs exist and are in `pending` status
5. Check circuit breaker: if `jobs_completed_today >= max_jobs_per_day`, daemon stops

### Worker Auth Rejected (401)

The backend rejects requests with `401 Invalid worker token`. Verify:
- `IDEAREFINERY_WORKER_AUTH_TOKEN` env var is set on the backend
- Worker passes matching `--worker-token`
- Header is `x-idearefinery-worker-token: <token>` or `Authorization: Bearer <token>`

### DynamoDB Not Accessible

```bash
# List tables in local Floci
aws dynamodb list-tables --endpoint-url http://localhost:4566

# Check the table exists
aws dynamodb describe-table \
  --table-name idearefinery-prod \
  --endpoint-url http://localhost:4566
```

If the table is missing, re-apply infrastructure:
```bash
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_floci.ps1 -Command infra-apply
```

## 6. Test Commands

### Full Test Suite

```bash
# Karigar worker tests
python3 -m pytest workers/karigar/tests/ -q --tb=short

# Backend tests
python3 -m pytest backend/tests/ -q --tb=short

# All tests combined
python3 -m pytest workers/karigar/tests/ backend/tests/ -q --tb=short
```

### Key Test Files

```
workers/karigar/tests/
├── test_circuit_breaker.py    Circuit breaker logic
├── test_backend_client.py     Backend HTTP client
├── test_karigar_runner.py     Job execution runner
├── test_e2e_integration.py    End-to-end integration
├── test_real_engines.py       Real engine dispatch
└── test_daemon.py             Daemon controller

backend/tests/
├── test_factory_run.py        Factory run core
├── test_factory_run_service.py Factory run service
├── test_factory_run_e2e.py    Factory run E2E
├── test_factory_orchestrator.py Orchestration
├── test_phase_engine.py       Phase engine
├── test_policy_engine.py      Policy engine
├── test_worker_context_bundle.py Worker context
└── ... (30+ test files)
```

## 7. Auto-Start (Windows)

Install automatic startup on user logon:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-install-autostart
```

Disable:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-uninstall-autostart
```

Check status:

```powershell
make local-status
```

The script registers a Task Scheduler task (`IdeaRefineryLocalStack`) or falls back to a Startup-folder shortcut.
