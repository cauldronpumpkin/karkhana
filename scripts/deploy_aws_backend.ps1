param(
  [string]$Region = "us-east-1",
  [string]$StackName = "idearefinery-backend-prod"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$BuildDir = Join-Path $Root ".build\lambda"
$PackageDir = Join-Path $BuildDir "package"
$ZipPath = Join-Path $BuildDir "idearefinery-backend.zip"
$TemplatePath = Join-Path $Root "infra\cloudformation\idearefinery-backend.yaml"

if (Test-Path $BuildDir) {
  Remove-Item -LiteralPath $BuildDir -Recurse -Force
}
New-Item -ItemType Directory -Path $PackageDir | Out-Null

python -m pip install --upgrade --target $PackageDir `
  --platform manylinux2014_aarch64 `
  --python-version 3.11 `
  --implementation cp `
  --only-binary=:all: `
  fastapi `
  mangum `
  openai `
  python-dotenv `
  python-multipart `
  httpx `
  boto3 `
  PyJWT `
  cryptography `
  pydantic-settings
Copy-Item -Path (Join-Path $Root "backend") -Destination $PackageDir -Recurse -Force

if (Test-Path $ZipPath) {
  Remove-Item -LiteralPath $ZipPath -Force
}
Compress-Archive -Path (Join-Path $PackageDir "*") -DestinationPath $ZipPath -Force

$codexLbApiKey = ""
if ($env:CODEX_LB_API_KEY) {
  $codexLbApiKey = $env:CODEX_LB_API_KEY
} elseif (Test-Path (Join-Path $Root ".env")) {
  $envLine = Get-Content (Join-Path $Root ".env") | Where-Object { $_ -match "^CODEX_LB_API_KEY=" } | Select-Object -First 1
  if ($envLine) {
    $codexLbApiKey = ($envLine -replace "^CODEX_LB_API_KEY=", "").Trim('"').Trim("'")
  }
}

aws cloudformation deploy `
  --region $Region `
  --stack-name $StackName `
  --template-file $TemplatePath `
  --capabilities CAPABILITY_NAMED_IAM `
  --parameter-overrides CodexLbApiKey="$codexLbApiKey"

aws lambda update-function-code `
  --region $Region `
  --function-name idearefinery-backend-prod `
  --zip-file "fileb://$ZipPath" | Out-Null

aws lambda wait function-updated `
  --region $Region `
  --function-name idearefinery-backend-prod

$endpoint = aws cloudformation describe-stacks `
  --region $Region `
  --stack-name $StackName `
  --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue | [0]" `
  --output text

Write-Output "API endpoint: $endpoint"
$health = Invoke-RestMethod -Uri "$endpoint/api/health" -Method Get
Write-Output ("Health: " + ($health | ConvertTo-Json -Compress))
