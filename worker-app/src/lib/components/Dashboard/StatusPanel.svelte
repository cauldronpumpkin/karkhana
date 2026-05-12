<script>
  import { onMount } from 'svelte'
  import { invoke } from '@tauri-apps/api/core'
  import Card from '../UI/Card.svelte'
  import Badge from '../UI/Badge.svelte'
  import Button from '../UI/Button.svelte'
  import {
    workerStatus,
    connectionHealth,
    workerConfig,
    health,
    updateHealth,
    clearErrors,
    revoked,
  } from '../../stores.js'

  let config = $state({})
  let status = $state('idle')
  let connHealth = $state({ connected: false, lastHeartbeat: null, uptime: 0 })
  let healthData = $state({ apiConnected: false, sqsMessages: 0, sessionCount: 0, lastJobTime: null, errorCount: 0 })
  let revokedState = $state({ isRevoked: false, reason: '', countdown: 0 })
  let pollHandle = $state(null)

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

  let apiDotVariant = $derived.by(() => {
    if (healthData.apiConnected) return 'success'
    if (connHealth.connected) return 'warning'
    return 'error'
  })

  let apiDotLabel = $derived.by(() => {
    if (healthData.apiConnected) return 'Connected'
    if (connHealth.connected) return 'Degraded'
    return 'Disconnected'
  })

  let lastJobLabel = $derived.by(() => {
    if (!healthData.lastJobTime) return 'Never'
    return new Date(healthData.lastJobTime).toLocaleTimeString()
  })

  let countdownDisplay = $derived.by(() => {
    if (!revokedState.isRevoked || revokedState.countdown <= 0) return ''
    return `Auto-cleanup in ${revokedState.countdown}s`
  })

  async function fetchHealth() {
    try {
      const data = await invoke('get_app_health')
      updateHealth(data)
    } catch {
      // health endpoint may not be available yet — degrade gracefully
    }
  }

  async function handleClearErrors() {
    try {
      await invoke('clear_errors_command')
      clearErrors()
    } catch {
      clearErrors()
    }
  }

  async function handleReregister() {
    try {
      await invoke('reregister_worker_command')
    } catch (e) {
      console.error('Re-register failed:', e)
    }
  }

  async function handleRevoke() {
    try {
      const result = await invoke('revoke_worker')
      revoked.set({
        isRevoked: true,
        reason: result?.reason || 'Manually revoked',
        countdown: result?.countdown ?? 60,
      })
    } catch (e) {
      console.error('Revoke failed:', e)
    }
  }

  function statusVariant(s) {
    if (s === 'active') return 'success'
    if (s === 'pairing') return 'warning'
    if (s === 'error') return 'error'
    return 'muted'
  }

  onMount(async () => {
    try {
      config = await invoke('load_config_command')
      workerConfig.set(config)
    } catch (e) {
      console.error('Failed to load config:', e)
    }
    fetchHealth()
  })

  workerStatus.subscribe(s => status = s)
  connectionHealth.subscribe(h => connHealth = h)
  health.subscribe(h => healthData = h)
  revoked.subscribe(r => revokedState = r)

  // Poll health every 5 seconds
  $effect(() => {
    pollHandle = setInterval(fetchHealth, 5000)
    return () => {
      if (pollHandle) clearInterval(pollHandle)
    }
  })
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
      <strong>{connHealth.uptime ? `${Math.floor(connHealth.uptime / 3600)}h ${Math.floor((connHealth.uptime % 3600) / 60)}m` : '—'}</strong>
    </article>
    <article class="metric">
      <span class="mono-label">Last Heartbeat</span>
      <strong>{connHealth.lastHeartbeat ? new Date(connHealth.lastHeartbeat).toLocaleTimeString() : '—'}</strong>
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

<!-- System Health Card -->
<Card title="System Health">
  <div class="health-grid">
    <article class="health-metric">
      <span class="health-dot dot-{apiDotVariant}"></span>
      <span class="mono-label">API</span>
      <Badge variant={apiDotVariant}>{apiDotLabel}</Badge>
    </article>
    <article class="health-metric">
      <span class="mono-label">SQS Messages</span>
      <strong>{healthData.sqsMessages ?? '—'}</strong>
    </article>
    <article class="health-metric">
      <span class="mono-label">Sessions</span>
      <strong>{healthData.sessionCount ?? '—'}</strong>
    </article>
    <article class="health-metric">
      <span class="mono-label">Last Job</span>
      <strong>{lastJobLabel}</strong>
    </article>
    <article class="health-metric">
      <span class="mono-label">Errors (1h)</span>
      <strong class="error-count">{healthData.errorCount ?? 0}</strong>
    </article>
    <article class="health-metric actions">
      <Button variant="ghost" size="sm" onclick={handleClearErrors}>Clear Errors</Button>
    </article>
    <article class="health-metric actions">
      {#if (status === 'active' || status === 'pairing') && !revokedState.isRevoked}
        <Button variant="danger" size="sm" onclick={handleRevoke}>Revoke Worker</Button>
      {/if}
    </article>
  </div>
</Card>

<!-- Revocation Banner -->
{#if revokedState.isRevoked}
  <Card title="" padding="var(--spacing-md)" border={true}>
    <div class="revoke-banner">
      <div class="revoke-message">
        <strong>Worker Revoked:</strong> {revokedState.reason || 'No reason provided'}
      </div>
      {#if countdownDisplay}
        <div class="revoke-countdown">{countdownDisplay}</div>
      {/if}
      <Button variant="warning" size="sm" onclick={handleReregister}>Re-register</Button>
    </div>
  </Card>
{/if}

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

  /* System Health */
  .health-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--spacing-md);
  }

  .health-metric {
    align-items: center;
    background: linear-gradient(180deg, rgba(8, 14, 21, 0.9), rgba(4, 9, 14, 0.82));
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-md);
    display: flex;
    gap: var(--spacing-sm);
    padding: var(--spacing-md);
  }

  .health-metric.actions {
    justify-content: center;
  }

  .health-metric strong {
    color: var(--color-text);
    font-size: 0.92rem;
  }

  .health-metric .error-count {
    color: var(--color-error);
  }

  .health-dot {
    border-radius: 50%;
    display: inline-block;
    flex-shrink: 0;
    height: 10px;
    width: 10px;
  }

  .dot-success {
    background: var(--color-success);
    box-shadow: 0 0 6px var(--color-success);
  }

  .dot-warning {
    background: var(--color-warning);
    box-shadow: 0 0 6px var(--color-warning);
  }

  .dot-error {
    background: var(--color-error);
    box-shadow: 0 0 6px var(--color-error);
  }

  /* Revocation */
  .revoke-banner {
    align-items: center;
    background: rgba(255, 61, 79, 0.13);
    border: 1px solid var(--color-error);
    border-radius: var(--border-radius-md);
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-md);
    justify-content: space-between;
    padding: var(--spacing-md);
  }

  .revoke-message {
    color: var(--color-error);
    font-size: 0.9rem;
  }

  .revoke-countdown {
    color: var(--color-warning);
    font-family: var(--font-mono);
    font-size: 0.85rem;
  }

  @media (max-width: 640px) {
    .status-grid {
      grid-template-columns: repeat(2, 1fr);
    }
    .health-grid {
      grid-template-columns: 1fr;
    }
    .revoke-banner {
      flex-direction: column;
      align-items: flex-start;
    }
  }
</style>
