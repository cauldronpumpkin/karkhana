param(
  [Parameter(Mandatory = $true)]
  [ValidateSet(
    "env-check",
    "up",
    "down",
    "infra-plan",
    "infra-apply",
    "sam-build",
    "sam-deploy",
    "lambda-deploy",
    "seed",
    "smoke-test",
    "status"
  )]
  [string]$Command,
  [string]$Region = "ap-south-1",
  [string]$EndpointUrl = "http://localhost:4566",
  [string]$StackName = "idearefinery-local",
  [string]$TableName = "idearefinery-prod"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$TemplatePath = Join-Path $Root "infra\cloudformation\idearefinery-backend.yaml"
$BuildDir = Join-Path $Root ".build\local-lambda"
$PackageDir = Join-Path $BuildDir "package"
$ZipPath = Join-Path $BuildDir "idearefinery-backend-local.zip"

function Set-LocalAwsEnv {
  $env:AWS_ACCESS_KEY_ID = "test"
  $env:AWS_SECRET_ACCESS_KEY = "test"
  $env:AWS_DEFAULT_REGION = $Region
  $env:AWS_REGION = $Region
  $env:AWS_ENDPOINT_URL = $EndpointUrl
  $env:AWS_ENDPOINT_URL_DYNAMODB = $EndpointUrl
  $env:AWS_ENDPOINT_URL_SQS = $EndpointUrl
  $env:AWS_ENDPOINT_URL_STS = $EndpointUrl
  $env:AWS_ENDPOINT_URL_S3 = $EndpointUrl
  $env:IDEAREFINERY_STORAGE = "dynamodb"
  $env:DYNAMODB_TABLE_NAME = $TableName
  $env:IDEAREFINERY_WORKER_AUTH_TOKEN = "local-worker-token"
  $env:IDEAREFINERY_WORKER_SQS_REGION = $Region
}

function Assert-LocalAwsEnv {
  Set-LocalAwsEnv
  if ($env:AWS_PROFILE -and $env:AWS_PROFILE -notin @("local", "floci", "localstack", "test")) {
    throw "Refusing local AWS command with AWS_PROFILE='$env:AWS_PROFILE'. Unset it or use local/floci/localstack/test."
  }
  if ($env:AWS_PROFILE) {
    Remove-Item Env:AWS_PROFILE
  }
  if ($env:AWS_ACCESS_KEY_ID -ne "test" -or $env:AWS_SECRET_ACCESS_KEY -ne "test") {
    throw "Refusing local AWS command without fake credentials AWS_ACCESS_KEY_ID=test and AWS_SECRET_ACCESS_KEY=test."
  }
  if ($env:AWS_REGION -ne $Region -or $env:AWS_DEFAULT_REGION -ne $Region) {
    throw "Refusing local AWS command unless AWS_REGION and AWS_DEFAULT_REGION are $Region."
  }
  if ($EndpointUrl -notmatch "^http://(localhost|127\.0\.0\.1):4566/?$") {
    throw "Refusing non-local AWS endpoint '$EndpointUrl'. Expected http://localhost:4566."
  }
}

function AwsLocal {
  param([Parameter(ValueFromRemainingArguments = $true)] [string[]] $Args)
  Assert-LocalAwsEnv
  & aws --endpoint-url $EndpointUrl --region $Region @Args
  if ($LASTEXITCODE -ne 0) {
    throw "aws local command failed: aws --endpoint-url $EndpointUrl --region $Region $($Args -join ' ')"
  }
}

function Build-LocalLambdaPackage {
  Assert-LocalAwsEnv
  if (Test-Path $BuildDir) {
    Remove-Item -LiteralPath $BuildDir -Recurse -Force
  }
  New-Item -ItemType Directory -Path $PackageDir | Out-Null
  python -m pip install --quiet --upgrade --target $PackageDir fastapi mangum openai python-dotenv python-multipart httpx boto3 PyJWT cryptography pydantic-settings pyyaml
  Copy-Item -Path (Join-Path $Root "backend") -Destination $PackageDir -Recurse -Force
  [System.IO.File]::WriteAllText(
    (Join-Path $PackageDir "lambda_function.py"),
    "from backend.app.lambda_handler import handler`n",
    [System.Text.UTF8Encoding]::new($false)
  )
  Compress-Archive -Path (Join-Path $PackageDir "*") -DestinationPath $ZipPath -Force
  Write-Output $ZipPath
}

switch ($Command) {
  "env-check" {
    Assert-LocalAwsEnv
    Write-Output "local env ok: endpoint=$EndpointUrl region=$Region access_key=$env:AWS_ACCESS_KEY_ID profile=$env:AWS_PROFILE"
  }
  "up" {
    Assert-LocalAwsEnv
    docker compose -f (Join-Path $Root "docker-compose.floci.yml") up -d
  }
  "down" {
    docker compose -f (Join-Path $Root "docker-compose.floci.yml") down
  }
  "infra-plan" {
    Assert-LocalAwsEnv
    AwsLocal cloudformation validate-template --template-body "file://$TemplatePath" | Out-Host
    Write-Output "local infra plan ok: CloudFormation template is syntactically valid for Floci endpoint $EndpointUrl"
  }
  "infra-apply" {
    Assert-LocalAwsEnv
    AwsLocal cloudformation deploy --stack-name $StackName --template-file $TemplatePath --capabilities CAPABILITY_NAMED_IAM --parameter-overrides CodexLbApiKey="" WorkerAuthToken="local-worker-token" | Out-Host
  }
  "sam-build" {
    if (-not (Test-Path (Join-Path $Root "template.yaml")) -and -not (Test-Path (Join-Path $Root "template.yml"))) {
      Write-Output "SAM template not present; skipping local SAM build. This repo uses CloudFormation plus Lambda packaging."
      exit 0
    }
    Assert-LocalAwsEnv
    sam build
  }
  "sam-deploy" {
    Write-Output "SAM template not present; use local-lambda-deploy instead."
    exit 0
  }
  "lambda-deploy" {
    Assert-LocalAwsEnv
    $zip = Build-LocalLambdaPackage
    $envJsonPath = Join-Path $BuildDir "lambda-env.json"
    $lambdaEnv = @{
      Variables = @{
        IDEAREFINERY_STORAGE = "dynamodb"
        DYNAMODB_TABLE_NAME = $TableName
        AI_PROVIDER = "codex-lb"
        AI_MODEL = "gpt-5.5"
        CODEX_LB_API_BASE_URL = "http://127.0.0.1:2455/v1"
        CODEX_LB_MODEL = "gpt-5.5"
        IDEAREFINERY_WORKER_AUTH_TOKEN = "local-worker-token"
        IDEAREFINERY_WORKER_CLAIM_TIMEOUT_SECONDS = "900"
        IDEAREFINERY_WORKER_MAX_RETRIES = "3"
        IDEAREFINERY_WORKER_COMMAND_QUEUE_URL = "$EndpointUrl/000000000000/idearefinery-worker-commands.fifo"
        IDEAREFINERY_WORKER_EVENT_QUEUE_URL = "$EndpointUrl/000000000000/idearefinery-worker-events.fifo"
        IDEAREFINERY_WORKER_CLIENT_ROLE_ARN = "arn:aws:iam::000000000000:role/idearefinery-worker-client-prod-role"
        IDEAREFINERY_WORKER_SQS_REGION = $Region
        IDEAREFINERY_WORKER_CREDENTIAL_TTL_SECONDS = "3600"
        AWS_ENDPOINT_URL = $EndpointUrl
        AWS_ENDPOINT_URL_DYNAMODB = $EndpointUrl
        AWS_ENDPOINT_URL_SQS = $EndpointUrl
        AWS_ENDPOINT_URL_STS = $EndpointUrl
        AWS_ENDPOINT_URL_S3 = $EndpointUrl
      }
    }
    [System.IO.File]::WriteAllText(
      $envJsonPath,
      ($lambdaEnv | ConvertTo-Json -Depth 5),
      [System.Text.UTF8Encoding]::new($false)
    )

    $existingName = AwsLocal lambda list-functions --query "Functions[?FunctionName=='idearefinery-backend-prod'].FunctionName | [0]" --output text
    if ($existingName -eq "idearefinery-backend-prod") {
      AwsLocal lambda update-function-code --function-name idearefinery-backend-prod --zip-file "fileb://$zip" | Out-Host
      AwsLocal lambda update-function-configuration --function-name idearefinery-backend-prod --handler lambda_function.handler --environment "file://$envJsonPath" | Out-Host
    } else {
      AwsLocal lambda create-function `
        --function-name idearefinery-backend-prod `
        --runtime python3.11 `
        --handler lambda_function.handler `
        --role arn:aws:iam::000000000000:role/idearefinery-backend-prod-role `
        --zip-file "fileb://$zip" `
        --timeout 30 `
        --memory-size 256 `
        --environment "file://$envJsonPath" | Out-Host
    }

    $queueArn = AwsLocal sqs get-queue-attributes --queue-url "$EndpointUrl/000000000000/idearefinery-worker-events.fifo" --attribute-names QueueArn --query "Attributes.QueueArn" --output text
    $mapping = & aws --endpoint-url $EndpointUrl --region $Region lambda list-event-source-mappings --function-name idearefinery-backend-prod --event-source-arn $queueArn --query "EventSourceMappings[0].UUID" --output text 2>$null
    if ($LASTEXITCODE -eq 0 -and $mapping -and $mapping -ne "None") {
      Write-Output "event source mapping already exists: $mapping"
    } else {
      AwsLocal lambda create-event-source-mapping --function-name idearefinery-backend-prod --event-source-arn $queueArn --batch-size 10 | Out-Host
    }
  }
  "seed" {
    Assert-LocalAwsEnv
    Write-Output "No required seed data or Cognito users found for this repo. Worker auth uses IDEAREFINERY_WORKER_AUTH_TOKEN=local-worker-token."
  }
  "status" {
    Assert-LocalAwsEnv
    docker compose -f (Join-Path $Root "docker-compose.floci.yml") ps
    AwsLocal sts get-caller-identity | Out-Host
    AwsLocal dynamodb list-tables | Out-Host
    AwsLocal lambda list-functions --query "Functions[].FunctionName" | Out-Host
  }
  "smoke-test" {
    Assert-LocalAwsEnv
    Invoke-RestMethod -Uri "$EndpointUrl/_floci/health" -Method Get | ConvertTo-Json -Compress | Write-Output
    AwsLocal sts get-caller-identity | Out-Host
    AwsLocal dynamodb describe-table --table-name $TableName | Out-Host
    AwsLocal sqs list-queues | Out-Host
    AwsLocal lambda get-function --function-name idearefinery-backend-prod | Out-Host

    $responsePath = Join-Path $BuildDir "lambda-health-response.json"
    Write-Warning "lambda_api_gateway_status=deprecated_unsupported. Local-first smoke uses direct FastAPI/Uvicorn; Lambda/API Gateway resources are retained only as Floci inventory."
    if (Test-Path $responsePath) {
      Write-Output "lambda_last_response_path=$responsePath"
    }

    $python = @'
import os
from fastapi.testclient import TestClient
from backend.app.repository import set_repository
from backend.app.main import app

os.environ["IDEAREFINERY_STORAGE"] = "dynamodb"
os.environ["DYNAMODB_TABLE_NAME"] = "idearefinery-prod"
os.environ["AWS_ENDPOINT_URL"] = "http://localhost:4566"
os.environ["AWS_REGION"] = "ap-south-1"
os.environ["AWS_DEFAULT_REGION"] = "ap-south-1"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["IDEAREFINERY_WORKER_AUTH_TOKEN"] = "local-worker-token"
set_repository(None)
client = TestClient(app)
health = client.get("/api/health")
print("app_health", health.status_code, health.text)
missing = client.post("/api/worker/claim", json={"worker_id": "local-smoke"})
print("worker_claim_without_token", missing.status_code, missing.text)
valid = client.post("/api/worker/claim", json={"worker_id": "local-smoke"}, headers={"x-idearefinery-worker-token": "local-worker-token"})
print("worker_claim_with_token", valid.status_code, valid.text[:300])
raise SystemExit(0 if health.status_code == 200 and missing.status_code == 401 and valid.status_code in (200, 400) else 1)
'@
    $python | uv run python -
  }
}
