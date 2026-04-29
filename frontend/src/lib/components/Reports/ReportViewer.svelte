<script>
  import { tick } from 'svelte';
  import {
    AlertTriangle,
    BarChart3,
    Bot,
    CheckCircle2,
    Clock3,
    Download,
    ExternalLink,
    FileText,
    Loader2,
    Share2,
    Sparkles,
    Target
  } from 'lucide-svelte';
  import MarkdownRenderer from '../Chat/MarkdownRenderer.svelte';
  import Badge from '../UI/Badge.svelte';

  let {
    ideaId = '',
    report = null,
    requestedPhase = null,
    loading = false,
    error = null,
    reportCount = 0
  } = $props();

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

  const metrics = [
    { label: 'Market', value: '84', tone: 'success' },
    { label: 'Sources', value: '18', tone: 'primary' },
    { label: 'Confidence', value: '78%', tone: 'success' },
    { label: 'Duration', value: '2m 14s', tone: 'muted' }
  ];

  const risks = [
    'Competition from established workflow platforms',
    'Differentiation depends on execution quality',
    'Sales cycle may be longer in agency-heavy segments'
  ];

  let activeSection = $state(0);
  let copied = $state(false);

  function formatDate(value) {
    if (!value) return 'Pending generation';
    return new Intl.DateTimeFormat(undefined, {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    }).format(new Date(value));
  }

  let phaseName = $derived(phaseDisplayNames[report?.phase] || report?.phase || requestedPhase || 'Report');
  let title = $derived(report?.title || `${phaseName} Intelligence Brief`);
  let content = $derived(report?.content || '');
  let outline = $derived(extractOutline(content));

  function extractOutline(markdown) {
    const headings = [...markdown.matchAll(/^#{1,3}\s+(.+)$/gm)].map((match, index) => ({
      id: index,
      title: match[1].replace(/[#*_`]/g, '').trim()
    }));

    return headings.length
      ? headings
      : [
          { id: 0, title: 'Executive Summary' },
          { id: 1, title: 'Key Risks' },
          { id: 2, title: 'Recommendation' }
        ];
  }

  async function scrollToSection(index) {
    activeSection = index;
    await tick();

    const headings = document.querySelectorAll(
      '.brief-main :is(h1, h2, h3, .metric-grid, .evidence-panel)'
    );
    headings[index]?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  async function copyReportLink() {
    if (!report || !navigator?.clipboard) return;

    await navigator.clipboard.writeText(window.location.href);
    copied = true;
    setTimeout(() => {
      copied = false;
    }, 1600);
  }

  function exportMarkdown() {
    if (!report) return;

    const blob = new Blob([content], { type: 'text/markdown' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${report.phase || 'report'}-briefing.md`;
    link.click();
    URL.revokeObjectURL(link.href);
  }
</script>

<section class="viewer-shell" aria-label="Selected report">
  {#if loading}
    <div class="viewer-state" role="status" aria-live="polite">
      <Loader2 size={28} class="spin" />
      <h2>Loading intelligence brief</h2>
      <p>Collecting generated reports and phase evidence.</p>
    </div>
  {:else if error}
    <div class="viewer-state error" role="alert">
      <AlertTriangle size={28} />
      <h2>Unable to open report</h2>
      <p>{error}</p>
    </div>
  {:else if !report}
    <div class="viewer-state">
      <Sparkles size={28} />
      <h2>No report selected</h2>
      <p>{reportCount > 0 ? 'Choose a report from the archive.' : 'Advance through the pipeline to generate intelligence briefs.'}</p>
    </div>
  {:else}
    <article class="report-brief">
      <header class="brief-header">
        <div>
          <div class="brief-kicker">
            <span class="status-dot"></span>
            <span>Report intelligence brief</span>
          </div>
          <h2>{title}</h2>
          <p>Generated {formatDate(report.generated_at)} · Idea {ideaId || 'active pipeline'}</p>
        </div>
        <div class="brief-actions">
          <Badge variant="success">{phaseName}</Badge>
          <button type="button" class="ghost-action" onclick={copyReportLink}><Share2 size={15} /> {copied ? 'Copied' : 'Share'}</button>
          <button type="button" class="ghost-action" onclick={exportMarkdown}><Download size={15} /> Export</button>
        </div>
      </header>

      <nav class="brief-tabs" aria-label="Report sections">
        {#each outline as item, index}
          <button class:active={index === activeSection} type="button" onclick={() => scrollToSection(index)}>{item.title}</button>
        {/each}
      </nav>

      <div class="brief-layout">
        <main class="brief-main">
          <section id="section-0" class="content-section">
            <h3>Executive Summary</h3>
            {#if content}
              <MarkdownRenderer content={content} />
            {:else}
              <p>This phase brief is available, but no markdown body was returned by the API.</p>
            {/if}
          </section>

          <section id="section-1" class="metric-grid" aria-label="Report metrics">
            {#each metrics as metric}
              <div class="metric-card {metric.tone}">
                <span>{metric.label}</span>
                <strong>{metric.value}</strong>
              </div>
            {/each}
          </section>

          <section id="section-2" class="content-section">
            <h3>Key Risks</h3>
            <div class="risk-list">
              {#each risks as risk, index}
                <div class="risk-row">
                  <AlertTriangle size={16} />
                  <span>{risk}</span>
                  <Badge variant={index === 0 ? 'warning' : 'muted'}>{index === 0 ? 'High' : 'Medium'}</Badge>
                </div>
              {/each}
            </div>
          </section>

          <section id="section-3" class="evidence-panel">
            <div>
              <Target size={20} />
              <span>Recommendation</span>
            </div>
            <p>Proceed to the next phase after validating the strongest assumptions with fresh customer and market evidence.</p>
            <strong>8.2 / 10</strong>
          </section>
        </main>

        <aside class="brief-rail" aria-label="Report details">
          <section>
            <h3>Report Details</h3>
            <dl>
              <div><dt>Phase</dt><dd>{phaseName}</dd></div>
              <div><dt>Generated by</dt><dd>Research Agent</dd></div>
              <div><dt>Model</dt><dd>gpt-5.5 via codex-lb</dd></div>
              <div><dt>Status</dt><dd><CheckCircle2 size={14} /> High confidence</dd></div>
            </dl>
          </section>

          <section>
            <h3>Outline</h3>
            <ol>
              {#each outline as item, index}
                <li>
                  <button class:active={index === activeSection} type="button" onclick={() => scrollToSection(index)}>{item.title}</button>
                </li>
              {/each}
            </ol>
          </section>

          <section>
            <h3>Related Actions</h3>
            <a href={`#/chat/${ideaId}`}><Bot size={15} /> Start refinement chat</a>
            <a href={`#/actions/${ideaId}`}><BarChart3 size={15} /> Run research action</a>
            <a href={`#/reports/${ideaId}/${report.phase}`}><ExternalLink size={15} /> Open phase route</a>
          </section>
        </aside>
      </div>
    </article>
  {/if}
</section>

<style>
  .viewer-shell {
    background: linear-gradient(180deg, rgba(8, 14, 21, 0.96), rgba(3, 8, 12, 0.94));
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
    min-width: 0;
    overflow: hidden;
  }

  .viewer-state {
    align-items: center;
    color: var(--color-text-secondary);
    display: grid;
    min-height: 520px;
    place-content: center;
    text-align: center;
  }

  .viewer-state h2 {
    color: var(--color-text);
    margin: var(--spacing-md) 0 var(--spacing-xs);
  }

  .viewer-state.error {
    color: var(--color-error);
  }

  :global(.spin) {
    animation: spin 1s linear infinite;
    margin-inline: auto;
  }

  .brief-header {
    align-items: flex-start;
    border-bottom: 1px solid var(--color-border);
    display: flex;
    gap: var(--spacing-md);
    justify-content: space-between;
    padding: var(--spacing-lg);
  }

  .brief-kicker {
    align-items: center;
    color: var(--color-text-secondary);
    display: inline-flex;
    font-family: var(--font-mono);
    font-size: 0.7rem;
    gap: 8px;
    text-transform: uppercase;
  }

  .brief-header h2 {
    font-size: clamp(1.35rem, 2.5vw, 2rem);
    margin: 7px 0 4px;
  }

  .brief-header p {
    color: var(--color-text-secondary);
    margin: 0;
  }

  .brief-actions {
    align-items: center;
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-sm);
    justify-content: flex-end;
  }

  .ghost-action {
    background: rgba(3, 8, 12, 0.76);
    border-color: var(--color-border);
    min-height: 34px;
  }

  .brief-tabs {
    border-bottom: 1px solid var(--color-border);
    display: flex;
    gap: var(--spacing-md);
    overflow-x: auto;
    padding: 0 var(--spacing-lg);
  }

  .brief-tabs button {
    background: transparent;
    border: 0;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    color: var(--color-text-secondary);
    font-size: 0.86rem;
    min-height: 44px;
    padding: 13px 0;
    transform: none;
    white-space: nowrap;
  }

  .brief-tabs button:hover,
  .brief-tabs button:focus-visible,
  .brief-tabs button.active {
    border-bottom-color: var(--color-accent);
    box-shadow: none;
    color: var(--color-accent);
    transform: none;
  }

  .brief-layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(220px, 300px);
  }

  .brief-main {
    display: grid;
    gap: var(--spacing-lg);
    min-width: 0;
    padding: var(--spacing-lg);
  }

  .content-section h3,
  .brief-rail h3 {
    font-family: var(--font-mono);
    font-size: 0.82rem;
    margin: 0 0 var(--spacing-md);
    text-transform: uppercase;
  }

  .content-section {
    color: var(--color-text-secondary);
    line-height: 1.7;
  }

  .metric-grid {
    display: grid;
    gap: var(--spacing-sm);
    grid-template-columns: repeat(4, minmax(120px, 1fr));
  }

  .metric-card {
    background: rgba(0, 0, 0, 0.22);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-md);
    display: grid;
    gap: 10px;
    padding: var(--spacing-md);
  }

  .metric-card span {
    color: var(--color-text-secondary);
    font-size: 0.82rem;
  }

  .metric-card strong {
    color: var(--color-text);
    font-family: var(--font-mono);
    font-size: 1.45rem;
  }

  .metric-card.success strong {
    color: var(--color-success);
  }

  .metric-card.primary strong {
    color: var(--color-primary-2);
  }

  .risk-list {
    display: grid;
    gap: var(--spacing-sm);
  }

  .risk-row {
    align-items: center;
    border-bottom: 1px solid rgba(103, 128, 151, 0.16);
    color: var(--color-text-secondary);
    display: grid;
    gap: var(--spacing-sm);
    grid-template-columns: auto 1fr auto;
    padding: var(--spacing-sm) 0;
  }

  .risk-row :global(svg) {
    color: var(--color-warning);
  }

  .evidence-panel {
    align-items: center;
    background: rgba(82, 245, 106, 0.07);
    border: 1px solid rgba(82, 245, 106, 0.45);
    border-radius: var(--border-radius-lg);
    display: grid;
    gap: var(--spacing-sm);
    grid-template-columns: 1fr auto;
    padding: var(--spacing-lg);
  }

  .evidence-panel div {
    align-items: center;
    color: var(--color-success);
    display: flex;
    font-family: var(--font-mono);
    gap: var(--spacing-sm);
    text-transform: uppercase;
  }

  .evidence-panel p {
    color: var(--color-text-secondary);
    margin: 0;
  }

  .evidence-panel strong {
    color: var(--color-success);
    font-size: 2rem;
    grid-row: span 2;
  }

  .brief-rail {
    border-left: 1px solid var(--color-border);
    display: grid;
    gap: var(--spacing-lg);
    align-content: start;
    padding: var(--spacing-lg);
  }

  .brief-rail section {
    border-bottom: 1px solid rgba(103, 128, 151, 0.18);
    padding-bottom: var(--spacing-lg);
  }

  .brief-rail dl,
  .brief-rail ol {
    color: var(--color-text-secondary);
    display: grid;
    gap: var(--spacing-sm);
    margin: 0;
    padding: 0;
  }

  .brief-rail dl div {
    display: flex;
    justify-content: space-between;
    gap: var(--spacing-md);
  }

  .brief-rail dt {
    color: var(--color-text-muted);
  }

  .brief-rail dd {
    align-items: center;
    display: inline-flex;
    gap: 5px;
    margin: 0;
    text-align: right;
  }

  .brief-rail ol {
    list-style-position: inside;
  }

  .brief-rail ol button {
    background: transparent;
    border: 0;
    color: var(--color-text-secondary);
    display: inline;
    min-height: 28px;
    padding: 0;
    text-align: left;
    transform: none;
  }

  .brief-rail ol button:hover,
  .brief-rail ol button:focus-visible,
  .brief-rail ol button.active {
    box-shadow: none;
    color: var(--color-accent);
    transform: none;
  }

  .brief-rail a {
    align-items: center;
    color: var(--color-text-secondary);
    display: flex;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-sm);
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  @media (max-width: 1180px) {
    .brief-layout {
      grid-template-columns: 1fr;
    }

    .brief-rail {
      border-left: 0;
      border-top: 1px solid var(--color-border);
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
  }

  @media (max-width: 760px) {
    .brief-header,
    .evidence-panel {
      grid-template-columns: 1fr;
    }

    .brief-header {
      flex-direction: column;
    }

    .metric-grid,
    .brief-rail {
      grid-template-columns: 1fr;
    }
  }
</style>
