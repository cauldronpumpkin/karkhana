<#
.SYNOPSIS
    One-click installer for the IdeaRefinery/Karkhana OpenClaude local worker.

.DESCRIPTION
    Installs Python (if missing), pip dependencies, pairs the worker with the
    IdeaRefinery backend, and optionally registers a startup scheduled task.

.PARAMETER ApiBase
    Base URL of the IdeaRefinery API. Falls back to $env:IDEAREFINERY_API_BASE_URL.

.PARAMETER TenantId
    Optional tenant identifier sent during pairing.

.PARAMETER DisplayName
    Human-readable name for this worker instance.

.PARAMETER StatePath
    Path to the worker state file. Defaults to
    $env:USERPROFILE\.idearefinery-worker\openclaude-local\state.json

.PARAMETER NoScheduledTask
    Skip registering the Windows Scheduled Task.

.EXAMPLE
    .\install.ps1 -ApiBase https://your-api.example.com

.EXAMPLE
    .\install.ps1 -ApiBase https://your-api.example.com -TenantId acme-corp -DisplayName "Build Server"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$ApiBase = $env:IDEAREFINERY_API_BASE_URL,

    [Parameter(Mandatory = $false)]
    [string]$TenantId,

    [Parameter(Mandatory = $false)]
    [string]$DisplayName = "OpenClaude local worker",

    [Parameter(Mandatory = $false)]
    [string]$StatePath = "$env:USERPROFILE\.idearefinery-worker\openclaude-local\state.json",

    [Parameter(Mandatory = $false)]
    [switch]$NoScheduledTask
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# ── Helpers ────────────────────────────────────────────────────────────────────

function Write-Status {
    param([string]$Message, [string]$Color = "Cyan")
    Write-Host "[IdeaRefinery] " -NoNewline -ForegroundColor DarkGray
    Write-Host $Message -ForegroundColor $Color
}

function Write-ErrorExit {
    param([string]$Message)
    Write-Host "[IdeaRefinery] ERROR: " -NoNewline -ForegroundColor Red
    Write-Host $Message -ForegroundColor Red
    exit 1
}

# ── Validate required parameters ───────────────────────────────────────────────

if (-not $ApiBase) {
    Write-ErrorExit "ApiBase is required. Set IDEAREFINERY_API_BASE_URL or pass -ApiBase <url>."
}

# ── Resolve paths ──────────────────────────────────────────────────────────────

$Root = $PSScriptRoot
if (-not $Root) {
    Write-ErrorExit "PSScriptRoot is empty. Run this script from a file, not an interactive session."
}

$WorkerScript = Join-Path $Root "worker.py"
$RequirementsFile = Join-Path $Root "requirements.txt"

if (-not (Test-Path $WorkerScript)) {
    Write-ErrorExit "worker.py not found at '$WorkerScript'. Ensure the script is in the worker directory."
}
if (-not (Test-Path $RequirementsFile)) {
    Write-ErrorExit "requirements.txt not found at '$RequirementsFile'."
}

# ── Python detection & installation ────────────────────────────────────────────

function Get-PythonInfo {
    $candidates = @("python", "python3", "py")
    foreach ($cmd in $candidates) {
        $found = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($found) {
            return $found
        }
    }
    return $null
}

function Get-PythonVersion {
    param([string]$PythonPath)
    try {
        $output = & $PythonPath --version 2>&1
        if ($output -match "(\d+)\.(\d+)") {
            return [PSCustomObject]@{
                Major = [int]$Matches[1]
                Minor = [int]$Matches[2]
                Raw   = $output
            }
        }
    }
    catch {
        # ignore
    }
    return $null
}

Write-Status "Checking for Python 3.10+ ..."

$PythonCmd = Get-PythonInfo
$PythonExe = $null

if ($PythonCmd) {
    $version = Get-PythonVersion -PythonPath $PythonCmd.Source
    if ($version -and $version.Major -ge 3 -and $version.Minor -ge 10) {
        $PythonExe = $PythonCmd.Source
        Write-Status "Found $($version.Raw) at $PythonExe" -Color Green
    }
    else {
        $raw = if ($version) { $version.Raw } else { "unknown version" }
        Write-Status "Found $raw but 3.10+ is required." -Color Yellow
    }
}

# ── Install Python via winget if missing ───────────────────────────────────────

if (-not $PythonExe) {
    Write-Status "Python 3.10+ not found. Attempting to install via winget ..." -Color Yellow

    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        Write-ErrorExit @"
winget is not available. Install Python 3.10+ manually:
  1. Download from https://www.python.org/downloads/
  2. During install, check 'Add Python to PATH'
  3. Re-run this installer.
"@
    }

    Write-Status "Installing Python 3.12 via winget ..."
    $installResult = & winget install --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements --silent 2>&1

    if ($LASTEXITCODE -ne 0) {
        Write-Status "winget install exited with code $LASTEXITCODE." -Color Yellow
        Write-ErrorExit @"
Automatic Python installation failed. Please install manually:
  1. Download from https://www.python.org/downloads/
  2. During install, check 'Add Python to PATH'
  3. Re-run this installer.
"@
    }

    Write-Status "Python installed. Refreshing PATH ..."

    # Refresh PATH from registry for the current session
    $envPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$envPath;$userPath"

    $PythonCmd = Get-PythonInfo
    if ($PythonCmd) {
        $version = Get-PythonVersion -PythonPath $PythonCmd.Source
        if ($version -and $version.Major -ge 3 -and $version.Minor -ge 10) {
            $PythonExe = $PythonCmd.Source
            Write-Status "Found $($version.Raw) at $PythonExe" -Color Green
        }
    }

    if (-not $PythonExe) {
        Write-ErrorExit @"
Python was installed but not found on PATH after install.
Please close this window, open a new PowerShell, and re-run the installer.
"@
    }
}

# ── Install pip dependencies ───────────────────────────────────────────────────

Write-Status "Installing pip dependencies ..."
$pipResult = & $PythonExe -m pip install -r $RequirementsFile 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Status "pip install failed (exit $LASTEXITCODE):" -Color Red
    Write-Host $pipResult -ForegroundColor Red
    Write-ErrorExit "Failed to install requirements. Check the output above."
}
Write-Status "Dependencies installed." -Color Green

# ── Pair the worker ────────────────────────────────────────────────────────────

Write-Status "Starting pairing flow with $ApiBase ..."
Write-Status "This will block until approved in the Local Workers web UI." -Color Yellow

# Build a temporary config so --display-name is honoured (worker.py reads it from JSON)
$TempConfig = Join-Path $Root "worker-config.install.json"
@{ display_name = $DisplayName } | ConvertTo-Json | Set-Content -Path $TempConfig -Encoding UTF8

$pairArgs = @($WorkerScript, "pair", "--api-base", $ApiBase, "--state", $StatePath, "--config", $TempConfig)
if ($TenantId) {
    $pairArgs += "--tenant-id"
    $pairArgs += $TenantId
}

$pairOutput = & $PythonExe $pairArgs 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Status "Pairing failed (exit $LASTEXITCODE):" -Color Red
    Write-Host $pairOutput -ForegroundColor Red
    Remove-Item $TempConfig -ErrorAction SilentlyContinue
    Write-ErrorExit "Worker pairing failed. Check the output above."
}

# Clean up temp config; if no permanent config exists, rename it so the worker keeps the display name
$PermanentConfig = Join-Path $Root "worker-config.json"
if (-not (Test-Path $PermanentConfig)) {
    Rename-Item $TempConfig $PermanentConfig -Force
}
else {
    Remove-Item $TempConfig -ErrorAction SilentlyContinue
}

Write-Host $pairOutput
Write-Status "Worker paired successfully. State saved to $StatePath" -Color Green

# ── Register scheduled task (startup, user-level) ──────────────────────────────

if (-not $NoScheduledTask) {
    $taskName = "IdeaRefineryLocalWorker"

    Write-Status "Registering scheduled task '$taskName' (runs at system startup) ..."

    $action = New-ScheduledTaskAction `
        -Execute $PythonExe `
        -Argument "`"$WorkerScript`" run --state `"$StatePath`"" `
        -WorkingDirectory $Root

    $trigger = New-ScheduledTaskTrigger -AtStartup

    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RestartCount 5 `
        -RestartInterval (New-TimeSpan -Minutes 2) `
        -ExecutionTimeLimit (New-TimeSpan -Hours 0)

    try {
        Register-ScheduledTask `
            -TaskName $taskName `
            -Action $action `
            -Trigger $trigger `
            -Settings $settings `
            -Description "Runs the IdeaRefinery OpenClaude local worker at system startup." `
            -Force | Out-Null

        Write-Status "Scheduled task '$taskName' registered." -Color Green
    }
    catch {
        Write-Status "Failed to register scheduled task: $_" -Color Red
        Write-Status "You can still run the worker manually:" -Color Yellow
        Write-Host "  $PythonExe `"$WorkerScript`" run --state `"$StatePath`""
    }
}

# ── Done ───────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Status "Installation complete!" -Color Green
Write-Host ""
Write-Host "  State file : $StatePath"
Write-Host "  Worker     : $WorkerScript"
Write-Host "  Run manual : $PythonExe `"$WorkerScript`" run --state `"$StatePath`""
Write-Host ""
