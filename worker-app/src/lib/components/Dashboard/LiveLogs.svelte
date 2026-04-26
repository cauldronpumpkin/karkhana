<script>
  import { onMount } from 'svelte'
  import { listen } from '@tauri-apps/api/event'
  import Card from '../UI/Card.svelte'
  import Button from '../UI/Button.svelte'
  import { logs } from '../../stores.js'

  let logLines = $state([])
  let container = $state(null)

  logs.subscribe(l => {
    logLines = l
    if (container) {
      requestAnimationFrame(() => {
        container.scrollTop = container.scrollHeight
      })
    }
  })

  onMount(() => {
    const unsubs = []
    listen('worker-log', (e) => {
      logs.update(l => [...l, e.payload.line].slice(-500))
    }).then(u => unsubs.push(u))

    return () => unsubs.forEach(u => u())
  })

  function clearLogs() {
    logs.set([])
  }

  function formatLine(line) {
    const time = new Date().toLocaleTimeString('en-US', { hour12: false })
    if (line.startsWith('$ ')) {
      return { time, text: line, type: 'command' }
    }
    if (line.startsWith('exit code:') && !line.includes('0')) {
      return { time, text: line, type: 'error' }
    }
    return { time, text: line, type: 'normal' }
  }
</script>

<Card title="Live Logs">
  <div class="toolbar">
    <Button variant="ghost" size="sm" onclick={clearLogs}>Clear</Button>
  </div>
  <div class="log-container" bind:this={container}>
    {#each logLines as line}
      {@const formatted = formatLine(line)}
      <div class="log-line {formatted.type}">
        <span class="log-time">[{formatted.time}]</span>
        <span class="log-text">{formatted.text}</span>
      </div>
    {/each}
  </div>
</Card>

<style>
  .toolbar {
    display: flex;
    justify-content: flex-end;
    margin-bottom: var(--spacing-sm);
  }

  .log-container {
    background: rgba(4, 9, 14, 0.88);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-md);
    font-family: var(--font-mono);
    font-size: 0.78rem;
    max-height: 480px;
    overflow-y: auto;
    padding: var(--spacing-md);
  }

  .log-line {
    line-height: 1.6;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .log-line + .log-line {
    margin-top: 2px;
  }

  .log-time {
    color: var(--color-text-muted);
    margin-right: var(--spacing-sm);
  }

  .log-line.command .log-text {
    color: var(--color-primary-2);
  }

  .log-line.error .log-text {
    color: var(--color-error);
  }

  .log-line.normal .log-text {
    color: var(--color-text-secondary);
  }
</style>
