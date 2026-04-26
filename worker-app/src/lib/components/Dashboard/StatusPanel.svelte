<script>
  import { onMount } from 'svelte'
  import { invoke } from '@tauri-apps/api/core'
  import Card from '../UI/Card.svelte'
  import Badge from '../UI/Badge.svelte'
  import { workerStatus, connectionHealth, workerConfig } from '../../stores.js'

  let config = $state({})
  let status = $state('idle')
  let health = $state({ connected: false, lastHeartbeat: null, uptime: 0 })

  onMount(async () => {
    try {
      config = await invoke('load_config_command')
      workerConfig.set(config)
    } catch (e) {
      console.error('Failed to load config:', e)
    }
  })

  workerStatus.subscribe(s => status = s)
  connectionHealth.subscribe(h => health = h)

  function statusVariant(s) {
    if (s === 'active') return 'success'
    if (s === 'pairing') return 'warning'
    if (s === 'error') return 'error'
    return 'muted'
  }
</script>

<Card title="Worker Status">
  <div class="status-grid">
    <article class="metric">
      <span class="mono-label">Status</span>
      <Badge variant={statusVariant(status)}>{status}</Badge>
    </article>
    <article class="metric">
      <span class="mono-label">API Base</span>
      <strong>{config.api_base || '—'}</strong>
    </article>
    <article class="metric">
      <span class="mono-label">Worker ID</span>
      <strong>{config.display_name || '—'}</strong>
    </article>
    <article class="metric">
      <span class="mono-label">Tenant</span>
      <strong>{config.tenant_id || '—'}</strong>
    </article>
    <article class="metric">
      <span class="mono-label">Engine</span>
      <strong>{config.engine || '—'}</strong>
    </article>
    <article class="metric">
      <span class="mono-label">Platform</span>
      <strong>{typeof navigator !== 'undefined' ? navigator.platform : '—'}</strong>
    </article>
    <article class="metric">
      <span class="mono-label">Uptime</span>
      <strong>{health.uptime ? `${Math.floor(health.uptime / 3600)}h ${Math.floor((health.uptime % 3600) / 60)}m` : '—'}</strong>
    </article>
    <article class="metric">
      <span class="mono-label">Last Heartbeat</span>
      <strong>{health.lastHeartbeat ? new Date(health.lastHeartbeat).toLocaleTimeString() : '—'}</strong>
    </article>
  </div>

  {#if config.capabilities?.length}
    <div class="capabilities">
      <span class="mono-label">Capabilities</span>
      <div class="capability-list">
        {#each config.capabilities as cap}
          <Badge variant="primary">{cap}</Badge>
        {/each}
      </div>
    </div>
  {/if}
</Card>

<style>
  .status-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: var(--spacing-md);
  }

  .metric {
    background: linear-gradient(180deg, rgba(8, 14, 21, 0.9), rgba(4, 9, 14, 0.82));
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-md);
    padding: var(--spacing-md);
  }

  .metric strong {
    color: var(--color-text);
    display: block;
    font-size: 0.92rem;
    margin-top: var(--spacing-xs);
  }

  .capabilities {
    margin-top: var(--spacing-lg);
  }

  .capability-list {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-sm);
    margin-top: var(--spacing-sm);
  }

  @media (max-width: 640px) {
    .status-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }
</style>
