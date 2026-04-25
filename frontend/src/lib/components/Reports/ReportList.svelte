<script>
  import {
    AlertCircle,
    Archive,
    ChevronRight,
    FileText,
    Loader2,
    Search,
    Sparkles
  } from 'lucide-svelte';

  let {
    ideaId = '',
    reports = [],
    selectedPhase = null,
    loading = false,
    error = null
  } = $props();

  let query = $state('');

  const phaseDisplayNames = {
    capture: 'Capture',
    clarify: 'Clarify',
    refine: 'Refine',
    market_research: 'Market Research',
    competitive_analysis: 'Competitive Analysis',
    monetization: 'Monetization',
    feasibility: 'Feasibility',
    tech_spec: 'Tech Spec',
    score: 'Scoring',
    research: 'Research',
    build: 'Build'
  };

  const phaseNumbers = {
    capture: '01',
    clarify: '02',
    refine: '02',
    market_research: '03',
    competitive_analysis: '04',
    monetization: '05',
    feasibility: '06',
    tech_spec: '07',
    score: '08',
    research: '09',
    build: '10'
  };

  let filteredReports = $derived(
    reports.filter((report) => {
      const searchText = `${report.title || ''} ${report.phase || ''} ${report.content || ''}`;
      return searchText.toLowerCase().includes(query.trim().toLowerCase());
    })
  );

  let groupedReports = $derived(() => {
    const groups = [];

    for (const report of filteredReports) {
      const phase = report.phase || 'other';
      let group = groups.find((item) => item.phase === phase);

      if (!group) {
        group = { phase, reports: [] };
        groups.push(group);
      }

      group.reports.push(report);
    }

    return groups;
  });

  function viewReport(report) {
    if (!ideaId || !report?.phase) return;
    window.location.hash = `/reports/${ideaId}/${report.phase}`;
  }

  function handleReportKeydown(event, report) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      viewReport(report);
      return;
    }

    if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;

    const buttons = [...document.querySelectorAll('.report-row')];
    const currentIndex = buttons.indexOf(event.currentTarget);
    const direction = event.key === 'ArrowDown' ? 1 : -1;
    const nextButton = buttons[currentIndex + direction];

    if (nextButton) {
      event.preventDefault();
      nextButton.focus();
    }
  }

  function formatDate(value) {
    if (!value) return 'Pending timestamp';

    return new Intl.DateTimeFormat(undefined, {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    }).format(new Date(value));
  }

  function preview(content = '') {
    return content
      .replace(/[#*_>`-]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, 112);
  }
</script>

<aside class="report-browser" aria-label="Report browser">
  <div class="browser-toolbar">
    <label class="search-field">
      <Search size={16} aria-hidden="true" />
      <span class="visually-hidden">Search reports</span>
      <input bind:value={query} type="search" placeholder="Search reports..." />
    </label>
  </div>

  <div class="browser-label">
    <span>Grouped by phase</span>
    <span>{filteredReports.length}</span>
  </div>

  {#if loading}
    <div class="state-panel" role="status" aria-live="polite">
      <Loader2 size={22} class="spin" />
      <strong>Loading reports</strong>
      <p>Collecting generated briefings for this idea.</p>
    </div>
  {:else if error}
    <div class="state-panel error" role="alert">
      <AlertCircle size={22} />
      <strong>Reports unavailable</strong>
      <p>{error}</p>
    </div>
  {:else if reports.length === 0}
    <div class="state-panel">
      <Sparkles size={22} />
      <strong>No reports yet</strong>
      <p>Advance through phases to generate the first briefing.</p>
    </div>
  {:else if filteredReports.length === 0}
    <div class="state-panel">
      <Search size={22} />
      <strong>No matches</strong>
      <p>Try a title, phase, or phrase from the report body.</p>
    </div>
  {:else}
    <div class="phase-list">
      {#each groupedReports() as group}
        <section class="phase-section" aria-labelledby={`phase-${group.phase}`}>
          <h2 id={`phase-${group.phase}`}>
            <span class="phase-number">{phaseNumbers[group.phase] || '--'}</span>
            <span>{phaseDisplayNames[group.phase] || group.phase}</span>
            <small>{group.reports.length}</small>
          </h2>

          <div class="report-stack">
            {#each group.reports as report}
              <button
                class:active={report.phase === selectedPhase}
                class="report-row"
                type="button"
                aria-current={report.phase === selectedPhase ? 'page' : undefined}
                onclick={() => viewReport(report)}
                onkeydown={(event) => handleReportKeydown(event, report)}
              >
                <span class="report-status" aria-hidden="true"></span>
                <span class="report-copy">
                  <strong>{report.title || `${phaseDisplayNames[report.phase] || report.phase} Report`}</strong>
                  <small>{preview(report.content) || 'Generated phase briefing'}</small>
                </span>
                <span class="report-meta">
                  <time datetime={report.generated_at}>{formatDate(report.generated_at)}</time>
                  <ChevronRight size={14} aria-hidden="true" />
                </span>
              </button>
            {/each}
          </div>
        </section>
      {/each}
    </div>
  {/if}

  <button class="archive-row" type="button" disabled>
    <Archive size={15} />
    Archived reports
    <span>0</span>
  </button>
</aside>

<style>
  .report-browser {
    background: linear-gradient(180deg, rgba(8, 14, 21, 0.95), rgba(3, 8, 12, 0.94));
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
    display: flex;
    flex-direction: column;
    min-height: 620px;
    overflow: hidden;
  }

  .browser-toolbar {
    border-bottom: 1px solid var(--color-border);
    padding: var(--spacing-md);
  }

  .search-field {
    align-items: center;
    background: rgba(2, 6, 10, 0.86);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-md);
    color: var(--color-text-muted);
    display: flex;
    gap: var(--spacing-sm);
    padding: 0 var(--spacing-sm);
  }

  .search-field:focus-within {
    border-color: rgba(0, 186, 255, 0.82);
    box-shadow: 0 0 0 3px rgba(0, 120, 255, 0.16);
  }

  .search-field input {
    background: transparent;
    border: 0;
    box-shadow: none;
    min-width: 0;
    outline: 0;
    padding-left: 0;
    width: 100%;
  }

  .browser-label {
    align-items: center;
    color: var(--color-text-secondary);
    display: flex;
    font-family: var(--font-mono);
    font-size: 0.68rem;
    justify-content: space-between;
    padding: var(--spacing-sm) var(--spacing-md);
    text-transform: uppercase;
  }

  .phase-list {
    display: grid;
    gap: var(--spacing-sm);
    overflow-y: auto;
    padding: 0 var(--spacing-md) var(--spacing-md);
  }

  .phase-section {
    border-top: 1px solid rgba(103, 128, 151, 0.18);
    padding-top: var(--spacing-sm);
  }

  .phase-section h2 {
    align-items: center;
    color: var(--color-text-secondary);
    display: flex;
    font-family: var(--font-mono);
    font-size: 0.72rem;
    font-weight: 600;
    gap: var(--spacing-sm);
    letter-spacing: 0;
    margin: 0 0 var(--spacing-xs);
    text-transform: uppercase;
  }

  .phase-section h2 small {
    color: var(--color-text-muted);
    margin-left: auto;
  }

  .phase-number {
    color: var(--color-primary-2);
  }

  .report-stack {
    display: grid;
    gap: 2px;
  }

  .report-row {
    align-items: center;
    background: transparent;
    border: 1px solid transparent;
    border-radius: var(--border-radius-md);
    color: var(--color-text);
    display: grid;
    gap: var(--spacing-sm);
    grid-template-columns: 8px minmax(0, 1fr) auto;
    justify-content: initial;
    min-height: 58px;
    padding: var(--spacing-sm);
    text-align: left;
    transform: none;
    width: 100%;
  }

  .report-row:hover,
  .report-row:focus-visible,
  .report-row.active {
    background: rgba(0, 120, 255, 0.1);
    border-color: rgba(0, 186, 255, 0.34);
    box-shadow: none;
    transform: none;
  }

  .report-row.active {
    box-shadow: inset 3px 0 0 var(--color-accent);
  }

  .report-status {
    background: var(--color-success);
    border-radius: 999px;
    box-shadow: 0 0 12px rgba(82, 245, 106, 0.5);
    height: 7px;
    width: 7px;
  }

  .report-copy {
    display: grid;
    gap: 2px;
    min-width: 0;
  }

  .report-copy strong,
  .report-copy small {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .report-copy strong {
    font-size: 0.9rem;
    font-weight: 600;
  }

  .report-copy small,
  .report-meta {
    color: var(--color-text-secondary);
    font-size: 0.75rem;
  }

  .report-meta {
    align-items: center;
    display: inline-flex;
    gap: 6px;
  }

  .state-panel {
    align-items: center;
    color: var(--color-text-secondary);
    display: grid;
    gap: var(--spacing-sm);
    justify-items: center;
    margin: var(--spacing-md);
    min-height: 220px;
    padding: var(--spacing-xl);
    text-align: center;
  }

  .state-panel strong {
    color: var(--color-text);
  }

  .state-panel p {
    margin: 0;
  }

  .state-panel.error {
    color: var(--color-error);
  }

  .archive-row {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid var(--color-border);
    color: var(--color-text-secondary);
    justify-content: flex-start;
    margin: auto var(--spacing-md) var(--spacing-md);
    transform: none;
  }

  .archive-row span {
    margin-left: auto;
  }

  :global(.spin) {
    animation: spin 0.9s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  @media (max-width: 1120px) {
    .report-browser {
      min-height: auto;
    }

    .phase-list {
      max-height: 360px;
    }
  }
</style>
