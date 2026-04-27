<script>
  import { invoke } from '@tauri-apps/api/core'
  import { listen } from '@tauri-apps/api/event'
  import { onMount } from 'svelte'
  import Card from '../UI/Card.svelte'
  import Button from '../UI/Button.svelte'
  import Input from '../UI/Input.svelte'
  import Badge from '../UI/Badge.svelte'
  import { pairingStatus } from '../../stores.js'

  let inviteLink = $state('')
  let status = $state(null)
  let error = $state('')

  pairingStatus.subscribe(s => {
    status = s
  })

  async function handleInviteLinkSubmit() {
    error = ''
    if (!inviteLink.trim()) {
      error = 'Invite link is required'
      return
    }
    try {
      await invoke('pair_with_invite_link', {
        inviteLink: inviteLink.trim(),
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
    <p class="description">
      Paste an invite link from your Karkhana dashboard to connect this worker.
    </p>
    <form onsubmit={(e) => { e.preventDefault(); handleInviteLinkSubmit(); }}>
      <div class="form-fields">
        <Input label="Invite Link" bind:value={inviteLink} placeholder="idearefinery://connect?api_base=...&amp;token=..." />
      </div>
      {#if error}
        <p class="error">{error}</p>
      {/if}
      <div class="actions">
        <Button type="submit">Connect Worker</Button>
      </div>
    </form>
  {:else if status.status === 'dev_paired'}
    <div class="success">
      <Badge variant="success">Paired</Badge>
      <p>Worker connected! Worker ID: <code>{status.worker_id}</code></p>
      <p class="hint">You can now start the worker from the dashboard.</p>
    </div>
  {:else if status.status === 'approved'}
    <div class="success">
      <Badge variant="success">Paired</Badge>
      <p>Worker connected! Worker ID: <code>{status.worker_id}</code></p>
    </div>
  {:else if status.status === 'waiting'}
    <div class="waiting">
      <span class="spinner"></span>
      <p>Registering worker...</p>
    </div>
  {:else if status.status === 'denied'}
    <div class="denied">
      <Badge variant="error">Denied</Badge>
      <p>{status.reason || 'Pairing was denied'}</p>
      <Button onclick={() => pairingStatus.set(null)}>Try Again</Button>
    </div>
  {:else}
    <div class="error-state">
      <p>Unknown status: {status?.status}</p>
      <Button onclick={() => pairingStatus.set(null)}>Reset</Button>
    </div>
  {/if}
</Card>

<style>
  .description {
    color: var(--color-text-secondary);
    font-size: 0.9rem;
    margin-bottom: var(--spacing-lg);
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
    margin-top: var(--spacing-sm);
  }

  .waiting,
  .success,
  .denied,
  .error-state {
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
