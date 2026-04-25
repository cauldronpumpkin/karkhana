param(
  [string]$Region = "us-east-1",
  [string]$AppName = "karkhana",
  [string]$Repository = "https://github.com/cauldronpumpkin/karkhana.git",
  [string]$BranchName = "main",
  [string]$ApiBaseUrl = "https://api.karkhana.one",
  [string]$DomainName = "karkhana.one"
)

$ErrorActionPreference = "Stop"

function Invoke-AwsText {
  param(
    [Parameter(Mandatory = $true)]
    [string[]]$Arguments
  )

  $output = & aws @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "aws $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
  }
  return $output
}

if (-not $env:GITHUB_TOKEN -and -not $env:GH_TOKEN) {
  throw "Set GITHUB_TOKEN or GH_TOKEN with access to $Repository, then rerun this script."
}

$token = if ($env:GITHUB_TOKEN) { $env:GITHUB_TOKEN } else { $env:GH_TOKEN }

$appId = aws amplify list-apps `
  --region $Region `
  --query "apps[?name=='$AppName'].appId | [0]" `
  --output text

if (-not $appId -or $appId -eq "None") {
  $appId = Invoke-AwsText @(
    "amplify", "create-app",
    "--region", $Region,
    "--name", $AppName,
    "--repository", $Repository,
    "--platform", "WEB",
    "--access-token", $token,
    "--environment-variables", "VITE_API_BASE_URL=$ApiBaseUrl",
    "--query", "app.appId",
    "--output", "text"
  )
} else {
  aws amplify update-app `
    --region $Region `
    --app-id $appId `
    --environment-variables "VITE_API_BASE_URL=$ApiBaseUrl" | Out-Null
}

if (-not $appId -or $appId -eq "None") {
  throw "Amplify app id was not returned."
}

$branchExists = aws amplify list-branches `
  --region $Region `
  --app-id $appId `
  --query "branches[?branchName=='$BranchName'].branchName | [0]" `
  --output text

if (-not $branchExists -or $branchExists -eq "None") {
  aws amplify create-branch `
    --region $Region `
    --app-id $appId `
    --branch-name $BranchName `
    --framework "Svelte" `
    --stage PRODUCTION `
    --enable-auto-build | Out-Null
}

$domainExists = aws amplify list-domain-associations `
  --region $Region `
  --app-id $appId `
  --query "domainAssociations[?domainName=='$DomainName'].domainName | [0]" `
  --output text

if (-not $domainExists -or $domainExists -eq "None") {
  aws amplify create-domain-association `
    --region $Region `
    --app-id $appId `
    --domain-name $DomainName `
    --sub-domain-settings prefix=www,branchName=$BranchName prefix=,branchName=$BranchName | Out-Null
}

aws amplify start-job `
  --region $Region `
  --app-id $appId `
  --branch-name $BranchName `
  --job-type RELEASE | Out-Null

$defaultDomain = aws amplify get-app `
  --region $Region `
  --app-id $appId `
  --query "app.defaultDomain" `
  --output text

Write-Output "Amplify app: $appId"
Write-Output "Default URL: https://$BranchName.$defaultDomain"
