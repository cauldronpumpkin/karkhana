<script>
  import { wsStore } from '../../websocket.svelte.js';
  import { Play, Terminal, AlertTriangle, CheckCircle2, Loader2, Info } from 'lucide-svelte';

  let { factoryRunId = '' } = $props();

  /** @type {Array<{type: string, run_id: string, payload: object, timestamp: string}>} */
  let entries = $state([]);
  let containerEl = $state(null);

  // Connection status derived reactively from wsStore
  let connectionStatus = $derived(wsStore.connected);

  // Maximum entries to keep in memory
  const MAX_ENTRIES = 500;

  // Track previous topic so we can unsubscribe on prop change
  let previousTopic = $state('');

  // Subscribe/unsubscribe reactively whenever factoryRunId changes
  $effect(() => {
    if (!factoryRunId) return;

    const newTopic = `run:${factoryRunId}`;

    // Unsubscribe from old topic if different
    if (previousTopic && previousTopic !== newTopic) {
      wsStore.send({ type: 'unsubscribe', topic: previousTopic });
    }

    wsStore.send({ type: 'subscribe', topic: newTopic });
    previousTopic = newTopic;

    // Cleanup on destroy or re-run
    return () => {
      wsStore.send({ type: 'unsubscribe', topic: newTopic });
    };
  });

  // Watch for new WebSocket messages
  $effect(() => {
    // Access lastMessage reactively — this re-runs when it changes
    const msg = wsStore.lastMessage;
    if (!msg || !msg.run_id || msg.run_id !== factoryRunId) return;

    // Cap entries at MAX_ENTRIES to prevent memory leaks on long runs
    entries = [
      ...entries.slice(-(MAX_ENTRIES - 1)),
      {
        type: msg.type || 'unknown',
        run_id: msg.run_id,
        payload: msg.payload || {},
        timestamp: new Date().toISOString(),
      },
    ];

    // Auto-scroll to bottom
    queueMicrotask(() => {
      if (containerEl) {
        containerEl.scrollTop = containerEl.scrollHeight;
      }
    });
  });

  const iconFor = (eventType) => {
    if (eventType === 'job:started') return Play;
    if (eventType === 'job:completed') return CheckCircle2;
    if (eventType === 'job:failed') return AlertTriangle;
    if (eventType === 'job:checkpoint') return Info;
    if (eventType === 'job:verification') return Info;
    return Terminal;
  };

  const colorClass = (eventType) => {
    if (eventType === 'job:started') return 'event-started';
    if (eventType === 'job:completed') return 'event-completed';
    if (eventType === 'job:failed') return 'event-failed';
    if (eventType === 'job:checkpoint') return 'event-checkpoint';
    if (eventType === 'job:verification') return 'event-checkpoint';
    return '';
  };

  const titleFor = (entry) => {
    const { type, payload } = entry;
    const jobId = payload?.job_id || '?';
    const summary = payload?.summary || payload?.error || '';
    switch (type) {
      case 'job:started':
        return `Job ${jobId} — ${payload?.task_title || 'starting'}`;
      case 'job:checkpoint':
        return `Job ${jobId} checkpoint — ${payload?.verification_count || 0} verifications`;
      case 'job:completed':
        return `Job ${jobId} completed${summary ? ' — ' + summary : ''}`;
      case 'job:failed':
        return `Job ${jobId} failed — ${summary}`;
      default:
        return `${type}`;
    }
  };

  const fmtTime = (iso) => {
    try {
      return new Date(iso).toLocaleTimeString();
    } catch {
      return iso;
    }
  };

</script>

<div class="run-log" class:disconnected={!connectionStatus}>
  <div class="log-header">
    <div class="log-title">
      <Terminal size={16} />
      <span>Live Log</span>
      {#if factoryRunId}
        <span class="run-badge">{factoryRunId.slice(0, 8)}</span>
      {/if}
    </div>
    <div class="log-status">
      {#if connectionStatus}
        <span class="dot live"></span>
        <span>Connected</span>
      {:else}
        <span class="dot disconnected"></span>
        <span>Disconnected</span>
      {/if}
      <span class="entry-count">{entries.length} events</span>
    </div>
  </div>

  <div class="log-entries" bind:this={containerEl}>
    {#if entries.length === 0}
      <div class="log-empty">
        <Loader2 size={16} class="spin" />
        <span>Waiting for events from Karigar worker...</span>
        <p>Start a job and live logs will appear here in real-time.</p>
      </div>
    {:else}
      {#each entries as entry, i (i)}
        <div class="log-entry {colorClass(entry.type)}">
          <div class="entry-icon">
            <svelte:component this={iconFor(entry.type)} size={14} />
          </div>
          <div class="entry-body">
            <div class="entry-title">{titleFor(entry)}</div>
            {#if entry.payload}
              <div class="entry-details">
                {#each Object.entries(entry.payload) as [key, value]}
                  {#if key !== 'job_id' && key !== 'task_title' && key !== 'summary' && key !== 'error' && value !== undefined && value !== null && value !== ''}
                    <div class="detail-row">
                      <span class="detail-key">{key}</span>
                      <span class="detail-value">
                        {#if Array.isArray(value)}
                          {value.length ? value.join(', ') : '(none)'}
                        {:else if typeof value === 'object'}
                          {JSON.stringify(value)}
                        {:else}
                          {String(value)}
                        {/if}
                      </span>
                    </div>
                  {/if}
                {/each}
              </div>
            {/if}
          </div>
          <div class="entry-time">{fmtTime(entry.timestamp)}</div>
        </div>
      {/each}
    {/if}
  </div>
</div>

<style>
  .run-log {
    display: flex;
    flex-direction: column;
    height: 100%;
    border: 1px solid var(--color-border, #e2e8f0);
    border-radius: 8px;
    background: var(--color-bg, #ffffff);
    overflow: hidden;
  }

  .run-log.disconnected {
    opacity: 0.85;
  }

  .log-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid var(--color-border, #e2e8f0);
    background: var(--color-bg-secondary, #f8fafc);
    flex-shrink: 0;
  }

  .log-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    font-size: 14px;
    color: var(--color-text, #1e293b);
  }

  .run-badge {
    font-family: monospace;
    font-size: 11px;
    background: var(--color-accent, #e0e7ff);
    color: var(--color-accent-text, #3730a3);
    padding: 2px 6px;
    border-radius: 4px;
    font-weight: 500;
  }

  .log-status {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--color-text-muted, #94a3b8);
  }

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
  }
  .dot.live {
    background: #22c55e;
    animation: pulse-dot 1.5s infinite;
  }
  .dot.disconnected {
    background: #94a3b8;
  }
  @keyframes pulse-dot {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  .entry-count {
    margin-left: 8px;
    padding-left: 8px;
    border-left: 1px solid var(--color-border, #e2e8f0);
  }

  .log-entries {
    flex: 1;
    overflow-y: auto;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .log-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 40px;
    color: var(--color-text-muted, #94a3b8);
    font-size: 14px;
    text-align: center;
  }

  .log-empty p {
    font-size: 12px;
    margin: 0;
  }

  .spin {
    animation: spin 1s linear infinite;
  }
  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  .log-entry {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 8px 10px;
    border-radius: 6px;
    background: var(--color-bg-secondary, #f8fafc);
    border-left: 3px solid var(--color-border, #e2e8f0);
    font-size: 13px;
  }

  .log-entry.event-started {
    border-left-color: #3b82f6;
    background: #eff6ff;
  }
  .log-entry.event-completed {
    border-left-color: #22c55e;
    background: #f0fdf4;
  }
  .log-entry.event-failed {
    border-left-color: #ef4444;
    background: #fef2f2;
  }
  .log-entry.event-checkpoint {
    border-left-color: #f59e0b;
    background: #fffbeb;
  }

  .entry-icon {
    flex-shrink: 0;
    margin-top: 1px;
    color: var(--color-text-muted, #94a3b8);
  }
  .event-started .entry-icon { color: #3b82f6; }
  .event-completed .entry-icon { color: #22c55e; }
  .event-failed .entry-icon { color: #ef4444; }
  .event-checkpoint .entry-icon { color: #f59e0b; }

  .entry-body {
    flex: 1;
    min-width: 0;
  }

  .entry-title {
    font-weight: 500;
    color: var(--color-text, #1e293b);
    line-height: 1.4;
    word-break: break-word;
  }

  .entry-details {
    margin-top: 4px;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .detail-row {
    display: flex;
    gap: 8px;
    font-size: 11px;
  }

  .detail-key {
    color: var(--color-text-muted, #94a3b8);
    font-family: monospace;
    flex-shrink: 0;
    text-transform: capitalize;
  }

  .detail-value {
    color: var(--color-text-secondary, #64748b);
    word-break: break-word;
  }

  .entry-time {
    flex-shrink: 0;
    font-size: 11px;
    color: var(--color-text-muted, #94a3b8);
    font-family: monospace;
    white-space: nowrap;
  }
</style>
