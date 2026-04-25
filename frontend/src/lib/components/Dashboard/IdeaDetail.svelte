<script>
  import { BarChart3, CalendarClock, Flag, Target, Wrench } from 'lucide-svelte';
  import Badge from '../UI/Badge.svelte';
  import ScoreBar from './ScoreBar.svelte';

  let { idea = {
    id: '',
    title: '',
    slug: '',
    description: '',
    current_phase: '',
    status: '',
    created_at: '',
    updated_at: '',
    scores: []
  } } = $props();

  const scoreDimensions = [
    { key: 'tam', name: 'Market Size' },
    { key: 'competition', name: 'Competition' },
    { key: 'feasibility', name: 'Feasibility' },
    { key: 'time_to_mvp', name: 'Time to MVP' },
    { key: 'revenue', name: 'Revenue' },
    { key: 'uniqueness', name: 'Uniqueness' },
    { key: 'personal_fit', name: 'Personal Fit' }
  ];

  const scoreToPercent = (score = 0) => Math.round(Math.min(100, Math.max(0, score <= 10 ? score * 10 : score)));

  const formatPhase = (phase = '') => phase
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase()) || 'Capture';

  const scoreValue = (dimension) => idea.scores?.find((score) => score.dimension === dimension)?.value || 0;

  let compositeScore = $derived(scoreToPercent(idea.composite_score || 0));
  let miniMetrics = $derived([
    { label: 'Market', value: scoreToPercent(scoreValue('tam') || idea.composite_score || 0), icon: BarChart3 },
    { label: 'Feasibility', value: scoreToPercent(scoreValue('feasibility') || idea.composite_score || 0), icon: Wrench },
    { label: 'Problem', value: scoreToPercent(scoreValue('competition') || idea.composite_score || 0), icon: Target }
  ]);
</script>

<div class="idea-detail">
  <div class="idea-header">
    <div>
      <p class="mono-label">Idea dossier</p>
      <h1>{idea.title}</h1>
    </div>
    <ScoreBar variant="ring" dimension="Composite score" value={compositeScore} max={100} />
  </div>
  
  <div class="idea-meta">
    <span class="status-badge">
      <Badge variant={idea.status === 'active' ? 'success' : 'error'}>
        {idea.status}
      </Badge>
      <Badge variant="primary" size="md">
        <Flag size={13} />
        {formatPhase(idea.current_phase)}
      </Badge>
    </span>
    <span class="dates">
      <CalendarClock size={14} />
      Created {new Date(idea.created_at).toLocaleDateString()} | Updated {new Date(idea.updated_at).toLocaleDateString()}
    </span>
  </div>
  
  <section class="detail-metrics" aria-label="Idea metric summary">
    {#each miniMetrics as metric}
      {@const Icon = metric.icon}
      <article>
        <Icon size={18} />
        <span>{metric.label}</span>
        <strong>{metric.value}</strong>
      </article>
    {/each}
  </section>

  <div class="idea-description">
    <p>{idea.description}</p>
  </div>
  
  <div class="scores-section">
    <h2>Scores</h2>
    {#each scoreDimensions as dimension}
      <ScoreBar 
        dimension={dimension.name} 
        value={scoreValue(dimension.key)}
      />
    {/each}
  </div>
  
  <div class="phase-history">
    <h2>Phase History</h2>
    <div class="phase-timeline">
      <div class="phase-item current">
        <div class="phase-badge">
          <Badge variant="primary">
            {formatPhase(idea.current_phase)}
          </Badge>
        </div>
        <div class="phase-date">
          Current
        </div>
      </div>
      <!-- In a real app, this would show historical phases -->
    </div>
  </div>
</div>

<style>
  .idea-detail {
    max-width: 920px;
    margin: 0 auto;
  }
  
  .idea-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: var(--spacing-lg);
    margin-bottom: var(--spacing-lg);
  }
  
  .idea-header h1 {
    color: var(--color-text);
    margin: var(--spacing-xs) 0 0;
    font-size: 1.75rem;
    font-weight: 700;
  }
  
  .idea-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-lg);
    padding-bottom: var(--spacing-md);
    border-bottom: 1px solid var(--color-border);
  }
  
  .status-badge {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    flex-wrap: wrap;
  }
  
  .dates {
    align-items: center;
    color: var(--color-text-secondary);
    display: inline-flex;
    gap: 6px;
    font-size: 0.875rem;
  }

  .detail-metrics {
    display: grid;
    gap: var(--spacing-md);
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin-bottom: var(--spacing-lg);
  }

  .detail-metrics article {
    align-items: center;
    background: rgba(5, 10, 15, 0.72);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
    display: grid;
    gap: 2px 10px;
    grid-template-columns: 28px 1fr;
    padding: var(--spacing-md);
  }

  .detail-metrics svg {
    color: var(--color-primary-2);
    grid-row: span 2;
  }

  .detail-metrics span {
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.68rem;
    text-transform: uppercase;
  }

  .detail-metrics strong {
    color: var(--color-text);
    font-size: 1.2rem;
    line-height: 1;
  }
  
  .idea-description {
    background: rgba(5, 10, 15, 0.68);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
    margin-bottom: var(--spacing-xl);
    padding: var(--spacing-lg);
    line-height: 1.6;
  }

  .idea-description p {
    margin: 0;
  }
  
  .scores-section {
    margin-bottom: var(--spacing-xl);
  }
  
  .scores-section h2 {
    color: var(--color-text);
    margin: 0 0 var(--spacing-lg) 0;
    font-size: 1.25rem;
    font-weight: 600;
  }
  
  .phase-history {
    margin-top: var(--spacing-xl);
  }
  
  .phase-history h2 {
    color: var(--color-text);
    margin: 0 0 var(--spacing-lg) 0;
    font-size: 1.25rem;
    font-weight: 600;
  }
  
  .phase-timeline {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }
  
  .phase-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
  }
  
  .phase-badge {
    flex-shrink: 0;
  }
  
  .phase-date {
    color: var(--color-text-secondary);
    font-size: 0.875rem;
  }
  
  .phase-item.current {
    border-left: 3px solid var(--color-accent);
    padding-left: var(--spacing-md);
  }

  @media (max-width: 720px) {
    .idea-header,
    .idea-meta {
      align-items: flex-start;
      flex-direction: column;
    }

    .detail-metrics {
      grid-template-columns: 1fr;
    }
  }
</style>
