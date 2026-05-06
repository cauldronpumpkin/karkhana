<script>
  import { onMount } from 'svelte'
  import { listen } from '@tauri-apps/api/event'
  import Card from '../UI/Card.svelte'
  import Button from '../UI/Button.svelte'
  import { logs, logEntries, addLog } from '../../stores.js'

  const MAX_ENTRIES = 1000

  let logLines = $state([])
  let allEntries = $state([])
  let container = $state(null)
  let levelFilter = $state('All')
  let searchText = $state('')
  let autoScroll = $state(true)

  const LEVELS = ['All', 'Info', 'Warn', 'Error', 'Debug']

  // Computed: apply level filter
  let levelFiltered = $derived.by(() => {
    if (levelFilter === 'All') return allEntries
    return allEntries.filter(e => {
      const lv = (e.level || '').toLowerCase()
      const fv = levelFilter.toLowerCase()
      return lv === fv || (fv === 'warn' && lv === 'warning')
    })
  })

  // Computed: apply search filter on top of level filter
  let filtered = $derived.by(() => {
    if (!searchText.trim()) return levelFiltered
    const q = searchText.toLowerCase()
    return levelFiltered.filter(e => (e.message || e.text || '').toLowerCase().includes(q))
  })

  // Wire old-style logs store to new logEntries
  logs.subscribe(l => {
    logLines = l
  })

  logEntries.subscribe(e => {
    allEntries = e
  })

  // Auto-scroll effect
  $effect(() => {
    // Triggered whenever filtered changes — scroll if autoScroll is ON
    filtered
    if (autoScroll && container) {
      requestAnimationFrame(() => {
        container.scrollTop = container.scrollHeight
      })
    }
  })

  onMount(() => {
    const unsubs = []

    listen('worker-log', (e) => {
      const line = e.payload?.line ?? e.payload
      // Add to old logs store for backward compat
      logs.update(l => [...l, line].slice(-MAX_ENTRIES))
      // Determine level from line
      let level = 'Info'
      const lower = (line || '').toLowerCase()
      if (lower.includes('error') || lower.startsWith('exit code:') && !lower.includes('exit code: 0')) {
        level = 'Error'
      } else if (lower.includes('warn')) {
        level = 'Warn'
      } else if (lower.includes('debug')) {
        level = 'Debug'
      }
      addLog(level, line)
    }).then(u => unsubs.push(u))

    return () => unsubs.forEach(u => u())
  })

  function clearLogs() {
    logs.set([])
    logEntries.set([])
  }

  function exportLogs() {
    const lines = filtered.map(e => {
      const time = new Date(e.timestamp).toLocaleTimeString('en-US', { hour12: false })
      const level = (e.level || 'INFO').toUpperCase()
      return `[${time}] [${level}] ${e.message || e.text || ''}`
    })
    const content = lines.join('\n')
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `worker-logs-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  function lineClass(entry) {
    const lv = (entry.level || '').toLowerCase()
    if (lv === 'error') return 'error'
    if (lv === 'warn' || lv === 'warning') return 'warn'
    if (lv === 'debug') return 'debug'
    return 'normal'
  }

  function formatTime(ts) {
    return new Date(ts).toLocaleTimeString('en-US', { hour12: false })
  }
</script>

<Card title="Live Logs">
  <div class="toolbar">
    <div class="filter-group">
      {#each LEVELS as lv}
        <button
          class="filter-btn"
          class:active={levelFilter === lv}
          onclick={() => levelFilter = lv}
        >
          {lv}
        </button>
      {/each}
    </div>
    <div class="search-group">
      <input
        class="search-input"
        type="text"
        placeholder="Filter logs..."
        bind:value={searchText}
      />
    </div>
    <div class="controls">
      <label class="toggle-label">
        <input type="checkbox" bind:checked={autoScroll} />
        <span class="toggle-text">Auto-scroll</span>
      </label>
      <Button variant="ghost" size="sm" onclick={exportLogs}>Export</Button>
      <Button variant="ghost" size="sm" onclick={clearLogs}>Clear</Button>
    </div>
  </div>
  <div class="log-container" bind:this={container}>
    {#each filtered as entry}
      <div class="log-line {lineClass(entry)}">
        <span class="log-time">[{formatTime(entry.timestamp)}]</span>
        <span class="log-level {lineClass(entry)}">{entry.level || 'INFO'}</span>
        <span class="log-text">{entry.message || entry.text || ''}</span>
      </div>
    {/each}
    {#if filtered.length === 0 && allEntries.length === 0}
      <div class="log-empty">No logs yet. Waiting for worker output...</div>
    {:else if filtered.length === 0}
      <div class="log-empty">No logs match the current filter.</div>
    {/if}
  </div>
</Card>

<style>
  .toolbar {
    align-items: center;
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-sm);
    justify-content: space-between;
    margin-bottom: var(--spacing-sm);
  }

  .filter-group {
    display: flex;
    gap: 2px;
  }

  .filter-btn {
    background: rgba(7, 13, 19, 0.9);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-sm);
    color: var(--color-text-muted);
    cursor: pointer;
    font-family: var(--font-mono);
    font-size: 0.7rem;
    padding: 4px 10px;
    transition: all 0.15s;
  }

  .filter-btn:hover {
    border-color: var(--color-primary);
    color: var(--color-text);
  }

  .filter-btn.active {
    background: rgba(0, 120, 255, 0.15);
    border-color: var(--color-primary);
    color: var(--color-primary);
  }

  .search-group {
    flex: 1;
    min-width: 140px;
    max-width: 260px;
  }

  .search-input {
    background: rgba(4, 9, 14, 0.88);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-sm);
    color: var(--color-text);
    font-family: var(--font-mono);
    font-size: 0.75rem;
    padding: 6px 10px;
    width: 100%;
  }

  .search-input:focus {
    border-color: var(--color-primary);
    outline: none;
  }

  .controls {
    align-items: center;
    display: flex;
    gap: var(--spacing-sm);
    flex-shrink: 0;
  }

  .toggle-label {
    align-items: center;
    cursor: pointer;
    display: flex;
    gap: 4px;
    user-select: none;
  }

  .toggle-text {
    color: var(--color-text-muted);
    font-size: 0.75rem;
  }

  .toggle-label input[type="checkbox"] {
    accent-color: var(--color-primary);
    cursor: pointer;
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
    align-items: baseline;
    display: flex;
    gap: var(--spacing-sm);
  }

  .log-line + .log-line {
    margin-top: 2px;
  }

  .log-time {
    color: var(--color-text-muted);
    flex-shrink: 0;
  }

  .log-level {
    flex-shrink: 0;
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    min-width: 42px;
    text-align: center;
    border-radius: var(--border-radius-sm);
    padding: 0 4px;
  }

  .log-level.normal {
    color: var(--color-text-secondary);
    background: rgba(115, 130, 145, 0.1);
  }

  .log-level.warn {
    color: var(--color-warning);
    background: rgba(255, 159, 28, 0.12);
  }

  .log-level.error {
    color: var(--color-error);
    background: rgba(255, 61, 79, 0.12);
  }

  .log-level.debug {
    color: var(--color-text-muted);
    background: rgba(115, 130, 145, 0.08);
  }

  .log-line.normal .log-text {
    color: var(--color-text-secondary);
  }

  .log-line.warn .log-text {
    color: var(--color-warning);
  }

  .log-line.error .log-text {
    color: var(--color-error);
  }

  .log-line.debug .log-text {
    color: var(--color-text-muted);
  }

  .log-empty {
    color: var(--color-text-muted);
    font-style: italic;
    padding: var(--spacing-md);
    text-align: center;
  }
</style>
