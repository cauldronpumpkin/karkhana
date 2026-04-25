<script>
  import Bot from 'lucide-svelte/icons/bot';
  import MessageBubble from './MessageBubble.svelte';

  let { messages = [], showTimestamps = false, autoScroll = true } = $props();

  let messagesEnd;

  $effect(() => {
    if (autoScroll && messagesEnd) {
      messages; // track messages changes
      messagesEnd.scrollIntoView({ behavior: 'smooth' });
    }
  });
</script>

<div class="message-list">
  {#if messages.length === 0}
    <div class="empty-state">
      <Bot size={22} aria-hidden="true" />
      <strong>Start refining this idea</strong>
      <p>Ask for market validation, sharper positioning, scoring, or a build handoff.</p>
    </div>
  {:else}
    {#each messages as message (message.id)}
      <MessageBubble 
        {message} 
        showTimestamp={showTimestamps} 
      />
    {/each}
  {/if}
  <div bind:this={messagesEnd}></div>
</div>

<style>
  .message-list {
    display: flex;
    flex: 1;
    flex-direction: column;
    gap: var(--spacing-md);
    height: 100%;
    overflow-y: auto;
    padding: var(--spacing-lg);
    scrollbar-color: var(--color-border) transparent;
    scrollbar-width: thin;
  }

  .message-list::-webkit-scrollbar {
    width: 6px;
  }

  .message-list::-webkit-scrollbar-track {
    background: transparent;
  }

  .message-list::-webkit-scrollbar-thumb {
    background-color: var(--color-border);
    border-radius: var(--border-radius-sm);
  }

  .message-list::-webkit-scrollbar-thumb:hover {
    background-color: var(--color-text-secondary);
  }

  .empty-state {
    align-items: center;
    border: 1px dashed rgba(103, 128, 151, 0.34);
    border-radius: var(--border-radius-lg);
    color: var(--color-text-secondary);
    display: grid;
    gap: var(--spacing-xs);
    justify-items: center;
    margin: auto;
    max-width: 360px;
    padding: var(--spacing-xl);
    text-align: center;
  }

  .empty-state strong {
    color: var(--color-text);
    font-size: 1rem;
  }

  .empty-state p {
    line-height: 1.5;
    margin: 0;
  }
</style>
