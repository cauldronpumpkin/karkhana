<script>
  import { X } from 'lucide-svelte';

  let { title = '', showClose = true, onclose, children } = $props();

  function handleClose() {
    onclose?.();
  }
</script>

<div
  class="modal-overlay"
  role="presentation"
  onclick={handleClose}
  onkeydown={(event) => event.key === 'Escape' && handleClose()}
>
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <section class="modal" onclick={(e) => e.stopPropagation()}>
    <header class="modal-header">
      {#if title}
        <div>
          <span class="modal-kicker"><span class="status-dot"></span> Command module</span>
          <h2 class="modal-title">{title}</h2>
        </div>
      {/if}
      {#if showClose}
        <button class="modal-close" onclick={handleClose} aria-label="Close modal">
          <X size={18} />
        </button>
      {/if}
    </header>
    <div class="modal-content">
      {@render children?.()}
    </div>
  </section>
</div>

<style>
  .modal-overlay {
    align-items: center;
    backdrop-filter: blur(14px);
    background:
      radial-gradient(circle at 50% 10%, rgba(0, 120, 255, 0.18), transparent 40%),
      rgba(0, 0, 0, 0.72);
    bottom: 0;
    display: flex;
    justify-content: center;
    left: 0;
    padding: var(--spacing-lg);
    position: fixed;
    right: 0;
    top: 0;
    z-index: 1000;
  }

  .modal {
    background: linear-gradient(180deg, rgba(9, 16, 23, 0.98), rgba(4, 8, 13, 0.98));
    border: 1px solid var(--color-border-strong);
    border-radius: var(--border-radius-lg);
    box-shadow: var(--shadow-md), 0 0 44px rgba(0, 120, 255, 0.18);
    max-height: 86vh;
    max-width: 640px;
    overflow-y: auto;
    padding: var(--spacing-lg);
    width: min(92vw, 640px);
  }

  .modal-header {
    align-items: flex-start;
    border-bottom: 1px solid var(--color-border);
    display: flex;
    justify-content: space-between;
    margin-bottom: var(--spacing-lg);
    padding-bottom: var(--spacing-md);
  }

  .modal-kicker {
    align-items: center;
    color: var(--color-text-secondary);
    display: inline-flex;
    font-family: var(--font-mono);
    font-size: 0.68rem;
    gap: 7px;
    text-transform: uppercase;
  }

  .modal-title {
    color: var(--color-text);
    font-size: 1.35rem;
    font-weight: 700;
    margin: 6px 0 0;
  }

  .modal-close {
    background: rgba(255, 255, 255, 0.03);
    border-color: var(--color-border);
    min-height: 34px;
    padding: 7px;
  }

  .modal-content {
    color: var(--color-text);
  }
</style>
