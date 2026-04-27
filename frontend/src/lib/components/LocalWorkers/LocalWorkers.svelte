<script>
  import { onMount } from 'svelte';
  import { CheckCircle2, Clipboard, KeyRound, Link2, Loader2, RefreshCw, RotateCw, ServerCog, ShieldOff, TerminalSquare, XCircle } from 'lucide-svelte';
  import Button from '../UI/Button.svelte';
  import Badge from '../UI/Badge.svelte';

  const API_GATEWAY = 'https://api.karkhana.one';

  async function gwApi(path, opts = {}) {
    const res = await fetch(`${API_GATEWAY}${path}`, { headers: { 'Content-Type': 'application/json' }, ...opts });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }
  async function gwPost(path, body) { return gwApi(path, { method: 'POST', body: JSON.stringify(body) }); }

  let state = $state({ workers: [], requests: [], events: [] });
  let isLoading = $state(true);
  let isActing = $state('');
  let error = $state('');
  let copied = $state(false);
  let inviteLink = $state('');
  let workerIdInput = $state('');

  let pendingRequests = $derived(state.requests.filter((r) => r.status === 'pending'));
  let approvedWorkers = $derived(state.workers.filter((w) => w.status === 'approved'));

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
      const res = await fetch(`${API_GATEWAY}/api/worker/invite-link?api_base=${encodeURIComponent(API_GATEWAY)}${workerIdInput ? `&worker_id=${encodeURIComponent(workerIdInput)}` : ''}`);
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
    <div class="notice error" role="alert">{error}</div>
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
    <article><span>API</span><strong>Live</strong><small>API Gateway</small></article>
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
        <Badge variant="primary">{state.workers.length}</Badge>
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
  </div>
</div>

<style>
  .workers-page { margin: 0 auto; max-width: 1240px; }
  .hero, .panel header, .worker-row, .request-row { align-items: flex-start; display: flex; gap: var(--spacing-md); justify-content: space-between; }
  .hero { margin-bottom: var(--spacing-lg); }
  .hero h1 { color: var(--color-text); font-size: 2.2rem; line-height: 1; margin: var(--spacing-xs) 0; }
  .hero p, .panel p, .panel small, .request-row span, .worker-row span { color: var(--color-text-secondary); }
  .hero-actions, .row-actions { align-items: center; display: flex; flex-wrap: wrap; gap: var(--spacing-sm); }
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
  .row-list, .event-list { display: grid; gap: 10px; }
  .request-row, .worker-row, .event-list article, .empty { background: rgba(3, 8, 12, 0.48); border: 1px solid rgba(103, 128, 151, 0.18); border-radius: var(--border-radius-md); padding: var(--spacing-md); }
  .request-row strong, .request-row small, .request-row span, .worker-row strong, .worker-row small, .worker-row span, .event-list strong, .event-list small { display: block; }
  .empty { color: var(--color-text-secondary); min-height: 64px; }
  .notice.error { border-color: rgba(255, 61, 79, 0.42); color: var(--color-error); margin-bottom: var(--spacing-lg); }
  .spin { animation: spin 1s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  @media (max-width: 900px) { .hero, .worker-row, .request-row { flex-direction: column; } .status-grid, .workspace { grid-template-columns: 1fr; } }
</style>
