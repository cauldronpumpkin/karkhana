# Local-First Floci Runtime

The supported local runtime is Floci-backed and runs from this repo. It uses:

- Floci at `http://localhost:4566` for DynamoDB, SQS, STS, Lambda inventory, and local AWS-compatible resources.
- Local Uvicorn for the FastAPI backend.
- The built frontend served by FastAPI from `frontend/dist`.
- Local log files under `.local/logs`.
- Worker-token auth with `IDEAREFINERY_WORKER_AUTH_TOKEN=local-worker-token`.

Cloud AWS deployment is deprecated for now. Do not run real AWS deploy or delete commands as part of local verification.

## Commands

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-env-check
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-up
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-status
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-smoke-test
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-logs
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-restart
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-down
```

Makefile aliases with the same names call the same script.

## Auto-start

Install boot/logon startup for this Windows user:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-install-autostart
```

Disable it:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_stack.ps1 -Command local-uninstall-autostart
```

The script first attempts to register a current-user Task Scheduler task named `IdeaRefineryLocalStack` that points at `scripts/local_stack.ps1 -Command local-up`.

On Windows machines where the current user cannot register scheduled tasks, the verified supported fallback is a Startup-folder shortcut:

```text
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\IdeaRefineryLocalStack.lnk
```

`local-status` reports which autostart mechanism is installed. The fallback does not require elevation and starts the same `local-up` command at user logon.

## Lambda And API Gateway

Lambda and API Gateway resources remain in Floci as deprecated inventory, but they are not the supported local app path. `local-smoke-test` reports this as `lambda_api_gateway_status=deprecated_unsupported` and then verifies the direct FastAPI/Uvicorn app path, worker-token auth, and frontend serving.

For real AWS resource inventory and deletion, see `docs/aws-retirement.md`.

## Auth

Do not add `AUTH_DISABLED`, `SKIP_AUTH`, or local auth bypasses. Worker endpoints remain protected. Local smoke testing verifies that `/api/worker/claim` rejects a missing token and accepts `x-idearefinery-worker-token: local-worker-token`.

## Cognito

Cognito is not implemented in this repo. The local runtime does not create or fake Cognito users.

## Amplify

Amplify is not needed for the local runtime because FastAPI serves `frontend/dist` locally. Existing Amplify scripts are retained only for cloud history and retirement inventory.
