<script>
  import { onMount } from 'svelte';
  import { CheckCircle2, Check, Clipboard, GitBranch, GitFork, Loader2, RefreshCw, Server, ShieldCheck, TerminalSquare, XCircle } from 'lucide-svelte';
  import { api, apiPost, getBuildNextActions } from '../../api.js';
  import Button from '../UI/Button.svelte';
  import Badge from '../UI/Badge.svelte';
  import KarkhanaRunPanel from '../Karkhana/KarkhanaRunPanel.svelte';

  let { ideaId = '' } = $props();

  let state = $state(null);
  let isLoading = $state(true);
  let isReindexing = $state(false);
  let showCreateRun = $state(false);
  let createAutonomy = $state('autonomous_development');
  let createIntentSummary = $state('');
  let createIntentDetails = $state('');
  let isCreatingRun = $state(false);
  let error = $state('');
  let selectedRunId = $state('');
  let nextActions = $state([]);
  let nextActionsSummary = $state(null);
  let nextActionsLoading = $state(true);
  let nextActionsError = $state('');
  let copiedPromptId = $state('');
  let clipboardMessage = $state('');
  let clipboardTone = $state('');
  let clipboardTimeout = null;

  let project = $derived(state?.project || null);
  let latestIndex = $derived(state?.latest_index || null);
  let indexSummary = $derived(state?.index_summary || null);
  let healthSummary = $derived(state?.health_summary || null);
  let actionableMetadata = $derived(indexSummary?.actionable_metadata || healthSummary?.actionable_metadata || null);
  let combinedRisks = $derived([...new Set([...(healthSummary?.dependency_risks || []), ...(latestIndex?.risks || [])])]);
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

  async function loadNextActions() {
    if (!ideaId) return;
    nextActionsLoading = true;
    nextActionsError = '';
    try {
      const response = await getBuildNextActions(ideaId);
      nextActions = response?.next_actions || [];
      nextActionsSummary = response?.status_summary || null;
    } catch (err) {
      nextActionsError = err.message || 'Unable to load next actions.';
    } finally {
      nextActionsLoading = false;
    }
  }

  async function reindex() {
    isReindexing = true;
    try {
      await apiPost(`/api/ideas/${ideaId}/project/reindex`, {});
      await loadProject();
      await loadNextActions();
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
        intent: createIntentSummary.trim()
          ? {
              summary: createIntentSummary.trim(),
              details: createIntentDetails.trim() ? { notes: createIntentDetails.trim() } : {},
            }
          : null,
      });
      showCreateRun = false;
      createIntentSummary = '';
      createIntentDetails = '';
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
    if (status === 'healthy' || status === 'fresh') return 'success';
    if (status === 'needs_attention' || status === 'needs_reindex' || status === 'stale') return 'warning';
    if (status.includes('failed')) return 'error';
    if (status === 'running' || status === 'claimed' || status === 'queued') return 'warning';
    return 'muted';
  }

  function workerLabel(job) {
    return job.worker_state?.worker_id || job.worker_id || 'unclaimed';
  }

  function jobHeartbeatLabel(job) {
    const heartbeat = job.worker_state?.heartbeat_at || job.heartbeat_at;
    if (job.execution_state?.is_stale) return 'heartbeat expired';
    return heartbeat ? `heartbeat ${formatDate(heartbeat)}` : `updated ${formatDate(job.updated_at)}`;
  }

  function actionPrompt(action) {
    return action.opencode_prompt || action.codex_prompt || '';
  }

  function opencodeSummary(job) {
    const details = job.opencode || {};
    return [details.engine || job.engine, details.model || job.model, details.agent || job.agent_name].filter(Boolean).join(' · ');
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

  $effect(() => () => {
    if (clipboardTimeout) clearTimeout(clipboardTimeout);
  });

  function setClipboardFeedback(message, tone = 'success') {
    clipboardMessage = message;
    clipboardTone = tone;
    if (clipboardTimeout) clearTimeout(clipboardTimeout);
    clipboardTimeout = setTimeout(() => {
      clipboardMessage = '';
      clipboardTone = '';
    }, 2000);
  }

  async function copyPrompt(prompt, index) {
    try {
      let copied = false;
      if (navigator?.clipboard?.writeText) {
        try {
          await navigator.clipboard.writeText(prompt);
          copied = true;
        } catch {
          copied = false;
        }
      }

      if (!copied) {
        const textarea = document.createElement('textarea');
        textarea.value = prompt;
        textarea.setAttribute('readonly', 'true');
        textarea.style.position = 'absolute';
        textarea.style.left = '-9999px';
        document.body.appendChild(textarea);
        try {
          textarea.select();
          copied = document.execCommand('copy');
        } finally {
          if (textarea.parentNode) document.body.removeChild(textarea);
        }
        if (!copied) throw new Error('Clipboard fallback unavailable.');
      }
      copiedPromptId = `${index}`;
      setClipboardFeedback('Prompt copied to clipboard.');
      setTimeout(() => { if (copiedPromptId === `${index}`) copiedPromptId = ''; }, 1500);
    } catch (err) {
      copiedPromptId = '';
      setClipboardFeedback(err?.message || 'Unable to copy prompt.', 'error');
    }
  }

  onMount(loadProject);
  onMount(loadNextActions);
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
        <strong>{healthSummary?.status ?? project.health_status}</strong>
        <small>{healthSummary?.summary || `Updated ${formatDate(project.updated_at)}`}</small>
      </article>
    </section>

    <div class="workspace">
      <section class="panel">
        <header>
          <h2><ShieldCheck size={18} /> Next actions</h2>
        </header>
        {#if nextActionsLoading}
          <div class="empty compact"><Loader2 size={24} class="spin" /> Loading next actions...</div>
        {:else if nextActionsError}
          <div class="empty compact"><XCircle size={24} /> {nextActionsError}</div>
        {:else}
          {#if nextActionsSummary}
            <div class="facts">
              <span>{nextActionsSummary.current_phase}</span>
              <span>{nextActionsSummary.current_step}</span>
              <span>{nextActionsSummary.project_attached ? 'project linked' : 'no project twin'}</span>
              <span>{nextActionsSummary.project_health?.index_freshness?.state ?? `${nextActions.length} actions`}</span>
            </div>
          {/if}
          {#if nextActions.length}
            <div class="next-actions-list">
              {#each nextActions as action, index}
                <article class="next-action-row">
                  <div class="factory-row-head">
                    <div>
                      <strong>{action.title}</strong>
                      <small>Priority {action.priority} · {action.suggested_owner}</small>
                    </div>
                  </div>
                  <p>{action.reason}</p>
                  {#if action.opencode_command}
                    <small class="job-meta">Command: {action.opencode_command}</small>
                  {/if}
                  {#if actionPrompt(action)}
                    <div class="prompt-actions">
                      <Button size="sm" variant="secondary" onclick={() => copyPrompt(actionPrompt(action), index)}>
                        {#if copiedPromptId === `${index}`}<Check size={14} /> Copied{:else}<Clipboard size={14} /> Copy OpenCode prompt{/if}
                      </Button>
                    </div>
                  {/if}
                </article>
              {/each}
            </div>
          {:else}
            <div class="empty compact">No next actions available.</div>
          {/if}
          {#if clipboardMessage}
            <div class:success={clipboardTone === 'success'} class:error={clipboardTone === 'error'} class="clipboard-feedback">{clipboardMessage}</div>
          {/if}
        {/if}
      </section>

      <section class="panel">
        <header>
          <h2><Server size={18} /> Codebase dossier</h2>
          <Badge variant={statusTone(project.index_status)}>{project.index_status}</Badge>
        </header>
        {#if latestIndex}
          <div class="facts">
            <span>{indexSummary?.file_count ?? latestIndex.file_inventory?.length ?? 0} files</span>
            <span>{indexSummary?.manifest_count ?? latestIndex.manifests?.length ?? 0} manifests</span>
            <span>{indexSummary?.route_hint_count ?? latestIndex.route_map?.length ?? 0} route hints</span>
            <span>{indexSummary?.todo_count ?? latestIndex.todos?.length ?? 0} TODOs</span>
          </div>
          {#if healthSummary}
            <div class="health-card">
              <div class="factory-row-head">
                <strong>{healthSummary.summary}</strong>
                <Badge variant={statusTone(healthSummary.index_freshness?.state)}>{healthSummary.index_freshness?.state || 'unknown'}</Badge>
              </div>
              <p>{healthSummary.index_freshness?.reason || 'Index freshness has not been assessed yet.'}</p>
            </div>
          {/if}
          <h3>Detected stack</h3>
          <p>{indexSummary?.detected_stack?.length ? indexSummary.detected_stack.join(', ') : project.detected_stack?.length ? project.detected_stack.join(', ') : 'No stack summary yet.'}</p>
          <h3>Manifests</h3>
          <p>{indexSummary?.manifest_paths?.length ? indexSummary.manifest_paths.join(', ') : 'No manifests detected yet.'}</p>
          <h3>Commands</h3>
          <p>{indexSummary?.test_commands?.length ? `Tests: ${indexSummary.test_commands.join(' | ')}` : 'No test commands detected yet.'}</p>
          {#if indexSummary?.build_commands?.length}
            <p>Build/deploy: {indexSummary.build_commands.join(' | ')}</p>
          {/if}
          <h3>Structure hints</h3>
          {#if indexSummary?.route_hints?.length}
            <ul class="compact-list">
              {#each indexSummary.route_hints as hint}
                <li>{hint}</li>
              {/each}
            </ul>
          {:else}
            <p>No route or app structure hints detected yet.</p>
          {/if}
          <h3>Deployment hints</h3>
          <p>{indexSummary?.deploy_hints?.length ? indexSummary.deploy_hints.join(', ') : 'No deployment hints detected yet.'}</p>
          {#if actionableMetadata}
            <h3>Planning metadata</h3>
            <div class="facts wrapped">
              <span>{actionableMetadata.package_manifests?.length || 0} package manifests</span>
              <span>{actionableMetadata.likely_test_commands?.length || 0} test commands</span>
              <span>{actionableMetadata.likely_build_commands?.length || 0} build commands</span>
              <span>{actionableMetadata.index_status?.is_stale ? 'stale index' : 'fresh enough'}</span>
            </div>
            {#if actionableMetadata.next_action_hints?.length}
              <ul class="compact-list">
                {#each actionableMetadata.next_action_hints as hint}
                  <li>{hint}</li>
                {/each}
              </ul>
            {/if}
          {/if}
          <h3>Risks</h3>
          {#if combinedRisks.length}
            <ul>
              {#each combinedRisks as risk}
                <li>{risk}</li>
              {/each}
            </ul>
          {:else}
            <p>No indexed risks yet.</p>
          {/if}
          {#if indexSummary?.todo_samples?.length}
            <h3>TODO/FIXME samples</h3>
            <ul class="compact-list">
              {#each indexSummary.todo_samples as todo}
                <li>{todo}</li>
              {/each}
            </ul>
          {/if}
          {#if healthSummary?.missing_info?.length}
            <h3>Missing signals</h3>
            <ul class="compact-list">
              {#each healthSummary.missing_info as gap}
                <li>{gap}</li>
              {/each}
            </ul>
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
                  <small>{job.status} · priority {job.priority ?? job.execution_state?.priority ?? 50} · {workerLabel(job)}</small>
                  <small>{jobHeartbeatLabel(job)} · retries {job.retry_count || 0}</small>
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
                <Badge variant={statusTone(job.status)}>{job.execution_state?.category || job.status}</Badge>
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

  .compact {
    min-height: 0;
  }

  .clipboard-feedback {
    margin-top: var(--spacing-sm);
    font-size: 0.9rem;
  }

  .clipboard-feedback.success {
    color: var(--color-success);
  }

  .clipboard-feedback.error {
    color: var(--color-error);
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

  .health-card {
    background: rgba(0, 120, 255, 0.08);
    border: 1px solid rgba(0, 240, 255, 0.16);
    border-radius: var(--border-radius-md);
    margin-top: var(--spacing-md);
    padding: 10px;
  }

  .health-card p {
    margin: 8px 0 0;
  }

  .compact-list {
    margin: 6px 0 0;
    padding-left: 18px;
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

  .next-actions-list {
    display: grid;
    gap: 10px;
  }

  .next-action-row {
    background: rgba(4, 9, 14, 0.82);
    border: 1px solid rgba(103, 128, 151, 0.22);
    border-radius: var(--border-radius-md);
    padding: 10px;
  }

  .prompt-actions {
    margin-top: 8px;
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
