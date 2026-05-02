<script>
  import { onMount } from 'svelte';
  import { CheckCircle2, Clipboard, KeyRound, Link2, Loader2, RefreshCw, RotateCw, ServerCog, ShieldOff, TerminalSquare, XCircle } from 'lucide-svelte';
  import Button from '../UI/Button.svelte';
  import Badge from '../UI/Badge.svelte';
  import { API_BASE } from '../../api.js';

  const API_GATEWAY = API_BASE?.replace(/\/$/, '') || '';
  const WORKER_API_BASE = (import.meta.env.VITE_WORKER_API_BASE_URL || API_GATEWAY || window.location.origin).replace(/\/$/, '');

  async function gwApi(path, opts = {}) {
    const isBodyMethod = opts.method === 'POST' || opts.method === 'PUT' || opts.method === 'PATCH';
    const headers = isBodyMethod ? { 'Content-Type': 'application/json' } : {};
    const res = await fetch(`${API_GATEWAY}${path}`, { headers, ...opts });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }
  async function gwPost(path, body) { return gwApi(path, { method: 'POST', body: JSON.stringify(body) }); }

  let state = $state({ workers: [], requests: [], events: [], jobs: [] });
  let isLoading = $state(true);
  let isActing = $state('');
  let error = $state('');
  let copied = $state(false);
  let inviteLink = $state('');
  let workerIdInput = $state('');

  let pendingRequests = $derived(state.requests.filter((r) => r.status === 'pending'));
  let approvedWorkers = $derived(state.workers.filter((w) => w.status === 'approved'));
  let hasRevokedWorkers = $derived(state.workers.some((w) => w.status === 'revoked'));
  let activeJobs = $derived((state.jobs || []).filter((j) => ['queued', 'waiting_for_machine', 'failed_retryable', 'claimed', 'running'].includes(j.status)));
  let failedJobs = $derived((state.jobs || []).filter((j) => j.status?.includes('failed')));

  function firstValue(...values) {
    return values.find((value) => typeof value === 'string' && value.trim()) || '';
  }

  function inspectionBranch(job) {
    return firstValue(
      job.branch_name,
      job.result?.branch_name,
      job.opencode?.branch_name,
      job.payload?.branch,
      job.payload?.branch_name
    );
  }

  function inspectionDraftPrUrl(job) {
    return firstValue(
      job.draft_pr_url,
      job.draft_pr?.html_url,
      job.draft_pr?.url,
      job.result?.draft_pr_url,
      job.result?.draft_pr?.html_url,
      job.result?.draft_pr?.url,
      job.result?.pull_request_url,
      job.result?.pr_url,
      job.opencode?.draft_pr_url,
      job.payload?.draft_pr_url
    );
  }

  function inspectionVerificationResults(job) {
    const results = job.verification_results || job.result?.verification_results || [];
    return Array.isArray(results) ? results : [];
  }

  function inspectionGraphifyStatus(job) {
    return firstValue(
      job.graphify_status,
      job.result?.graphify_status,
      job.safety_net_results?.graphify_status
    ) || (
      inspectionGraphifyUpdated(job) === true
        ? 'updated'
        : inspectionGraphifyUpdated(job) === false
          ? 'required'
          : ''
    );
  }

  function inspectionGraphifyUpdated(job) {
    const value = job.graphify_updated ?? job.result?.graphify_updated ?? job.safety_net_results?.graphify_updated;
    return typeof value === 'boolean' ? value : null;
  }

  function verificationTone(status = '') {
    const normalized = String(status).toLowerCase();
    if (['passed', 'success', 'completed', 'ok', 'true'].includes(normalized)) return 'success';
    if (['failed', 'error', 'blocked', 'false'].includes(normalized)) return 'error';
    if (['warning', 'partial', 'needs_review'].includes(normalized)) return 'warning';
    return 'muted';
  }

  function inspectionGraphifyTone(job) {
    if (inspectionGraphifyUpdated(job) === true) return 'success';
    if (inspectionGraphifyUpdated(job) === false) return 'warning';
    if (inspectionGraphifyStatus(job)) return 'accent';
    return 'muted';
  }

  function humanReviewReason(job) {
    return firstValue(
      job.review_reason,
      job.result?.review_reason,
      job.result?.blocked_reason,
      job.result?.failure_reason,
      job.error
    );
  }

  function needsHumanReview(job) {
    if (job.needs_human_review === true || job.result?.needs_human_review === true) return true;
    if (job.review_state === 'needs_human_review' || job.result?.review_state === 'needs_human_review') return true;
    if (job.status === 'blocked') return true;
    if (inspectionGraphifyUpdated(job) === false) return true;
    return inspectionVerificationResults(job).some((result) => {
      const status = String(result.status || result.state || result.outcome || '').toLowerCase();
      return ['failed', 'error', 'blocked'].includes(status);
    });
  }

  function humanReviewLabel(job) {
    if (needsHumanReview(job)) return 'Needs human review';
    return 'Autonomy: ready';
  }

  async function loadWorkers() {
    isLoading = true; error = '';
    try {
      state = await gwApi('/api/local-workers');
    } catch (err) {
      error = err.message || 'Failed to load workers.';
    } finally {
      isLoading = false;
    }
  }

  async function generateInviteLink() {
    isActing = 'invite'; error = '';
    try {
      const res = await fetch(`${API_GATEWAY}/api/worker/invite-link?api_base=${encodeURIComponent(WORKER_API_BASE)}${workerIdInput ? `&worker_id=${encodeURIComponent(workerIdInput)}` : ''}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      inviteLink = data.invite_link;
    } catch (err) {
      error = err.message || 'Failed to generate invite link.';
    } finally {
      isActing = '';
    }
  }

  async function copyInviteLink() {
    await navigator.clipboard?.writeText(inviteLink);
    copied = true;
    setTimeout(() => copied = false, 1600);
  }

  async function approve(requestId) {
    await act(`approve:${requestId}`, async () => {
      await gwPost(`/api/local-workers/requests/${requestId}/approve`, {});
      await loadWorkers();
    });
  }

  async function deny(requestId) {
    await act(`deny:${requestId}`, async () => {
      await gwPost(`/api/local-workers/requests/${requestId}/deny`, { reason: 'Denied from dashboard' });
      await loadWorkers();
    });
  }

  async function revoke(workerId) {
    await act(`revoke:${workerId}`, async () => {
      await gwPost(`/api/local-workers/${workerId}/revoke`, {});
      await loadWorkers();
    });
  }

  async function rotate(workerId) {
    await act(`rotate:${workerId}`, async () => {
      await gwPost(`/api/local-workers/${workerId}/rotate-credentials`, {});
      await loadWorkers();
    });
  }

  async function purgeRevoked() {
    await act('purge-revoked', async () => {
      await gwPost('/api/local-workers/purge-revoked', {});
      await loadWorkers();
    });
  }

  async function act(key, fn) {
    isActing = key; error = '';
    try { await fn(); } catch (err) { error = err.message || 'Action failed.'; }
    finally { isActing = ''; }
  }

  function statusTone(s = '') {
    if (s === 'approved' || s === 'completed') return 'success';
    if (s === 'denied' || s === 'revoked' || s?.includes('failed')) return 'error';
    if (s === 'pending' || s === 'running' || s === 'queued' || s === 'claimed') return 'warning';
    return 'muted';
  }

  function fmtDate(v) {
    return v ? new Date(v).toLocaleString() : 'never';
  }

  function workerLabel(job) {
    return job.worker_state?.worker_id || job.worker_id || 'unclaimed';
  }

  function jobHeartbeatLabel(job) {
    const heartbeat = job.worker_state?.heartbeat_at || job.heartbeat_at;
    if (job.execution_state?.is_stale) return 'heartbeat expired';
    return heartbeat ? `heartbeat ${fmtDate(heartbeat)}` : `updated ${fmtDate(job.updated_at)}`;
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

  function verificationSummary(job) {
    const results = inspectionVerificationResults(job);
    if (!results.length) return '';
    const passed = results.filter((result) => {
      const status = String(result.status || result.state || result.outcome || '').toLowerCase();
      return ['passed', 'success', 'completed', 'ok'].includes(status);
    }).length;
    return `${passed}/${results.length} verification${results.length === 1 ? '' : 's'} passed`;
  }

  onMount(loadWorkers);
</script>

<div class="workers-page">
  <section class="hero">
    <div>
      <span class="mono-label"><ServerCog size={15} /> Worker management</span>
      <h1>Local Workers</h1>
      <p>Generate invite links for your workers, approve pending requests, and manage connected machines.</p>
    </div>
    <div class="hero-actions">
      <Button onclick={loadWorkers} disabled={isLoading}>
        {#if isLoading}<span class="spin"><Loader2 size={16} /></span> Loading{:else}<RefreshCw size={16} /> Refresh{/if}
      </Button>
    </div>
  </section>

  {#if error}
    <div class="notice error error-state" role="alert">
      <XCircle size={18} />
      <div>
        <strong>Worker dashboard could not load</strong>
        <span>{error}</span>
      </div>
      <Button size="sm" variant="secondary" onclick={loadWorkers} disabled={isLoading}>
        <RefreshCw size={14} /> Retry
      </Button>
    </div>
  {/if}

  <!-- Invite Link Section -->
  <section class="panel invite-panel">
    <header>
      <h2><Link2 size={18} /> Invite a Worker</h2>
      <Badge variant="primary">New</Badge>
    </header>
    <div class="invite-form">
      <div class="invite-row">
        <input type="text" class="input" placeholder="Worker ID (optional, defaults to hostname)" bind:value={workerIdInput} />
        <Button onclick={generateInviteLink} disabled={isActing === 'invite'}>
          {#if isActing === 'invite'}<span class="spin"><Loader2 size={16} /></span> Generating{:else}<Link2 size={16} /> Generate Link{/if}
        </Button>
      </div>
      {#if inviteLink}
        <div class="link-output">
          <code>{inviteLink}</code>
          <Button size="sm" variant="secondary" onclick={copyInviteLink}>
            {#if copied}<CheckCircle2 size={14} />{:else}<Clipboard size={14} />{/if}
              {copied ? 'Copied' : 'Copy'}
          </Button>
        </div>
        <p class="hint">Paste this link into the worker app's Invite Link field to connect.</p>
      {/if}
    </div>
  </section>

  <section class="status-grid">
    <article><span>Approved</span><strong>{approvedWorkers.length}</strong><small>Ready for coding work</small></article>
    <article><span>Pending</span><strong>{pendingRequests.length}</strong><small>Awaiting approval</small></article>
    <article><span>Total</span><strong>{state.workers.length}</strong><small>Registered machines</small></article>
    <article><span>Jobs</span><strong>{activeJobs.length}</strong><small>{failedJobs.length} failed/retryable</small></article>
  </section>

  <div class="workspace">
    <section class="panel">
      <header>
        <h2><CheckCircle2 size={18} /> Connection Requests</h2>
        <Badge variant={pendingRequests.length ? 'warning' : 'muted'}>{pendingRequests.length}</Badge>
      </header>
      {#if isLoading}
        <div class="empty"><span class="spin"><Loader2 size={20} /></span> Loading...</div>
      {:else if pendingRequests.length}
        <div class="row-list">
          {#each pendingRequests as request}
            <article class="request-row">
              <div>
                <strong>{request.display_name || request.machine_name}</strong>
                <small>{request.machine_name} &middot; {request.platform} &middot; {request.engine}{#if request.tenant_id} &middot; {request.tenant_id}{/if}</small>
                <span>{request.capabilities?.join(', ')}</span>
              </div>
              <div class="row-actions">
                <Button size="sm" onclick={() => approve(request.id)} disabled={isActing === `approve:${request.id}`}>
                  <CheckCircle2 size={14} /> Approve
                </Button>
                <Button size="sm" variant="danger" onclick={() => deny(request.id)} disabled={isActing === `deny:${request.id}`}>
                  <XCircle size={14} /> Deny
                </Button>
              </div>
            </article>
          {/each}
        </div>
      {:else}
        <div class="empty">No pending requests. Generate an invite link above.</div>
      {/if}
    </section>

    <section class="panel">
      <header>
        <h2><ServerCog size={18} /> Connected Workers</h2>
        <div class="header-actions">
          <Button size="sm" variant="danger" onclick={purgeRevoked} disabled={!hasRevokedWorkers || isActing === 'purge-revoked'}>
            {#if isActing === 'purge-revoked'}<span class="spin"><Loader2 size={14} /></span> Purging{:else}<ShieldOff size={14} /> Purge Revoked{/if}
          </Button>
          <Badge variant="primary">{state.workers.length}</Badge>
        </div>
      </header>
      {#if state.workers.length}
        <div class="row-list">
          {#each state.workers as worker}
            <article class="worker-row">
              <div>
                <strong>{worker.display_name || worker.machine_name}</strong>
                <small>{worker.machine_name} &middot; {worker.platform} &middot; last seen {fmtDate(worker.last_seen_at)}</small>
                <span>{worker.capabilities?.join(', ') || 'No capabilities'}</span>
              </div>
              <Badge variant={statusTone(worker.status)}>{worker.status}</Badge>
              <div class="row-actions">
                <Button size="sm" variant="secondary" onclick={() => rotate(worker.id)} disabled={worker.status !== 'approved' || isActing === `rotate:${worker.id}`}>
                  <RotateCw size={14} /> Rotate
                </Button>
                <Button size="sm" variant="danger" onclick={() => revoke(worker.id)} disabled={worker.status !== 'approved' || isActing === `revoke:${worker.id}`}>
                  <ShieldOff size={14} /> Revoke
                </Button>
              </div>
            </article>
          {/each}
        </div>
      {:else}
        <div class="empty">No workers connected yet. Generate an invite link above to get started.</div>
      {/if}
    </section>

    <section class="panel">
      <header>
        <h2><TerminalSquare size={18} /> Worker Jobs</h2>
        <Badge variant={activeJobs.length ? 'warning' : 'muted'}>{state.jobs?.length || 0}</Badge>
      </header>
      {#if failedJobs.length}
        <div class="failed-callout">
          <strong>{failedJobs.length} failed or retryable job{failedJobs.length === 1 ? '' : 's'}</strong>
          <p>Review the error, logs, and OpenCode debug prompt before re-running.</p>
        </div>
      {/if}
      {#if state.jobs?.length}
        <div class="row-list">
          {#each state.jobs as job}
            <article class="job-row">
              <div>
                <strong>{job.job_type}</strong>
                <small>{job.status} &middot; priority {job.priority ?? job.execution_state?.priority ?? 50} &middot; {workerLabel(job)}</small>
                <small>{jobHeartbeatLabel(job)} &middot; retries {job.retry_count || 0}</small>
                {#if job.error}<span class="job-error">{job.error}</span>{/if}
                {#if opencodeSummary(job)}<span class="job-meta">OpenCode: {opencodeSummary(job)}</span>{/if}
                {#if branchLabel(job)}<span class="job-meta">Branch: {branchLabel(job)}</span>{/if}
                <div class="inspection-row">
                  <Badge variant={needsHumanReview(job) ? 'warning' : 'success'}>
                    {humanReviewLabel(job)}
                  </Badge>
                  {#if inspectionBranch(job)}
                    <Badge variant="muted">Branch: {inspectionBranch(job)}</Badge>
                  {/if}
                  {#if inspectionDraftPrUrl(job)}
                    <a class="inspection-link" href={inspectionDraftPrUrl(job)} target="_blank" rel="noreferrer">Draft PR</a>
                  {/if}
                  {#if inspectionVerificationResults(job).length}
                    <Badge variant={verificationTone(inspectionVerificationResults(job)[0]?.status)}>
                      {verificationSummary(job)}
                    </Badge>
                  {/if}
                  {#if inspectionGraphifyStatus(job)}
                    <Badge variant={inspectionGraphifyTone(job)}>
                      Graphify: {inspectionGraphifyStatus(job)}{#if inspectionGraphifyUpdated(job) !== null} ({inspectionGraphifyUpdated(job) ? 'updated' : 'pending'}){/if}
                    </Badge>
                  {/if}
                </div>
                {#if needsHumanReview(job) && humanReviewReason(job)}
                  <span class="review-reason">Reason: {humanReviewReason(job)}</span>
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
                {#if inspectionVerificationResults(job).length}
                  <details>
                    <summary>Verification results</summary>
                    <div class="verification-list">
                      {#each inspectionVerificationResults(job) as result, index}
                        <div class="verification-row">
                          <Badge variant={verificationTone(result.status || result.state || result.outcome)}>
                            {result.command || result.name || `Check ${index + 1}`}
                          </Badge>
                          <span>{result.summary || result.message || result.output || result.status || 'n/a'}</span>
                        </div>
                      {/each}
                    </div>
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
        <div class="empty empty-state">
          <span class="empty-icon"><TerminalSquare size={22} /></span>
          <div>
            <strong>No worker jobs are waiting</strong>
            <span>
              {#if approvedWorkers.length}
                {approvedWorkers.length} approved worker{approvedWorkers.length === 1 ? '' : 's'} ready when a build job is queued.
              {:else}
                Connect and approve a worker before starting a Level 1 canary.
              {/if}
            </span>
          </div>
        </div>
      {/if}
    </section>
  </div>
</div>

<style>
  .workers-page { margin: 0 auto; max-width: 1240px; }
  .hero, .panel header, .worker-row, .request-row, .job-row { align-items: flex-start; display: flex; gap: var(--spacing-md); justify-content: space-between; }
  .hero { margin-bottom: var(--spacing-lg); }
  .hero h1 { color: var(--color-text); font-size: 2.2rem; line-height: 1; margin: var(--spacing-xs) 0; }
  .hero p, .panel p, .panel small, .request-row span, .worker-row span { color: var(--color-text-secondary); }
  .hero-actions, .row-actions, .header-actions { align-items: center; display: flex; flex-wrap: wrap; gap: var(--spacing-sm); }
  .status-grid, .workspace { display: grid; gap: var(--spacing-md); margin-bottom: var(--spacing-lg); }
  .status-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .workspace { grid-template-columns: minmax(0, 0.85fr) minmax(0, 1.15fr); }
  .status-grid article, .panel, .notice { background: rgba(5, 10, 15, 0.72); border: 1px solid var(--color-border); border-radius: var(--border-radius-lg); padding: var(--spacing-md); }
  .status-grid span { color: var(--color-text-secondary); font-family: var(--font-mono); font-size: 0.68rem; text-transform: uppercase; }
  .status-grid strong { color: var(--color-text); display: block; font-size: 1.75rem; line-height: 1; margin: 10px 0 6px; }
  .panel { margin-bottom: var(--spacing-lg); }
  .panel header { margin-bottom: var(--spacing-md); }
  .panel h2 { align-items: center; color: var(--color-text); display: flex; font-size: 1.1rem; gap: 8px; margin: 0; }
  .invite-form { display: flex; flex-direction: column; gap: var(--spacing-md); }
  .invite-row { display: flex; gap: var(--spacing-sm); }
  .input { background: rgba(3, 8, 12, 0.48); border: 1px solid var(--color-border); border-radius: var(--border-radius-md); color: var(--color-text); flex: 1; font-family: var(--font-mono); font-size: 0.85rem; padding: var(--spacing-sm) var(--spacing-md); }
  .input::placeholder { color: var(--color-text-secondary); }
  .link-output { align-items: center; display: flex; gap: var(--spacing-sm); }
  .link-output code { background: rgba(0, 0, 0, 0.28); border: 1px solid rgba(103, 128, 151, 0.2); border-radius: var(--border-radius-md); color: var(--color-success); flex: 1; font-family: var(--font-mono); font-size: 0.74rem; overflow-x: auto; padding: var(--spacing-sm); white-space: pre-wrap; }
  .hint { color: var(--color-text-secondary); font-size: 0.78rem; margin: 0; }
  .row-list { display: grid; gap: 10px; }
  .request-row, .worker-row, .job-row, .empty { background: rgba(3, 8, 12, 0.48); border: 1px solid rgba(103, 128, 151, 0.18); border-radius: var(--border-radius-md); padding: var(--spacing-md); }
  .empty-state { align-items: flex-start; display: flex; gap: 10px; }
  .empty-icon { color: var(--color-primary-2); flex: 0 0 auto; margin-top: 2px; }
  .empty-state strong { color: var(--color-text); display: block; font-size: 0.9rem; margin-bottom: 3px; }
  .empty-state span { color: var(--color-text-secondary); display: block; font-size: 0.78rem; line-height: 1.4; }
  .request-row strong, .request-row small, .request-row span, .worker-row strong, .worker-row small, .worker-row span, .job-row strong, .job-row small, .job-row span { display: block; }
  .job-error { color: var(--color-error) !important; }
  .job-meta { color: var(--color-primary-2) !important; }
  .inspection-row { align-items: center; display: flex; flex-wrap: wrap; gap: 8px; margin-top: 6px; }
  .inspection-link { color: var(--color-accent); font-size: 0.8rem; text-decoration: none; }
  .inspection-link:hover { text-decoration: underline; }
  .review-reason { color: var(--color-text-secondary); display: block; font-size: 0.76rem; margin-top: 6px; }
  .verification-list { display: grid; gap: 6px; margin-top: 8px; }
  .verification-row { align-items: flex-start; display: flex; gap: 8px; }
  .verification-row span { color: var(--color-text-secondary); font-size: 0.74rem; line-height: 1.35; }
  .failed-callout {
    background: rgba(255, 61, 79, 0.08);
    border: 1px solid rgba(255, 61, 79, 0.24);
    border-radius: var(--border-radius-md);
    color: var(--color-text-secondary);
    margin-bottom: 10px;
    padding: var(--spacing-sm) var(--spacing-md);
  }
  .failed-callout strong { color: var(--color-error); display: block; }
  details { margin-top: 6px; }
  summary { color: var(--color-primary-2); cursor: pointer; font-size: 0.8rem; }
  pre { background: rgba(0, 0, 0, 0.26); border-radius: var(--border-radius-sm); color: var(--color-text-secondary); font-size: 0.72rem; margin: 6px 0 0; max-height: 180px; overflow: auto; padding: 8px; white-space: pre-wrap; }
  .empty { color: var(--color-text-secondary); min-height: 64px; }
  .notice.error { border-color: rgba(255, 61, 79, 0.42); color: var(--color-error); margin-bottom: var(--spacing-lg); }
  .error-state { align-items: flex-start; display: flex; gap: 10px; }
  .error-state > div { flex: 1; }
  .error-state strong { color: var(--color-error); display: block; font-size: 0.9rem; margin-bottom: 3px; }
  .error-state span { color: var(--color-text-secondary); display: block; font-size: 0.78rem; line-height: 1.4; }
  .spin { animation: spin 1s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  @media (max-width: 900px) { .hero, .worker-row, .request-row { flex-direction: column; } .status-grid, .workspace { grid-template-columns: 1fr; } }
</style>
