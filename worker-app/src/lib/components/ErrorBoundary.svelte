<script>
  /**
   * ErrorBoundary — Svelte 5 compatible.
   * Catches runtime errors via $effect + window error listener.
   *
   * NOTE: Svelte 5 does not have a built-in render-error boundary (no `onerror`
   * lifecycle). This component catches errors in event handlers and async code,
   * and registers a global window error handler. For true render-error catching,
   * wrap in try/catch at the parent level or use <svelte:window onerror>.
   */
  let { children } = $props()
  let caughtError = $state(null)

  function reset() {
    caughtError = null
  }

  // Register a global handler so unhandled errors show the fallback UI
  $effect(() => {
    function handler(event) {
      const message = event?.message ?? event?.toString?.() ?? 'Unknown error'
      caughtError = message
    }
    if (typeof window !== 'undefined') {
      window.addEventListener('error', handler)
      return () => window.removeEventListener('error', handler)
    }
  })
</script>

{#if caughtError}
  <div class="error-boundary">
    <div class="error-boundary-content">
      <h2>Something went wrong</h2>
      <p class="error-message">{caughtError}</p>
      <button onclick={reset}>Retry</button>
    </div>
  </div>
{:else}
  {@render children?.()}
{/if}

<style>
  .error-boundary {
    border: 2px solid var(--color-error, #e74c3c);
    border-radius: var(--border-radius-md, 8px);
    padding: 24px;
    margin: 16px 0;
    background: rgba(231, 76, 60, 0.08);
  }

  .error-boundary-content {
    text-align: center;
  }

  .error-boundary-content h2 {
    margin: 0 0 12px 0;
    color: var(--color-error, #e74c3c);
    font-size: 1.1rem;
    font-weight: 700;
  }

  .error-message {
    color: var(--color-error, #c0392b);
    font-family: var(--font-mono, monospace);
    font-size: 0.9rem;
    margin-bottom: 16px;
    padding: 8px 12px;
    background: rgba(0, 0, 0, 0.05);
    border-radius: var(--border-radius-sm, 4px);
    word-break: break-word;
    text-align: left;
    white-space: pre-wrap;
  }

  .error-boundary-content button {
    padding: 8px 20px;
    border: 1px solid var(--color-error, #e74c3c);
    border-radius: var(--border-radius-sm, 4px);
    background: transparent;
    color: var(--color-error, #e74c3c);
    cursor: pointer;
    font-size: 0.85rem;
    font-weight: 600;
    transition: background 0.15s ease, color 0.15s ease;
  }

  .error-boundary-content button:hover {
    background: var(--color-error, #e74c3c);
    color: #fff;
  }
</style>
