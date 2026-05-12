<script>
  import { onMount } from 'svelte';
  import {
    CheckCircle2,
    Clock,
    Loader2,
    Play,
    RefreshCw,
    XCircle,
    Lock
  } from 'lucide-svelte';
  import { api } from '../../api.js';
  import Badge from '../UI/Badge.svelte';
  import Button from '../UI/Button.svelte';
  import Card from '../UI/Card.svelte';

  let { runId = '' } = $props();

  let entries = $state([]);
  let isLoading = $state(true);
  let error = $state('');

  const phases = [
    { key: 'planning', label: 'Planning', color: '#0078ff', bgColor: 'rgba(0, 120, 255, 0.12)', textColor: '#5ca8ff' },
    { key: 'building', label: 'Building', color: '#ff9f1c', bgColor: 'rgba(255, 159, 28, 0.12)', textColor: '#ffb84d' },
    { key: 'reviewing', label: 'Reviewing', color: '#8b5cf6', bgColor: 'rgba(139, 92, 246, 0.12)', textColor: '#a78bfa' },
    { key: 'verifying', label: 'Verifying', color: '#facc15', bgColor: 'rgba(250, 204, 21, 0.12)', textColor: '#fde047' },
    { key: 'complete', label: 'Complete', color: '#52f56a', bgColor: 'rgba(82, 245, 106, 0.12)', textColor: '#52f56a' }
  ];

  let phaseStatuses = $derived(computePhaseStatuses(entries));

  function computePhaseStatuses(entries) {
    const result = {};
    const seen = new Set();

    for (const entry of entries) {
      const stage = entry.stage;
      if (!stage || seen.has(stage)) continue;
      seen.add(stage);

      if (entry.status === 'completed' || entry.status === 'final') {
        result[stage] = 'completed';
      } else if (entry.status === 'in_progress' || entry.status === 'running') {
        result[stage] = 'in_progress';
      } else if (entry.status === 'failed' || entry.status === 'error') {
        result[stage] = 'failed';
      } else {
        result[stage] = 'pending';
      }
    }

    for (const phase of phases) {
      if (!result[phase.key]) {
        result[phase.key] = 'not_started';
      }
    }

    return result;
  }

  function findCurrentPhase(statuses) {
    for (const phase of phases) {
      if (statuses[phase.key] === 'in_progress') return phase.key;
    }
    for (let i = phases.length - 1; i >= 0; i--) {
      const key = phases[i].key;
      if (statuses[key] === 'completed') return key;
    }
    return null;
  }

  let currentPhase = $derived(findCurrentPhase(phaseStatuses));

  let completedCount = $derived(
    Object.values(phaseStatuses).filter(s => s === 'completed').length
  );

  let totalPhases = phases.length;

  function getPhaseIcon(status) {
    if (status === 'completed') return CheckCircle2;
    if (status === 'in_progress') return Play;
    if (status === 'failed') return XCircle;
    return Clock;
  }

  function getPhaseDetails(stageKey) {
    const stageEntries = entries.filter(e => e.stage === stageKey);
    return stageEntries;
  }

  async function loadEntries() {
    if (!runId) return;
    isLoading = true;
    error = '';
    try {
      const data = await api(`/api/ledgers/${runId}`);
      entries = Array.isArray(data) ? data : (data.entries || data.ledgers || []);
    } catch (err) {
      error = err.message || 'Failed to load ledger data.';
    } finally {
      isLoading = false;
    }
  }

  onMount(loadEntries);
</script>

<div class="ledger-timeline">
  <div class="timeline-header">
    <div>
      <p class="mono-label">Phase Timeline</p>
      <p class="subtitle">{completedCount} of {totalPhases} phases complete</p>
    </div>
    {#if error}
      <Button size="sm" variant="secondary" onclick={loadEntries}>
        <RefreshCw size={14} /> Retry
      </Button>
    {/if}
  </div>

  {#if isLoading}
    <section class="loading-state">
      <span class="spin"><Loader2 size={22} /></span>
      Loading timeline...
    </section>
  {:else}
    <!-- Vertical timeline (default) -->
    <div class="timeline-vertical">
      {#each phases as phase, i}
        {@const status = phaseStatuses[phase.key] || 'not_started'}
        {@const PhaseIcon = getPhaseIcon(status)}
        {@const isCurrent = currentPhase === phase.key}
        <div class="timeline-node" class:is-completed={status === 'completed'} class:is-active={isCurrent} class:is-failed={status === 'failed'}>
          <div class="timeline-connector">
            <div class="connector-line" class:filled={status === 'completed'}></div>
            <div class="connector-dot" class:active={isCurrent} style="background: {phase.color}; box-shadow: {isCurrent ? `0 0 16px ${phase.color}` : 'none'};">
              <PhaseIcon size={14} color={status === 'not_started' ? '#657384' : '#fff'} />
            </div>
            {#if i < phases.length - 1}
              <div class="connector-line connector-bottom" class:filled={status === 'completed'}></div>
            {/if}
          </div>
          <div class="timeline-content">
            <div class="phase-header">
              <h3 class="phase-name" style="color: {phase.textColor};">{phase.label}</h3>
              <Badge variant={
                status === 'completed' ? 'success' :
                status === 'in_progress' ? 'warning' :
                status === 'failed' ? 'error' :
                'muted'
              } size="sm">
                {status === 'not_started' ? 'Pending' : status.replace(/_/g, ' ')}
              </Badge>
            </div>

            <!-- Horizontal micro timeline for this phase's entries -->
            {#if getPhaseDetails(phase.key).length > 0}
              <div class="phase-entries">
                {#each getPhaseDetails(phase.key) as entry}
                  <div class="phase-entry" style="border-left-color: {phase.color};">
                    <span class="entry-title">{entry.title || 'Untitled'}</span>
                    <span class="entry-meta">
                      {#if entry.status}
                        <Badge variant={
                          entry.status === 'completed' ? 'success' :
                          entry.status === 'in_progress' ? 'warning' :
                          'muted'
                        } size="sm">{entry.status}</Badge>
                      {/if}
                    </span>
                  </div>
                {/each}
              </div>
            {:else if status === 'not_started'}
              <p class="empty-phase">No entries recorded for this phase yet.</p>
            {/if}
          </div>
        </div>
      {/each}
    </div>

    <!-- Horizontal mini timeline for wider screens -->
    <div class="timeline-horizontal">
      <div class="hbar-track">
        {#each phases as phase, i}
          {@const status = phaseStatuses[phase.key] || 'not_started'}
          {@const isCurrent = currentPhase === phase.key}
          <div class="hbar-node" class:is-completed={status === 'completed'} class:is-active={isCurrent}>
            {#if i > 0}
              <div class="hbar-connector" class:filled={status === 'completed' || phases[i - 1] && phaseStatuses[phases[i - 1].key] === 'completed'}></div>
            {/if}
            <div class="hbar-dot" class:active={isCurrent} style="background: {phase.color};">
              {#if isCurrent && (status === 'in_progress')}
                <span class="pulse-ring" style="border-color: {phase.color};"></span>
              {/if}
            </div>
            <span class="hbar-label" style="color: {isCurrent || status === 'completed' ? phase.textColor : 'var(--color-text-muted)'};">{phase.label}</span>
          </div>
        {/each}
      </div>
      <div class="hbar-progress">
        <div class="hbar-progress-fill" style="width: {(completedCount / totalPhases) * 100}%;"></div>
      </div>
    </div>
  {/if}
</div>

<style>
  .ledger-timeline {
    max-width: 960px;
    margin: 0 auto;
  }

  .timeline-header {
    align-items: center;
    display: flex;
    gap: var(--spacing-lg);
    justify-content: space-between;
    margin-bottom: var(--spacing-lg);
  }

  .mono-label {
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.68rem;
    margin: 0;
    text-transform: uppercase;
  }

  .subtitle {
    color: var(--color-text-secondary);
    font-size: 0.82rem;
    margin: 4px 0 0;
  }

  .loading-state {
    align-items: center;
    background: rgba(5, 10, 15, 0.72);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
    color: var(--color-text-secondary);
    display: flex;
    gap: var(--spacing-sm);
    justify-content: center;
    min-height: 120px;
  }

  .spin {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* Vertical timeline */
  .timeline-vertical {
    display: flex;
    flex-direction: column;
    gap: 0;
  }

  .timeline-node {
    display: flex;
    gap: var(--spacing-md);
    min-height: 80px;
    padding-bottom: var(--spacing-lg);
  }

  .timeline-connector {
    align-items: center;
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    position: relative;
    width: 36px;
  }

  .connector-line {
    background: var(--color-border);
    flex: 1;
    min-height: 14px;
    width: 2px;
  }

  .connector-line.filled {
    background: var(--color-success);
  }

  .connector-bottom {
    flex: 1;
    min-height: 14px;
  }

  .connector-dot {
    align-items: center;
    border-radius: 50%;
    display: flex;
    height: 32px;
    justify-content: center;
    position: relative;
    transition: box-shadow 0.3s ease;
    width: 32px;
    z-index: 1;
  }

  .connector-dot.active {
    animation: dotPulse 1.8s ease-in-out infinite;
  }

  @keyframes dotPulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.15); }
  }

  .timeline-content {
    background: rgba(5, 10, 15, 0.5);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-md);
    flex: 1;
    min-width: 0;
    padding: var(--spacing-md);
    transition: border-color 0.2s;
  }

  .timeline-node.is-active .timeline-content {
    border-color: rgba(0, 174, 255, 0.3);
  }

  .timeline-node.is-completed .timeline-content {
    opacity: 0.85;
  }

  .phase-header {
    align-items: center;
    display: flex;
    gap: 8px;
    justify-content: space-between;
    margin-bottom: var(--spacing-sm);
  }

  .phase-name {
    font-size: 1rem;
    font-weight: 600;
    margin: 0;
  }

  .phase-entries {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .phase-entry {
    align-items: center;
    border-left: 2px solid;
    display: flex;
    gap: 8px;
    justify-content: space-between;
    padding: 4px 0 4px var(--spacing-sm);
  }

  .phase-entry .entry-title {
    color: var(--color-text-secondary);
    font-size: 0.8rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .phase-entry .entry-meta {
    flex-shrink: 0;
  }

  .empty-phase {
    color: var(--color-text-muted);
    font-size: 0.78rem;
    margin: 4px 0 0;
    padding-left: 8px;
  }

  /* Horizontal mini timeline */
  .timeline-horizontal {
    background: rgba(5, 10, 15, 0.72);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
    margin-bottom: var(--spacing-lg);
    padding: var(--spacing-lg);
  }

  .hbar-track {
    align-items: flex-start;
    display: flex;
    justify-content: space-between;
    margin-bottom: var(--spacing-md);
    position: relative;
  }

  .hbar-node {
    align-items: center;
    display: flex;
    flex: 1;
    flex-direction: column;
    gap: 8px;
    position: relative;
  }

  .hbar-connector {
    background: var(--color-border);
    height: 2px;
    position: absolute;
    right: 50%;
    top: 12px;
    width: 100%;
    z-index: 0;
  }

  .hbar-connector.filled {
    background: var(--color-success);
  }

  .hbar-dot {
    border-radius: 50%;
    height: 24px;
    position: relative;
    width: 24px;
    z-index: 1;
  }

  .hbar-dot.active {
    animation: dotPulse 1.8s ease-in-out infinite;
  }

  .pulse-ring {
    animation: pulseRing 2s ease-out infinite;
    border: 2px solid;
    border-radius: 50%;
    height: 36px;
    left: -6px;
    opacity: 0;
    position: absolute;
    top: -6px;
    width: 36px;
  }

  @keyframes pulseRing {
    0% { transform: scale(0.8); opacity: 0.8; }
    100% { transform: scale(1.8); opacity: 0; }
  }

  .hbar-label {
    font-family: var(--font-mono);
    font-size: 0.68rem;
    text-align: center;
    text-transform: uppercase;
    white-space: nowrap;
  }

  .hbar-progress {
    background: var(--color-border);
    border-radius: 999px;
    height: 3px;
    overflow: hidden;
    width: 100%;
  }

  .hbar-progress-fill {
    background: linear-gradient(90deg, var(--color-primary), var(--color-success));
    border-radius: 999px;
    height: 100%;
    transition: width 0.5s ease;
  }

  /* Hide horizontal on narrow screens, show vertical */
  @media (max-width: 640px) {
    .timeline-horizontal {
      display: none;
    }

    .timeline-node {
      padding-bottom: var(--spacing-md);
    }

    .phase-header {
      flex-direction: column;
      align-items: flex-start;
      gap: 4px;
    }
  }

  @media (min-width: 641px) {
    .timeline-vertical {
      display: none;
    }
  }
</style>
