<script>
  import { AtSign, Bot, Paperclip, SendHorizontal, Search } from 'lucide-svelte';

  let {
    value = $bindable(''),
    placeholder = 'Ask anything about your idea...',
    disabled = false,
    providers = [],
    selectedProvider = '',
    selectedModel = '',
    onmodelChange,
    onsend
  } = $props();

  function handleModelChange(event) {
    const [provider, model] = event.currentTarget.value.split('::');
    onmodelChange?.({ provider, model });
  }

  function submit() {
    const content = value.trim();
    if (!content || disabled) return;
    onsend?.(content);
    value = '';
  }

  function handleKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }
</script>

<form class="chat-input" onsubmit={(event) => { event.preventDefault(); submit(); }}>
  <div class="composer-shell">
    <div class="prompt-caret" aria-hidden="true">&gt;_</div>
    <textarea
      bind:value
      {placeholder}
      {disabled}
      rows="3"
      onkeydown={handleKeydown}
      aria-label="Message"
    ></textarea>

    <div class="composer-actions">
      <button type="button" class="tool-button" disabled={disabled}>
        <Paperclip size={15} />
        Attach
      </button>
      <button type="button" class="tool-button" disabled={disabled}>
        <Search size={15} />
        Research
      </button>
      <button type="button" class="tool-button" disabled={disabled}>
        <AtSign size={15} />
        Add context
      </button>
      <label class="model-pill">
        <Bot size={14} />
        <select
          aria-label="AI model"
          disabled={disabled || providers.length === 0}
          value={`${selectedProvider}::${selectedModel}`}
          onchange={handleModelChange}
        >
          {#if providers.length === 0}
            <option value="::">Loading models</option>
          {:else}
            {#each providers as provider}
              {#each provider.models as model}
                <option value={`${provider.id}::${model}`}>
                  {provider.name} / {model}
                </option>
              {/each}
            {/each}
          {/if}
        </select>
      </label>
      <button class="send-button" type="submit" disabled={disabled || !value.trim()} aria-label="Send message">
        <SendHorizontal size={17} />
      </button>
    </div>
  </div>
</form>

<style>
  .chat-input {
    margin: 0;
  }

  .composer-shell {
    background:
      linear-gradient(180deg, rgba(6, 12, 18, 0.98), rgba(3, 7, 12, 0.96)),
      radial-gradient(circle at 15% 0%, rgba(0, 120, 255, 0.14), transparent 38%);
    border: 1px solid rgba(0, 120, 255, 0.78);
    border-radius: var(--border-radius-lg);
    box-shadow: 0 0 0 1px rgba(0, 240, 255, 0.12), 0 0 26px rgba(0, 120, 255, 0.2);
    display: grid;
    gap: var(--spacing-sm);
    grid-template-columns: auto minmax(0, 1fr);
    padding: var(--spacing-md);
  }

  .prompt-caret {
    color: var(--color-accent);
    font-family: var(--font-mono);
    font-size: 1rem;
    padding-top: 3px;
  }

  textarea {
    background: transparent;
    border: 0;
    box-shadow: none;
    min-height: 78px;
    padding: 0;
    resize: none;
    width: 100%;
  }

  textarea:focus {
    border: 0;
    box-shadow: none;
  }

  .composer-actions {
    align-items: center;
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-sm);
    grid-column: 2;
  }

  .tool-button,
  .model-pill {
    align-items: center;
    background: rgba(0, 0, 0, 0.22);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-md);
    color: var(--color-text-secondary);
    display: inline-flex;
    font-size: 0.78rem;
    gap: 7px;
    min-height: 32px;
    padding: 7px 10px;
  }

  .tool-button:hover:not(:disabled) {
    color: var(--color-text);
  }

  .model-pill {
    margin-left: auto;
  }

  .model-pill select {
    appearance: none;
    background: transparent;
    border: 0;
    color: var(--color-text-secondary);
    cursor: pointer;
    font: inherit;
    max-width: min(46vw, 260px);
    outline: 0;
  }

  .model-pill select:disabled {
    cursor: not-allowed;
  }

  .model-pill option {
    background: #050a0f;
    color: var(--color-text);
  }

  .send-button {
    min-height: 34px;
    min-width: 42px;
    padding: 8px 10px;
  }

  @media (max-width: 640px) {
    .composer-shell {
      grid-template-columns: 1fr;
    }

    .prompt-caret {
      display: none;
    }

    .composer-actions {
      grid-column: 1;
    }

    .model-pill {
      margin-left: 0;
    }
  }
</style>
