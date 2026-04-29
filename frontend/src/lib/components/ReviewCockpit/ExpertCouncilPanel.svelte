<script>
  import {
    AlertTriangle,
    ChevronDown,
    ChevronRight,
    ShieldAlert,
    Users
  } from 'lucide-svelte';
  import Badge from '../UI/Badge.svelte';
  import ExpertCouncilCard from './ExpertCouncilCard.svelte';

  let { packet = null } = $props();
  let expanded = $state(true);

  const summaryDecisionTone = (decision) => {
    if (decision === 'ready') return 'success';
    if (decision === 'needs_changes') return 'warning';
    if (decision === 'blocked') return 'error';
    return 'muted';
  };

  const severityTone = (severity) => {
    if (severity === 'critical') return 'error';
    if (severity === 'high') return 'error';
    if (severity === 'medium') return 'warning';
    return 'muted';
  };

  let summary = $derived(packet?.council_summary || {});
  let experts = $derived(packet?.expert_reviews || []);
  let activeExperts = $derived(experts.filter(e => e.activated));
  let hasConflicts = $derived(summary.conflict_count > 0);
  let hasPatches = $derived((summary.artifact_patch_proposals || []).length > 0);
</script>

{#if experts.length > 0}
  <section class="detail-section">
    <button class="section-header" onclick={() => expanded = !expanded}>
      {#if expanded}<ChevronDown size={18} />{:else}<ChevronRight size={18} />{/if}
      <h2>Expert Council</h2>
      <Badge variant={summaryDecisionTone(summary.overall_decision)}>
        {summary.overall_decision?.replace(/_/g, ' ') || 'pending'}
      </Badge>
      <Badge variant="muted">{activeExperts.length}/{experts.length} active</Badge>
      {#if summary.unresolved_blockers_count > 0}
        <Badge variant="error">{summary.unresolved_blockers_count} blocker(s)</Badge>
      {/if}
    </button>

    {#if expanded}
      <div class="section-body">
        {#if hasConflicts}
          <div class="conflict-banner">
            <ShieldAlert size={16} />
            <span>
              {summary.conflict_count} conflict(s) detected between experts.
              {#each summary.conflicts || [] as conflict}
                <div class="conflict-detail">
                  <Badge variant="error">{conflict.role_a}</Badge>
                  vs
                  <Badge variant="error">{conflict.role_b}</Badge>
                  <span class="conflict-desc">{conflict.description}</span>
                </div>
              {/each}
            </span>
          </div>
        {/if}

        <div class="council-summary-strip">
          <div class="summary-item">
            <span class="label">Decision</span>
            <Badge variant={summaryDecisionTone(summary.overall_decision)}>
              {summary.overall_decision?.replace(/_/g, ' ') || 'pending'}
            </Badge>
          </div>
          <div class="summary-item">
            <span class="label">Severity</span>
            <Badge variant={severityTone(summary.highest_severity)}>
              {summary.highest_severity || 'low'}
            </Badge>
          </div>
          <div class="summary-item">
            <span class="label">Blockers</span>
            <Badge variant={summary.unresolved_blockers_count > 0 ? 'error' : 'success'}>
              {summary.unresolved_blockers_count || 0}
            </Badge>
          </div>
          <div class="summary-item">
            <span class="label">Active</span>
            <Badge variant="muted">{summary.active_roles_count || 0} roles</Badge>
          </div>
        </div>

        <div class="expert-cards">
          {#each experts as expert}
            <ExpertCouncilCard {expert} expanded={false} />
          {/each}
        </div>

        {#if hasPatches}
          <div class="patch-section">
            <span class="label">Artifact Patch Proposals</span>
            {#each summary.artifact_patch_proposals || [] as patch}
              <div class="patch-row">
                <Badge variant="muted">{patch.artifact_key}</Badge>
                <span class="patch-desc">{patch.patch_description}</span>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    {/if}
  </section>
{/if}

<style>
  .detail-section {
    background: rgba(5, 10, 15, 0.6);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-md);
    overflow: hidden;
  }

  .section-header {
    align-items: center;
    background: transparent;
    border: 0;
    color: var(--color-text);
    cursor: pointer;
    display: flex;
    gap: var(--spacing-sm);
    padding: var(--spacing-md);
    width: 100%;
    text-align: left;
  }

  .section-header:hover {
    background: rgba(0, 120, 255, 0.04);
  }

  .section-header h2 {
    flex: 1;
    font-size: 0.95rem;
    margin: 0;
  }

  .section-body {
    border-top: 1px solid rgba(103, 128, 151, 0.18);
    padding: var(--spacing-md);
    display: grid;
    gap: var(--spacing-sm);
  }

  .conflict-banner {
    align-items: flex-start;
    background: rgba(255, 80, 80, 0.08);
    border: 1px solid rgba(255, 80, 80, 0.2);
    border-radius: var(--border-radius-sm);
    color: var(--color-error);
    display: flex;
    gap: 8px;
    padding: var(--spacing-sm) var(--spacing-md);
    font-size: 0.82rem;
  }

  .conflict-detail {
    align-items: center;
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-top: 6px;
    font-size: 0.78rem;
  }

  .conflict-desc {
    color: var(--color-text-secondary);
    font-size: 0.75rem;
  }

  .council-summary-strip {
    display: flex;
    gap: var(--spacing-md);
    flex-wrap: wrap;
  }

  .summary-item {
    align-items: center;
    display: flex;
    gap: 6px;
  }

  .label {
    color: var(--color-text-secondary);
    display: block;
    font-family: var(--font-mono);
    font-size: 0.68rem;
    text-transform: uppercase;
  }

  .expert-cards {
    display: grid;
    gap: 6px;
  }

  .patch-section {
    display: grid;
    gap: 6px;
  }

  .patch-row {
    align-items: center;
    display: flex;
    gap: 8px;
    font-size: 0.78rem;
  }

  .patch-desc {
    color: var(--color-text-secondary);
  }
</style>
