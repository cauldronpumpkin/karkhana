<script>
  import { onMount } from 'svelte';
  import {
    ArrowRight,
    BookOpen,
    Clock,
    FileText,
    Loader2,
    RefreshCw,
    XCircle
  } from 'lucide-svelte';
  import { api } from '../../api.js';
  import Badge from '../UI/Badge.svelte';
  import Button from '../UI/Button.svelte';
  import Card from '../UI/Card.svelte';

  let { runId = '', onSelectLedger } = $props();

  let entries = $state([]);
  let isLoading = $state(true);
  let error = $state('');

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
    return v ? new Date(v).toLocaleString() : 'n/a';
  }

  function shortId(id) {
    return id ? id.slice(0, 12) : 'n/a';
  }

  async function loadLedgers() {
    if (!runId) return;
    isLoading = true;
    error = '';
    try {
      const data = await api(`/api/ledgers/${runId}`);
      entries = Array.isArray(data) ? data : (data.entries || data.ledgers || []);
    } catch (err) {
      error = err.message || 'Failed to load ledger entries.';
    } finally {
      isLoading = false;
    }
  }

  function selectEntry(entry) {
    onSelectLedger?.(entry.id || entry.ledger_id);
  }

  onMount(loadLedgers);
</script>

<div class="ledger-list">
  <div class="list-header">
    <div>
      <p class="mono-label"><BookOpen size={13} /> Factory Run Ledger</p>
      <p class="subtitle">Chronological record of phases, decisions, and outcomes</p>
    </div>
    <Button size="sm" variant="secondary" onclick={loadLedgers}>
      <RefreshCw size={14} /> Refresh
    </Button>
  </div>

  {#if isLoading}
    <section class="loading-state">
      <span class="spin"><Loader2 size={22} /></span>
      Loading ledger entries...
    </section>
  {:else if error}
    <section class="error-state">
      <XCircle size={22} />
      <p>{error}</p>
      <Button size="sm" onclick={loadLedgers}><RefreshCw size={14} /> Retry</Button>
    </section>
  {:else if entries.length === 0}
    <section class="empty-state">
      <FileText size={28} />
      <h3>No ledger entries yet</h3>
      <p>Ledger entries will appear here as the factory run progresses through its phases.</p>
    </section>
  {:else}
    <div class="entries-list">
      {#each entries as entry, i}
        <button
          type="button"
          class="entry-row"
          onclick={() => selectEntry(entry)}
          onkeydown={(e) => { if (e.key === 'Enter') selectEntry(entry); }}
        >
          <span class="entry-index">{i + 1}</span>
          <div class="entry-main">
            <div class="entry-title-row">
              <strong class="entry-title">{entry.title || 'Untitled Entry'}</strong>
              {#if entry.stage}
                <Badge variant={stageTone(entry.stage)} size="sm">{stageLabel(entry.stage)}</Badge>
              {/if}
            </div>
            <div class="entry-meta">
              {#if entry.status}
                <Badge variant={statusTone(entry.status)} size="sm">{entry.status}</Badge>
              {/if}
              <span class="entry-date">
                <Clock size={12} />
                {fmtDate(entry.created_at)}
              </span>
            </div>
          </div>
          <ArrowRight size={16} class="entry-arrow" />
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .ledger-list {
    max-width: 960px;
    margin: 0 auto;
  }

  .list-header {
    align-items: flex-start;
    display: flex;
    gap: var(--spacing-lg);
    justify-content: space-between;
    margin-bottom: var(--spacing-lg);
  }

  .list-header .mono-label {
    align-items: center;
    color: var(--color-text-secondary);
    display: flex;
    font-family: var(--font-mono);
    font-size: 0.68rem;
    gap: 6px;
    margin: 0;
    text-transform: uppercase;
  }

  .subtitle {
    color: var(--color-text-secondary);
    font-size: 0.82rem;
    margin: 4px 0 0;
  }

  .loading-state,
  .error-state,
  .empty-state {
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

  .entries-list {
    display: grid;
    gap: 8px;
  }

  .entry-row {
    align-items: center;
    background: rgba(5, 10, 15, 0.6);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-md);
    cursor: pointer;
    display: flex;
    gap: var(--spacing-md);
    padding: var(--spacing-md);
    text-align: left;
    transition: background 0.15s, border-color 0.15s;
  }

  .entry-row:hover {
    background: rgba(0, 120, 255, 0.04);
    border-color: rgba(0, 174, 255, 0.2);
  }

  .entry-index {
    color: var(--color-text-muted);
    font-family: var(--font-mono);
    font-size: 0.78rem;
    min-width: 28px;
  }

  .entry-main {
    flex: 1;
    min-width: 0;
  }

  .entry-title-row {
    align-items: center;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 6px;
  }

  .entry-title {
    color: var(--color-text);
    font-size: 0.92rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .entry-meta {
    align-items: center;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .entry-date {
    align-items: center;
    color: var(--color-text-muted);
    display: inline-flex;
    font-family: var(--font-mono);
    font-size: 0.68rem;
    gap: 4px;
  }

  .entry-arrow {
    color: var(--color-text-muted);
    flex-shrink: 0;
    opacity: 0.5;
    transition: opacity 0.15s;
  }

  .entry-row:hover .entry-arrow {
    opacity: 1;
    color: var(--color-accent);
  }

  @media (max-width: 640px) {
    .entry-row {
      flex-direction: column;
      align-items: flex-start;
      gap: var(--spacing-sm);
    }

    .entry-index {
      display: none;
    }
  }
</style>
