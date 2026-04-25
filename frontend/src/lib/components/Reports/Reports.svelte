<script>
  import { onMount } from 'svelte';
  import ReportList from './ReportList.svelte';
  import ReportViewer from './ReportViewer.svelte';
  import { api } from '../../api.js';

  let { ideaId = '', phase = null } = $props();

  let reports = $state([]);
  let loading = $state(true);
  let error = $state(null);

  const phaseOrder = [
    'capture',
    'clarify',
    'refine',
    'market_research',
    'competitive_analysis',
    'monetization',
    'feasibility',
    'tech_spec',
    'score',
    'research',
    'build'
  ];

  let sortedReports = $derived(
    [...reports].sort((a, b) => {
      const aIndex = phaseOrder.indexOf(a.phase);
      const bIndex = phaseOrder.indexOf(b.phase);
      const phaseSort =
        (aIndex === -1 ? 99 : aIndex) - (bIndex === -1 ? 99 : bIndex);

      if (phaseSort !== 0) return phaseSort;

      return new Date(b.generated_at || 0) - new Date(a.generated_at || 0);
    })
  );

  let selectedReport = $derived(
    sortedReports.find((report) => report.phase === phase) || sortedReports[0] || null
  );

  function normalizeReports(data) {
    if (Array.isArray(data)) return data;
    if (Array.isArray(data?.reports)) return data.reports;
    return [];
  }

  async function loadReports() {
    if (!ideaId) {
      reports = [];
      error = null;
      loading = false;
      return;
    }

    loading = true;
    error = null;

    try {
      const data = await api(`/api/ideas/${ideaId}/reports`);
      reports = normalizeReports(data);
    } catch (err) {
      error = err.message || 'Unable to load reports.';
    } finally {
      loading = false;
    }
  }

  onMount(loadReports);
</script>

<div class="reports-container">
  <section class="reports-hero" aria-labelledby="reports-title">
    <div>
      <span class="mono-label">Intelligence archive</span>
      <h1 id="reports-title">Reports</h1>
      <p>AI-generated briefings across the idea pipeline.</p>
    </div>
    <div class="reports-summary" aria-label="Report summary">
      <span>{reports.length}</span>
      <small>{reports.length === 1 ? 'report' : 'reports'} indexed</small>
    </div>
  </section>

  <div class="reports-workspace">
    <ReportList
      {ideaId}
      reports={sortedReports}
      selectedPhase={selectedReport?.phase}
      {loading}
      {error}
    />
    <ReportViewer
      {ideaId}
      report={selectedReport}
      requestedPhase={phase}
      {loading}
      {error}
      reportCount={reports.length}
    />
  </div>
</div>

<style>
  .reports-container {
    display: grid;
    gap: var(--spacing-md);
    min-height: calc(100vh - 156px);
  }

  .reports-hero {
    align-items: end;
    display: flex;
    gap: var(--spacing-lg);
    justify-content: space-between;
  }

  .reports-hero h1 {
    font-size: clamp(1.75rem, 3vw, 2.5rem);
    line-height: 1;
    margin: 6px 0 4px;
  }

  .reports-hero p {
    color: var(--color-text-secondary);
    margin: 0;
  }

  .reports-summary {
    align-items: flex-end;
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
    display: grid;
    min-width: 138px;
    padding: var(--spacing-sm) var(--spacing-md);
    text-align: right;
  }

  .reports-summary span {
    color: var(--color-success);
    font-family: var(--font-mono);
    font-size: 1.45rem;
    line-height: 1.1;
  }

  .reports-summary small {
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.68rem;
    text-transform: uppercase;
  }

  .reports-workspace {
    display: grid;
    gap: var(--spacing-md);
    grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
    min-height: 0;
  }

  @media (max-width: 1120px) {
    .reports-workspace {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 680px) {
    .reports-hero {
      align-items: stretch;
      flex-direction: column;
    }

    .reports-summary {
      text-align: left;
    }
  }
</style>
