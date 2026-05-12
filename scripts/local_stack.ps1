param(
  [Parameter(Mandatory = $true)]
  [ValidateSet(
    "local-env-check",
    "local-up",
    "local-down",
    "local-status",
    "local-seed",
    "local-smoke-test",
    "local-logs",
    "local-install-autostart",
    "local-uninstall-autostart",
    "local-restart"
  )]
  [string]$Command,
  [string]$Region = "ap-south-1",
  [string]$EndpointUrl = "http://localhost:4566",
  [string]$BackendPort = "8000"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$LocalDir = Join-Path $Root ".local"
$LogDir = Join-Path $LocalDir "logs"
$BackendPid = Join-Path $LocalDir "backend.pid"
$FlociScript = Join-Path $Root "scripts\local_floci.ps1"
$TaskName = "IdeaRefineryLocalStack"
$StartupShortcut = Join-Path ([Environment]::GetFolderPath("Startup")) "IdeaRefineryLocalStack.lnk"

function Ensure-Dirs {
  New-Item -ItemType Directory -Path $LocalDir -Force | Out-Null
  New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

function Set-LocalRuntimeEnv {
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
  $env:DYNAMODB_TABLE_NAME = "idearefinery-prod"
  $env:IDEAREFINERY_WORKER_AUTH_TOKEN = "local-worker-token"
  $env:IDEAREFINERY_WORKER_SQS_REGION = $Region
  $env:IDEAREFINERY_WORKER_COMMAND_QUEUE_URL = "$EndpointUrl/000000000000/idearefinery-worker-commands.fifo"
  $env:IDEAREFINERY_WORKER_EVENT_QUEUE_URL = "$EndpointUrl/000000000000/idearefinery-worker-events.fifo"
  $env:IDEAREFINERY_CORS_ORIGINS = "http://localhost:5173,http://localhost:4173,http://localhost:$BackendPort,http://127.0.0.1:$BackendPort"
  $env:IDEAREFINERY_CORS_ORIGIN_REGEX = ""
  if ($env:AWS_PROFILE -and $env:AWS_PROFILE -notin @("local", "floci", "localstack", "test")) {
    throw "Refusing local stack command with AWS_PROFILE='$env:AWS_PROFILE'. Unset it or use local/floci/localstack/test."
  }
  if ($env:AWS_PROFILE) {
    Remove-Item Env:AWS_PROFILE
  }
}

function Invoke-Floci {
  param([string]$FlociCommand)
  powershell -NoProfile -ExecutionPolicy Bypass -File $FlociScript -Command $FlociCommand -Region $Region -EndpointUrl $EndpointUrl
}

function Invoke-Floci-BestEffort {
  param([string]$FlociCommand)
  try {
    Invoke-Floci $FlociCommand
  } catch {
    Write-Warning "Floci command '$FlociCommand' did not complete: $($_.Exception.Message)"
  }
}

function Stop-Backend {
  if (Test-Path $BackendPid) {
    $pidValue = (Get-Content $BackendPid -Raw).Trim()
    if ($pidValue) {
      $process = Get-Process -Id ([int]$pidValue) -ErrorAction SilentlyContinue
      if ($process) {
        Stop-Process -Id $process.Id -Force
      }
    }
    Remove-Item $BackendPid -Force
  }
  $listeners = Get-NetTCPConnection -LocalPort ([int]$BackendPort) -State Listen -ErrorAction SilentlyContinue
  foreach ($listener in $listeners) {
    $process = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
    if ($process) {
      Stop-Process -Id $process.Id -Force
    }
  }
}

function Start-Backend {
  Ensure-Dirs
  Set-LocalRuntimeEnv
  $health = $null
  try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/api/health" -Method Get -TimeoutSec 2
  } catch {
    $health = $null
  }
  if ($health -and $health.status -eq "ok") {
    Write-Output "backend already healthy on http://127.0.0.1:$BackendPort"
    return
  }

  Push-Location $Root
  try {
    if (Test-Path "frontend\package.json") {
      npm --prefix frontend run build
    }
    $logPath = Join-Path $LogDir "backend.log"
    $envBlock = @"
`$env:AWS_ACCESS_KEY_ID='test'
`$env:AWS_SECRET_ACCESS_KEY='test'
`$env:AWS_DEFAULT_REGION='$Region'
`$env:AWS_REGION='$Region'
`$env:AWS_ENDPOINT_URL='$EndpointUrl'
`$env:AWS_ENDPOINT_URL_DYNAMODB='$EndpointUrl'
`$env:AWS_ENDPOINT_URL_SQS='$EndpointUrl'
`$env:AWS_ENDPOINT_URL_STS='$EndpointUrl'
`$env:AWS_ENDPOINT_URL_S3='$EndpointUrl'
`$env:IDEAREFINERY_STORAGE='dynamodb'
`$env:DYNAMODB_TABLE_NAME='idearefinery-prod'
`$env:IDEAREFINERY_WORKER_AUTH_TOKEN='local-worker-token'
`$env:IDEAREFINERY_WORKER_SQS_REGION='$Region'
`$env:IDEAREFINERY_WORKER_COMMAND_QUEUE_URL='$EndpointUrl/000000000000/idearefinery-worker-commands.fifo'
`$env:IDEAREFINERY_WORKER_EVENT_QUEUE_URL='$EndpointUrl/000000000000/idearefinery-worker-events.fifo'
`$env:IDEAREFINERY_CORS_ORIGINS='http://localhost:5173,http://localhost:4173,http://localhost:$BackendPort,http://127.0.0.1:$BackendPort'
`$env:IDEAREFINERY_CORS_ORIGIN_REGEX=''
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port $BackendPort *> '$logPath'
"@
    $proc = Start-Process powershell -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $envBlock) -WorkingDirectory $Root -WindowStyle Hidden -PassThru
    Set-Content -Path $BackendPid -Value $proc.Id -Encoding ascii
    Start-Sleep -Seconds 4
    Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/api/health" -Method Get -TimeoutSec 10 | ConvertTo-Json -Compress | Write-Output
  } finally {
    Pop-Location
  }
}

function Install-Autostart {
  $script = Join-Path $Root "scripts\local_stack.ps1"
  $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`" -Command local-up" -WorkingDirectory $Root
  $trigger = New-ScheduledTaskTrigger -AtLogOn
  $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
  try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Starts the Idea Refinery Floci-backed local stack." -Force | Out-Host
    Get-ScheduledTask -TaskName $TaskName | Format-List TaskName,State,TaskPath | Out-Host
  } catch {
    Write-Warning "Task Scheduler registration failed: $($_.Exception.Message). Falling back to the current user's Startup folder."
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($StartupShortcut)
    $shortcut.TargetPath = "powershell.exe"
    $shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$script`" -Command local-up"
    $shortcut.WorkingDirectory = $Root
    $shortcut.WindowStyle = 7
    $shortcut.Description = "Starts the Idea Refinery Floci-backed local stack."
    $shortcut.Save()
    Write-Output "startup shortcut installed: $StartupShortcut"
  }
}

function Uninstall-Autostart {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
  if (Test-Path $StartupShortcut) {
    Remove-Item $StartupShortcut -Force
  }
}

function Smoke-Test {
  Set-LocalRuntimeEnv
  Invoke-Floci "smoke-test"
  $base = "http://127.0.0.1:$BackendPort"
  $health = Invoke-RestMethod -Uri "$base/api/health" -Method Get -TimeoutSec 10
  Write-Output "backend_health=$($health.status)"
  $ideas = Invoke-RestMethod -Uri "$base/api/ideas" -Method Get -TimeoutSec 10
  Write-Output "ideas_count=$($ideas.Count)"
  try {
    Invoke-RestMethod -Uri "$base/api/worker/claim" -Method Post -ContentType "application/json" -Body '{"worker_id":"local-smoke"}' -TimeoutSec 10 | Out-Null
    throw "worker claim without token unexpectedly succeeded"
  } catch {
    if ($_.Exception.Response.StatusCode.value__ -ne 401) {
      throw
    }
    Write-Output "worker_auth_missing_token=401"
  }
  $claim = Invoke-RestMethod -Uri "$base/api/worker/claim" -Method Post -ContentType "application/json" -Headers @{"x-idearefinery-worker-token"="local-worker-token"} -Body '{"worker_id":"local-smoke","capabilities":["repo_index","agent_branch_work","test_verify"]}' -TimeoutSec 10
  Write-Output "worker_auth_valid_token=200 claim_present=$($null -ne $claim.claim)"
  $frontend = Invoke-WebRequest -Uri "$base/" -UseBasicParsing -TimeoutSec 10
  Write-Output "frontend_status=$($frontend.StatusCode)"
}

switch ($Command) {
  "local-env-check" {
    Set-LocalRuntimeEnv
    Invoke-Floci "env-check"
  }
  "local-up" {
    Ensure-Dirs
    Set-LocalRuntimeEnv
    Invoke-Floci "up"
    Invoke-Floci-BestEffort "infra-apply"
    Invoke-Floci-BestEffort "lambda-deploy"
    Start-Backend
  }
  "local-down" {
    Stop-Backend
    Invoke-Floci "down"
  }
  "local-status" {
    Set-LocalRuntimeEnv
    Invoke-Floci "status"
    try {
      Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/api/health" -Method Get -TimeoutSec 3 | ConvertTo-Json -Compress | Write-Output
    } catch {
      Write-Output "backend not healthy on http://127.0.0.1:$BackendPort"
    }
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($task) {
      $task | Format-List TaskName,State,TaskPath | Out-Host
    } elseif (Test-Path $StartupShortcut) {
      Write-Output "autostart installed via Startup folder: $StartupShortcut"
    } else {
      Write-Output "autostart task not installed: $TaskName"
    }
  }
  "local-seed" {
    Invoke-Floci "seed"
  }
  "local-smoke-test" {
    Smoke-Test
  }
  "local-logs" {
    Get-ChildItem $LogDir -Filter "*.log" -ErrorAction SilentlyContinue | ForEach-Object {
      Write-Output "== $($_.FullName) =="
      Get-Content $_.FullName -Tail 120
    }
    docker compose -f (Join-Path $Root "docker-compose.floci.yml") logs --tail 120
  }
  "local-install-autostart" {
    Install-Autostart
  }
  "local-uninstall-autostart" {
    Uninstall-Autostart
  }
  "local-restart" {
    Stop-Backend
    Invoke-Floci "up"
    Start-Backend
  }
}
