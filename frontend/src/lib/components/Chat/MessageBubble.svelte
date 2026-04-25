<script>
  import {
    Bot,
    Clipboard,
    Code2,
    Copy,
    ThumbsDown,
    ThumbsUp,
    UserRound
  } from 'lucide-svelte';
  import MarkdownRenderer from './MarkdownRenderer.svelte';

  let { message = {
    id: '',
    role: 'user',
    content: '',
    timestamp: new Date(),
    isStreaming: false
  }, showTimestamp = false } = $props();

  let isUser = $derived(message.role === 'user');
  let roleLabel = $derived(isUser ? 'You' : 'AI Cofounder');
  let formattedTime = $derived(formatTime(message.timestamp));

  function formatTime(value) {
    const date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) return '';

    return date.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit'
    });
  }
</script>

<article class="message-bubble" class:user={isUser} class:assistant={!isUser}>
  <div class="avatar" aria-hidden="true">
    {#if isUser}
      <UserRound size={18} />
    {:else}
      <Bot size={19} />
    {/if}
  </div>

  <div class="message-content">
    <div class="message-meta">
      <span class="message-role">{roleLabel}</span>
      {#if showTimestamp && formattedTime}
        <span class="message-time">{formattedTime}</span>
      {/if}
    </div>
    
    <div class="message-text">
      {#if message.isStreaming}
        <div class="streaming-indicator" aria-label="Assistant is writing">
          <span class="dot"></span>
          <span class="dot"></span>
          <span class="dot"></span>
        </div>
      {/if}

      {#if isUser}
        <p>{message.content}</p>
      {:else}
        <MarkdownRenderer content={message.content} />
      {/if}
    </div>

    {#if !isUser}
      <div class="message-actions" aria-label="Message actions">
        <button type="button" aria-label="Copy response">
          <Copy size={14} aria-hidden="true" />
        </button>
        <button type="button" aria-label="Mark helpful">
          <ThumbsUp size={14} aria-hidden="true" />
        </button>
        <button type="button" aria-label="Mark not helpful">
          <ThumbsDown size={14} aria-hidden="true" />
        </button>
        <button type="button" aria-label="Generate build snippet">
          <Code2 size={14} aria-hidden="true" />
        </button>
        <button type="button" aria-label="Save to notes">
          <Clipboard size={14} aria-hidden="true" />
        </button>
      </div>
    {/if}
  </div>
</article>

<style>
  .message-bubble {
    animation: fadeIn 0.24s ease;
    display: grid;
    gap: var(--spacing-sm);
    grid-template-columns: 36px minmax(0, 1fr);
    max-width: min(860px, 100%);
  }

  .message-bubble.user {
    margin-left: auto;
    max-width: min(760px, 92%);
  }

  .message-bubble.assistant {
    margin-right: auto;
    width: 100%;
  }

  .avatar {
    align-items: center;
    background: rgba(7, 13, 19, 0.92);
    border: 1px solid var(--color-border);
    border-radius: 50%;
    color: var(--color-text-secondary);
    display: flex;
    height: 32px;
    justify-content: center;
    margin-top: 2px;
    width: 32px;
  }

  .assistant .avatar {
    border-color: rgba(0, 240, 255, 0.45);
    color: var(--color-accent);
  }

  .user .avatar {
    color: var(--color-text);
  }

  .message-content {
    min-width: 0;
  }

  .message-meta {
    align-items: center;
    display: flex;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-xs);
  }

  .message-role {
    color: var(--color-text);
    font-weight: 700;
  }

  .assistant .message-role {
    color: var(--color-success);
  }

  .message-time {
    color: var(--color-text-muted);
    font-family: var(--font-mono);
    font-size: 0.76rem;
  }

  .message-text {
    border-radius: var(--border-radius-md);
    color: var(--color-text);
    line-height: 1.6;
    overflow-wrap: anywhere;
  }

  .message-text :global(p:first-child) {
    margin-top: 0;
  }

  .message-text :global(p:last-child) {
    margin-bottom: 0;
  }

  .message-text p {
    margin: 0;
  }

  .user .message-text {
    background: rgba(0, 120, 255, 0.12);
    border: 1px solid rgba(0, 120, 255, 0.28);
    padding: var(--spacing-md);
  }

  .assistant .message-text {
    background: transparent;
    border-left: 1px solid rgba(103, 128, 151, 0.3);
    padding: var(--spacing-sm) 0 var(--spacing-sm) var(--spacing-md);
  }

  .message-actions {
    display: flex;
    gap: var(--spacing-xs);
    margin-top: var(--spacing-sm);
  }

  .message-actions button {
    align-items: center;
    background: transparent;
    border: 1px solid transparent;
    border-radius: var(--border-radius-sm);
    color: var(--color-text-muted);
    cursor: pointer;
    display: inline-flex;
    height: 28px;
    justify-content: center;
    padding: 0;
    width: 28px;
  }

  .message-actions button:hover {
    border-color: var(--color-border);
    color: var(--color-text);
  }

  .streaming-indicator {
    display: inline-flex;
    gap: var(--spacing-xs);
    margin-right: var(--spacing-sm);
    vertical-align: middle;
  }

  .dot {
    animation: pulse 1.5s infinite;
    background-color: var(--color-accent);
    border-radius: 50%;
    height: 6px;
    width: 6px;
  }

  .dot:nth-child(2) {
    animation-delay: 0.3s;
  }

  .dot:nth-child(3) {
    animation-delay: 0.6s;
  }

  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @keyframes pulse {
    0%, 100% {
      opacity: 1;
    }
    50% {
      opacity: 0.3;
    }
  }

  @media (max-width: 640px) {
    .message-bubble,
    .message-bubble.user {
      grid-template-columns: 30px minmax(0, 1fr);
      max-width: 100%;
    }

    .avatar {
      height: 28px;
      width: 28px;
    }
  }
</style>
