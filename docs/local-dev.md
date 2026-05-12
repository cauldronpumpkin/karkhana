# Local Development Setup

> Single backend server over Floci (local AWS emulator). For the PowerShell-driven script flow, see `docs/local-first-floci.md` and `scripts/local_stack.ps1`.
>
> **Note:** The Lambda/API Gateway deployment path (via `backend.app.lambda_handler`) is deprecated. The supported runtime is a direct Uvicorn server on `:8000` using `uvicorn backend.app.main:app`. CloudFormation templates and Lambda-related files are retained for history and retirement inventory only.

## Prerequisites

- **Docker** — for running Floci
- **Python 3.11+** — for the backend
- **git** — to clone the repo (if not already done)

## Quick Start (bash / WSL)

### 1. Start Floci

```bash
docker compose -f docker-compose.floci.yml up -d
```

Wait for Floci to be ready:

```bash
sleep 5
curl -s http://localhost:4566/_floci/health | head -1
# Expect: {"version":"...","edition":...}
```

### 2. Create the DynamoDB Table

> The table may already exist from a previous setup — the command is idempotent.

```bash
AWS_ACCESS_KEY_ID=test \
AWS_SECRET_ACCESS_KEY=test \
AWS_DEFAULT_REGION=ap-south-1 \
AWS_ENDPOINT_URL=http://localhost:4566 \
aws dynamodb create-table \
  --table-name idearefinery-prod \
  --attribute-definitions \
    AttributeName=pk,AttributeType=S \
    AttributeName=sk,AttributeType=S \
  --key-schema \
    AttributeName=pk,KeyType=HASH \
    AttributeName=sk,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --endpoint-url http://localhost:4566 \
  2>&1 || echo "Table may already exist"
```

Verify the table exists:

```bash
AWS_ACCESS_KEY_ID=test \
AWS_SECRET_ACCESS_KEY=test \
AWS_DEFAULT_REGION=ap-south-1 \
aws dynamodb list-tables \
  --endpoint-url http://localhost:4566
```

### 3. Install Python Dependencies

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv-linux
source .venv-linux/bin/activate
pip install fastapi uvicorn boto3 pydantic-settings python-dotenv \
  python-multipart httpx openai mangum PyJWT cryptography pyyaml
```

> The project also has a `pyproject.toml` for the full dependency list. The packages above are the minimum for local dev.

### 4. Start the Backend

```bash
AWS_ACCESS_KEY_ID=test \
AWS_SECRET_ACCESS_KEY=test \
AWS_DEFAULT_REGION=ap-south-1 \
AWS_REGION=ap-south-1 \
AWS_ENDPOINT_URL=http://localhost:4566 \
AWS_ENDPOINT_URL_DYNAMODB=http://localhost:4566 \
IDEAREFINERY_STORAGE=dynamodb \
DYNAMODB_TABLE_NAME=idearefinery-prod \
IDEAREFINERY_WORKER_AUTH_TOKEN=local-worker-token \
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

Or run in the background:

```bash
AWS_ACCESS_KEY_ID=test \
AWS_SECRET_ACCESS_KEY=test \
AWS_DEFAULT_REGION=ap-south-1 \
AWS_REGION=ap-south-1 \
AWS_ENDPOINT_URL=http://localhost:4566 \
AWS_ENDPOINT_URL_DYNAMODB=http://localhost:4566 \
IDEAREFINERY_STORAGE=dynamodb \
DYNAMODB_TABLE_NAME=idearefinery-prod \
IDEAREFINERY_WORKER_AUTH_TOKEN=local-worker-token \
nohup uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 \
  > /tmp/backend.log 2>&1 &
```

### 5. Verify

```bash
# Health check
curl -s http://localhost:8000/api/health
# Expect: {"status":"ok"}

# Swagger docs
curl -s http://localhost:8000/docs | head -5
# Expect: <!DOCTYPE html>...

# Open in browser
# http://localhost:8000/docs
```

## Environment Variables Reference

All required env vars for local development:

| Variable | Value | Notes |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | `test` | Fake credential for Floci |
| `AWS_SECRET_ACCESS_KEY` | `test` | Fake credential for Floci |
| `AWS_DEFAULT_REGION` | `ap-south-1` | Must match table region |
| `AWS_REGION` | `ap-south-1` | Used by repository layer |
| `AWS_ENDPOINT_URL` | `http://localhost:4566` | Base Floci endpoint |
| `AWS_ENDPOINT_URL_DYNAMODB` | `http://localhost:4566` | Per-service override (checked first) |
| `IDEAREFINERY_STORAGE` | `dynamodb` | Storage backend selection |
| `DYNAMODB_TABLE_NAME` | `idearefinery-prod` | Table to use |
| `IDEAREFINERY_WORKER_AUTH_TOKEN` | `local-worker-token` | Worker auth token |

Optional for worker/SQS features (not needed for basic API):

| Variable | Value |
|---|---|
| `AWS_ENDPOINT_URL_SQS` | `http://localhost:4566` |
| `AWS_ENDPOINT_URL_STS` | `http://localhost:4566` |
| `AWS_ENDPOINT_URL_S3` | `http://localhost:4566` |
| `IDEAREFINERY_WORKER_SQS_REGION` | `ap-south-1` |
| `IDEAREFINERY_WORKER_COMMAND_QUEUE_URL` | `http://localhost:4566/000000000000/idearefinery-worker-commands.fifo` |
| `IDEAREFINERY_WORKER_EVENT_QUEUE_URL` | `http://localhost:4566/000000000000/idearefinery-worker-events.fifo` |
| `IDEAREFINERY_CORS_ORIGINS` | `http://localhost:5173,http://localhost:8000` |
| `IDEAREFINERY_CORS_ORIGIN_REGEX` | (empty for local) |

All of these are set automatically by `scripts/local_stack.ps1`. The table above is useful for manual setup or debugging.

## Project Structure

```
.
├── docker-compose.floci.yml   # Floci container config
├── backend/
│   └── app/
│       ├── main.py            # FastAPI app entry point
│       ├── config.py          # Pydantic settings (reads .env)
│       ├── repository.py      # Storage backends (DynamoDB, JSON, memory)
│       └── aws_endpoints.py   # Endpoint URL resolution
├── scripts/
│   ├── local_stack.ps1        # PowerShell orchestration script
│   └── local_floci.ps1        # Lower-level Floci ops
└── docs/
    ├── local-dev.md           # This file — manual bash setup
    ├── local-first-floci.md   # PowerShell-driven flow
    └── local-floci.md         # Floci runbook
```

## Troubleshooting

### "Table not found" on startup

Ensure both `AWS_ENDPOINT_URL` and `AWS_ENDPOINT_URL_DYNAMODB` are set. The code checks the per-service override first:

```python
def endpoint_url(service: str) -> str | None:
    service_key = service.upper().replace("-", "_")
    return os.getenv(f"AWS_ENDPOINT_URL_{service_key}") or os.getenv("AWS_ENDPOINT_URL")
```

Without these, boto3 connects to real AWS (and the table won't exist there).

### Floci health check fails

- Ensure Docker is running
- Check `docker compose -f docker-compose.floci.yml ps`
- Check `docker logs idearefinery-floci`
- Floci may take 5–10 seconds on first start

### Port 8000 already in use

```bash
fuser -k 8000/tcp
# or
lsof -ti:8000 | xargs -r kill -9
```

### Python dependencies missing

If you see `ModuleNotFoundError`, ensure you're using the virtual environment and all packages from `pyproject.toml` dependencies are installed.

### Windows venv on WSL

The repo ships a `.venv/` with Windows `.exe` binaries. On WSL, create a separate Linux venv (e.g., `.venv-linux/`) instead.

## Cleanup

```bash
# Stop the backend
fuser -k 8000/tcp

# Stop Floci
docker compose -f docker-compose.floci.yml down

# Remove Floci data volumes (optional)
docker compose -f docker-compose.floci.yml down -v
```

## See Also

- `docs/local-first-floci.md` — PowerShell-driven local runtime (the primary supported flow)
- `docs/local-floci.md` — Lower-level Floci runbook
- `.env.local.example` — Environment variable reference
- `scripts/local_stack.ps1` — Orchestration script for `local-up`, `local-down`, etc.
