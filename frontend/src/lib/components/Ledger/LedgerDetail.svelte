<script>
  import { onMount } from 'svelte';
  import { marked } from 'marked';
  import DOMPurify from 'dompurify';
  import {
    ArrowLeft,
    Calendar,
    Clock,
    FileText,
    Loader2,
    RefreshCw,
    Tag,
    XCircle
  } from 'lucide-svelte';
  import { api } from '../../api.js';
  import Badge from '../UI/Badge.svelte';
  import Button from '../UI/Button.svelte';

  let { runId = '', ledgerId = '', onBack } = $props();

  let entry = $state(null);
  let isLoading = $state(true);
  let error = $state('');

  marked.setOptions({
    breaks: true,
    gfm: true,
    headerIds: false,
    mangle: false
  });

  let renderedBody = $derived(entry?.body ? DOMPurify.sanitize(marked.parse(entry.body)) : '');
  let title = $derived(entry?.title || entry?.frontmatter?.title || 'Untitled Entry');
  let stage = $derived(entry?.stage || entry?.frontmatter?.stage || '');
  let status = $derived(entry?.status || entry?.frontmatter?.status || '');
  let createdAt = $derived(entry?.created_at || entry?.frontmatter?.created_at || '');
  let updatedAt = $derived(entry?.updated_at || entry?.frontmatter?.updated_at || '');

  const stageTone = (stage) => {
    const tones = {
      planning: 'primary',
      building: 'warning',
      reviewing: 'accent',
      verifying: 'warning',
      complete: 'success'
    };
    return tones[stage] || 'muted';
  };

  const stageLabel = (stage) => {
    return stage ? stage.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) : 'Unknown';
  };

  const statusTone = (status) => {
    if (status === 'completed' || status === 'final') return 'success';
    if (status === 'in_progress' || status === 'running') return 'warning';
    if (status === 'failed' || status === 'error') return 'error';
    return 'muted';
  };

  function fmtDate(v) {
    if (!v) return 'n/a';
    try {
      return new Date(v).toLocaleString();
    } catch {
      return v;
    }
  }

  async function loadEntry() {
    if (!runId || !ledgerId) return;
    isLoading = true;
    error = '';
    try {
      entry = await api(`/api/ledgers/${runId}/${ledgerId}`);
    } catch (err) {
      error = err.message || 'Failed to load ledger entry.';
    } finally {
      isLoading = false;
    }
  }

  function handleBack() {
    onBack?.();
  }

  onMount(loadEntry);
</script>

<div class="ledger-detail">
  {#if isLoading}
    <section class="loading-state">
      <span class="spin"><Loader2 size={22} /></span>
      Loading ledger entry...
    </section>
  {:else if error && !entry}
    <section class="error-state">
      <XCircle size={22} />
      <p>{error}</p>
      <Button size="sm" onclick={loadEntry}><RefreshCw size={14} /> Retry</Button>
    </section>
  {:else if entry}
    <header class="detail-header">
      <button class="back-btn" onclick={handleBack}>
        <ArrowLeft size={16} /> Back to ledger
      </button>
      <div class="header-info">
        <div>
          <p class="mono-label"><FileText size={13} /> Ledger Entry</p>
          <h1>{title}</h1>
        </div>
        <div class="header-badges">
          {#if stage}
            <Badge variant={stageTone(stage)}>{stageLabel(stage)}</Badge>
          {/if}
          {#if status}
            <Badge variant={statusTone(status)}>{status}</Badge>
          {/if}
        </div>
      </div>
      <div class="header-actions">
        <Button size="sm" variant="secondary" onclick={loadEntry}>
          <RefreshCw size={14} /> Refresh
        </Button>
      </div>
    </header>

    <section class="meta-strip">
      <article>
        <span><Calendar size={13} /> Created</span>
        <strong>{fmtDate(createdAt)}</strong>
      </article>
      <article>
        <span><Clock size={13} /> Updated</span>
        <strong>{fmtDate(updatedAt)}</strong>
      </article>
      {#if stage}
        <article>
          <span><Tag size={13} /> Stage</span>
          <strong>{stageLabel(stage)}</strong>
        </article>
      {/if}
      {#if status}
        <article>
          <span>Status</span>
          <Badge variant={statusTone(status)} size="sm">{status}</Badge>
        </article>
      {/if}
    </section>

    {#if renderedBody}
      <section class="entry-body">
        <h2 class="section-label">Entry Body</h2>
        <div class="markdown-body">{@html renderedBody}</div>
      </section>
    {:else}
      <section class="empty-body">
        <FileText size={24} />
        <p>This ledger entry has no body content.</p>
      </section>
    {/if}
  {/if}
</div>

<style>
  .ledger-detail {
    max-width: 960px;
    margin: 0 auto;
  }

  .loading-state,
  .error-state {
    align-items: center;
    background: rgba(5, 10, 15, 0.72);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
    color: var(--color-text-secondary);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
    justify-content: center;
    min-height: 200px;
    text-align: center;
  }

  .error-state {
    color: var(--color-error);
  }

  .spin {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .detail-header {
    margin-bottom: var(--spacing-lg);
  }

  .back-btn {
    align-items: center;
    background: transparent;
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-md);
    color: var(--color-text-secondary);
    cursor: pointer;
    display: inline-flex;
    font-size: 0.82rem;
    gap: 6px;
    margin-bottom: var(--spacing-md);
    padding: 6px 12px;
    transition: color 0.15s, border-color 0.15s;
  }

  .back-btn:hover {
    border-color: var(--color-accent);
    color: var(--color-text);
  }

  .header-info {
    align-items: flex-start;
    display: flex;
    gap: var(--spacing-lg);
    justify-content: space-between;
    flex-wrap: wrap;
  }

  .mono-label {
    align-items: center;
    color: var(--color-text-secondary);
    display: flex;
    font-family: var(--font-mono);
    font-size: 0.68rem;
    gap: 6px;
    margin: 0;
    text-transform: uppercase;
  }

  .header-info h1 {
    color: var(--color-text);
    font-size: 1.6rem;
    line-height: 1.2;
    margin: 4px 0 0;
  }

  .header-badges {
    align-items: center;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .header-actions {
    display: flex;
    gap: 8px;
    margin-top: var(--spacing-md);
  }

  .meta-strip {
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
    display: grid;
    gap: 0;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    margin-bottom: var(--spacing-lg);
    overflow: hidden;
  }

  .meta-strip article {
    background: rgba(5, 10, 15, 0.68);
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: var(--spacing-md);
    position: relative;
  }

  .meta-strip article + article {
    border-left: 1px solid var(--color-border);
  }

  .meta-strip article span {
    align-items: center;
    color: var(--color-text-muted);
    display: inline-flex;
    font-family: var(--font-mono);
    font-size: 0.65rem;
    gap: 4px;
    text-transform: uppercase;
  }

  .meta-strip article strong {
    color: var(--color-text);
    font-size: 0.88rem;
  }

  .section-label {
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.68rem;
    letter-spacing: 0.04em;
    margin: 0 0 var(--spacing-md);
    text-transform: uppercase;
  }

  .entry-body {
    background: rgba(5, 10, 15, 0.6);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
    padding: var(--spacing-lg);
  }

  .markdown-body {
    color: var(--color-text);
    line-height: 1.65;
  }

  .markdown-body :global(h1),
  .markdown-body :global(h2),
  .markdown-body :global(h3),
  .markdown-body :global(h4) {
    color: var(--color-text);
    margin-top: var(--spacing-lg);
    margin-bottom: var(--spacing-md);
    font-weight: 600;
  }

  .markdown-body :global(h1) { font-size: 1.5rem; }
  .markdown-body :global(h2) { font-size: 1.25rem; }
  .markdown-body :global(h3) { font-size: 1.1rem; }
  .markdown-body :global(h4) { font-size: 1rem; }

  .markdown-body :global(p) {
    margin-bottom: var(--spacing-md);
  }

  .markdown-body :global(ul),
  .markdown-body :global(ol) {
    margin-left: var(--spacing-lg);
    margin-bottom: var(--spacing-md);
  }

  .markdown-body :global(li) {
    margin-bottom: var(--spacing-sm);
  }

  .markdown-body :global(blockquote) {
    border-left: 3px solid var(--color-accent);
    margin: var(--spacing-lg) 0;
    padding: var(--spacing-md) var(--spacing-lg);
    background: var(--color-bg);
    color: var(--color-text-secondary);
  }

  .markdown-body :global(code) {
    background: var(--color-surface);
    padding: 2px 6px;
    border-radius: var(--border-radius-sm);
    font-family: var(--font-mono);
    font-size: 0.875rem;
  }

  .markdown-body :global(pre) {
    background: var(--color-surface);
    padding: var(--spacing-md);
    border-radius: var(--border-radius-md);
    overflow-x: auto;
    margin: var(--spacing-lg) 0;
  }

  .markdown-body :global(pre code) {
    background: none;
    padding: 0;
    border-radius: 0;
  }

  .markdown-body :global(strong) {
    font-weight: 600;
  }

  .markdown-body :global(a) {
    color: var(--color-accent);
    text-decoration: none;
  }

  .markdown-body :global(a:hover) {
    text-decoration: underline;
  }

  .empty-body {
    align-items: center;
    background: rgba(5, 10, 15, 0.72);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
    color: var(--color-text-secondary);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
    justify-content: center;
    min-height: 160px;
    text-align: center;
  }

  @media (max-width: 640px) {
    .header-info {
      flex-direction: column;
      gap: var(--spacing-md);
    }

    .meta-strip {
      grid-template-columns: 1fr;
    }

    .meta-strip article + article {
      border-left: 0;
      border-top: 1px solid var(--color-border);
    }
  }
</style>
