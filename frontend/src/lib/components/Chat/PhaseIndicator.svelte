<script>
  import { Activity, Check, Circle, X } from 'lucide-svelte';
  import Badge from '../UI/Badge.svelte';
  import Button from '../UI/Button.svelte';

  let {
    currentPhase = 'capture',
    suggestedPhase = null,
    ideaId = '',
    connectionState = 'online',
    onapprovePhase,
    onrejectPhase
  } = $props();

  const phaseLabels = {
    capture: 'Capture',
    clarify: 'Clarify',
    refine: 'Refine',
    score: 'Score',
    research: 'Research',
    build: 'Build'
  };

  let phaseName = $derived(phaseLabels[currentPhase] || currentPhase || 'Capture');
  let suggestedName = $derived(phaseLabels[suggestedPhase] || suggestedPhase);

  function handleApprove() {
    onapprovePhase?.(suggestedPhase);
  }

  function handleReject() {
    onrejectPhase?.({ phase: suggestedPhase, reason: 'User rejected phase advancement' });
  }
</script>

<div class="phase-indicator" data-idea-id={ideaId}>
  <div class="status-pill">
    {#if connectionState === 'online'}
      <span class="status-dot online">
        <Circle size={10} aria-hidden="true" />
      </span>
    {:else}
      <span class="status-dot">
        <Activity size={14} aria-hidden="true" />
      </span>
    {/if}
    <span>{connectionState === 'online' ? 'Agents online' : 'Connecting'}</span>
  </div>

  <div class="phase-badge">
    <span>Phase</span>
    <Badge variant="primary" size="md">
      {phaseName}
    </Badge>
  </div>

  {#if suggestedPhase}
    <div class="phase-actions">
      <span class="phase-suggestion">
        Suggested: <Badge variant="accent" size="sm">{suggestedName}</Badge>
      </span>
      <div class="action-buttons">
        <Button variant="secondary" size="sm" onclick={handleApprove}>
          <Check size={14} aria-hidden="true" />
          Approve
        </Button>
        <Button variant="ghost" size="sm" onclick={handleReject}>
          <X size={14} aria-hidden="true" />
          Reject
        </Button>
      </div>
    </div>
  {/if}
</div>

<style>
  .phase-indicator {
    align-items: center;
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-sm);
    justify-content: flex-end;
  }

  .status-pill,
  .phase-badge,
  .phase-actions,
  .phase-suggestion,
  .action-buttons {
    align-items: center;
    display: flex;
    gap: var(--spacing-sm);
  }

  .status-pill,
  .phase-badge,
  .phase-actions {
    background: rgba(7, 13, 19, 0.88);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-sm);
    min-height: 38px;
    padding: 7px 10px;
  }

  .status-pill,
  .phase-badge > span,
  .phase-suggestion {
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.75rem;
  }

  .status-pill {
    color: var(--color-success);
    text-transform: uppercase;
  }

  .status-dot {
    align-items: center;
    color: var(--color-warning);
    display: inline-flex;
  }

  .status-dot.online {
    color: var(--color-success);
    fill: currentColor;
  }

  @media (max-width: 760px) {
    .phase-indicator {
      justify-content: flex-start;
      width: 100%;
    }

    .phase-actions {
      align-items: flex-start;
      flex-direction: column;
      width: 100%;
    }
  }
</style>
