param(
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"

$brokenPattern = "if \(Test-Path 'graphify-out/graph\.json'\)"
$replacementCommand = "if [ -f 'graphify-out/graph.json' ]; then printf '%s\n' '{`"hookSpecificOutput`":{`"hookEventName`":`"PreToolUse`",`"additionalContext`":`"graphify: Knowledge graph exists. Read graphify-out/GRAPH_REPORT.md for god nodes and community structure before searching raw files.`"}}'; fi"

$roots = @(
    (Join-Path $env:USERPROFILE ".codex"),
    (Join-Path $env:USERPROFILE ".claude"),
    (Join-Path $env:USERPROFILE ".config\opencode"),
    (Join-Path $env:USERPROFILE "Documents\idearefinery")
) | Where-Object { Test-Path $_ }

if (-not $roots) {
    Write-Host "No candidate config roots found." -ForegroundColor Yellow
    exit 1
}

$candidateFiles = foreach ($root in $roots) {
    Get-ChildItem -Path $root -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Extension -in @(".json", ".jsonc", ".toml", ".yaml", ".yml", ".md", ".txt") -or
            $_.Name -match "settings|config|hook|agent|opencode|codex|claude"
        }
}

$hookMatches = @()

foreach ($file in $candidateFiles) {
    try {
        $text = Get-Content -LiteralPath $file.FullName -Raw -ErrorAction Stop
    } catch {
        continue
    }

    if ($text -match $brokenPattern -and $text -match "hookSpecificOutput" -and $text -match "graphify-out/GRAPH_REPORT\.md") {
        $hookMatches += [pscustomobject]@{
            Path = $file.FullName
            Text = $text
        }
    }
}

if (-not $hookMatches) {
    Write-Host "No broken Graphify PreToolUse hook was found in candidate config roots." -ForegroundColor Yellow
    Write-Host "Searched:"
    $roots | ForEach-Object { Write-Host "  $_" }
    exit 2
}

Write-Host "Found $($hookMatches.Count) file(s) containing the broken Graphify hook:" -ForegroundColor Cyan
$hookMatches | ForEach-Object { Write-Host "  $($_.Path)" }

if ($WhatIfOnly) {
    Write-Host "WhatIfOnly set; no files changed." -ForegroundColor Yellow
    exit 0
}

$changed = 0

foreach ($match in $hookMatches) {
    $path = $match.Path
    $text = $match.Text
    $backup = "$path.bak-graphify-hook-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

    Copy-Item -LiteralPath $path -Destination $backup

    # Replace the whole command string when the hook is stored as a JSON array item.
    $newText = $text -replace '"if \(Test-Path ''graphify-out/graph\.json''\) \{ ''\{\\"hookSpecificOutput\\":\{\\"hookEventName\\":\\"PreToolUse\\",\\"additionalContext\\":\\"graphify: Knowledge graph exists\. Read graphify-out/GRAPH_REPORT\.md for god nodes and community structure before searching raw files\.\\"\}\}'' \}"',
        ('"' + ($replacementCommand -replace '\\', '\\' -replace '"', '\"') + '"')

    # Replace command values shaped like: "command": "if (Test-Path ... }"
    $newText = $newText -replace '("command"\s*:\s*)"if \(Test-Path ''graphify-out/graph\.json''\) \{ ''\{\\"hookSpecificOutput\\":\{\\"hookEventName\\":\\"PreToolUse\\",\\"additionalContext\\":\\"graphify: Knowledge graph exists\. Read graphify-out/GRAPH_REPORT\.md for god nodes and community structure before searching raw files\.\\"\}\}'' \}"',
        ('$1"' + ($replacementCommand -replace '\\', '\\' -replace '"', '\"') + '"')

    # Fallback for unescaped TOML/plain command entries.
    $newText = $newText -replace "if \(Test-Path 'graphify-out/graph\.json'\) \{ '\{`"hookSpecificOutput`":\{`"hookEventName`":`"PreToolUse`",`"additionalContext`":`"graphify: Knowledge graph exists\. Read graphify-out/GRAPH_REPORT\.md for god nodes and community structure before searching raw files\.`"\}\}' \}",
        $replacementCommand

    if ($newText -eq $text) {
        Write-Host "Matched but could not safely rewrite exact command in: $path" -ForegroundColor Yellow
        Write-Host "Backup created: $backup"
        continue
    }

    Set-Content -LiteralPath $path -Value $newText -NoNewline
    $changed += 1
    Write-Host "Updated: $path" -ForegroundColor Green
    Write-Host "Backup:  $backup"
}

Write-Host ""
Write-Host "Changed $changed file(s)." -ForegroundColor Cyan
Write-Host "Restart Codex/Codex CLI after this so the hook config is reloaded." -ForegroundColor Cyan
