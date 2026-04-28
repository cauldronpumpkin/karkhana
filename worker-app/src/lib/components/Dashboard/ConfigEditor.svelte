<script>
  import { invoke } from '@tauri-apps/api/core'
  import { onMount } from 'svelte'
  import Card from '../UI/Card.svelte'
  import Button from '../UI/Button.svelte'
  import Input from '../UI/Input.svelte'
  import Badge from '../UI/Badge.svelte'

  let config = $state({})
  let saved = $state(false)

  const capabilities = [
    'repo_index',
    'architecture_dossier',
    'gap_analysis',
    'build_task_plan',
    'agent_branch_work',
    'test_verify',
    'sync_remote_state',
    'permission_guard',
    'circuit_breaker',
    'litellm_proxy',
    'diff_api',
    'verification_runner',
    'graphify_update',
  ]

  const highAutonomyCaps = [
    'permission_guard',
    'circuit_breaker',
    'litellm_proxy',
    'diff_api',
    'verification_runner',
    'graphify_update',
  ]

  let engineWarning = $derived.by(() => {
    const e = config.engine
    if (!e) return ''
    if (e === 'opencode-server') return ''
    if (e === 'openclaude' || e === 'opencode' || e === 'codex') {
      return 'Limited fallback mode — not valid for Factory Run autonomous_development or full_autopilot levels.'
    }
    return ''
  })

  let capabilityWarning = $derived.by(() => {
    const missing = highAutonomyCaps.filter(c => !config.capabilities?.includes(c))
    if (missing.length === 0) return ''
    return 'Missing high-autonomy capabilities: ' + missing.join(', ') + '. Add opencode-server engine or enable these capabilities for factory deployment.'
  })

  onMount(async () => {
    try {
      config = await invoke('load_config_command')
    } catch (e) {
      console.error('Failed to load config:', e)
    }
  })

  function toggleCapability(cap) {
    const caps = config.capabilities || []
    if (caps.includes(cap)) {
      config = { ...config, capabilities: caps.filter(c => c !== cap) }
    } else {
      config = { ...config, capabilities: [...caps, cap] }
    }
  }

  async function handleSave() {
    saved = false
    try {
      await invoke('save_config_command', { config })
      saved = true
    } catch (e) {
      console.error('Failed to save config:', e)
    }
  }
</script>

<Card title="Configuration">
  <div class="config-form">
    {#if engineWarning}
      <div class="warning-banner">
        <strong>Engine Warning:</strong> {engineWarning}
        <p class="recommendation">Recommended: set engine to <code>opencode-server</code> for full factory capability.</p>
      </div>
    {/if}

    {#if capabilityWarning}
      <div class="warning-banner warn">
        <strong>Capability Warning:</strong> {capabilityWarning}
      </div>
    {/if}

    {#if config.engine === 'opencode-server'}
      <div class="info-banner">
        <strong>opencode-server mode</strong> — full execution engine with permission guard, circuit breaker, LiteLLM proxy, diff API, verification runner, and graphify update support. Recommended for all factory deployments.
      </div>
    {/if}

    <Card title="General" border={false} padding="0">
      <div class="field-group">
        <Input label="API Base URL" bind:value={config.api_base} />
        <Input label="Display Name" bind:value={config.display_name} />
        <Input label="Tenant ID" bind:value={config.tenant_id} />
        <Input label="Workspace Root" bind:value={config.workspace_root} />
        <Input label="Poll Seconds" type="number" bind:value={config.poll_seconds} />
        <div class="engine-field">
          <Input label="Engine" bind:value={config.engine} />
          {#if config.engine === 'opencode-server'}
            <Badge variant="success">recommended</Badge>
          {:else if config.engine}
            <Badge variant="error">limited</Badge>
          {/if}
        </div>
      </div>
    </Card>

    <Card title="Capabilities" border={false} padding="0">
      <div class="capability-grid">
        {#each capabilities as cap}
          {@const isHighAutonomy = highAutonomyCaps.includes(cap)}
          <label class="capability-item">
            <input
              type="checkbox"
              checked={config.capabilities?.includes(cap)}
              onchange={() => toggleCapability(cap)}
            />
            <Badge variant={isHighAutonomy ? 'accent' : 'primary'}>{cap}</Badge>
          </label>
        {/each}
      </div>
      <p class="cap-note">High-autonomy capabilities (accent) required for autonomous_development and full_autopilot levels.</p>
    </Card>

    <Card title="OpenClaude Settings" border={false} padding="0">
      <div class="field-group">
        <Input label="Model" bind:value={config.openclaude.model} />
        <Input label="Agent" bind:value={config.openclaude.agent} />
        <Input label="Permission Mode" bind:value={config.openclaude.permission_mode} />
        <Input label="Output Format" bind:value={config.openclaude.output_format} />
        <Input label="Max Budget USD" bind:value={config.openclaude.max_budget_usd} />
        <Input label="System Prompt" bind:value={config.openclaude.system_prompt} />
      </div>
      <p class="cap-note">OpenClaude settings only apply when engine is set to <code>openclaude</code> (limited fallback mode).</p>
    </Card>

    <div class="actions">
      {#if saved}
        <span class="saved">Saved!</span>
      {/if}
      <Button onclick={handleSave}>Save Config</Button>
    </div>
  </div>
</Card>

<style>
  .config-form {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-lg);
  }

  .field-group {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .engine-field {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .capability-grid {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-sm);
  }

  .capability-item {
    align-items: center;
    cursor: pointer;
    display: flex;
    gap: var(--spacing-sm);
  }

  .cap-note {
    color: var(--color-text-muted);
    font-size: 0.8rem;
    margin-top: var(--spacing-sm);
  }

  .actions {
    align-items: center;
    display: flex;
    gap: var(--spacing-md);
    justify-content: flex-end;
  }

  .saved {
    color: var(--color-success);
    font-family: var(--font-mono);
    font-size: 0.8rem;
  }

  .warning-banner {
    background: rgba(255, 193, 7, 0.15);
    border: 1px solid var(--color-warning, #ffc107);
    border-radius: var(--border-radius-md);
    color: var(--color-warning, #ffc107);
    font-size: 0.85rem;
    padding: var(--spacing-md);
  }

  .warning-banner.warn {
    background: rgba(255, 152, 0, 0.12);
    border-color: #ff9800;
    color: #ff9800;
  }

  .warning-banner .recommendation {
    margin-top: var(--spacing-sm);
    opacity: 0.85;
  }

  .warning-banner code {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 3px;
    padding: 1px 4px;
  }

  .info-banner {
    background: rgba(33, 150, 243, 0.12);
    border: 1px solid #2196f3;
    border-radius: var(--border-radius-md);
    color: #90caf9;
    font-size: 0.85rem;
    padding: var(--spacing-md);
  }
</style>
