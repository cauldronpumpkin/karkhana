<script>
  let { dimension = '', value = 0, max = 10, variant = 'bar' } = $props();

  let normalized = $derived(Math.min(100, Math.max(0, (value / max) * 100)));

  const getScoreColor = () => {
    const percent = normalized;
    if (percent >= 70) return 'score-green';
    if (percent >= 40) return 'score-yellow';
    return 'score-red';
  };

  const getScoreWidth = () => `${normalized}%`;
</script>

{#if variant === 'ring'}
  <div
    class="score-ring {getScoreColor()}"
    aria-label={`${dimension}: ${Math.round(value)} out of ${max}`}
    style={`--score: ${normalized * 3.6}deg`}
  >
    <div class="ring-core">
      <strong>{Math.round(value)}</strong>
      <span>/{max}</span>
    </div>
  </div>
{:else}
  <div class="score-bar">
    <div class="score-label">
      <span class="dimension">{dimension}</span>
      <span class="value">{value}</span>
    </div>
    <div class="score-container">
      <div class="score-track">
        <div class="score-fill {getScoreColor()}" style={`width: ${getScoreWidth()}`}></div>
      </div>
    </div>
  </div>
{/if}

<style>
  .score-bar {
    margin-bottom: var(--spacing-md);
  }

  .score-label {
    display: flex;
    justify-content: space-between;
    margin-bottom: var(--spacing-xs);
    font-size: 0.875rem;
  }

  .dimension {
    color: var(--color-text-secondary);
  }

  .value {
    color: var(--color-text);
    font-weight: 600;
  }

  .score-container {
    height: 8px;
    background-color: var(--color-surface);
    border-radius: var(--border-radius-sm);
    overflow: hidden;
  }

  .score-track {
    height: 100%;
    background-color: var(--color-border);
  }

  .score-fill {
    height: 100%;
    transition: width 0.3s ease;
  }

  .score-green {
    background-color: var(--color-success);
  }

  .score-yellow {
    background-color: var(--color-warning);
  }

  .score-red {
    background-color: var(--color-error);
  }

  .score-ring {
    --ring-color: var(--color-primary-2);
    align-items: center;
    background:
      conic-gradient(var(--ring-color) var(--score), rgba(103, 128, 151, 0.18) 0),
      rgba(6, 12, 18, 0.8);
    border-radius: 999px;
    display: inline-flex;
    flex: 0 0 auto;
    height: 76px;
    justify-content: center;
    position: relative;
    width: 76px;
  }

  .score-ring::after {
    background: rgba(5, 10, 15, 0.96);
    border: 1px solid rgba(103, 128, 151, 0.24);
    border-radius: inherit;
    content: "";
    inset: 8px;
    position: absolute;
  }

  .ring-core {
    align-items: baseline;
    display: flex;
    gap: 2px;
    position: relative;
    z-index: 1;
  }

  .ring-core strong {
    color: var(--color-text);
    font-size: 1.55rem;
    font-weight: 700;
    line-height: 1;
  }

  .ring-core span {
    color: var(--color-text-secondary);
    font-size: 0.78rem;
  }

  .score-ring.score-green {
    --ring-color: var(--color-success);
  }

  .score-ring.score-yellow {
    --ring-color: var(--color-warning);
  }

  .score-ring.score-red {
    --ring-color: var(--color-primary-2);
  }
</style>
