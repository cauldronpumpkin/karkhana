<script>
  import { onMount } from 'svelte';
  import {
    AlertTriangle,
    ArrowLeft,
    CheckCircle2,
    ChevronDown,
    ChevronRight,
    Clock,
    FileText,
    Loader2,
    PauseCircle,
    Play,
    RefreshCw,
    Send,
    ShieldCheck,
    Wrench,
    XCircle
  } from 'lucide-svelte';
  import {
    createReviewPacket,
    getReviewPacket,
    submitIntervention,
    startWaitWindow,
    recordExpiry
  } from '../../api.js';
  import Badge from '../UI/Badge.svelte';
  import Button from '../UI/Button.svelte';
  import ExpertCouncilPanel from './ExpertCouncilPanel.svelte';

  let { factoryRunId = '' } = $props();

  let packet = $state(null);
  let isLoading = $state(true);
  let error = $state('');
  let actionLoading = $state(false);
  let showRationaleModal = $state(false);
  let rationaleAction = $state('');
  let rationaleText = $state('');
  let expandedSection = $state('execution');

  const stateTone = (state) => {
    if (state === 'approved') return 'success';
    if (state === 'rejected') return 'error';
    if (state === 'wait_window') return 'warning';
    if (state === 'awaiting_review') return 'accent';
    if (state === 'paused') return 'muted';
    if (state === 'modification_requested') return 'warning';
    if (state === 'no_objection_recorded') return 'success';
    if (state === 'ready_to_continue') return 'success';
    return 'muted';
  };

  const stateLabel = (state) => {
    const labels = {
      awaiting_review: 'Awaiting Review',
      wait_window: 'Wait Window',
      no_objection_recorded: 'No Objection',
      ready_to_continue: 'Ready to Continue',
      approved: 'Approved',
      rejected: 'Rejected',
      modification_requested: 'Changes Requested',
      paused: 'Paused',
    };
    return labels[state] || state;
  };

  const verdictTone = (verdict) => {
    if (verdict === 'pass') return 'success';
    if (verdict === 'fail') return 'error';
    return 'warning';
  };

  const impactTone = (impact) => {
    if (impact === 'high') return 'error';
    if (impact === 'medium') return 'warning';
    if (impact === 'low') return 'success';
    return 'muted';
  };

  const groupRequirementTags = (tags = []) => {
    return tags.reduce((acc, tag) => {
      const status = tag.evidence_status || 'unknown';
      if (!acc[status]) acc[status] = [];
      acc[status].push(tag);
      return acc;
    }, { supported: [], inferred: [], assumption: [], open_question: [], unknown: [] });
  };

  let availableActions = $derived(packet?.allowed_actions || []);
  let wwState = $derived(packet?.wait_window_state || '');
  let isTerminal = $derived(wwState === 'approved' || wwState === 'rejected');
  let requirementGroups = $derived(groupRequirementTags(packet?.research_handoff?.requirement_tags || []));

  function fmtDate(v) {
    return v ? new Date(v).toLocaleString() : 'n/a';
  }

  function shortId(id) {
    return id ? id.slice(0, 12) : 'n/a';
  }

  async function loadPacket() {
    if (!factoryRunId) return;
    isLoading = true;
    error = '';
    try {
      try {
        packet = await getReviewPacket(factoryRunId);
      } catch {
        packet = await createReviewPacket(factoryRunId);
      }
    } catch (err) {
      error = err.message || 'Failed to load review packet.';
    } finally {
      isLoading = false;
    }
  }

  async function handleAction(action) {
    if (action === 'reject' || action === 'request_changes') {
      rationaleAction = action;
      rationaleText = '';
      showRationaleModal = true;
      return;
    }
    await doAction(action);
  }

  async function doAction(action, rationale = null) {
    actionLoading = true;
    try {
      packet = await submitIntervention(factoryRunId, action, rationale);
    } catch (err) {
      error = err.message || 'Action failed.';
    } finally {
      actionLoading = false;
    }
  }

  async function handleStartWaitWindow() {
    actionLoading = true;
    try {
      packet = await startWaitWindow(factoryRunId);
    } catch (err) {
      error = err.message || 'Failed to start wait window.';
    } finally {
      actionLoading = false;
    }
  }

  async function handleRecordExpiry() {
    actionLoading = true;
    try {
      packet = await recordExpiry(factoryRunId);
    } catch (err) {
      error = err.message || 'Failed to record expiry.';
    } finally {
      actionLoading = false;
    }
  }

  function submitRationale() {
    if (!rationaleText.trim()) return;
    showRationaleModal = false;
    doAction(rationaleAction, rationaleText);
  }

  function goBack() {
    window.location.hash = '/review';
  }

  function toggleSection(section) {
    expandedSection = expandedSection === section ? '' : section;
  }

  onMount(loadPacket);
</script>

<div class="review-detail">
  {#if isLoading}
    <section class="loading-state">
      <span class="spin"><Loader2 size={22} /></span>
      Loading review packet...
    </section>
  {:else if error && !packet}
    <section class="error-state">
      <XCircle size={22} />
      <p>{error}</p>
      <Button size="sm" onclick={loadPacket}><RefreshCw size={14} /> Retry</Button>
    </section>
  {:else if packet}
    <header class="detail-header">
      <button class="back-btn" onclick={goBack}>
        <ArrowLeft size={16} /> Back to queue
      </button>
      <div class="header-info">
        <div>
          <p class="mono-label">Review Packet</p>
          <h1>{shortId(packet.run_id)}</h1>
        </div>
        <div class="header-badges">
          <Badge variant={packet.packet_type === 'research_handoff' ? 'warning' : 'muted'}>
            {packet.packet_type?.replace(/_/g, ' ') || 'standard'}
          </Badge>
          <Badge variant={stateTone(wwState)}>{stateLabel(wwState)}</Badge>
          <Badge variant={packet.run_status === 'running' ? 'warning' : 'muted'}>{packet.run_status}</Badge>
          {#if packet.autonomy_level}
            <Badge variant="accent">{packet.autonomy_level.replace(/_/g, ' ')}</Badge>
          {/if}
        </div>
      </div>
      <div class="header-actions">
        <Button size="sm" variant="secondary" onclick={loadPacket}>
          <RefreshCw size={14} /> Refresh
        </Button>
      </div>
    </header>

    <section class="meta-strip">
      <article>
        <span>Promise</span>
        <strong>{packet.promise || 'Not set'}</strong>
      </article>
      <article>
        <span>Branch</span>
        <strong class="mono">{packet.branch_name || 'n/a'}</strong>
      </article>
      <article>
        <span>Worker</span>
        <strong>{packet.worker_display_name || packet.worker_id?.slice(0, 8) || 'n/a'}</strong>
        {#if packet.worker_machine_name}
          <small>{packet.worker_machine_name}</small>
        {/if}
      </article>
      <article>
        <span>Template</span>
        <strong>{packet.template_id || 'n/a'}</strong>
        {#if packet.template_version}
          <small>v{packet.template_version}</small>
        {/if}
      </article>
      <article>
        <span>Created</span>
        <strong>{fmtDate(packet.created_at)}</strong>
      </article>
      {#if packet.expires_at}
        <article>
          <span>Expires</span>
          <strong>{fmtDate(packet.expires_at)}</strong>
        </article>
      {/if}
    </section>

    <div class="sections">
      <section class="detail-section">
        <button class="section-header" onclick={() => toggleSection('execution')}>
          {#if expandedSection === 'execution'}<ChevronDown size={18} />{:else}<ChevronRight size={18} />{/if}
          <h2>Execution Trace</h2>
          <Badge variant="muted">{packet.execution_trace?.total_steps || 0} steps</Badge>
          {#if packet.execution_trace?.repair_loop_triggered}
            <Badge variant="error"><Wrench size={12} /> Repair loop</Badge>
          {/if}
        </button>
        {#if expandedSection === 'execution'}
          <div class="section-body">
            {#if packet.execution_trace?.entries?.length}
              <div class="trace-list">
                {#each packet.execution_trace.entries as entry, i}
                  <div class="trace-entry">
                    <span class="trace-num">{i + 1}</span>
                    <Badge variant={entry.status === 'completed' || entry.status === 'passed' ? 'success' : entry.status === 'failed' ? 'error' : 'muted'}>
                      {entry.type}
                    </Badge>
                    <span class="trace-detail">
                      {entry.job_type || entry.verification_type || entry.classification || ''}
                    </span>
                    <span class="trace-outcome">{entry.outcome || entry.status}</span>
                    {#if entry.branch}
                      <Badge variant="muted">{entry.branch}</Badge>
                    {/if}
                  </div>
                {/each}
              </div>
            {:else}
              <p class="empty-text">No execution trace entries recorded.</p>
            {/if}
          </div>
        {/if}
      </section>

      <section class="detail-section">
        <button class="section-header" onclick={() => toggleSection('changes')}>
          {#if expandedSection === 'changes'}<ChevronDown size={18} />{:else}<ChevronRight size={18} />{/if}
          <h2>{packet.packet_type === 'research_handoff' ? 'Research Handoff' : 'Change & Review Summary'}</h2>
          <Badge variant={impactTone(packet.blast_radius?.impact_score)}>
            {packet.blast_radius?.impact_score || 'unknown'} impact
          </Badge>
          {#if packet.packet_type === 'research_handoff'}
            <Badge variant="muted">{packet.research_artifact_ids?.length || 0} artifacts</Badge>
          {:else}
            <Badge variant="muted">{packet.changed_files?.length || 0} files</Badge>
          {/if}
        </button>
        {#if expandedSection === 'changes'}
          <div class="section-body">
            {#if packet.packet_type === 'research_handoff'}
              <div class="handoff-grid">
                <div class="handoff-col">
                  <h4>Supported Facts</h4>
                  {#if packet.research_handoff?.supported_facts?.length}
                    <ul class="file-list">
                      {#each packet.research_handoff.supported_facts as item}
                        <li><FileText size={13} /> {item.text || item.label || item}</li>
                      {/each}
                    </ul>
                  {:else}
                    <p class="empty-text">No supported facts recorded.</p>
                  {/if}

                  <h4>Interpretations</h4>
                  {#if packet.research_handoff?.interpretations?.length}
                    <ul class="file-list">
                      {#each packet.research_handoff.interpretations as item}
                        <li><FileText size={13} /> {item.text || item.label || item}</li>
                      {/each}
                    </ul>
                  {:else}
                    <p class="empty-text">No interpretations recorded.</p>
                  {/if}
                </div>

                <div class="handoff-col">
                  <h4>Implementation Requirements</h4>
                  {#if packet.research_handoff?.implementation_requirements?.length}
                    <ul class="file-list">
                      {#each packet.research_handoff.implementation_requirements as item}
                        <li><FileText size={13} /> {item.text || item.label || item}</li>
                      {/each}
                    </ul>
                  {:else}
                    <p class="empty-text">No implementation requirements recorded.</p>
                  {/if}

                  <h4>Assumptions</h4>
                  {#if packet.research_handoff?.assumptions?.length}
                    <ul class="file-list">
                      {#each packet.research_handoff.assumptions as item}
                        <li><FileText size={13} /> {item.text || item.label || item}</li>
                      {/each}
                    </ul>
                  {:else}
                    <p class="empty-text">No assumptions recorded.</p>
                  {/if}

                  <h4>Open Questions</h4>
                  {#if packet.research_handoff?.open_questions?.length}
                    <ul class="file-list">
                      {#each packet.research_handoff.open_questions as item}
                        <li><FileText size={13} /> {item.text || item.label || item}</li>
                      {/each}
                    </ul>
                  {:else}
                    <p class="empty-text">No open questions recorded.</p>
                  {/if}
                </div>
              </div>

              <div class="handoff-actions">
                <h4>Proposed Next Actions</h4>
                {#if packet.research_handoff?.proposed_next_actions?.length}
                  <ul class="file-list">
                    {#each packet.research_handoff.proposed_next_actions as item}
                      <li><FileText size={13} /> {item.text || item.label || item}</li>
                    {/each}
                  </ul>
                {:else}
                  <p class="empty-text">No next actions recorded.</p>
                {/if}
              </div>

              <div class="handoff-tags">
                <h4>Requirement Tags</h4>
                <div class="tag-groups">
                  {#each Object.entries(requirementGroups) as [status, tags]}
                    {#if tags.length}
                      <div class="tag-group">
                        <strong>{status.replace(/_/g, ' ')}</strong>
                        <div class="module-badges">
                          {#each tags as tag}
                            <Badge variant={status === 'supported' ? 'success' : status === 'inferred' ? 'accent' : status === 'assumption' ? 'warning' : 'muted'}>
                              {tag.label || tag.text || tag}
                            </Badge>
                          {/each}
                        </div>
                      </div>
                    {/if}
                  {/each}
                </div>
              </div>
            {:else}
              <div class="change-grid">
                <div class="change-col">
                  <h4>Blast Radius</h4>
                  {#if packet.blast_radius?.impacted_files?.length}
                    <ul class="file-list">
                      {#each packet.blast_radius.impacted_files as file}
                        <li><FileText size={13} /> {file}</li>
                      {/each}
                    </ul>
                  {:else}
                    <p class="empty-text">No files impacted.</p>
                  {/if}
                  {#if packet.blast_radius?.impacted_modules?.length}
                    <h4>Impacted Modules</h4>
                    <div class="module-badges">
                      {#each packet.blast_radius.impacted_modules as mod}
                        <Badge variant="muted">{mod}</Badge>
                      {/each}
                    </div>
                  {/if}
                </div>
                <div class="change-col">
                  <h4>Changed Files</h4>
                  {#if packet.changed_files?.length}
                    <ul class="file-list">
                      {#each packet.changed_files as file}
                        <li><FileText size={13} /> {file}</li>
                      {/each}
                    </ul>
                  {:else}
                    <p class="empty-text">No changed files detected.</p>
                  {/if}
                  {#if packet.diff_summary_uri}
                    <p class="uri-ref">Diff: {packet.diff_summary_uri}</p>
                  {/if}
                </div>
              </div>
            {/if}
          </div>
        {/if}
      </section>

      <section class="detail-section">
        <button class="section-header" onclick={() => toggleSection('controls')}>
          {#if expandedSection === 'controls'}<ChevronDown size={18} />{:else}<ChevronRight size={18} />{/if}
          <h2>Review Packet & Risk Controls</h2>
          <Badge variant={verdictTone(packet.evaluator_verdict?.verdict)}>
            {packet.evaluator_verdict?.verdict || 'pending'}
          </Badge>
          {#if packet.safety_net_results?.tests_passed}
            <Badge variant="success"><ShieldCheck size={12} /> Safe</Badge>
          {:else}
            <Badge variant="error"><AlertTriangle size={12} /> Unsafe</Badge>
          {/if}
        </button>
        {#if expandedSection === 'controls'}
          <div class="section-body">
            <div class="risk-grid">
              <div class="risk-col">
                <h4>Safety Net Results</h4>
                <div class="check-list">
                  <div class="check-row">
                    <span>Tests Passed</span>
                    <Badge variant={packet.safety_net_results?.tests_passed ? 'success' : 'error'}>
                      {packet.safety_net_results?.tests_passed ? 'Yes' : 'No'}
                    </Badge>
                  </div>
                  <div class="check-row">
                    <span>Graphify Status</span>
                    <Badge variant="muted">{packet.safety_net_results?.graphify_status || 'pending'}</Badge>
                  </div>
                  <div class="check-row">
                    <span>Errors</span>
                    <Badge variant={packet.safety_net_results?.error_count > 0 ? 'error' : 'success'}>
                      {packet.safety_net_results?.error_count || 0}
                    </Badge>
                  </div>
                  <div class="check-row">
                    <span>Lint Errors</span>
                    <Badge variant={packet.safety_net_results?.lint_errors > 0 ? 'warning' : 'success'}>
                      {packet.safety_net_results?.lint_errors || 0}
                    </Badge>
                  </div>
                  <div class="check-row">
                    <span>Repair Loop</span>
                    <Badge variant={packet.safety_net_results?.repair_loop_triggered ? 'warning' : 'success'}>
                      {packet.safety_net_results?.repair_loop_triggered ? 'Yes' : 'No'}
                    </Badge>
                  </div>
                </div>
              </div>
              <div class="risk-col">
                <h4>Evaluator Verdict</h4>
                <div class="verdict-box">
                  <Badge variant={verdictTone(packet.evaluator_verdict?.verdict)}>
                    {packet.evaluator_verdict?.verdict || 'pending'}
                  </Badge>
                  <span class="confidence">
                    Confidence: {((packet.evaluator_verdict?.confidence_score || 0) * 100).toFixed(0)}%
                  </span>
                  <p class="verdict-note">{packet.evaluator_verdict?.justification || ''}</p>
                </div>

                <h4>Decision Gates</h4>
                <div class="gate-info">
                  <div class="check-row">
                    <span>Autonomy</span>
                    <Badge variant="accent">{packet.decision_gates?.autonomy_level || 'n/a'}</Badge>
                  </div>
                  <div class="check-row">
                    <span>Policy</span>
                    <Badge variant={packet.decision_gates?.policy_result?.status === 'pass' ? 'success' : 'warning'}>
                      {packet.decision_gates?.policy_result?.status || 'n/a'}
                    </Badge>
                  </div>
                </div>
              </div>
            </div>
          </div>
        {/if}
      </section>

      <ExpertCouncilPanel {packet} />
    </div>

    <section class="actions-panel">
      <h3>Actions</h3>
      {#if isTerminal}
        <div class="terminal-banner">
          <Badge variant={wwState === 'approved' ? 'success' : 'error'}>
            This run has been {stateLabel(wwState)} and resolved at {fmtDate(packet.resolved_at)}.
          </Badge>
        </div>
      {:else}
        <div class="action-buttons">
          {#if wwState === 'awaiting_review' && availableActions.includes('approve')}
            <Button variant="primary" onclick={() => handleAction('approve')} disabled={actionLoading}>
              <CheckCircle2 size={15} /> Approve
            </Button>
          {/if}
          {#if availableActions.includes('request_changes')}
            <Button variant="secondary" onclick={() => handleAction('request_changes')} disabled={actionLoading}>
              <Wrench size={15} /> Request Changes
            </Button>
          {/if}
          {#if availableActions.includes('reject')}
            <Button variant="secondary" onclick={() => handleAction('reject')} disabled={actionLoading}>
              <XCircle size={15} /> Reject
            </Button>
          {/if}
          {#if availableActions.includes('pause')}
            <Button variant="secondary" onclick={() => handleAction('pause')} disabled={actionLoading}>
              <PauseCircle size={15} /> Pause
            </Button>
          {/if}
          {#if availableActions.includes('continue_after_no_objection')}
            <Button variant="primary" onclick={() => handleAction('continue_after_no_objection')} disabled={actionLoading}>
              <Play size={15} /> Continue (No Objection)
            </Button>
          {/if}
          {#if wwState === 'awaiting_review'}
            <Button variant="secondary" onclick={handleStartWaitWindow} disabled={actionLoading}>
              <Clock size={15} /> Start Wait Window
            </Button>
          {/if}
          {#if wwState === 'wait_window'}
            <Button variant="secondary" onclick={handleRecordExpiry} disabled={actionLoading}>
              <Clock size={15} /> Record Expiry
            </Button>
          {/if}
        </div>
      {/if}
    </section>

    {#if packet.telemetry_events?.length}
      <section class="telemetry-section">
        <h3>Telemetry</h3>
        <div class="telemetry-list">
          {#each packet.telemetry_events as event}
            <div class="telemetry-row">
              <Badge variant="muted">{event.event_type}</Badge>
              <small>{event.timestamp ? new Date(event.timestamp).toLocaleString() : ''}</small>
              {#if event.action}
                <small>{event.action}: {event.from_state} &rarr; {event.to_state}</small>
              {/if}
            </div>
          {/each}
        </div>
      </section>
    {/if}
  {:else}
    <section class="empty-state">
      <p>Select a factory run to review.</p>
    </section>
  {/if}
</div>

{#if showRationaleModal}
  <div class="modal-overlay" onclick={() => { showRationaleModal = false; }}>
    <div class="modal-box" onclick={(e) => e.stopPropagation()}>
      <h3>Rationale Required</h3>
      <p>Why are you {rationaleAction === 'reject' ? 'rejecting' : 'requesting changes for'} this run?</p>
      <textarea bind:value={rationaleText} rows="4" placeholder="Enter your rationale..."></textarea>
      <div class="modal-actions">
        <Button variant="secondary" onclick={() => { showRationaleModal = false; }}>Cancel</Button>
        <Button variant="primary" onclick={submitRationale} disabled={!rationaleText.trim()}>
          <Send size={14} /> Submit
        </Button>
      </div>
    </div>
  </div>
{/if}

<style>
  .review-detail {
    margin: 0 auto;
    max-width: 1240px;
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
    min-height: 180px;
    text-align: center;
  }

  .error-state { color: var(--color-error); }

  .detail-header {
    margin-bottom: var(--spacing-lg);
  }

  .back-btn {
    align-items: center;
    background: transparent;
    border: 0;
    color: var(--color-accent);
    cursor: pointer;
    display: inline-flex;
    font-size: 0.85rem;
    gap: 6px;
    margin-bottom: var(--spacing-md);
    padding: 0;
  }

  .back-btn:hover { text-decoration: underline; }

  .header-info {
    align-items: flex-start;
    display: flex;
    gap: var(--spacing-lg);
    justify-content: space-between;
    flex-wrap: wrap;
  }

  .header-info h1 {
    color: var(--color-text);
    font-family: var(--font-mono);
    font-size: 1.4rem;
    margin: 2px 0;
  }

  .mono-label {
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.68rem;
    text-transform: uppercase;
  }

  .header-badges {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    align-items: center;
  }

  .header-actions {
    display: flex;
    gap: 8px;
    margin-top: var(--spacing-sm);
  }

  .meta-strip {
    display: grid;
    gap: var(--spacing-md);
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    margin-bottom: var(--spacing-lg);
  }

  .meta-strip article {
    background: rgba(5, 10, 15, 0.72);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-md);
    padding: var(--spacing-sm) var(--spacing-md);
  }

  .meta-strip span {
    color: var(--color-text-secondary);
    display: block;
    font-family: var(--font-mono);
    font-size: 0.68rem;
    text-transform: uppercase;
  }

  .meta-strip strong {
    color: var(--color-text);
    display: block;
    font-size: 0.88rem;
    margin: 2px 0;
  }

  .meta-strip small {
    color: var(--color-text-secondary);
    font-size: 0.72rem;
  }

  .sections {
    display: grid;
    gap: 8px;
    margin-bottom: var(--spacing-lg);
  }

  .detail-section {
    background: rgba(5, 10, 15, 0.6);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-md);
    overflow: hidden;
  }

  .section-header {
    align-items: center;
    background: transparent;
    border: 0;
    color: var(--color-text);
    cursor: pointer;
    display: flex;
    gap: var(--spacing-sm);
    padding: var(--spacing-md);
    width: 100%;
    text-align: left;
  }

  .section-header:hover {
    background: rgba(0, 120, 255, 0.04);
  }

  .section-header h2 {
    flex: 1;
    font-size: 0.95rem;
    margin: 0;
  }

  .section-body {
    border-top: 1px solid rgba(103, 128, 151, 0.18);
    padding: var(--spacing-md);
  }

  .trace-list {
    display: grid;
    gap: 6px;
  }

  .trace-entry {
    align-items: center;
    background: rgba(4, 9, 14, 0.7);
    border: 1px solid rgba(103, 128, 151, 0.14);
    border-radius: var(--border-radius-sm);
    display: flex;
    gap: var(--spacing-sm);
    padding: 8px 12px;
    font-size: 0.82rem;
  }

  .trace-num {
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.72rem;
    min-width: 24px;
  }

  .trace-detail {
    color: var(--color-text);
    flex: 1;
  }

  .trace-outcome {
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.78rem;
  }

  .change-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--spacing-lg);
  }

  .handoff-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--spacing-lg);
  }

  .handoff-col,
  .handoff-actions,
  .handoff-tags {
    margin-top: var(--spacing-md);
  }

  .change-col h4 {
    color: var(--color-text);
    font-size: 0.85rem;
    margin: 0 0 8px;
  }

  .file-list {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .file-list li {
    align-items: center;
    color: var(--color-text-secondary);
    display: flex;
    font-family: var(--font-mono);
    font-size: 0.78rem;
    gap: 6px;
    padding: 3px 0;
  }

  .module-badges {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-top: 8px;
  }

  .tag-groups {
    display: grid;
    gap: var(--spacing-sm);
  }

  .tag-group strong {
    color: var(--color-text-secondary);
    display: block;
    font-family: var(--font-mono);
    font-size: 0.68rem;
    margin-bottom: 6px;
    text-transform: uppercase;
  }

  .uri-ref {
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.72rem;
    margin-top: 8px;
  }

  .risk-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--spacing-lg);
  }

  .risk-col h4 {
    color: var(--color-text);
    font-size: 0.85rem;
    margin: 0 0 8px;
  }

  .check-list {
    display: grid;
    gap: 6px;
  }

  .check-row {
    align-items: center;
    display: flex;
    justify-content: space-between;
    font-size: 0.85rem;
    color: var(--color-text-secondary);
    padding: 4px 0;
  }

  .verdict-box {
    background: rgba(4, 9, 14, 0.5);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-sm);
    display: grid;
    gap: 8px;
    padding: var(--spacing-sm) var(--spacing-md);
    margin-bottom: var(--spacing-md);
  }

  .confidence {
    color: var(--color-text-secondary);
    font-size: 0.78rem;
  }

  .verdict-note {
    color: var(--color-text-secondary);
    font-size: 0.75rem;
    margin: 0;
    line-height: 1.4;
  }

  .gate-info {
    display: grid;
    gap: 6px;
  }

  .actions-panel {
    background: rgba(5, 10, 15, 0.72);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
    padding: var(--spacing-md);
    margin-bottom: var(--spacing-lg);
  }

  .actions-panel h3 {
    color: var(--color-text);
    font-size: 1rem;
    margin: 0 0 var(--spacing-sm);
  }

  .action-buttons {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
  }

  .terminal-banner {
    padding: var(--spacing-sm);
  }

  .telemetry-section {
    background: rgba(5, 10, 15, 0.5);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-md);
    padding: var(--spacing-md);
  }

  .telemetry-section h3 {
    color: var(--color-text);
    font-size: 0.9rem;
    margin: 0 0 var(--spacing-sm);
  }

  .telemetry-list {
    display: grid;
    gap: 6px;
  }

  .telemetry-row {
    align-items: center;
    display: flex;
    gap: 10px;
    font-size: 0.78rem;
  }

  .telemetry-row small {
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.72rem;
  }

  .empty-text {
    color: var(--color-text-secondary);
    font-size: 0.82rem;
  }

  .modal-overlay {
    align-items: center;
    background: rgba(0, 0, 0, 0.6);
    bottom: 0;
    display: flex;
    justify-content: center;
    left: 0;
    position: fixed;
    right: 0;
    top: 0;
    z-index: 200;
  }

  .modal-box {
    background: rgba(10, 16, 24, 0.98);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
    max-width: 520px;
    padding: var(--spacing-lg);
    width: 90%;
  }

  .modal-box h3 {
    color: var(--color-text);
    margin: 0 0 8px;
  }

  .modal-box p {
    color: var(--color-text-secondary);
    font-size: 0.85rem;
    margin: 0 0 var(--spacing-md);
  }

  .modal-box textarea {
    background: rgba(4, 9, 14, 0.8);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-md);
    color: var(--color-text);
    font-family: var(--font-mono);
    font-size: 0.85rem;
    padding: var(--spacing-sm);
    width: 100%;
    resize: vertical;
  }

  .modal-box textarea:focus {
    outline: none;
    border-color: var(--color-accent);
  }

  .modal-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    margin-top: var(--spacing-md);
  }

  .spin {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  @media (max-width: 768px) {
    .change-grid,
    .handoff-grid,
    .risk-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
