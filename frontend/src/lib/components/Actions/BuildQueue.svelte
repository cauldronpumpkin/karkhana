<script>
  import { onMount } from 'svelte';
  import { CheckCircle2, GitBranch, Loader2, RefreshCw, XCircle } from 'lucide-svelte';
  import { api } from '../../api.js';
  import Button from '../UI/Button.svelte';
  import Badge from '../UI/Badge.svelte';

  let { ideaId = '' } = $props();

  let jobs = $state([]);
  let isLoading = $state(false);
  let error = $state('');

  async function loadJobs() {
    if (!ideaId) return;
    isLoading = true;
    error = '';
    try {
      const data = await api(`/api/ideas/${ideaId}/jobs`);
      jobs = data.jobs || [];
    } catch (err) {
      error = err.message || 'Build queue could not be loaded.';
      jobs = [];
    } finally {
      isLoading = false;
    }
  }

  function tone(status = '') {
    if (status === 'completed') return 'success';
    if (status.includes('failed')) return 'error';
    if (['queued', 'claimed', 'running', 'waiting_for_machine'].includes(status)) return 'warning';
    return 'muted';
  }

  function iconFor(status = '') {
    if (status === 'completed') return CheckCircle2;
    if (status.includes('failed')) return XCircle;
    return Loader2;
  }

  function formatDate(value) {
    return value ? new Date(value).toLocaleString() : 'never';
  }

  function workerLabel(job) {
    return job.worker_state?.worker_id || job.worker_id || 'waiting for worker';
  }

  function statusSummary(job) {
    const state = job.execution_state || {};
    const heartbeat = job.worker_state?.heartbeat_at || job.heartbeat_at;
    if (state.is_stale) return 'heartbeat expired';
    if (heartbeat) return `heartbeat ${formatDate(heartbeat)}`;
    if (job.run_after) return `retry after ${formatDate(job.run_after)}`;
    return `updated ${formatDate(job.updated_at)}`;
  }

  function opencodeSummary(job) {
    const details = job.opencode || {};
    const parts = [details.engine || job.engine, details.model || job.model, details.agent || job.agent_name].filter(Boolean);
    return parts.length ? parts.join(' · ') : '';
  }

  function branchLabel(job) {
    return job.branch_name || job.opencode?.branch_name || job.payload?.branch || job.payload?.branch_name || '';
  }

  function promptPreview(job) {
    return job.opencode?.prompt_preview || job.payload?.prompt || job.payload?.role_prompt || job.payload?.codex_prompt || '';
  }

  function resultSummary(job) {
    return job.result?.agent_output || job.result?.summary || JSON.stringify(job.result, null, 2);
  }

  onMount(loadJobs);
</script>

<section class="build-queue">
  <div class="section-heading">
    <div>
      <span class="mono-label"><GitBranch size={14} /> Local worker</span>
      <h2>Build Queue</h2>
    </div>
    <Button size="sm" variant="secondary" onclick={loadJobs} disabled={isLoading}>
      <RefreshCw size={14} />
      Refresh
    </Button>
  </div>

  {#if error}
    <div class="notice error">{error}</div>
  {:else if isLoading}
    <div class="queue-empty">
      <span class="spin"><Loader2 size={20} /></span>
      Loading build queue...
    </div>
  {:else if jobs.length}
    <div class="queue-list">
      {#each jobs as job}
        {@const Icon = iconFor(job.status)}
        <article class="queue-row">
          <span class:spin={['claimed', 'running'].includes(job.status)}><Icon size={18} /></span>
          <div>
            <strong>{job.job_type}</strong>
            <small>{job.status} · priority {job.priority ?? job.execution_state?.priority ?? 50} · {workerLabel(job)} · retries {job.retry_count || 0}</small>
            <small>{statusSummary(job)}</small>
            {#if job.error}
              <small class="job-error">{job.error}</small>
            {/if}
            {#if opencodeSummary(job)}
              <small class="job-meta">OpenCode: {opencodeSummary(job)}</small>
            {/if}
            {#if branchLabel(job)}
              <small class="job-meta">Branch: {branchLabel(job)}</small>
            {/if}
            {#if job.command || job.opencode?.command}
              <details>
                <summary>OpenCode command</summary>
                <pre>{job.command || job.opencode.command}</pre>
              </details>
            {/if}
            {#if promptPreview(job)}
              <details>
                <summary>OpenCode prompt</summary>
                <pre>{promptPreview(job)}</pre>
              </details>
            {/if}
            {#if job.logs_tail}
              <details>
                <summary>Logs</summary>
                <pre>{job.logs_tail}</pre>
              </details>
            {/if}
            {#if job.result}
              <details>
                <summary>Result</summary>
                <pre>{resultSummary(job)}</pre>
              </details>
            {/if}
            {#if job.debug_prompt}
              <details>
                <summary>Debug follow-up</summary>
                <pre>{job.debug_prompt}</pre>
              </details>
            {/if}
            {#if job.error && promptPreview(job)}
              <details>
                <summary>Suggested OpenCode retry prompt</summary>
                <pre>{job.debug_prompt || promptPreview(job)}</pre>
              </details>
            {/if}
          </div>
          <Badge variant={tone(job.status)}>{job.status}</Badge>
        </article>
      {/each}
    </div>
  {:else}
    <div class="queue-empty">
      <GitBranch size={32} />
      <strong>No build jobs queued</strong>
      <p>Project twin indexing and agent tasks will appear here after importing a GitHub project.</p>
    </div>
  {/if}
</section>

<style>
  .build-queue {
    margin-bottom: var(--spacing-xl);
  }

  .section-heading {
    align-items: center;
    display: flex;
    justify-content: space-between;
    margin-bottom: var(--spacing-md);
  }

  .section-heading h2 {
    color: var(--color-text);
    font-size: 1.25rem;
    margin: 6px 0 0;
  }

  .queue-list {
    display: grid;
    gap: 10px;
  }

  .queue-row,
  .queue-empty,
  .notice {
    background: linear-gradient(180deg, rgba(8, 14, 21, 0.95), rgba(4, 9, 14, 0.9));
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
  }

  .queue-row {
    align-items: center;
    display: grid;
    gap: var(--spacing-md);
    grid-template-columns: auto 1fr auto;
    padding: var(--spacing-md);
  }

  .queue-row > span {
    color: var(--color-primary-2);
  }

  .queue-row strong,
  .queue-row small {
    display: block;
  }

  .queue-row small,
  .queue-empty p {
    color: var(--color-text-secondary);
  }

  .job-error {
    color: var(--color-error) !important;
  }

  .job-meta {
    color: var(--color-primary-2) !important;
  }

  details {
    margin-top: 6px;
  }

  summary {
    color: var(--color-primary-2);
    cursor: pointer;
    font-size: 0.8rem;
  }

  pre {
    background: rgba(0, 0, 0, 0.26);
    border-radius: var(--border-radius-sm);
    color: var(--color-text-secondary);
    font-size: 0.72rem;
    margin: 6px 0 0;
    max-height: 180px;
    overflow: auto;
    padding: 8px;
    white-space: pre-wrap;
  }

  .queue-empty {
    align-items: center;
    color: var(--color-text-secondary);
    display: grid;
    gap: var(--spacing-sm);
    justify-items: center;
    min-height: 160px;
    padding: var(--spacing-lg);
    text-align: center;
  }

  .notice {
    color: var(--color-error);
    padding: var(--spacing-md);
  }

  .spin {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
