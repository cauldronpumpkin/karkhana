param(
  [string]$ApiBase = "http://localhost:8000",
  [string]$WorkerToken = "",
  [string]$WorkerId = $env:COMPUTERNAME,
  [string]$WorkspaceRoot = "$env:USERPROFILE\.idearefinery-worker\repos",
  [string]$Engine = "openclaude",
  [int]$PollSeconds = 60,
  [switch]$Uninstall
)

$ErrorActionPreference = "Stop"
$taskName = "IdeaRefinery Local Worker"
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$workerScript = Join-Path $repoRoot "scripts\idearefinery_worker.py"
$python = (Get-Command python -ErrorAction SilentlyContinue).Source

if (-not $python) {
  throw "python was not found on PATH. Install Python or update PATH before installing the worker."
}

if ($Uninstall) {
  if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Removed scheduled task '$taskName'."
  } else {
    Write-Host "Scheduled task '$taskName' was not installed."
  }
  exit 0
}

New-Item -ItemType Directory -Force -Path $WorkspaceRoot | Out-Null

$arguments = @(
  "`"$workerScript`"",
  "--api-base", "`"$ApiBase`"",
  "--worker-id", "`"$WorkerId`"",
  "--workspace-root", "`"$WorkspaceRoot`"",
  "--engine", "`"$Engine`"",
  "--poll-seconds", "$PollSeconds"
)
if ($WorkerToken) {
  $arguments += @("--token", "`"$WorkerToken`"")
}

$action = New-ScheduledTaskAction -Execute $python -Argument ($arguments -join " ") -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -StartWhenAvailable `
  -RestartCount 3 `
  -RestartInterval (New-TimeSpan -Minutes 2)

Register-ScheduledTask `
  -TaskName $taskName `
  -Action $action `
  -Trigger $trigger `
  -Settings $settings `
  -Description "Polls Idea Refinery for queued GitHub project twin jobs and runs local agent work." `
  -Force | Out-Null

Write-Host "Installed scheduled task '$taskName'."
Write-Host "Worker script: $workerScript"
Write-Host "Workspace: $WorkspaceRoot"
