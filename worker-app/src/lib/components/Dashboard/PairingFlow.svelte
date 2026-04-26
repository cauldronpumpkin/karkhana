<script>
  import { invoke } from '@tauri-apps/api/core'
  import { listen } from '@tauri-apps/api/event'
  import { onMount } from 'svelte'
  import Card from '../UI/Card.svelte'
  import Button from '../UI/Button.svelte'
  import Input from '../UI/Input.svelte'
  import Badge from '../UI/Badge.svelte'
  import { pairingStatus } from '../../stores.js'

  let mode = $state('dashboard')
  let apiBase = $state('')
  let displayName = $state('')
  let tenantId = $state('')
  let workerAuthToken = $state('')
  let workerId = $state('')
  let status = $state(null)
  let error = $state('')

  pairingStatus.subscribe(s => {
    status = s
    if (s?.status === 'denied') {
      error = s.reason || 'Pairing denied'
    }
  })

  async function handleDashboardSubmit() {
    error = ''
    try {
      await invoke('start_pairing', {
        apiBase: apiBase || 'http://localhost:8000',
        displayName: displayName || 'OpenClaude local worker',
        tenantId: tenantId || null,
      })
    } catch (e) {
      error = e
    }
  }

  async function handleDevTokenSubmit() {
    error = ''
    if (!workerAuthToken.trim()) {
      error = 'Worker auth token is required'
      return
    }
    if (!workerId.trim()) {
      error = 'Worker ID is required'
      return
    }
    try {
      await invoke('pair_with_dev_token', {
        apiBase: apiBase || 'http://localhost:8000',
        workerAuthToken: workerAuthToken.trim(),
        workerId: workerId.trim(),
      })
    } catch (e) {
      error = e
    }
  }

  onMount(() => {
    const unlisten = listen('pairing-status-changed', (event) => {
      pairingStatus.set(event.payload)
    })
    return () => unlisten.then((f) => f())
  })
</script>

<Card title="Pair Worker">
  {#if !status || status.status === 'idle'}
    <div class="mode-toggle">
      <button
        class="mode-btn"
        class:active={mode === 'dashboard'}
        onclick={() => mode = 'dashboard'}
      >Dashboard Pairing</button>
      <button
        class="mode-btn"
        class:active={mode === 'dev'}
        onclick={() => mode = 'dev'}
      >Dev Token</button>
    </div>

    {#if mode === 'dashboard'}
      <form onsubmit={(e) => { e.preventDefault(); handleDashboardSubmit(); }}>
        <div class="form-fields">
          <Input label="API Base URL" bind:value={apiBase} placeholder="http://localhost:8000" />
          <Input label="Display Name" bind:value={displayName} placeholder="OpenClaude local worker" />
          <Input label="Tenant ID (optional)" bind:value={tenantId} />
        </div>
        {#if error}
          <p class="error">{error}</p>
        {/if}
        <div class="actions">
          <Button type="submit">Start Pairing</Button>
        </div>
      </form>
    {:else}
      <form onsubmit={(e) => { e.preventDefault(); handleDevTokenSubmit(); }}>
        <div class="form-fields">
          <Input label="API Base URL" bind:value={apiBase} placeholder="http://localhost:8000" />
          <Input label="Worker Auth Token" bind:value={workerAuthToken} type="password" placeholder="IDEAREFINERY_WORKER_AUTH_TOKEN" />
          <Input label="Worker ID" bind:value={workerId} placeholder="my-dev-worker-01" />
        </div>
        <p class="hint">
          Uses <code>X-IdeaRefinery-Worker-Token</code> for direct API access.
          No dashboard approval required.
        </p>
        {#if error}
          <p class="error">{error}</p>
        {/if}
        <div class="actions">
          <Button type="submit">Pair with Dev Token</Button>
        </div>
      </form>
    {/if}
  {:else if status.status === 'waiting'}
    <div class="waiting">
      <span class="spinner"></span>
      <p>Waiting for approval in Local Workers page...</p>
      <Badge variant="warning">Pending</Badge>
    </div>
  {:else if status.status === 'approved' || status.status === 'dev_paired'}
    <div class="success">
      <Badge variant="success">Paired</Badge>
      <p>Worker paired! Worker ID: <code>{status.worker_id}</code></p>
    </div>
  {:else if status.status === 'denied'}
    <div class="denied">
      <Badge variant="error">Denied</Badge>
      <p>{error}</p>
      <Button onclick={() => pairingStatus.set(null)}>Try Again</Button>
    </div>
  {/if}
</Card>

<style>
  .mode-toggle {
    display: flex;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-lg);
  }

  .mode-btn {
    background: transparent;
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-sm);
    color: var(--color-text-secondary);
    cursor: pointer;
    font-size: 0.9rem;
    padding: var(--spacing-sm) var(--spacing-md);
    transition: all 0.15s ease;
  }

  .mode-btn.active {
    background: var(--color-primary);
    border-color: var(--color-primary);
    color: white;
  }

  .mode-btn:hover:not(.active) {
    border-color: var(--color-primary);
    color: var(--color-text);
  }

  .form-fields {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-lg);
  }

  .actions {
    display: flex;
    justify-content: flex-end;
  }

  .error {
    color: var(--color-error);
    margin-bottom: var(--spacing-md);
  }

  .hint {
    color: var(--color-text-secondary);
    font-size: 0.85rem;
    margin-bottom: var(--spacing-md);
  }

  .waiting,
  .success,
  .denied {
    align-items: center;
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
    padding: var(--spacing-xl);
    text-align: center;
  }

  .spinner {
    animation: spin 1s linear infinite;
    border: 2px solid var(--color-border);
    border-radius: 50%;
    border-top-color: var(--color-primary);
    display: inline-block;
    height: 32px;
    width: 32px;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  code {
    background: rgba(4, 9, 14, 0.88);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-sm);
    font-family: var(--font-mono);
    font-size: 0.85rem;
    padding: 2px 6px;
  }
</style>
