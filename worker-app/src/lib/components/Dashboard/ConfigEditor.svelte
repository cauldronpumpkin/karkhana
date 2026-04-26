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
  ]

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
    <Card title="General" border={false} padding="0">
      <div class="field-group">
        <Input label="API Base URL" bind:value={config.api_base} />
        <Input label="Display Name" bind:value={config.display_name} />
        <Input label="Tenant ID" bind:value={config.tenant_id} />
        <Input label="Workspace Root" bind:value={config.workspace_root} />
        <Input label="Poll Seconds" type="number" bind:value={config.poll_seconds} />
        <Input label="Engine" bind:value={config.engine} />
      </div>
    </Card>

    <Card title="Capabilities" border={false} padding="0">
      <div class="capability-grid">
        {#each capabilities as cap}
          <label class="capability-item">
            <input
              type="checkbox"
              checked={config.capabilities?.includes(cap)}
              onchange={() => toggleCapability(cap)}
            />
            <Badge variant="primary">{cap}</Badge>
          </label>
        {/each}
      </div>
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
</style>
