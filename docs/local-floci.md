# Local AWS With Floci

> Status: retained as the lower-level Floci runbook. For the supported local-first app flow, use `docs/local-first-floci.md` and `scripts/local_stack.ps1`.

This repo uses AWS through CloudFormation and boto3. Terraform and SAM templates are not present in this checkout.

Use Floci as the local AWS emulator at `http://localhost:4566`. Local commands force fake credentials and refuse a real-looking `AWS_PROFILE`.

## One-command Flow

From the repo root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_floci.ps1 -Command env-check
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_floci.ps1 -Command up
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_floci.ps1 -Command infra-plan
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_floci.ps1 -Command infra-apply
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_floci.ps1 -Command lambda-deploy
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_floci.ps1 -Command seed
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_floci.ps1 -Command smoke-test
```

If `make` is available, equivalent aliases exist:

```powershell
make local-env-check
make local-up
make local-infra-plan
make local-infra-apply
make local-lambda-deploy
make local-seed
make local-smoke-test
```

Stop Floci:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_floci.ps1 -Command down
```

## Required Local AWS Environment

Use only fake local credentials:

```powershell
$env:AWS_ACCESS_KEY_ID="test"
$env:AWS_SECRET_ACCESS_KEY="test"
$env:AWS_DEFAULT_REGION="ap-south-1"
$env:AWS_REGION="ap-south-1"
$env:AWS_ENDPOINT_URL="http://localhost:4566"
$env:AWS_PROFILE=""
```

The script sets these automatically for local commands. It refuses to continue if `AWS_PROFILE` is set to anything other than `local`, `floci`, `localstack`, or `test`.

## What Deploys Locally

`infra/cloudformation/idearefinery-backend.yaml` creates:

- DynamoDB table `idearefinery-prod`
- SQS worker command/event queues and DLQs
- IAM roles for backend and local workers
- Lambda function `idearefinery-backend-prod`
- HTTP API Gateway v2 routes
- Lambda event source mapping for worker events

`local-lambda-deploy` packages the current backend code into `.build/local-lambda/` and updates the local Floci Lambda function.

The backend supports local AWS endpoint overrides through:

- `AWS_ENDPOINT_URL`
- `AWS_ENDPOINT_URL_DYNAMODB`
- `AWS_ENDPOINT_URL_SQS`
- `AWS_ENDPOINT_URL_STS`
- `AWS_ENDPOINT_URL_S3`

These are local-only env vars. Cloud deployments continue to use normal AWS endpoints.

## Smoke Test Coverage

`local-smoke-test` checks:

- Floci health endpoint
- local STS identity through the emulator
- DynamoDB table existence
- SQS queue listing
- Lambda function existence
- Lambda/API Gateway status as deprecated unsupported local inventory
- FastAPI app health using local DynamoDB env
- worker protected endpoint rejects missing token
- worker protected endpoint accepts `IDEAREFINERY_WORKER_AUTH_TOKEN`

## Cognito And Auth

No Cognito resources or Cognito-backed auth flow exist in the current CloudFormation/backend code. The repo currently uses:

- custom worker bearer token / `x-idearefinery-worker-token`
- local worker pairing tokens
- GitHub webhook signatures
- a WebSocket JWT hook, but no complete Cognito provider implementation in this checkout

Because Cognito is not implemented, local setup does not create a local user pool or seed Cognito users. This is documented rather than bypassed. Do not add `AUTH_DISABLED`, `SKIP_AUTH`, or any auth bypass for local Floci work.

## Known Floci Limitations

Floci compatibility depends on the local emulator image and implemented AWS service coverage. If CloudFormation deploy or API Gateway invocation is unsupported in the installed Floci version, keep the failure visible in verification output and use the app-level local smoke checks against DynamoDB/SQS resources that did deploy. Do not fall back to real AWS.

Observed with Floci `1.5.13` on this repo: CloudFormation creates DynamoDB, SQS, IAM, Lambda, and API Gateway inventory, but direct Lambda invocation is not treated as supported for the local-first runtime. Earlier smoke runs timed out after 30 seconds and wrote the body to `.build/local-lambda/lambda-health-response.json`. The smoke test now reports Lambda/API Gateway as deprecated unsupported and verifies the same FastAPI app path directly against local DynamoDB.

## Cloud Safety

Never run local setup with a real AWS profile. Never run `sam deploy`, `terraform apply`, or CloudFormation deploy against real AWS for this local workflow.

Before finalizing local AWS work, run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_floci.ps1 -Command env-check
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_floci.ps1 -Command status
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_floci.ps1 -Command smoke-test
```
