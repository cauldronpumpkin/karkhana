# AWS Deployment Deprecation And Retirement Runbook

AWS CloudFormation/Lambda/API Gateway/DynamoDB/SQS deployment is deprecated for now. The supported runtime is the local Floci stack documented in `docs/local-first-floci.md`.

## Read-only inventory

Run this only when you intentionally want to inspect real AWS resources:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/aws_retirement_inventory.ps1 -Region us-east-1 -NamePrefix idearefinery
```

This script only lists resources. It does not delete or modify anything.

The inventory covers:

- CloudFormation stacks
- Lambda functions
- API Gateway v2 APIs
- DynamoDB tables
- SQS queues
- IAM roles
- Amplify apps

## Manual deletion after explicit confirmation

Do not run these until a fresh session explicitly confirms the inventory and the intended deletion target.

```powershell
# CloudFormation, if the stack owns the resources
aws --region us-east-1 cloudformation delete-stack --stack-name idearefinery-backend-prod

# Only for orphaned resources after confirming they are not stack-managed
aws --region us-east-1 lambda delete-function --function-name <function-name>
aws --region us-east-1 apigatewayv2 delete-api --api-id <api-id>
aws --region us-east-1 dynamodb delete-table --table-name <table-name>
aws --region us-east-1 sqs delete-queue --queue-url <queue-url>
aws --region us-east-1 iam delete-role --role-name <role-name>
aws --region us-east-1 amplify delete-app --app-id <app-id>
```

Before deleting IAM roles, detach or delete attached policies explicitly after reviewing them. Before deleting DynamoDB, export or back up anything worth keeping.

## Current local replacement

- Backend: local Uvicorn from this repo.
- Frontend: built locally and served from FastAPI.
- DynamoDB/SQS/STS: Floci local emulation.
- Lambda/API Gateway: retained in Floci history, but the dependable app path is direct FastAPI.
- Cognito: not applicable; it is not implemented in this repo.
