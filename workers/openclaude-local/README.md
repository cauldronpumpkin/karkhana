# IdeaRefinery OpenClaude Local Worker

This folder is the complete local worker package for IdeaRefinery/Karkhana. Give a coding app this folder URL, have it run the installer, and the worker will request approval from the web app before receiving SQS credentials.

## What It Does

- Requests pairing with `POST /api/local-workers/register`.
- Waits until the Local Workers page approves the machine.
- Stores the worker id, API token, queue URLs, and short-lived SQS credentials in a local state file.
- Long-polls the shared FIFO command queue for `job_available` messages.
- Claims jobs through the backend before doing any work.
- Runs OpenClaude by default, with Codex/OpenCode fallback support.
- Uses branch-and-PR autonomy by default: create a branch, run tests, push it, report results, and never merge to main.
- Allows full repo control only when both local config and the job payload opt in.

## Quick Start

Windows:

```powershell
.\install.ps1 -ApiBase "https://your-api.example.com"
```

macOS/Linux:

```bash
chmod +x ./install.sh
./install.sh https://your-api.example.com
```

Then open the app, go to `#/workers`, and approve the pending connection request. The installer keeps polling until approval and writes local state.

## Manual Run

```bash
python worker.py pair --api-base https://your-api.example.com
python worker.py run
```

Use `python worker.py once` to process at most one message/job. The worker state defaults to:

```text
~/.idearefinery-worker/openclaude-local/state.json
```

## Configuration

Copy `worker-config.example.json` to `worker-config.json` or pass values through environment variables:

- `IDEAREFINERY_API_BASE_URL`
- `IDEAREFINERY_WORKER_STATE`
- `IDEAREFINERY_WORKER_WORKSPACE`
- `IDEAREFINERY_WORKER_ENGINE`
- `IDEAREFINERY_WORKER_ALLOW_FULL_CONTROL`
- `IDEAREFINERY_WORKER_POLL_SECONDS`

OpenClaude options are stored under `openclaude`:

- `model`
- `agent`
- `permission_mode`
- `output_format`
- `max_budget_usd`
- `system_prompt`
- `additional_dirs`

## Security Model

Approval is required before the worker receives a backend API token or SQS credentials. The shared FIFO command queue is treated as a transport only; every job is claimed and updated through the backend, which remains authoritative. Workers validate message envelopes before acting.

## Development

```bash
python -m pytest tests
```
