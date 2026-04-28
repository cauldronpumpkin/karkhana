<script>
  import { onMount } from 'svelte';
  import {
    AlertTriangle,
    CheckCircle2,
    ChevronDown,
    ChevronRight,
    Clock,
    Loader2,
    Play,
    RefreshCw,
    ShieldCheck,
    Wrench,
    XCircle
  } from 'lucide-svelte';
  import { getFactoryRun } from '../../api.js';
  import Badge from '../UI/Badge.svelte';
  import Button from '../UI/Button.svelte';
  import PromptInspector from './PromptInspector.svelte';

  let { factoryRunId = '', autonomyLevel = 'autonomous_development' } = $props();

  let bundle = $state(null);
  let isLoading = $state(true);
  let error = $state('');
  let expandedPhases = $state({});
  let showPromptFor = $state(null);

  let factoryRun = $derived(bundle?.factory_run || null);
  let phases = $derived(bundle?.phases || []);
  let batches = $derived(bundle?.batches || []);
  let verifications = $derived(bundle?.verifications || []);
  let trackingSummary = $derived(bundle?.tracking_summary || {});
  let trackingManifest = $derived(bundle?.tracking_manifest || {});

  let phaseProgress = $derived(trackingSummary.phase_progress || {});
  let batchProgress = $derived(trackingSummary.batch_progress || {});
  let verificationState = $derived(trackingSummary.verification_state || {});
  let queueState = $derived(trackingSummary.worker_queue_state || {});
  let activeRole = $derived(trackingSummary.active_role || null);

  let completedPhases = $derived(phases.filter((p) => p.status === 'completed').length);
  let completedBatches = $derived(batches.filter((b) => b.status === 'completed').length);
  let failedBatches = $derived(batches.filter((b) => b.status?.includes('failed')).length);
  let repairAttempts = $derived(
    verifications.filter((v) => v.repair_attempts > 0).reduce((sum, v) => sum + v.repair_attempts, 0)
  );

  let queuedWork = $derived(batches.filter((b) => b.status === 'queued').length);
  let runningWork = $derived(batches.filter((b) => ['running', 'in_progress'].includes(b.status)).length);
  let completedWork = $derived(batches.filter((b) => b.status === 'completed').length);

  let isSuggestOnly = $derived(autonomyLevel === 'suggest_only');
  let isFullAutopilot = $derived(autonomyLevel === 'full_autopilot');

  const roleLabels = {
    planner: 'Planner',
    architect: 'Architect',
    batch_planner: 'Batch Planner',
    worker: 'Worker',
    verifier: 'Verifier',
    bug_fixer: 'Bug Fixer',
    integrator: 'Integrator',
    release_manager: 'Release Manager',
    template_curator: 'Template Curator',
  };

  const phaseStatusIcon = (status) => {
    if (status === 'completed') return CheckCircle2;
    if (status?.includes('failed')) return XCircle;
    if (status === 'running' || status === 'in_progress') return Loader2;
    return Clock;
  };

  const statusTone = (status) => {
    if (status === 'completed') return 'success';
    if (status?.includes('failed')) return 'error';
    if (status === 'running' || status === 'in_progress') return 'warning';
    if (status === 'queued') return 'muted';
    return 'muted';
  };

  function togglePhase(phaseId) {
    expandedPhases[phaseId] = !expandedPhases[phaseId];
  }

  async function loadRun() {
    if (!factoryRunId) return;
    isLoading = true;
    error = '';
    try {
      bundle = await getFactoryRun(factoryRunId);
    } catch (err) {
      error = err.message || 'Failed to load factory run.';
    } finally {
      isLoading = false;
    }
  }

  function viewPrompt(batch) {
    showPromptFor = showPromptFor === batch.id ? null : batch.id;
  }

  function fmtDate(v) {
    return v ? new Date(v).toLocaleString() : 'n/a';
  }

  onMount(loadRun);
</script>

<div class="karkhana-panel">
  {#if isLoading}
    <section class="panel loading">
      <span class="spin"><Loader2 size={22} /></span>
      Loading factory run...
    </section>
  {:else if error}
    <section class="panel error-panel">
      <XCircle size={22} />
      <div>
        <h2>Failed to load run</h2>
        <p>{error}</p>
        <Button size="sm" onclick={loadRun}><RefreshCw size={14} /> Retry</Button>
      </div>
    </section>
  {:else if bundle}
    <header class="run-header">
      <div>
        <p class="mono-label">
          {#if activeRole}
            <Play size={13} /> {roleLabels[activeRole] || activeRole} active
          {:else}
            <Clock size={13} /> Idle
          {/if}
        </p>
        <h1>Factory Run</h1>
        <p class="run-id">{factoryRun?.id?.slice(0, 12) || 'pending'}</p>
      </div>
      <div class="header-actions">
        <Badge variant={isFullAutopilot ? 'warning' : isSuggestOnly ? 'muted' : 'accent'}>
          {isSuggestOnly ? 'Suggest Only' : isFullAutopilot ? 'Full Autopilot' : 'Autonomous'}
        </Badge>
        <Badge variant={statusTone(factoryRun?.status)}>
          {factoryRun?.status || 'queued'}
        </Badge>
        <Button size="sm" variant="secondary" onclick={loadRun}>
          <RefreshCw size={14} /> Refresh
        </Button>
      </div>
    </header>

    {#if isFullAutopilot}
      <section class="guardrail-banner">
        <AlertTriangle size={16} />
        <span>Full Autopilot active. Guardrails block deploys, paid services, secrets, and destructive DB changes.</span>
        <ShieldCheck size={16} />
      </section>
    {/if}

    <section class="metrics-strip">
      <article>
        <span>Active role</span>
        <strong>{roleLabels[activeRole] || 'None'}</strong>
        <small>Current execution role</small>
      </article>
      <article>
        <span>Phases</span>
        <strong>{completedPhases}/{phases.length}</strong>
        <small>{phaseProgress.in_progress || 0} in progress</small>
      </article>
      <article>
        <span>Batches</span>
        <strong>{completedBatches}/{batches.length}</strong>
        <small>{failedBatches} failed</small>
      </article>
      <article>
        <span>Verification</span>
        <strong>{verificationState.status || 'pending'}</strong>
        <small>{repairAttempts} repair attempts</small>
      </article>
      <article>
        <span>Worker</span>
        <strong>{queueState.active_worker_id ? 'Active' : 'Idle'}</strong>
        <small>{queueState.status || 'idle'}</small>
      </article>
    </section>

    <section class="work-strip">
      <article class="work-queued">
        <span>Queued</span><strong>{queuedWork}</strong>
      </article>
      <article class="work-running">
        <span>Running</span><strong>{runningWork}</strong>
      </article>
      <article class="work-completed">
        <span>Completed</span><strong>{completedWork}</strong>
      </article>
    </section>

    {#if isSuggestOnly && queuedWork > 0}
      <section class="suggest-banner">
        <Play size={16} />
        <span>Suggest Only mode: review and manually start tasks below. Prompts are ready to copy and run in your local OpenCode session.</span>
      </section>
    {/if}

    <section class="phases-section">
      <h2>Phases</h2>
      {#if phases.length}
        <div class="phase-list">
          {#each phases as phase}
            {@const Icon = phaseStatusIcon(phase.status)}
            {@const isExpanded = expandedPhases[phase.id]}
            {@const phaseBatches = batches.filter((b) => b.phase_id === phase.id)}
            {@const phaseVerifications = verifications.filter((v) => phaseBatches.some((b) => b.id === v.batch_id))}
            <article class="phase-card">
              <button class="phase-header" onclick={() => togglePhase(phase.id)}>
                <span class:spin={phase.status === 'running' || phase.status === 'in_progress'} class="phase-icon">
                  <Icon size={18} />
                </span>
                <div class="phase-info">
                  <strong>{phase.role || phase.name || 'Phase'}</strong>
                  <small>{phase.status} &middot; {phaseBatches.length} batch(es)</small>
                </div>
                {#if phaseVerifications.length}
                  <Badge variant={phaseVerifications.some((v) => v.status?.includes('failed')) ? 'error' : 'success'}>
                    {phaseVerifications.length} verify
                  </Badge>
                {/if}
                <span class="chevron">
                  {#if isExpanded}<ChevronDown size={16} />{:else}<ChevronRight size={16} />{/if}
                </span>
              </button>

              {#if isExpanded}
                <div class="phase-body">
                  {#if phase.prompt}
                    <PromptInspector
                      label="Role prompt"
                      prompt={phase.prompt}
                    />
                  {/if}

                  {#if phaseBatches.length}
                    <div class="batch-list">
                      {#each phaseBatches as batch}
                        <article class="batch-row">
                          <div class="batch-head">
                            <span class:spin={['running', 'in_progress'].includes(batch.status)} class="batch-icon">
                              {#if batch.status === 'completed'}
                                <CheckCircle2 size={15} />
                              {:else if batch.status?.includes('failed')}
                                <XCircle size={15} />
                              {:else if ['running', 'in_progress'].includes(batch.status)}
                                <Loader2 size={15} />
                              {:else}
                                <Clock size={15} />
                              {/if}
                            </span>
                            <div>
                              <strong>{batch.name || batch.id?.slice(0, 8)}</strong>
                              <small>{batch.status} &middot; retries {batch.retry_count || 0}</small>
                            </div>
                            <Badge variant={statusTone(batch.status)}>{batch.status}</Badge>
                          </div>

                          {#if batch.worker_prompt || batch.role_prompt}
                            <button class="prompt-toggle" onclick={() => viewPrompt(batch)}>
                              <Wrench size={13} />
                              {showPromptFor === batch.id ? 'Hide prompt' : 'View prompt'}
                            </button>
                          {/if}

                          {#if showPromptFor === batch.id}
                            <PromptInspector
                              label={batch.role || 'Task prompt'}
                              prompt={batch.worker_prompt || batch.role_prompt || ''}
                            />
                          {/if}

                          {#if isSuggestOnly && batch.status === 'queued'}
                            <div class="suggest-actions">
                              <span>Copy the prompt above and run in your local OpenCode session to execute this task.</span>
                            </div>
                          {/if}
                        </article>
                      {/each}
                    </div>
                  {:else}
                    <p class="empty-text">No batches in this phase yet.</p>
                  {/if}

                  {#if phaseVerifications.length}
                    <div class="verify-section">
                      <h4>Verification results</h4>
                      {#each phaseVerifications as ver}
                        <div class="verify-row">
                          <Badge variant={statusTone(ver.status)}>{ver.status}</Badge>
                          <small>{ver.verification_type || 'auto'} &middot; attempts {ver.repair_attempts || 0}</small>
                          {#if ver.output_summary}
                            <p>{ver.output_summary}</p>
                          {/if}
                        </div>
                      {/each}
                    </div>
                  {/if}

                  {#if phase.started_at || phase.completed_at}
                    <div class="timing">
                      {#if phase.started_at}<small>Started {fmtDate(phase.started_at)}</small>{/if}
                      {#if phase.completed_at}<small>Completed {fmtDate(phase.completed_at)}</small>{/if}
                    </div>
                  {/if}
                </div>
              {/if}
            </article>
          {/each}
        </div>
      {:else}
        <div class="empty-text">No phases created yet. The run may still be initializing.</div>
      {/if}
    </section>
  {:else}
    <section class="panel loading">
      <span>No factory run selected.</span>
    </section>
  {/if}
</div>

<style>
  .karkhana-panel {
    margin: 0 auto;
    max-width: 1240px;
  }

  .panel {
    background: rgba(5, 10, 15, 0.72);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
    padding: var(--spacing-lg);
  }

  .loading,
  .error-panel {
    align-items: center;
    display: grid;
    gap: var(--spacing-sm);
    justify-items: center;
    min-height: 180px;
    text-align: center;
    color: var(--color-text-secondary);
  }

  .error-panel {
    color: var(--color-error);
    grid-template-columns: auto 1fr;
    text-align: left;
  }

  .error-panel h2 {
    color: var(--color-error);
    margin: 0 0 4px;
  }

  .error-panel p {
    color: var(--color-text-secondary);
    margin: 0 0 8px;
  }

  .run-header {
    align-items: flex-start;
    display: flex;
    gap: var(--spacing-lg);
    justify-content: space-between;
    margin-bottom: var(--spacing-lg);
  }

  .run-header h1 {
    color: var(--color-text);
    font-size: 1.8rem;
    line-height: 1;
    margin: var(--spacing-xs) 0;
  }

  .mono-label {
    align-items: center;
    color: var(--color-text-secondary);
    display: inline-flex;
    font-family: var(--font-mono);
    font-size: 0.72rem;
    gap: 6px;
    text-transform: uppercase;
  }

  .run-id {
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.78rem;
    margin: 0;
  }

  .header-actions {
    align-items: center;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .guardrail-banner {
    align-items: center;
    background: rgba(255, 159, 28, 0.08);
    border: 1px solid rgba(255, 159, 28, 0.25);
    border-radius: var(--border-radius-md);
    color: var(--color-warning);
    display: flex;
    gap: var(--spacing-sm);
    font-size: 0.82rem;
    margin-bottom: var(--spacing-lg);
    padding: var(--spacing-sm) var(--spacing-md);
  }

  .suggest-banner {
    align-items: center;
    background: rgba(0, 240, 255, 0.06);
    border: 1px solid rgba(0, 240, 255, 0.2);
    border-radius: var(--border-radius-md);
    color: var(--color-accent);
    display: flex;
    gap: var(--spacing-sm);
    font-size: 0.82rem;
    margin-bottom: var(--spacing-lg);
    padding: var(--spacing-sm) var(--spacing-md);
  }

  .metrics-strip {
    display: grid;
    gap: var(--spacing-md);
    grid-template-columns: repeat(5, minmax(0, 1fr));
    margin-bottom: var(--spacing-md);
  }

  .metrics-strip article {
    background: rgba(5, 10, 15, 0.72);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
    padding: var(--spacing-md);
  }

  .metrics-strip span {
    color: var(--color-text-secondary);
    display: block;
    font-family: var(--font-mono);
    font-size: 0.68rem;
    text-transform: uppercase;
  }

  .metrics-strip strong {
    color: var(--color-text);
    display: block;
    font-size: 1.25rem;
    margin: 8px 0 4px;
  }

  .metrics-strip small {
    color: var(--color-text-secondary);
    display: block;
    font-size: 0.75rem;
  }

  .work-strip {
    display: grid;
    gap: var(--spacing-md);
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin-bottom: var(--spacing-lg);
  }

  .work-strip article {
    align-items: center;
    background: rgba(5, 10, 15, 0.5);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-md);
    display: flex;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm) var(--spacing-md);
  }

  .work-strip span {
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.72rem;
    text-transform: uppercase;
  }

  .work-strip strong {
    color: var(--color-text);
    font-size: 1.1rem;
  }

  .work-queued strong { color: var(--color-text-secondary); }
  .work-running strong { color: var(--color-warning); }
  .work-completed strong { color: var(--color-success); }

  .phases-section h2 {
    color: var(--color-text);
    font-size: 1.15rem;
    margin: 0 0 var(--spacing-md);
  }

  .phase-list {
    display: grid;
    gap: 10px;
  }

  .phase-card {
    background: rgba(5, 10, 15, 0.6);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-md);
    overflow: hidden;
  }

  .phase-header {
    align-items: center;
    background: transparent;
    border: 0;
    color: var(--color-text);
    cursor: pointer;
    display: flex;
    gap: var(--spacing-md);
    padding: var(--spacing-md);
    width: 100%;
    text-align: left;
  }

  .phase-header:hover {
    background: rgba(0, 120, 255, 0.04);
  }

  .phase-icon {
    color: var(--color-primary-2);
    display: flex;
  }

  .phase-info {
    flex: 1;
  }

  .phase-info strong {
    display: block;
    font-size: 0.92rem;
  }

  .phase-info small {
    color: var(--color-text-secondary);
    display: block;
    font-size: 0.78rem;
  }

  .chevron {
    color: var(--color-text-secondary);
    display: flex;
  }

  .phase-body {
    border-top: 1px solid rgba(103, 128, 151, 0.18);
    padding: var(--spacing-md);
  }

  .batch-list {
    display: grid;
    gap: 8px;
    margin-top: var(--spacing-sm);
  }

  .batch-row {
    background: rgba(4, 9, 14, 0.7);
    border: 1px solid rgba(103, 128, 151, 0.16);
    border-radius: var(--border-radius-sm);
    padding: var(--spacing-sm) var(--spacing-md);
  }

  .batch-head {
    align-items: center;
    display: flex;
    gap: var(--spacing-sm);
  }

  .batch-icon {
    color: var(--color-primary-2);
    display: flex;
  }

  .batch-head strong {
    display: block;
    font-size: 0.85rem;
  }

  .batch-head small {
    color: var(--color-text-secondary);
    display: block;
    font-size: 0.72rem;
  }

  .prompt-toggle {
    align-items: center;
    background: transparent;
    border: 0;
    color: var(--color-accent);
    cursor: pointer;
    display: inline-flex;
    font-size: 0.78rem;
    gap: 5px;
    margin-top: 6px;
    padding: 2px 0;
  }

  .prompt-toggle:hover {
    text-decoration: underline;
  }

  .suggest-actions {
    background: rgba(0, 240, 255, 0.04);
    border: 1px dashed rgba(0, 240, 255, 0.2);
    border-radius: var(--border-radius-sm);
    color: var(--color-text-secondary);
    font-size: 0.78rem;
    margin-top: 8px;
    padding: 8px;
  }

  .verify-section {
    margin-top: var(--spacing-md);
  }

  .verify-section h4 {
    color: var(--color-text);
    font-size: 0.82rem;
    margin: 0 0 8px;
  }

  .verify-row {
    align-items: center;
    background: rgba(4, 9, 14, 0.5);
    border: 1px solid rgba(103, 128, 151, 0.14);
    border-radius: var(--border-radius-sm);
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 6px;
    padding: 8px;
  }

  .verify-row small {
    color: var(--color-text-secondary);
    font-size: 0.72rem;
  }

  .verify-row p {
    color: var(--color-text-secondary);
    font-size: 0.78rem;
    margin: 0;
    width: 100%;
  }

  .timing {
    display: flex;
    gap: var(--spacing-md);
    margin-top: var(--spacing-sm);
  }

  .timing small {
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.68rem;
  }

  .empty-text {
    color: var(--color-text-secondary);
    font-size: 0.85rem;
  }

  .spin {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  @media (max-width: 960px) {
    .run-header {
      flex-direction: column;
    }

    .metrics-strip {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
  }

  @media (max-width: 640px) {
    .metrics-strip {
      grid-template-columns: 1fr 1fr;
    }

    .work-strip {
      grid-template-columns: 1fr;
    }
  }
</style>
