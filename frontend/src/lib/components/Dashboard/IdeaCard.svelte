<script>
  import { BarChart3, CalendarClock, GitBranch, MoreHorizontal, Target, Wrench } from 'lucide-svelte';
  import Badge from '../UI/Badge.svelte';
  import Card from '../UI/Card.svelte';
  import ScoreBar from './ScoreBar.svelte';

  let { idea, onclick } = $props();

  const scoreToPercent = (score = 0) => Math.round(Math.min(100, Math.max(0, score <= 10 ? score * 10 : score)));

  const getScoreColor = (score) => {
    if (score >= 75) return 'success';
    if (score >= 50) return 'warning';
    return 'error';
  };

  const getPhaseTone = (phase = '') => {
    const normalized = phase.toLowerCase();
    if (['build', 'handoff', 'prometheus'].includes(normalized)) return 'warning';
    if (['research', 'validate', 'validation'].includes(normalized)) return 'primary';
    if (['clarify', 'discovery'].includes(normalized)) return 'accent';
    return 'muted';
  };

  const formatPhase = (phase = '') => phase
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase()) || 'Capture';

  const formatUpdated = (idea) => {
    const source = idea.updated_at || idea.created_at;
    if (!source) return 'Updated recently';

    const diffMs = Date.now() - new Date(source).getTime();
    const diffHours = Math.max(1, Math.round(diffMs / 36e5));
    if (diffHours < 24) return `Updated ${diffHours}h ago`;
    const diffDays = Math.round(diffHours / 24);
    return `Updated ${diffDays}d ago`;
  };

  const miniMetrics = $derived([
    { label: 'Market', value: Math.max(0, Math.min(100, scoreToPercent(idea.composite_score || 0) + 6)), icon: BarChart3 },
    { label: 'Feasibility', value: Math.max(0, Math.min(100, scoreToPercent(idea.composite_score || 0) - 4)), icon: Wrench },
    { label: 'Problem', value: Math.max(0, Math.min(100, scoreToPercent(idea.composite_score || 0) + 2)), icon: Target }
  ]);

  let score = $derived(scoreToPercent(idea.composite_score || 0));
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
<div 
  class="idea-card" 
  onclick={onclick}
  role="button"
  tabindex="0"
  onkeydown={(e) => { if (e.key === 'Enter') onclick?.(); }}
>
  <Card>
    <div class="idea-header">
      <div>
        <h3 class="idea-title">{idea.title}</h3>
        <p class="idea-description">{idea.description}</p>
      </div>
      <ScoreBar variant="ring" dimension="Composite score" value={score} max={100} />
    </div>
    
    <div class="idea-status">
      <Badge variant={getPhaseTone(idea.current_phase)} size="sm">
        {formatPhase(idea.current_phase)}
      </Badge>
      {#if idea.source_type === 'github_project'}
        <Badge variant="primary" size="sm">
          <GitBranch size={12} />
          Project Twin
        </Badge>
      {/if}
      <span class="potential {getScoreColor(score)}">{score >= 75 ? 'Strong Potential' : score >= 50 ? 'Good Potential' : 'Needs Work'}</span>
    </div>

    <div class="mini-metrics" aria-label="Idea score drivers">
      {#each miniMetrics as metric}
        {@const Icon = metric.icon}
        <div>
          <Icon size={17} />
          <span>{metric.label}</span>
          <strong>{metric.value}</strong>
        </div>
      {/each}
    </div>
    
    <div class="idea-footer">
      <span class="idea-date">
        <CalendarClock size={14} />
        {formatUpdated(idea)}
      </span>
      <button type="button" class="more-button" aria-label={`Open ${idea.title} options`} onclick={(event) => event.stopPropagation()}>
        <MoreHorizontal size={18} />
      </button>
    </div>
  </Card>
</div>

<style>
  .idea-card {
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    cursor: pointer;
  }

  .idea-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }

  .idea-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-md);
  }

  .idea-title {
    color: var(--color-text);
    margin: 0;
    font-size: 1.125rem;
    font-weight: 600;
  }

  .idea-status {
    align-items: center;
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    justify-content: space-between;
    margin-bottom: var(--spacing-md);
  }

  .idea-status .potential {
    margin-left: auto;
  }

  .idea-description {
    color: var(--color-text-secondary);
    display: -webkit-box;
    font-size: 0.88rem;
    line-height: 1.35;
    margin: var(--spacing-xs) 0 0;
    min-height: 42px;
    overflow: hidden;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .potential {
    font-size: 0.76rem;
  }

  .potential.success {
    color: var(--color-success);
  }

  .potential.warning {
    color: var(--color-warning);
  }

  .potential.error {
    color: var(--color-text-secondary);
  }

  .mini-metrics {
    border-bottom: 1px solid rgba(103, 128, 151, 0.2);
    border-top: 1px solid rgba(103, 128, 151, 0.2);
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    margin-top: var(--spacing-md);
    padding: var(--spacing-md) 0;
  }

  .mini-metrics div {
    align-items: center;
    border-right: 1px solid rgba(103, 128, 151, 0.18);
    display: grid;
    gap: 2px 8px;
    grid-template-columns: 20px 1fr;
    padding: 0 var(--spacing-sm);
  }

  .mini-metrics div:first-child {
    padding-left: 0;
  }

  .mini-metrics div:last-child {
    border-right: 0;
    padding-right: 0;
  }

  .mini-metrics :global(svg) {
    color: var(--color-primary-2);
    grid-row: span 2;
  }

  .mini-metrics span {
    color: var(--color-text-muted);
    font-family: var(--font-mono);
    font-size: 0.62rem;
    text-transform: uppercase;
  }

  .mini-metrics strong {
    color: var(--color-text);
    font-size: 0.82rem;
  }

  .idea-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: var(--spacing-md);
  }

  .idea-date {
    align-items: center;
    color: var(--color-text-secondary);
    display: inline-flex;
    gap: 6px;
    font-size: 0.75rem;
  }

  .more-button {
    background: transparent;
    border: 0;
    color: var(--color-text-secondary);
    min-height: 28px;
    min-width: 30px;
    padding: 4px;
  }

  @media (max-width: 420px) {
    .mini-metrics {
      grid-template-columns: 1fr;
      gap: var(--spacing-sm);
    }

    .mini-metrics div {
      border-right: 0;
      padding: 0;
    }
  }
</style>
