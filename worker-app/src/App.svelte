<script>
  import { invoke } from '@tauri-apps/api/core'
  import { listen } from '@tauri-apps/api/event'
  import { onMount } from 'svelte'
  import StatusPanel from './lib/components/Dashboard/StatusPanel.svelte'
  import JobHistory from './lib/components/Dashboard/JobHistory.svelte'
  import LiveLogs from './lib/components/Dashboard/LiveLogs.svelte'
  import PairingFlow from './lib/components/Dashboard/PairingFlow.svelte'
  import ConfigEditor from './lib/components/Dashboard/ConfigEditor.svelte'
  import { workerStatus, logs, pairingStatus } from './lib/stores.js'

  let activeTab = $state('status')
  let isWorkerRunning = $state(false)

  async function toggleWorker() {
    if (isWorkerRunning) {
      await invoke('stop_worker')
      isWorkerRunning = false
      workerStatus.set('idle')
    } else {
      await invoke('start_worker')
      isWorkerRunning = true
      workerStatus.set('active')
    }
  }

  onMount(() => {
    invoke('get_worker_status').then(status => {
      isWorkerRunning = status
      workerStatus.set(status ? 'active' : 'idle')
    })

    const unsubs = []
    listen('worker-status', (e) => {
      workerStatus.set(e.payload.status)
    }).then(u => unsubs.push(u))
    listen('job-started', (e) => {
      workerStatus.set('active')
    }).then(u => unsubs.push(u))
    listen('job-completed', (e) => {
      // handled in JobHistory
    }).then(u => unsubs.push(u))
    listen('job-failed', (e) => {
      // handled in JobHistory
    }).then(u => unsubs.push(u))
    listen('worker-log', (e) => {
      logs.update(l => [...l, e.payload.line].slice(-500))
    }).then(u => unsubs.push(u))
    listen('pairing-status-changed', (e) => {
      pairingStatus.set(e.payload)
    }).then(u => unsubs.push(u))

    return () => {
      unsubs.forEach(u => u())
    }
  })
</script>

<div class="app">
  <header class="app-header">
    <div class="header-left">
      <h1>IdeaRefinery Worker</h1>
      <span class="status-badge" class:active={isWorkerRunning}>
        {isWorkerRunning ? 'Active' : 'Idle'}
      </span>
    </div>
    <div class="header-actions">
      <button onclick={toggleWorker}>
        {isWorkerRunning ? 'Stop Worker' : 'Start Worker'}
      </button>
    </div>
  </header>

  <nav class="app-tabs">
    <button class="tab" class:active={activeTab === 'status'} onclick={() => activeTab = 'status'}>Status</button>
    <button class="tab" class:active={activeTab === 'jobs'} onclick={() => activeTab = 'jobs'}>Jobs</button>
    <button class="tab" class:active={activeTab === 'logs'} onclick={() => activeTab = 'logs'}>Logs</button>
    <button class="tab" class:active={activeTab === 'pairing'} onclick={() => activeTab = 'pairing'}>Pairing</button>
    <button class="tab" class:active={activeTab === 'config'} onclick={() => activeTab = 'config'}>Config</button>
  </nav>

  <main class="app-main">
    {#if activeTab === 'status'}
      <StatusPanel />
    {:else if activeTab === 'jobs'}
      <JobHistory />
    {:else if activeTab === 'logs'}
      <LiveLogs />
    {:else if activeTab === 'pairing'}
      <PairingFlow />
    {:else if activeTab === 'config'}
      <ConfigEditor />
    {/if}
  </main>
</div>

<style>
  .app {
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
  }

  .app-header {
    align-items: center;
    background: linear-gradient(180deg, rgba(8, 14, 21, 0.98), rgba(4, 9, 14, 0.96));
    border-bottom: 1px solid var(--color-border);
    display: flex;
    justify-content: space-between;
    padding: var(--spacing-md) var(--spacing-lg);
  }

  .header-left {
    align-items: center;
    display: flex;
    gap: var(--spacing-md);
  }

  .header-left h1 {
    font-size: 1.15rem;
    font-weight: 700;
    margin: 0;
  }

  .status-badge {
    background: rgba(115, 130, 145, 0.18);
    border-radius: var(--border-radius-sm);
    color: var(--color-text-muted);
    font-family: var(--font-mono);
    font-size: 0.7rem;
    font-weight: 700;
    padding: 4px 8px;
    text-transform: uppercase;
  }

  .status-badge.active {
    background: rgba(82, 245, 106, 0.14);
    color: var(--color-success);
  }

  .app-tabs {
    background: rgba(4, 9, 14, 0.88);
    border-bottom: 1px solid var(--color-border);
    display: flex;
    gap: 2px;
    padding: 0 var(--spacing-lg);
  }

  .tab {
    background: transparent;
    border: 0;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    color: var(--color-text-secondary);
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 600;
    min-height: 40px;
    padding: 8px 14px;
    transition: color 0.18s ease, border-color 0.18s ease;
  }

  .tab:hover {
    color: var(--color-text);
  }

  .tab.active {
    border-bottom-color: var(--color-primary);
    color: var(--color-text);
  }

  .app-main {
    flex: 1;
    overflow-y: auto;
    padding: var(--spacing-lg);
  }
</style>
