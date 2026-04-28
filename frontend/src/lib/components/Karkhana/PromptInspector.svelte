<script>
  import { CheckCircle2, ChevronDown, ChevronRight, Clipboard } from 'lucide-svelte';

  let { label = 'Prompt', prompt = '' } = $props();

  let isExpanded = $state(false);
  let copied = $state(false);

  async function copyPrompt() {
    if (!prompt) return;
    await navigator.clipboard?.writeText(prompt);
    copied = true;
    setTimeout(() => copied = false, 1600);
  }

  function toggle() {
    isExpanded = !isExpanded;
  }
</script>

{#if prompt}
  <div class="prompt-inspector">
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div class="prompt-header" role="button" tabindex="0" onclick={toggle} onkeydown={(e) => e.key === 'Enter' && toggle()}>
      <span class="prompt-label">
        {#if isExpanded}<ChevronDown size={13} />{:else}<ChevronRight size={13} />{/if}
        {label}
      </span>
      <button class="copy-btn" onclick={(e) => { e.stopPropagation(); copyPrompt(); }} title="Copy prompt to clipboard">
        {#if copied}
          <CheckCircle2 size={13} />
        {:else}
          <Clipboard size={13} />
        {/if}
        {copied ? 'Copied' : 'Copy'}
      </button>
    </div>
    {#if isExpanded}
      <pre class="prompt-body">{prompt}</pre>
    {/if}
  </div>
{/if}

<style>
  .prompt-inspector {
    background: rgba(3, 6, 10, 0.7);
    border: 1px solid rgba(103, 128, 151, 0.2);
    border-radius: var(--border-radius-sm);
    margin-top: 8px;
    overflow: hidden;
  }

  .prompt-header {
    align-items: center;
    background: transparent;
    border: 0;
    color: var(--color-text-secondary);
    cursor: pointer;
    display: flex;
    font-size: 0.78rem;
    gap: 8px;
    justify-content: space-between;
    padding: 8px 10px;
    width: 100%;
  }

  .prompt-header:hover {
    background: rgba(0, 120, 255, 0.04);
  }

  .prompt-label {
    align-items: center;
    display: inline-flex;
    gap: 5px;
    font-family: var(--font-mono);
    font-size: 0.72rem;
    text-transform: uppercase;
  }

  .copy-btn {
    align-items: center;
    background: rgba(0, 120, 255, 0.08);
    border: 1px solid rgba(0, 120, 255, 0.2);
    border-radius: var(--border-radius-sm);
    color: var(--color-accent);
    cursor: pointer;
    display: inline-flex;
    font-family: var(--font-mono);
    font-size: 0.68rem;
    gap: 4px;
    padding: 3px 8px;
  }

  .copy-btn:hover {
    background: rgba(0, 120, 255, 0.16);
  }

  .prompt-body {
    background: rgba(0, 0, 0, 0.3);
    border-top: 1px solid rgba(103, 128, 151, 0.14);
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.72rem;
    line-height: 1.5;
    margin: 0;
    max-height: 340px;
    overflow-y: auto;
    padding: 10px;
    white-space: pre-wrap;
    word-break: break-word;
  }
</style>
