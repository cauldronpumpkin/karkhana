<script>
  import { onMount } from 'svelte'
  import { invoke } from '@tauri-apps/api/core'
  import Card from '../UI/Card.svelte'
  import Badge from '../UI/Badge.svelte'
  import { workerStatus, connectionHealth, workerConfig } from '../../stores.js'

  let config = $state({})
  let status = $state('idle')
  let health = $state({ connected: false, lastHeartbeat: null, uptime: 0 })

  const limitedEngines = ['opencode', 'openclaude', 'codex']
  const highAutonomyCaps = [
    'permission_guard', 'circuit_breaker', 'litellm_proxy',
    'diff_api', 'verification_runner', 'graphify_update',
  ]

  let engineLabel = $derived.by(() => {
    const e = config.engine
    if (!e) return { text: '—', variant: 'muted' }
    if (e === 'opencode-server') return { text: 'opencode-server', variant: 'success' }
    if (limitedEngines.includes(e)) return { text: e + ' (limited)', variant: 'error' }
    return { text: e, variant: 'warning' }
  })

  let engineNote = $derived.by(() => {
    const e = config.engine
    if (!e) return ''
    if (e === 'opencode-server') return ''
    if (limitedEngines.includes(e)) {
      return 'Limited fallback mode — not valid for Full Autopilot or Autonomous Development. Set engine to opencode-server.'
    }
    return ''
  })

  let capStatus = $derived.by(() => {
    const caps = config.capabilities || []
    const missing = highAutonomyCaps.filter(c => !caps.includes(c))
    if (missing.length === 0) return { text: 'Full', variant: 'success' }
    return { text: `Missing: ${missing.length}`, variant: 'error' }
  })

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
  {#if engineNote}
    <div class="warning-banner">
      <strong>Engine:</strong> {engineNote}
    </div>
  {/if}

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
      <Badge variant={engineLabel.variant}>{engineLabel.text}</Badge>
    </article>
    <article class="metric">
      <span class="mono-label">Capabilities</span>
      <Badge variant={capStatus.variant}>{capStatus.text}</Badge>
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
          <Badge variant={highAutonomyCaps.includes(cap) ? 'accent' : 'primary'}>{cap}</Badge>
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

  .warning-banner {
    background: rgba(255, 193, 7, 0.15);
    border: 1px solid var(--color-warning, #ffc107);
    border-radius: var(--border-radius-md);
    color: var(--color-warning, #ffc107);
    font-size: 0.85rem;
    margin-bottom: var(--spacing-md);
    padding: var(--spacing-sm) var(--spacing-md);
  }

  @media (max-width: 640px) {
    .status-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }
</style>
