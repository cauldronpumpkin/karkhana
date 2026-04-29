<script>
  import {
    AlertTriangle,
    CheckCircle2,
    ChevronDown,
    ChevronRight,
    Shield,
    XCircle,
    Info,
    FileText
  } from 'lucide-svelte';
  import Badge from '../UI/Badge.svelte';

  let { expert = null, expanded = false } = $props();

  const decisionTone = (decision) => {
    if (decision === 'approved') return 'success';
    if (decision === 'approved_with_notes') return 'success';
    if (decision === 'requests_changes') return 'warning';
    if (decision === 'blocked') return 'error';
    return 'muted';
  };

  const decisionLabel = (decision) => {
    const labels = {
      approved: 'Approved',
      approved_with_notes: 'Approved w/ Notes',
      requests_changes: 'Changes Requested',
      blocked: 'Blocked',
    };
    return labels[decision] || decision;
  };

  const authorityTone = (authority) => {
    if (authority === 'hard_gate') return 'error';
    if (authority === 'advisory') return 'accent';
    return 'muted';
  };

  const severityTone = (severity) => {
    if (severity === 'critical') return 'error';
    if (severity === 'high') return 'error';
    if (severity === 'medium') return 'warning';
    return 'muted';
  };
</script>

{#if expert}
  <div class="expert-card" class:inactive={!expert.activated}>
    <button class="expert-header" onclick={() => expanded = !expanded}>
      {#if expanded}<ChevronDown size={14} />{:else}<ChevronRight size={14} />{/if}
      <Shield size={14} />
      <span class="expert-name">{expert.display_name || expert.role}</span>
      <Badge variant={authorityTone(expert.authority)}>{expert.authority?.replace(/_/g, ' ')}</Badge>
      <Badge variant={decisionTone(expert.decision)}>{decisionLabel(expert.decision)}</Badge>
      {#if !expert.activated}
        <Badge variant="muted">Not activated</Badge>
      {:else}
        <Badge variant="muted">{expert.triggers_matched?.length || 0} triggers</Badge>
      {/if}
      <span class="confidence">{((expert.confidence || 0) * 100).toFixed(0)}%</span>
    </button>

    {#if expanded && expert.activated}
      <div class="expert-body">
        {#if expert.triggers_matched?.length}
          <div class="trigger-list">
            <span class="label">Triggers</span>
            {#each expert.triggers_matched as trigger}
              {#if trigger.matched}
                <Badge variant="accent">{trigger.trigger_type?.replace(/_/g, ' ')}</Badge>
              {/if}
            {/each}
          </div>
        {/if}

        {#if expert.findings?.length}
          <div class="findings-list">
            <span class="label">Findings ({expert.findings.length})</span>
            {#each expert.findings as finding}
              <div class="finding-row">
                <Badge variant={severityTone(finding.severity)}>{finding.severity}</Badge>
                {#if finding.blocking}
                  <Badge variant="error">Blocker</Badge>
                {/if}
                <span class="finding-text">{finding.summary}</span>
                {#if finding.file_path}
                  <code class="file-ref">{finding.file_path}</code>
                {/if}
              </div>
            {/each}
          </div>
        {/if}

        {#if expert.approvals?.length}
          <div class="approval-list">
            <span class="label">Approvals</span>
            {#each expert.approvals as approval}
              <div class="approval-row">
                <CheckCircle2 size={12} />
                <span>{approval.scope}: {approval.description}</span>
              </div>
            {/each}
          </div>
        {/if}

        {#if expert.artifact_patch_proposals?.length}
          <div class="patch-list">
            <span class="label">Artifact Proposals</span>
            {#each expert.artifact_patch_proposals as patch}
              <div class="patch-row">
                <FileText size={12} />
                <Badge variant="muted">{patch.artifact_key}</Badge>
                <span>{patch.patch_description}</span>
              </div>
            {/each}
          </div>
        {/if}

        {#if expert.summary}
          <p class="expert-summary">{expert.summary}</p>
        {/if}
      </div>
    {/if}
  </div>
{/if}

<style>
  .expert-card {
    background: rgba(4, 9, 14, 0.7);
    border: 1px solid rgba(103, 128, 151, 0.14);
    border-radius: var(--border-radius-sm);
    overflow: hidden;
  }

  .expert-card.inactive {
    opacity: 0.55;
  }

  .expert-header {
    align-items: center;
    background: transparent;
    border: 0;
    color: var(--color-text);
    cursor: pointer;
    display: flex;
    gap: 8px;
    padding: 8px 12px;
    width: 100%;
    text-align: left;
    font-size: 0.82rem;
  }

  .expert-header:hover {
    background: rgba(0, 120, 255, 0.04);
  }

  .expert-name {
    flex: 1;
    font-weight: 500;
  }

  .confidence {
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.68rem;
  }

  .expert-body {
    border-top: 1px solid rgba(103, 128, 151, 0.14);
    padding: 10px 12px;
    display: grid;
    gap: 8px;
  }

  .label {
    color: var(--color-text-secondary);
    display: block;
    font-family: var(--font-mono);
    font-size: 0.68rem;
    margin-bottom: 4px;
    text-transform: uppercase;
  }

  .trigger-list,
  .approval-list,
  .patch-list {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    align-items: center;
  }

  .findings-list {
    display: grid;
    gap: 6px;
  }

  .finding-row {
    align-items: center;
    display: flex;
    gap: 6px;
    font-size: 0.8rem;
    flex-wrap: wrap;
  }

  .finding-text {
    color: var(--color-text-secondary);
    flex: 1;
    min-width: 120px;
  }

  .file-ref {
    color: var(--color-accent);
    font-family: var(--font-mono);
    font-size: 0.68rem;
  }

  .approval-row {
    align-items: center;
    display: flex;
    gap: 6px;
    color: var(--color-text-secondary);
    font-size: 0.78rem;
  }

  .patch-row {
    align-items: center;
    display: flex;
    gap: 6px;
    color: var(--color-text-secondary);
    font-size: 0.78rem;
  }

  .expert-summary {
    color: var(--color-text-secondary);
    font-size: 0.78rem;
    margin: 0;
    line-height: 1.4;
  }
</style>
