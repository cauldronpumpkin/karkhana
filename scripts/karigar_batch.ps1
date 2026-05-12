# karigar_batch.ps1 - Karigar-Mini Dataset Pipeline
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File karigar_batch.ps1 -Command <cmd>
# Commands: generate, critic, dedup, promote, full-pipeline, status, next-batch, dry-run

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('generate','critic','dedup','promote','full-pipeline','status','next-batch','dry-run')]
    [string]$Command,
    [string]$BatchNumber = ''
)

# ============================================================
# CONFIG - model routing, paths, defaults
# ============================================================
$KARIGAR_MODEL          = 'deepseek-v4-pro'
$KARIGAR_CRITIC_MODEL   = 'deepseek-v4-pro'
$KARIGAR_BATCH_SIZE     = 25
$KARIGAR_REPO_ROOT      = "$env:USERPROFILE\Documents\idearefinery"
$KARIGAR_BASE           = 'docs\karigar-mini'
$KARIGAR_CANDIDATES     = "$KARIGAR_BASE\candidates"
$KARIGAR_ACCEPTED       = "$KARIGAR_BASE\accepted"
$KARIGAR_REJECTED       = "$KARIGAR_BASE\rejected"
$KARIGAR_TRAINING       = "$KARIGAR_BASE\training"

$env:AWS_ACCESS_KEY_ID     = 'test'
$env:AWS_SECRET_ACCESS_KEY = 'test'
$env:AWS_DEFAULT_REGION    = 'ap-south-1'
$env:AWS_REGION            = 'ap-south-1'
$env:AWS_ENDPOINT_URL      = 'http://localhost:4566'

function Get-NextBatchNumber {
    if (-not (Test-Path "$KARIGAR_REPO_ROOT\$KARIGAR_CANDIDATES")) { return 1 }
    $existing = Get-ChildItem "$KARIGAR_REPO_ROOT\$KARIGAR_CANDIDATES\batch-*.jsonl" -ErrorAction SilentlyContinue |
        ForEach-Object { if ($_.Name -match 'batch-(\d+)\.jsonl') { [int]$matches[1] } }
    if (-not $existing) { return 1 }
    return [int]($existing | Measure-Object -Maximum).Maximum + 1
}

function fmt-batch { param([int]$n) return $n.ToString('000') }

function Ensure-Directories {
    foreach ($d in @(
        "$KARIGAR_REPO_ROOT\$KARIGAR_CANDIDATES",
        "$KARIGAR_REPO_ROOT\$KARIGAR_ACCEPTED",
        "$KARIGAR_REPO_ROOT\$KARIGAR_REJECTED",
        "$KARIGAR_REPO_ROOT\$KARIGAR_TRAINING"
    )) {
        if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
    }
}

Ensure-Directories

switch ($Command) {
    'status' {
        $next = Get-NextBatchNumber
        Write-Host '=== Karigar Dataset Pipeline ==='
        Write-Host "Model (gen)   : $KARIGAR_MODEL"
        Write-Host "Model (critic): $KARIGAR_CRITIC_MODEL"
        Write-Host "Batch size    : $KARIGAR_BATCH_SIZE"
        Write-Host "Next batch    : batch-$((fmt-batch $next))"
        Write-Host "Repo root     : $KARIGAR_REPO_ROOT"
        foreach ($d in @($KARIGAR_CANDIDATES, $KARIGAR_ACCEPTED, $KARIGAR_REJECTED, $KARIGAR_TRAINING)) {
            $count = (Get-ChildItem "$KARIGAR_REPO_ROOT\$d\*.jsonl" -ErrorAction SilentlyContinue).Count
            Write-Host "  $d ($count files)"
        }
        $trainingPath = "$KARIGAR_REPO_ROOT\$KARIGAR_TRAINING\karigar-mini-sft.jsonl"
        if (Test-Path $trainingPath) {
            $tc = (Get-Content $trainingPath | Where-Object { $_.Trim() -ne '' }).Count
            Write-Host "Training dataset: $tc episodes"
        } else {
            Write-Host "Training dataset: (empty)"
        }
    }
    'next-batch' {
        Write-Host "Next batch: batch-$((fmt-batch (Get-NextBatchNumber)))"
    }
    'dry-run' {
        $next = (fmt-batch (Get-NextBatchNumber))
        Write-Host '=== DRY RUN ==='
        Write-Host "Would generate batch-$next"
        Write-Host "Model : $KARIGAR_MODEL"
        Write-Host "Repo  : $KARIGAR_REPO_ROOT"
        Write-Host "Schema: $(if (Test-Path "$KARIGAR_REPO_ROOT\docs\karigar-mini\KARIGAR_WORKER_EPISODE_SCHEMA.json") { 'FOUND' } else { 'MISSING' })"
        Write-Host "Directories: OK"
        Write-Host "Ready."
    }
    'generate' {
        $bn = if ($BatchNumber) { $BatchNumber } else { (fmt-batch (Get-NextBatchNumber)) }
        $out = "$KARIGAR_REPO_ROOT\$KARIGAR_CANDIDATES\batch-$bn.jsonl"
        if (Test-Path $out) { Write-Host "EXISTS: $out. Delete first to regenerate."; return }
        Write-Host "=== GENERATE batch-$bn ==="
        Write-Host "Model : $KARIGAR_MODEL"
        Write-Host "Size  : $KARIGAR_BATCH_SIZE"
        Write-Host "Output: $out"
        Write-Host ""
        Write-Host "Prompt a command-code agent (model=$KARIGAR_MODEL):"
        Write-Host '  Read docs/karigar-mini/HERMES_DATASET_GENERATION_CONTEXT.txt,'
        Write-Host '  KARIGAR_WORKER_EPISODE_SCHEMA.json, DATASET_GENERATION_PROMPTS.md,'
        Write-Host '  and KARIGAR_DATASET_QA_CHECKLIST.md.'
        Write-Host "  Generate $KARIGAR_BATCH_SIZE candidate episodes. Write to: $out"
        Write-Host '  Target label mix: 12-17 accept, 5-9 needs_review, 2-5 reject.'
    }
    'critic' {
        $bn = if ($BatchNumber) { $BatchNumber } else { (fmt-batch ((Get-NextBatchNumber) - 1)) }
        $inf = "$KARIGAR_REPO_ROOT\$KARIGAR_CANDIDATES\batch-$bn.jsonl"
        $outf = "$KARIGAR_REPO_ROOT\$KARIGAR_CANDIDATES\batch-$bn-critic.json"
        if (-not (Test-Path $inf)) { Write-Host "ERROR: $inf not found. Run generate first."; return }
        Write-Host "=== CRITIC batch-$bn ==="
        Write-Host "Model : $KARIGAR_CRITIC_MODEL"
        Write-Host "Output: $outf"
        Write-Host ""
        Write-Host "Prompt a command-code agent (model=$KARIGAR_CRITIC_MODEL):"
        Write-Host "  Read $inf and KARIGAR_DATASET_QA_CHECKLIST.md."
        Write-Host "  Review each episode. Output critic JSON to: $outf"
        Write-Host '  Target: 12-17 accept, 5-9 needs_review, 2-5 reject.'
    }
    'dedup' {
        $bn = if ($BatchNumber) { $BatchNumber } else { (fmt-batch ((Get-NextBatchNumber) - 1)) }
        Write-Host "=== DEDUP batch-$bn ==="
        $acceptedDir = "$KARIGAR_REPO_ROOT\$KARIGAR_ACCEPTED"
        $batchFile = "$KARIGAR_REPO_ROOT\$KARIGAR_CANDIDATES\batch-$bn.jsonl"
        if (-not (Test-Path $batchFile)) { Write-Host "ERROR: $batchFile not found."; return }

        $existingHashes = @{}
        Get-ChildItem "$acceptedDir\batch-*.jsonl" -ErrorAction SilentlyContinue | ForEach-Object {
            Get-Content $_.FullName | Where-Object { $_.Trim() -ne '' } | ForEach-Object {
                try {
                    $obj = $_ | ConvertFrom-Json
                    $h = "{0}|{1}" -f $obj.user_request, $obj.task_title
                    $existingHashes[$h] = $obj.episode_id
                } catch {}
            }
        }

        $dupes = 0
        Get-Content $batchFile | Where-Object { $_.Trim() -ne '' } | ForEach-Object {
            try {
                $obj = $_ | ConvertFrom-Json
                $h = "{0}|{1}" -f $obj.user_request, $obj.task_title
                if ($existingHashes.ContainsKey($h)) {
                    Write-Host "  DUPLICATE: $($obj.episode_id) -> $($existingHashes[$h])"
                    $dupes++
                }
            } catch {}
        }
        Write-Host "Dedup complete. ($dupes duplicates found)"
    }
    'promote' {
        $bn = if ($BatchNumber) { $BatchNumber } else { (fmt-batch ((Get-NextBatchNumber) - 1)) }
        $criticFile = "$KARIGAR_REPO_ROOT\$KARIGAR_CANDIDATES\batch-$bn-critic.json"
        $batchFile  = "$KARIGAR_REPO_ROOT\$KARIGAR_CANDIDATES\batch-$bn.jsonl"
        if (-not (Test-Path $criticFile)) { Write-Host "ERROR: critic file not found."; return }
        if (-not (Test-Path $batchFile))  { Write-Host "ERROR: batch file not found."; return }

        $critic = Get-Content $criticFile -Raw | ConvertFrom-Json
        $acceptIds = @($critic.reviews | Where-Object { $_.quality_label -eq 'accept' } | ForEach-Object { $_.episode_id })
        $rejectIds = @($critic.reviews | Where-Object { $_.quality_label -eq 'reject' } | ForEach-Object { $_.episode_id })

        Write-Host "=== PROMOTE batch-$bn ==="
        Write-Host "Accept: $($acceptIds.Count)  Reject: $($rejectIds.Count)"

        $episodes = @{}
        Get-Content $batchFile | Where-Object { $_.Trim() -ne '' } | ForEach-Object {
            try { $obj = $_ | ConvertFrom-Json; $episodes[$obj.episode_id] = $_ } catch {}
        }

        if ($acceptIds.Count -gt 0) {
            $ap = "$KARIGAR_REPO_ROOT\$KARIGAR_ACCEPTED\batch-$bn.jsonl"
            $tp = "$KARIGAR_REPO_ROOT\$KARIGAR_TRAINING\karigar-mini-sft.jsonl"
            Remove-Item $ap -ErrorAction SilentlyContinue
            $acceptIds | ForEach-Object {
                if ($episodes.ContainsKey($_)) {
                    $episodes[$_] | Out-File -FilePath $ap -Append -Encoding utf8
                    $episodes[$_] | Out-File -FilePath $tp -Append -Encoding utf8
                }
            }
            Write-Host "Promoted $($acceptIds.Count) to accepted/ and training/"
        }

        if ($rejectIds.Count -gt 0) {
            $rp = "$KARIGAR_REPO_ROOT\$KARIGAR_REJECTED\batch-$bn.jsonl"
            Remove-Item $rp -ErrorAction SilentlyContinue
            $rejectIds | ForEach-Object {
                if ($episodes.ContainsKey($_)) {
                    $episodes[$_] | Out-File -FilePath $rp -Append -Encoding utf8
                }
            }
            Write-Host "Quarantined $($rejectIds.Count) to rejected/"
        }
    }
    'full-pipeline' {
        $bn = (fmt-batch (Get-NextBatchNumber))
        Write-Host "=== FULL PIPELINE batch-$bn ==="
        Write-Host "Model : $KARIGAR_MODEL"
        Write-Host "Steps: 1.generate 2.critic 3.dedup 4.promote"
        Write-Host ""
        Write-Host "Run sequentially through command-code."
    }
}
