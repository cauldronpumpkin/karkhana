<script>
  import { onMount } from 'svelte';
  import { CheckCircle2, GitBranch, GitFork, Loader2, RefreshCw, Server, TerminalSquare, XCircle } from 'lucide-svelte';
  import { api, apiPost } from '../../api.js';
  import Button from '../UI/Button.svelte';
  import Badge from '../UI/Badge.svelte';

  let { ideaId = '' } = $props();

  let state = $state(null);
  let isLoading = $state(true);
  let isReindexing = $state(false);
  let error = $state('');

  let project = $derived(state?.project || null);
  let latestIndex = $derived(state?.latest_index || null);
  let jobs = $derived(state?.jobs || []);
  let runningJobs = $derived(jobs.filter((job) => ['queued', 'waiting_for_machine', 'failed_retryable', 'claimed', 'running'].includes(job.status)));
  let completedJobs = $derived(jobs.filter((job) => job.status === 'completed'));

  async function loadProject() {
    if (!ideaId) return;
    isLoading = true;
    error = '';
    try {
      state = await api(`/api/ideas/${ideaId}/project`);
    } catch (err) {
      error = err.message || 'Unable to load project twin.';
    } finally {
      isLoading = false;
    }
  }

  async function reindex() {
    isReindexing = true;
    try {
      await apiPost(`/api/ideas/${ideaId}/project/reindex`, {});
      await loadProject();
    } catch (err) {
      error = err.message || 'Unable to queue reindex.';
    } finally {
      isReindexing = false;
    }
  }

  function formatDate(value) {
    if (!value) return 'never';
    return new Date(value).toLocaleString();
  }

  function statusTone(status = '') {
    if (status === 'completed' || status === 'indexed') return 'success';
    if (status.includes('failed')) return 'error';
    if (status === 'running' || status === 'claimed' || status === 'queued') return 'warning';
    return 'muted';
  }

  onMount(loadProject);
</script>

<div class="project-twin">
  {#if isLoading}
    <section class="panel loading">
      <span class="spin"><Loader2 size={22} /></span>
      Loading project twin...
    </section>
  {:else if error}
    <section class="panel error">
      <XCircle size={22} />
      <div>
        <h1>Project twin unavailable</h1>
        <p>{error}</p>
      </div>
    </section>
  {:else if project}
    <section class="hero">
      <div>
        <p class="mono-label"><GitFork size={15} /> GitHub project twin</p>
        <h1>{project.repo_full_name}</h1>
        <p>{project.desired_outcome || project.current_status || 'Persistent codebase context and local-agent build queue.'}</p>
      </div>
      <Button onclick={reindex} disabled={isReindexing}>
        {#if isReindexing}
          <span class="spin"><Loader2 size={16} /></span>
          Queuing
        {:else}
          <RefreshCw size={16} />
          Reindex
        {/if}
      </Button>
    </section>

    <section class="status-grid">
      <article>
        <span>Index</span>
        <strong>{project.index_status}</strong>
        <small>Commit {project.last_indexed_commit || 'not indexed'}</small>
      </article>
      <article>
        <span>Worker queue</span>
        <strong>{runningJobs.length}</strong>
        <small>{completedJobs.length} completed jobs</small>
      </article>
      <article>
        <span>Branch</span>
        <strong>{project.active_branch || project.default_branch}</strong>
        <small>Default {project.default_branch}</small>
      </article>
      <article>
        <span>Health</span>
        <strong>{project.health_status}</strong>
        <small>Updated {formatDate(project.updated_at)}</small>
      </article>
    </section>

    <div class="workspace">
      <section class="panel">
        <header>
          <h2><Server size={18} /> Codebase dossier</h2>
          <Badge variant={statusTone(project.index_status)}>{project.index_status}</Badge>
        </header>
        {#if latestIndex}
          <div class="facts">
            <span>{latestIndex.file_inventory?.length || 0} files</span>
            <span>{latestIndex.manifests?.length || 0} manifests</span>
            <span>{latestIndex.route_map?.length || 0} route hints</span>
            <span>{latestIndex.todos?.length || 0} TODOs</span>
          </div>
          <h3>Detected stack</h3>
          <p>{project.detected_stack?.length ? project.detected_stack.join(', ') : 'No stack summary yet.'}</p>
          <h3>Test commands</h3>
          <p>{project.test_commands?.length ? project.test_commands.join(' | ') : 'No test commands detected yet.'}</p>
          <h3>Risks</h3>
          {#if latestIndex.risks?.length}
            <ul>
              {#each latestIndex.risks as risk}
                <li>{risk}</li>
              {/each}
            </ul>
          {:else}
            <p>No indexed risks yet.</p>
          {/if}
        {:else}
          <div class="empty">
            <TerminalSquare size={36} />
            <h3>Index queued</h3>
            <p>The local worker will clone and index this repository when it next checks in.</p>
          </div>
        {/if}
      </section>

      <section class="panel">
        <header>
          <h2><GitBranch size={18} /> Build queue</h2>
          <Badge variant="primary">{jobs.length}</Badge>
        </header>
        {#if jobs.length}
          <div class="job-list">
            {#each jobs as job}
              <article class="job-row">
                <span class="job-icon">
                  {#if job.status === 'completed'}
                    <CheckCircle2 size={17} />
                  {:else if job.status?.includes('failed')}
                    <XCircle size={17} />
                  {:else}
                    <Loader2 size={17} />
                  {/if}
                </span>
                <div>
                  <strong>{job.job_type}</strong>
                  <small>{job.status} · {job.worker_id || 'unclaimed'} · {formatDate(job.updated_at)}</small>
                </div>
                <Badge variant={statusTone(job.status)}>{job.retry_count || 0}</Badge>
              </article>
            {/each}
          </div>
        {:else}
          <div class="empty">
            <GitBranch size={36} />
            <h3>No jobs queued</h3>
            <p>Queue a reindex or build task to wake the local worker.</p>
          </div>
        {/if}
      </section>
    </div>
  {/if}
</div>

<style>
  .project-twin {
    margin: 0 auto;
    max-width: 1240px;
  }

  .hero {
    align-items: flex-start;
    display: flex;
    gap: var(--spacing-lg);
    justify-content: space-between;
    margin-bottom: var(--spacing-lg);
  }

  .hero h1 {
    color: var(--color-text);
    font-size: 2rem;
    margin: var(--spacing-xs) 0;
  }

  .hero p,
  .panel p,
  .panel li,
  .panel small {
    color: var(--color-text-secondary);
  }

  .status-grid {
    display: grid;
    gap: var(--spacing-md);
    grid-template-columns: repeat(4, minmax(0, 1fr));
    margin-bottom: var(--spacing-lg);
  }

  .status-grid article,
  .panel {
    background: rgba(5, 10, 15, 0.72);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
    padding: var(--spacing-md);
  }

  .status-grid span {
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.68rem;
    text-transform: uppercase;
  }

  .status-grid strong {
    color: var(--color-text);
    display: block;
    font-size: 1.35rem;
    margin: 8px 0 4px;
    overflow-wrap: anywhere;
  }

  .workspace {
    display: grid;
    gap: var(--spacing-md);
    grid-template-columns: minmax(0, 1.1fr) minmax(360px, 0.9fr);
  }

  .panel header {
    align-items: center;
    display: flex;
    justify-content: space-between;
    margin-bottom: var(--spacing-md);
  }

  .panel h2,
  .panel h3 {
    color: var(--color-text);
    margin: 0;
  }

  .panel h2 {
    align-items: center;
    display: inline-flex;
    font-size: 1.08rem;
    gap: 8px;
  }

  .panel h3 {
    font-size: 0.92rem;
    margin-top: var(--spacing-md);
  }

  .facts {
    display: grid;
    gap: 8px;
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .facts span {
    background: rgba(0, 120, 255, 0.1);
    border: 1px solid rgba(0, 240, 255, 0.18);
    border-radius: var(--border-radius-md);
    color: var(--color-text);
    padding: 8px;
    text-align: center;
  }

  .job-list {
    display: grid;
    gap: 10px;
  }

  .job-row {
    align-items: center;
    background: rgba(4, 9, 14, 0.8);
    border: 1px solid rgba(103, 128, 151, 0.22);
    border-radius: var(--border-radius-md);
    display: grid;
    gap: 10px;
    grid-template-columns: auto 1fr auto;
    padding: 10px;
  }

  .job-row strong,
  .job-row small {
    display: block;
  }

  .job-icon {
    color: var(--color-primary-2);
  }

  .empty,
  .loading,
  .error {
    align-items: center;
    display: grid;
    gap: var(--spacing-sm);
    justify-items: center;
    min-height: 220px;
    text-align: center;
  }

  .error {
    color: var(--color-error);
  }

  .spin {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  @media (max-width: 960px) {
    .hero,
    .workspace {
      grid-template-columns: 1fr;
    }

    .hero {
      flex-direction: column;
    }

    .status-grid,
    .facts {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 560px) {
    .status-grid,
    .facts {
      grid-template-columns: 1fr;
    }
  }
</style>
