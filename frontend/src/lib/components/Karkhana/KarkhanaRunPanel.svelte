<script>
  import { onMount } from 'svelte';
  import {
    AlertTriangle,
    CheckCircle2,
    ChevronDown,
    ChevronRight,
    Clock,
    FileText,
    Loader2,
    Play,
    RefreshCw,
    ShieldCheck,
    Sparkles,
    Upload,
    Wrench,
    XCircle
  } from 'lucide-svelte';
  import { createResearchArtifact, createResearchHandoff, getFactoryRun } from '../../api.js';
  import Badge from '../UI/Badge.svelte';
  import Button from '../UI/Button.svelte';
  import PromptInspector from './PromptInspector.svelte';

  let { factoryRunId = '', autonomyLevel = 'autonomous_development' } = $props();

  let bundle = $state(null);
  let isLoading = $state(true);
  let error = $state('');
  let expandedPhases = $state({});
  let showPromptFor = $state(null);
  let isImportingResearch = $state(false);
  let isGeneratingHandoff = $state(false);
  let researchTitle = $state('');
  let researchSource = $state('');
  let researchRawContent = $state('');
  let researchRawMetadataText = $state('{}');
  let researchNormalizedText = $state('');
  let researchError = $state('');

  let factoryRun = $derived(bundle?.factory_run || null);
  let phases = $derived(bundle?.phases || []);
  let batches = $derived(bundle?.batches || []);
  let verifications = $derived(bundle?.verifications || []);
  let trackingSummary = $derived(bundle?.tracking_summary || {});
  let trackingManifest = $derived(bundle?.tracking_manifest || {});
  let factoryState = $derived(bundle?.factory_state || {});
  let intent = $derived(bundle?.intent || null);
  let researchArtifacts = $derived(bundle?.research_artifacts || []);
  let researchArtifactCount = $derived(bundle?.research_artifact_count || researchArtifacts.length || 0);

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
  let tokenEconomy = $derived(extractTokenEconomy(trackingSummary, trackingManifest));
  let duplicateWork = $derived(extractDuplicateWork(trackingSummary, trackingManifest, tokenEconomy));
  let economyAssets = $derived(extractListMetric(tokenEconomy, ['template_assets_used', 'template_assets', 'assets_used', 'asset_refs']));
  let economyContextCards = $derived(extractListMetric(tokenEconomy, ['context_cards_used', 'context_cards', 'context_card_refs']));
  let economyInputTokens = $derived(readMetric(tokenEconomy, ['input_tokens_total', 'input_tokens', 'input_token_count', 'prompt_tokens', 'total_input_tokens']));
  let economyOutputTokens = $derived(readMetric(tokenEconomy, ['output_tokens', 'output_token_count', 'completion_tokens', 'total_output_tokens']));
  let economyCachedTokens = $derived(readMetric(tokenEconomy, ['input_tokens_cached', 'cached_tokens', 'cache_hit_tokens', 'cached_input_tokens']));
  let economyCacheRate = $derived(readMetric(tokenEconomy, ['cache_hit_rate', 'cache_hit_rate_pct', 'cache_hit_ratio']));
  let economyCostEstimate = $derived(readMetric(tokenEconomy, ['cost_estimate_usd', 'cost_estimate', 'estimated_cost', 'estimated_cost_usd', 'cost_usd']));
  let duplicateWorkCount = $derived(readMetric(duplicateWork, ['count', 'duplicate_count', 'duplicate_work_count']));
  let duplicateWorkStatus = $derived(readMetric(duplicateWork, ['status', 'state']));
  let hasTokenTelemetry = $derived(
    economyInputTokens !== null ||
      economyOutputTokens !== null ||
      economyCachedTokens !== null ||
      economyCacheRate !== null ||
      economyCostEstimate !== null ||
      economyAssets.length > 0 ||
      economyContextCards.length > 0 ||
      duplicateWorkCount !== null ||
      duplicateWorkStatus !== null
  );

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

  function parseJsonInput(text, fallback = {}) {
    const value = (text || '').trim();
    if (!value) return fallback;
    return JSON.parse(value);
  }

  async function importResearchArtifact() {
    if (!factoryRunId || !researchTitle.trim() || !researchSource.trim()) return;
    isImportingResearch = true;
    researchError = '';
    try {
      await createResearchArtifact(factoryRunId, {
        title: researchTitle.trim(),
        source: researchSource.trim(),
        raw_content: researchRawContent || null,
        raw_metadata: parseJsonInput(researchRawMetadataText, {}),
        normalized: researchNormalizedText.trim() ? parseJsonInput(researchNormalizedText, {}) : null,
      });
      researchTitle = '';
      researchSource = '';
      researchRawContent = '';
      researchRawMetadataText = '{}';
      researchNormalizedText = '';
      await loadRun();
    } catch (err) {
      researchError = err.message || 'Failed to import research artifact.';
    } finally {
      isImportingResearch = false;
    }
  }

  async function generateHandoff() {
    if (!factoryRunId) return;
    isGeneratingHandoff = true;
    researchError = '';
    try {
      await createResearchHandoff(factoryRunId);
      await loadRun();
    } catch (err) {
      researchError = err.message || 'Failed to generate research handoff.';
    } finally {
      isGeneratingHandoff = false;
    }
  }

  function fmtDate(v) {
    return v ? new Date(v).toLocaleString() : 'n/a';
  }

  function shortId(value) {
    return value ? value.slice(0, 12) : 'n/a';
  }

  function asList(value) {
    return Array.isArray(value) ? value.filter((item) => item !== null && item !== undefined && `${item}`.trim() !== '') : [];
  }

  function pickFirst(...values) {
    for (const value of values) {
      if (Array.isArray(value) && value.length) return value;
      if (value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length) return value;
      if (typeof value === 'string' && value.trim()) return value;
      if (typeof value === 'number' && Number.isFinite(value)) return value;
      if (typeof value === 'boolean') return value;
    }
    return null;
  }

  function findNested(source, keyPaths) {
    const roots = [source, source?.token_economy, source?.token_telemetry, source?.telemetry, source?.metrics, source?.summary];
    for (const root of roots) {
      if (!root || typeof root !== 'object') continue;
      for (const keyPath of keyPaths) {
        const parts = keyPath.split('.');
        let current = root;
        let found = true;
        for (const part of parts) {
          if (!current || typeof current !== 'object' || !(part in current)) {
            found = false;
            break;
          }
          current = current[part];
        }
        if (found && current !== undefined && current !== null && `${current}`.trim() !== '') {
          return current;
        }
      }
    }
    return null;
  }

  function extractTokenEconomy(summary, manifest) {
    return (
      pickFirst(
        summary?.token_economy,
        summary?.token_economy_totals,
        summary?.token_telemetry,
        manifest?.token_economy,
        manifest?.token_economy_totals,
        manifest?.token_telemetry,
        manifest?.telemetry?.token_economy,
        manifest?.telemetry?.token_telemetry
      ) || {}
    );
  }

  function extractDuplicateWork(summary, manifest, economy) {
    return (
      pickFirst(
        summary?.duplicate_work,
        summary?.duplicate_work_summary,
        summary?.duplicate_work_count !== undefined ? { duplicate_work_count: summary.duplicate_work_count } : null,
        manifest?.duplicate_work,
        manifest?.duplicate_work_summary,
        manifest?.duplicate_work_count !== undefined ? { duplicate_work_count: manifest.duplicate_work_count } : null,
        economy?.duplicate_work,
        economy?.duplicate_work_summary
      ) || {}
    );
  }

  function extractListMetric(source, keyPaths) {
    return asList(findNested(source, keyPaths));
  }

  function readMetric(source, keyPaths) {
    return findNested(source, keyPaths);
  }

  function formatMetricValue(value) {
    if (value === null || value === undefined || value === '') return 'n/a';
    return String(value);
  }

  function formatTokens(value) {
    return formatMetricValue(value);
  }

  function formatRate(value) {
    if (value === null || value === undefined || value === '') return 'n/a';
    const numeric = typeof value === 'number' ? value : Number(value);
    if (Number.isFinite(numeric)) {
      return numeric <= 1 ? `${Math.round(numeric * 1000) / 10}%` : `${numeric}%`;
    }
    return String(value);
  }

  function formatCost(value) {
    if (value === null || value === undefined || value === '') return 'n/a';
    if (typeof value === 'number' && Number.isFinite(value)) {
      return `$${value.toFixed(4).replace(/0+$/, '').replace(/\.$/, '')}`;
    }
    return String(value);
  }

  function formatListValue(value) {
    if (Array.isArray(value)) return value.map((item) => (typeof item === 'object' ? JSON.stringify(item) : String(item))).join(', ');
    if (value && typeof value === 'object') return JSON.stringify(value);
    return value === null || value === undefined || value === '' ? 'n/a' : String(value);
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

    <section class="factory-state">
      <div class="factory-state-summary">
        <div class="state-head">
          <div>
            <p class="section-label">Factory State</p>
            <h2>Intent and research</h2>
          </div>
          <Badge variant={factoryState.handoff_status === 'approved' ? 'success' : factoryState.handoff_status === 'awaiting_review' ? 'warning' : 'muted'}>
            {factoryState.handoff_status || 'not created'}
          </Badge>
        </div>
        <div class="state-grid">
          <article>
            <span>Intent</span>
            <strong>{intent?.summary || factoryState.intent_summary || 'No intent captured'}</strong>
            <small>{intent?.id ? `Intent ${shortId(intent.id)}` : 'Use the project run dialog to capture a goal.'}</small>
          </article>
          <article>
            <span>Correlation</span>
            <strong class="mono">{factoryState.correlation_id || factoryRun?.correlation_id || 'n/a'}</strong>
            <small>Shared event correlation id</small>
          </article>
          <article>
            <span>Budget</span>
            <strong>{Object.keys(factoryState.budget || {}).length || 0}</strong>
            <small>{Object.keys(factoryState.budget || {}).length ? 'Budget controls set' : 'No explicit budget'}</small>
          </article>
          <article>
            <span>Stop conditions</span>
            <strong>{(factoryState.stop_conditions || []).length}</strong>
            <small>{(factoryState.stop_conditions || []).length ? 'Active stop rules' : 'No stop rules yet'}</small>
          </article>
          <article>
            <span>Research artifacts</span>
            <strong>{researchArtifactCount}</strong>
            <small>Imported into this run</small>
          </article>
        </div>
        <div class="state-tags">
          {#if Object.entries(factoryState.budget || {}).length}
            {#each Object.entries(factoryState.budget || {}) as [key, value]}
              <Badge variant="accent">{key}: {String(value)}</Badge>
            {/each}
          {/if}
          {#each factoryState.stop_conditions || [] as stop}
            <Badge variant="muted">{stop}</Badge>
          {/each}
          {#if !Object.entries(factoryState.budget || {}).length && !(factoryState.stop_conditions || []).length}
            <span class="empty-inline">No budget or stop conditions have been captured yet.</span>
          {/if}
        </div>
      </div>

      <div class="research-form">
        <h3><FileText size={15} /> Import research</h3>
        {#if researchError}
          <p class="inline-error">{researchError}</p>
        {/if}
        <div class="form-grid">
          <input bind:value={researchTitle} placeholder="Title" />
          <input bind:value={researchSource} placeholder="Source" />
        </div>
        <textarea bind:value={researchRawContent} rows="4" placeholder="Raw content"></textarea>
        <div class="form-grid stacked">
          <textarea bind:value={researchRawMetadataText} rows="3" placeholder='Raw metadata JSON (optional)'></textarea>
          <textarea bind:value={researchNormalizedText} rows="3" placeholder='Normalized JSON (optional)'></textarea>
        </div>
        <div class="form-actions">
          <Button size="sm" variant="secondary" onclick={importResearchArtifact} disabled={isImportingResearch || !researchTitle.trim() || !researchSource.trim()}>
            {#if isImportingResearch}
              <span class="spin"><Loader2 size={14} /></span>
              Importing
            {:else}
              <Upload size={14} />
              Import
            {/if}
          </Button>
          <Button size="sm" onclick={generateHandoff} disabled={isGeneratingHandoff}>
            {#if isGeneratingHandoff}
              <span class="spin"><Loader2 size={14} /></span>
              Generating
            {:else}
              <Sparkles size={14} />
              Generate handoff
            {/if}
          </Button>
        </div>
      </div>
    </section>

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

    <section class="economy-panel">
      <div class="panel-head">
        <div>
          <p class="section-label">Token economy</p>
          <h2>Telemetry snapshot</h2>
        </div>
        <span class="panel-note">{trackingSummary.run_status || trackingManifest.run_status || factoryRun?.status || 'n/a'}</span>
      </div>
      {#if hasTokenTelemetry}
        <div class="economy-grid">
          <article>
            <span>Input tokens</span>
            <strong>{formatTokens(economyInputTokens)}</strong>
          </article>
          <article>
            <span>Output tokens</span>
            <strong>{formatTokens(economyOutputTokens)}</strong>
          </article>
          <article>
            <span>Cached tokens</span>
            <strong>{formatTokens(economyCachedTokens)}</strong>
          </article>
          <article>
            <span>Cache hit rate</span>
            <strong>{formatRate(economyCacheRate)}</strong>
          </article>
          <article>
            <span>Cost estimate</span>
            <strong>{formatCost(economyCostEstimate)}</strong>
          </article>
          <article>
            <span>Template assets</span>
            <strong>{formatListValue(economyAssets)}</strong>
          </article>
          <article>
            <span>Context cards</span>
            <strong>{formatListValue(economyContextCards)}</strong>
          </article>
          <article>
            <span>Duplicate work</span>
            <strong>{formatMetricValue(duplicateWorkCount)}</strong>
            <small>{formatMetricValue(duplicateWorkStatus)}</small>
          </article>
        </div>
      {:else}
        <p class="empty-inline">No token telemetry captured yet.</p>
      {/if}
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

  .factory-state {
    display: grid;
    gap: var(--spacing-md);
    grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
    margin-bottom: var(--spacing-lg);
  }

  .factory-state-summary,
  .research-form {
    background: rgba(5, 10, 15, 0.58);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-md);
    padding: var(--spacing-md);
  }

  .state-head {
    align-items: flex-start;
    display: flex;
    gap: var(--spacing-sm);
    justify-content: space-between;
    margin-bottom: var(--spacing-md);
  }

  .section-label {
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.68rem;
    margin: 0 0 4px;
    text-transform: uppercase;
  }

  .state-head h2 {
    color: var(--color-text);
    font-size: 1.05rem;
    margin: 0;
  }

  .state-grid {
    display: grid;
    gap: var(--spacing-sm);
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin-bottom: var(--spacing-sm);
  }

  .state-grid article {
    background: rgba(4, 9, 14, 0.7);
    border: 1px solid rgba(103, 128, 151, 0.16);
    border-radius: var(--border-radius-sm);
    padding: var(--spacing-sm);
  }

  .state-grid span {
    color: var(--color-text-secondary);
    display: block;
    font-family: var(--font-mono);
    font-size: 0.68rem;
    margin-bottom: 2px;
    text-transform: uppercase;
  }

  .state-grid strong {
    color: var(--color-text);
    display: block;
    font-size: 0.9rem;
    line-height: 1.2;
    margin-bottom: 4px;
    word-break: break-word;
  }

  .state-grid small {
    color: var(--color-text-secondary);
    display: block;
    font-size: 0.72rem;
  }

  .state-tags {
    align-items: center;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .empty-inline {
    color: var(--color-text-secondary);
    font-size: 0.78rem;
  }

  .research-form h3 {
    align-items: center;
    color: var(--color-text);
    display: inline-flex;
    gap: 6px;
    margin: 0 0 var(--spacing-sm);
  }

  .research-form input,
  .research-form textarea {
    background: rgba(4, 9, 14, 0.7);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-sm);
    color: var(--color-text);
    font: inherit;
    padding: 8px 10px;
    resize: vertical;
    width: 100%;
  }

  .research-form textarea {
    margin-bottom: 8px;
  }

  .form-grid {
    display: grid;
    gap: 8px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    margin-bottom: 8px;
  }

  .form-grid.stacked {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .form-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-top: 8px;
  }

  .inline-error {
    color: var(--color-error);
    font-size: 0.78rem;
    margin: 0 0 8px;
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

  .economy-panel {
    background: rgba(5, 10, 15, 0.58);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-md);
    margin-bottom: var(--spacing-md);
    padding: var(--spacing-md);
  }

  .panel-head {
    align-items: baseline;
    display: flex;
    gap: var(--spacing-sm);
    justify-content: space-between;
    margin-bottom: var(--spacing-md);
  }

  .panel-head h2 {
    color: var(--color-text);
    font-size: 1.05rem;
    margin: 0;
  }

  .panel-note {
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.72rem;
    text-transform: uppercase;
  }

  .economy-grid {
    display: grid;
    gap: var(--spacing-sm);
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .economy-grid article {
    background: rgba(4, 9, 14, 0.72);
    border: 1px solid rgba(103, 128, 151, 0.16);
    border-radius: var(--border-radius-sm);
    padding: var(--spacing-sm);
  }

  .economy-grid span {
    color: var(--color-text-secondary);
    display: block;
    font-family: var(--font-mono);
    font-size: 0.68rem;
    text-transform: uppercase;
  }

  .economy-grid strong {
    color: var(--color-text);
    display: block;
    font-size: 0.88rem;
    line-height: 1.25;
    margin-top: 6px;
    word-break: break-word;
  }

  .economy-grid small {
    color: var(--color-text-secondary);
    display: block;
    font-size: 0.72rem;
    margin-top: 4px;
    word-break: break-word;
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

  .mono {
    font-family: var(--font-mono);
  }

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

    .factory-state {
      grid-template-columns: 1fr;
    }

    .state-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .metrics-strip {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .economy-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 640px) {
    .state-grid {
      grid-template-columns: 1fr;
    }

    .form-grid,
    .form-grid.stacked {
      grid-template-columns: 1fr;
    }

    .metrics-strip {
      grid-template-columns: 1fr 1fr;
    }

    .work-strip {
      grid-template-columns: 1fr;
    }

    .economy-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
