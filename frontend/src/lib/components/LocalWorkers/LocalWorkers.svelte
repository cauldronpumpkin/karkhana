<script>
  import { onMount } from 'svelte';
  import {
    CheckCircle2,
    Clipboard,
    KeyRound,
    Loader2,
    RefreshCw,
    RotateCw,
    ServerCog,
    ShieldOff,
    TerminalSquare,
    XCircle
  } from 'lucide-svelte';
  import { api, apiPost } from '../../api.js';
  import Button from '../UI/Button.svelte';
  import Badge from '../UI/Badge.svelte';

  let state = $state({ workers: [], requests: [], events: [], jobs: [], sqs: {} });
  let isLoading = $state(true);
  let isActing = $state('');
  let error = $state('');
  let copied = $state(false);
  let rotatedCredentials = $state(null);

  const apiBase = typeof window !== 'undefined' ? window.location.origin : 'https://your-api.example.com';
  const installCommandWin = `irm https://your-server/install.ps1 | iex -ApiBase "${apiBase}"`;
  const installCommandMac = `curl -sSL https://your-server/install.sh | bash -s -- --api-base "${apiBase}"`;
  const installCommandManual = `cd workers/openclaude-local && .\\install.ps1 -ApiBase "${apiBase}"`;

  let pendingRequests = $derived(state.requests.filter((request) => request.status === 'pending'));
  let approvedWorkers = $derived(state.workers.filter((worker) => worker.status === 'approved'));
  let openJobs = $derived(state.jobs.filter((job) => !['completed', 'cancelled', 'failed_terminal'].includes(job.status)));

  async function loadWorkers() {
    isLoading = true;
    error = '';
    try {
      state = await api('/api/local-workers');
    } catch (err) {
      error = err.message || 'Local workers could not be loaded.';
    } finally {
      isLoading = false;
    }
  }

  async function approve(requestId) {
    await act(`approve:${requestId}`, async () => {
      rotatedCredentials = await apiPost(`/api/local-workers/requests/${requestId}/approve`, {});
      await loadWorkers();
    });
  }

  async function deny(requestId) {
    await act(`deny:${requestId}`, async () => {
      await apiPost(`/api/local-workers/requests/${requestId}/deny`, { reason: 'Denied from Local Workers page' });
      await loadWorkers();
    });
  }

  async function revoke(workerId) {
    await act(`revoke:${workerId}`, async () => {
      await apiPost(`/api/local-workers/${workerId}/revoke`, {});
      await loadWorkers();
    });
  }

  async function rotate(workerId) {
    await act(`rotate:${workerId}`, async () => {
      rotatedCredentials = await apiPost(`/api/local-workers/${workerId}/rotate-credentials`, {});
      await loadWorkers();
    });
  }

  async function act(key, fn) {
    isActing = key;
    error = '';
    try {
      await fn();
    } catch (err) {
      error = err.message || 'Worker action failed.';
    } finally {
      isActing = '';
    }
  }

  async function copyInstall() {
    const command = navigator.userAgent.includes('Win') ? installCommandWin : installCommandMac;
    await navigator.clipboard?.writeText(command);
    copied = true;
    setTimeout(() => (copied = false), 1600);
  }

  function statusTone(status = '') {
    if (status === 'approved' || status === 'completed') return 'success';
    if (status === 'denied' || status === 'revoked' || status?.includes('failed')) return 'error';
    if (status === 'pending' || status === 'running' || status === 'queued' || status === 'claimed') return 'warning';
    return 'muted';
  }

  function formatDate(value) {
    if (!value) return 'never';
    return new Date(value).toLocaleString();
  }

  onMount(loadWorkers);
</script>

<div class="workers-page">
  <section class="hero">
    <div>
      <span class="mono-label"><ServerCog size={15} /> OpenClaude worker control</span>
      <h1>Local Workers</h1>
      <p>Approve machines, issue queue credentials, and watch the local coding fleet that runs project twin jobs.</p>
    </div>
    <div class="hero-actions">
      <Button variant="secondary" onclick={copyInstall}>
        <Clipboard size={16} />
        {copied ? 'Copied' : 'Copy Install'}
      </Button>
      <Button onclick={loadWorkers} disabled={isLoading}>
        {#if isLoading}
          <span class="spin"><Loader2 size={16} /></span>
          Loading
        {:else}
          <RefreshCw size={16} />
          Refresh
        {/if}
      </Button>
    </div>
  </section>

  {#if error}
    <div class="notice error" role="alert">{error}</div>
  {/if}

  <section class="status-grid">
    <article>
      <span>Approved</span>
      <strong>{approvedWorkers.length}</strong>
      <small>Ready for coding work</small>
    </article>
    <article>
      <span>Pending</span>
      <strong>{pendingRequests.length}</strong>
      <small>Awaiting approval</small>
    </article>
    <article>
      <span>Open jobs</span>
      <strong>{openJobs.length}</strong>
      <small>Backend remains source of truth</small>
    </article>
    <article>
      <span>SQS</span>
      <strong>{state.sqs?.commands_configured ? 'Live' : 'Local'}</strong>
      <small>{state.sqs?.region || 'not configured'}</small>
    </article>
  </section>

  <section class="panel install-panel">
    <header>
      <h2><TerminalSquare size={18} /> One-click install</h2>
      <Badge variant={state.sqs?.commands_configured ? 'success' : 'warning'}>{state.sqs?.commands_configured ? 'SQS ready' : 'API fallback'}</Badge>
    </header>
    <div class="install-commands">
      <div class="install-block">
        <strong>Windows</strong>
        <code>{installCommandWin}</code>
      </div>
      <div class="install-block">
        <strong>macOS</strong>
        <code>{installCommandMac}</code>
      </div>
      <p class="hint">Optionally add <code>-TenantId "your-company"</code> to join a specific tenant.</p>
    </div>
  </section>

  {#if rotatedCredentials}
    <section class="panel credentials-panel">
      <header>
        <h2><KeyRound size={18} /> Newly issued credentials</h2>
        <Badge variant="warning">shown once</Badge>
      </header>
      <p>Worker {rotatedCredentials.worker?.display_name || rotatedCredentials.worker?.id} received a fresh API token and queue lease.</p>
      <code>{rotatedCredentials.credentials?.api_token || 'token unavailable'}</code>
    </section>
  {/if}

  <div class="workspace">
    <section class="panel">
      <header>
        <h2><CheckCircle2 size={18} /> Connection requests</h2>
        <Badge variant={pendingRequests.length ? 'warning' : 'muted'}>{pendingRequests.length}</Badge>
      </header>
      {#if isLoading}
        <div class="empty"><span class="spin"><Loader2 size={20} /></span> Loading requests...</div>
      {:else if pendingRequests.length}
        <div class="row-list">
          {#each pendingRequests as request}
            <article class="request-row">
              <div>
                <strong>{request.display_name}</strong>
                <small>{request.machine_name} · {request.platform} · {request.engine}{#if request.tenant_id} · {request.tenant_id}{/if}</small>
                <span>{request.capabilities?.join(', ')}</span>
              </div>
              <div class="row-actions">
                <Button size="sm" onclick={() => approve(request.id)} disabled={isActing === `approve:${request.id}`}>
                  <CheckCircle2 size={14} />
                  Approve
                </Button>
                <Button size="sm" variant="danger" onclick={() => deny(request.id)} disabled={isActing === `deny:${request.id}`}>
                  <XCircle size={14} />
                  Deny
                </Button>
              </div>
            </article>
          {/each}
        </div>
      {:else}
        <div class="empty">No machines are waiting for approval.</div>
      {/if}
    </section>

    <section class="panel">
      <header>
        <h2><ServerCog size={18} /> Approved workers</h2>
        <Badge variant="primary">{state.workers.length}</Badge>
      </header>
      {#if state.workers.length}
        <div class="row-list">
          {#each state.workers as worker}
            <article class="worker-row">
              <div>
                <strong>{worker.display_name}</strong>
                <small>{worker.machine_name} · {worker.platform} · last seen {formatDate(worker.last_seen_at)}</small>
                <span>{worker.capabilities?.join(', ') || 'No capabilities reported'}</span>
              </div>
              <Badge variant={statusTone(worker.status)}>{worker.status}</Badge>
              <div class="row-actions">
                <Button size="sm" variant="secondary" onclick={() => rotate(worker.id)} disabled={worker.status !== 'approved' || isActing === `rotate:${worker.id}`}>
                  <RotateCw size={14} />
                  Rotate
                </Button>
                <Button size="sm" variant="danger" onclick={() => revoke(worker.id)} disabled={worker.status !== 'approved' || isActing === `revoke:${worker.id}`}>
                  <ShieldOff size={14} />
                  Revoke
                </Button>
              </div>
            </article>
          {/each}
        </div>
      {:else}
        <div class="empty">Install a local worker and approve it here.</div>
      {/if}
    </section>
  </div>

  <section class="panel">
    <header>
      <h2><TerminalSquare size={18} /> Recent worker activity</h2>
      <Badge variant="muted">{state.events.length}</Badge>
    </header>
    {#if state.events.length}
      <div class="event-list">
        {#each state.events.slice(0, 12) as event}
          <article>
            <strong>{event.event_type}</strong>
            <small>{event.worker_id} · {formatDate(event.created_at)}</small>
            <code>{JSON.stringify(event.payload).slice(0, 220)}</code>
          </article>
        {/each}
      </div>
    {:else}
      <div class="empty">Worker heartbeats, completions, failures, and logs will appear here.</div>
    {/if}
  </section>
</div>

<style>
  .workers-page {
    margin: 0 auto;
    max-width: 1240px;
  }

  .hero,
  .panel header,
  .worker-row,
  .request-row {
    align-items: flex-start;
    display: flex;
    gap: var(--spacing-md);
    justify-content: space-between;
  }

  .hero {
    margin-bottom: var(--spacing-lg);
  }

  .hero h1 {
    color: var(--color-text);
    font-size: 2.2rem;
    line-height: 1;
    margin: var(--spacing-xs) 0;
  }

  .hero p,
  .panel p,
  .panel small,
  .request-row span,
  .worker-row span {
    color: var(--color-text-secondary);
  }

  .hero-actions,
  .row-actions {
    align-items: center;
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-sm);
  }

  .status-grid,
  .workspace {
    display: grid;
    gap: var(--spacing-md);
    grid-template-columns: repeat(4, minmax(0, 1fr));
    margin-bottom: var(--spacing-lg);
  }

  .workspace {
    grid-template-columns: minmax(0, 0.85fr) minmax(0, 1.15fr);
  }

  .status-grid article,
  .panel,
  .notice {
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
    font-size: 1.75rem;
    line-height: 1;
    margin: 10px 0 6px;
  }

  .panel {
    margin-bottom: var(--spacing-lg);
  }

  .panel header {
    margin-bottom: var(--spacing-md);
  }

  .panel h2 {
    align-items: center;
    color: var(--color-text);
    display: flex;
    font-size: 1.1rem;
    gap: 8px;
    margin: 0;
  }

  .install-commands {
    display: grid;
    gap: var(--spacing-sm);
  }

  .install-block strong {
    color: var(--color-text-secondary);
    display: block;
    font-family: var(--font-mono);
    font-size: 0.68rem;
    margin-bottom: 4px;
    text-transform: uppercase;
  }

  .hint {
    color: var(--color-text-secondary);
    font-size: 0.78rem;
    margin: var(--spacing-xs) 0 0;
  }

  .hint code {
    background: rgba(0, 0, 0, 0.2);
    display: inline;
    font-size: 0.74rem;
    padding: 2px 6px;
  }

  code {
    background: rgba(0, 0, 0, 0.28);
    border: 1px solid rgba(103, 128, 151, 0.2);
    border-radius: var(--border-radius-md);
    color: var(--color-success);
    display: block;
    font-family: var(--font-mono);
    font-size: 0.78rem;
    overflow-x: auto;
    padding: var(--spacing-sm);
    white-space: pre-wrap;
  }

  .row-list,
  .event-list {
    display: grid;
    gap: 10px;
  }

  .request-row,
  .worker-row,
  .event-list article,
  .empty {
    background: rgba(3, 8, 12, 0.48);
    border: 1px solid rgba(103, 128, 151, 0.18);
    border-radius: var(--border-radius-md);
    padding: var(--spacing-md);
  }

  .request-row strong,
  .request-row small,
  .request-row span,
  .worker-row strong,
  .worker-row small,
  .worker-row span,
  .event-list strong,
  .event-list small {
    display: block;
  }

  .empty {
    color: var(--color-text-secondary);
    min-height: 96px;
  }

  .notice.error {
    border-color: rgba(255, 61, 79, 0.42);
    color: var(--color-error);
    margin-bottom: var(--spacing-lg);
  }

  .spin {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  @media (max-width: 900px) {
    .hero,
    .worker-row,
    .request-row {
      align-items: stretch;
      flex-direction: column;
    }

    .status-grid,
    .workspace {
      grid-template-columns: 1fr;
    }
  }
</style>
