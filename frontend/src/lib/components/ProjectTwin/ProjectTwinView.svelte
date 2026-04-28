<script>
  import { onMount } from 'svelte';
  import { CheckCircle2, GitBranch, GitFork, Loader2, RefreshCw, Server, ShieldCheck, TerminalSquare, XCircle } from 'lucide-svelte';
  import { api, apiPost } from '../../api.js';
  import Button from '../UI/Button.svelte';
  import Badge from '../UI/Badge.svelte';
  import KarkhanaRunPanel from '../Karkhana/KarkhanaRunPanel.svelte';

  let { ideaId = '' } = $props();

  let state = $state(null);
  let isLoading = $state(true);
  let isReindexing = $state(false);
  let showCreateRun = $state(false);
  let createAutonomy = $state('autonomous_development');
  let isCreatingRun = $state(false);
  let error = $state('');
  let selectedRunId = $state('');

  let project = $derived(state?.project || null);
  let latestIndex = $derived(state?.latest_index || null);
  let factoryRuns = $derived(state?.factory_runs || []);
  let jobs = $derived(state?.jobs || []);
  let runningJobs = $derived(jobs.filter((job) => ['queued', 'waiting_for_machine', 'failed_retryable', 'claimed', 'running'].includes(job.status)));
  let completedJobs = $derived(jobs.filter((job) => job.status === 'completed'));

  const autonomyOptions = [
    {
      value: 'suggest_only',
      label: 'Suggest Only',
      description: 'Creates tasks and prompts without executing. Every step requires explicit human approval before a worker picks it up.',
    },
    {
      value: 'autonomous_development',
      label: 'Autonomous Development',
      description: 'Queues local worker tasks and repairs within configured limits. Exceeding repair limits blocks the run for human review.',
    },
    {
      value: 'full_autopilot',
      label: 'Full Autopilot',
      description: 'Broader automatic continuation within explicit safety guardrails. No deploys, paid services, secrets, or destructive DB changes.',
    },
  ];

  function autonomyLabel(level) {
    return autonomyOptions.find(o => o.value === level)?.label || level;
  }

  function autonomyVariant(level) {
    if (level === 'full_autopilot') return 'warning';
    if (level === 'suggest_only') return 'muted';
    return 'accent';
  }

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

  async function createFactoryRun() {
    if (!project) return;
    isCreatingRun = true;
    error = '';
    try {
      await apiPost(`/api/projects/${project.id}/factory-runs`, {
        template_id: 'default',
        autonomy_level: createAutonomy,
      });
      showCreateRun = false;
      await loadProject();
    } catch (err) {
      error = err.message || 'Unable to create factory run.';
    } finally {
      isCreatingRun = false;
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
          <h2><GitBranch size={18} /> Factory runs</h2>
          <div class="header-actions">
            {#if factoryRuns.length}
              <Badge variant="primary">{factoryRuns.length}</Badge>
            {/if}
            <Button size="sm" onclick={() => (showCreateRun = true)}>
              + New run
            </Button>
          </div>
        </header>
        {#if showCreateRun}
          <div class="create-run-dialog">
            <h3><ShieldCheck size={16} /> Start factory run</h3>
            <p class="dialog-intro">Choose how much autonomy the factory run should have.</p>
            <div class="autonomy-options">
              {#each autonomyOptions as option}
                <label class="autonomy-option" class:active={createAutonomy === option.value}>
                  <input type="radio" bind:group={createAutonomy} value={option.value} />
                  <div>
                    <strong>{option.label}</strong>
                    <p>{option.description}</p>
                  </div>
                </label>
              {/each}
            </div>
            <div class="dialog-actions">
              <Button variant="secondary" size="sm" onclick={() => (showCreateRun = false)} disabled={isCreatingRun}>Cancel</Button>
              <Button size="sm" onclick={createFactoryRun} disabled={isCreatingRun}>
                {#if isCreatingRun}
                  <span class="spin"><Loader2 size={14} /></span> Creating
                {:else}
                  Start run
                {/if}
              </Button>
            </div>
          </div>
        {/if}
        {#if factoryRuns.length}
          <div class="factory-list">
            {#each factoryRuns as run}
              {@const summary = run.tracking_summary || {}}
              {@const template = summary.template || {}}
              {@const phaseProgress = summary.phase_progress || {}}
              {@const batchProgress = summary.batch_progress || {}}
              {@const verificationState = summary.verification_state || {}}
              {@const queueState = summary.worker_queue_state || {}}
              {@const runConfig = run.factory_run?.config || {}}
              {@const autonomyLevel = runConfig.autonomy_level || 'autonomous_development'}
              <article class="factory-row">
                <div class="factory-row-head">
                  <div>
                    <strong>{template.template_id || run.factory_run?.template_id || 'Factory run'}</strong>
                    <small>{template.template_version || run.factory_run?.config?.template_version || 'unknown version'} · {run.factory_run?.id?.slice(0, 8) || 'pending'}</small>
                  </div>
                  <div class="factory-row-badges">
                    <Badge variant={autonomyVariant(autonomyLevel)}>{autonomyLabel(autonomyLevel)}</Badge>
                    <Badge variant={statusTone(summary.run_status || run.factory_run?.status)}>{summary.run_status || run.factory_run?.status || 'queued'}</Badge>
                  </div>
                </div>
                <div class="factory-metrics">
                  <span>Phases {phaseProgress.completed || 0}/{phaseProgress.total || 0}</span>
                  <span>Batches {batchProgress.completed || 0}/{batchProgress.total || 0}</span>
                  <span>Graphify {summary.graphify_status || 'pending'}</span>
                  <span>Verify {verificationState.status || 'pending'}</span>
                  <span>Queue {queueState.status || 'idle'}</span>
                  <span>Commit {summary.last_indexed_commit || 'n/a'}</span>
                </div>
                <p>
                  {queueState.active_worker_id
                    ? `Worker ${queueState.active_worker_id} is ${queueState.status || 'processing'} this run.`
                    : autonomyLevel === 'suggest_only'
                      ? 'Waiting for human approval to execute tasks.'
                      : 'No worker is actively processing this run right now.'}
                </p>
                <div class="factory-row-actions">
                  <Button
                    size="sm"
                    variant={selectedRunId === run.factory_run?.id ? 'primary' : 'secondary'}
                    onclick={() => selectedRunId = selectedRunId === run.factory_run?.id ? '' : run.factory_run?.id}
                  >
                    {selectedRunId === run.factory_run?.id ? 'Hide details' : 'View details'}
                  </Button>
                </div>
              </article>
              {#if selectedRunId === run.factory_run?.id}
                <div class="inline-run-panel">
                  <KarkhanaRunPanel
                    factoryRunId={run.factory_run?.id}
                    autonomyLevel={autonomyLevel}
                  />
                </div>
              {/if}
            {/each}
          </div>
        {:else if !showCreateRun}
          <div class="empty">
            <GitBranch size={36} />
            <h3>No factory runs yet</h3>
            <p>Start a factory run from the project actions to see its phase, queue, graphify, and verification state here.</p>
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

  .header-actions {
    align-items: center;
    display: flex;
    gap: 8px;
  }

  .factory-row-badges {
    align-items: center;
    display: flex;
    gap: 6px;
  }

  .create-run-dialog {
    background: rgba(4, 9, 14, 0.9);
    border: 1px solid rgba(0, 120, 255, 0.3);
    border-radius: var(--border-radius-md);
    margin-bottom: var(--spacing-md);
    padding: var(--spacing-md);
  }

  .create-run-dialog h3 {
    align-items: center;
    color: var(--color-text);
    display: inline-flex;
    font-size: 1rem;
    gap: 8px;
    margin: 0 0 4px;
  }

  .dialog-intro {
    color: var(--color-text-secondary);
    font-size: 0.85rem;
    margin: 0 0 12px;
  }

  .autonomy-options {
    display: grid;
    gap: 8px;
    margin-bottom: 12px;
  }

  .autonomy-option {
    background: rgba(5, 10, 15, 0.6);
    border: 1px solid rgba(103, 128, 151, 0.22);
    border-radius: var(--border-radius-sm);
    cursor: pointer;
    display: flex;
    gap: 10px;
    padding: 10px;
    transition: border-color 0.15s;
  }

  .autonomy-option:hover {
    border-color: rgba(0, 120, 255, 0.4);
  }

  .autonomy-option.active {
    border-color: rgba(0, 180, 255, 0.6);
    background: rgba(0, 120, 255, 0.08);
  }

  .autonomy-option input[type="radio"] {
    accent-color: var(--color-primary-2);
    margin-top: 3px;
    flex-shrink: 0;
  }

  .autonomy-option strong {
    color: var(--color-text);
    display: block;
    font-size: 0.88rem;
  }

  .autonomy-option p {
    color: var(--color-text-secondary);
    font-size: 0.78rem;
    margin: 4px 0 0;
  }

  .dialog-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
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

  .factory-list {
    display: grid;
    gap: 10px;
  }

  .factory-row {
    background: rgba(4, 9, 14, 0.82);
    border: 1px solid rgba(103, 128, 151, 0.22);
    border-radius: var(--border-radius-md);
    display: grid;
    gap: 10px;
    padding: 10px;
  }

  .factory-row-head {
    align-items: center;
    display: flex;
    justify-content: space-between;
    gap: 10px;
  }

  .factory-metrics {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .factory-metrics span {
    background: rgba(0, 120, 255, 0.1);
    border: 1px solid rgba(0, 240, 255, 0.12);
    border-radius: var(--border-radius-sm);
    color: var(--color-text-secondary);
    font-size: 0.75rem;
    padding: 5px 8px;
  }

  .factory-row p {
    margin: 0;
  }

  .factory-row-actions {
    display: flex;
    gap: 8px;
    margin-top: 4px;
  }

  .inline-run-panel {
    border-top: 1px solid rgba(103, 128, 151, 0.18);
    margin-top: 10px;
    padding-top: 10px;
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

    .factory-row-head {
      align-items: flex-start;
      flex-direction: column;
    }
  }
</style>
