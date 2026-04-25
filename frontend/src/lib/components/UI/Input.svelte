<script>
  let {
    label = '',
    type = 'text',
    value = $bindable(''),
    placeholder = '',
    required = false,
    disabled = false,
    id = ''
  } = $props();

  let inputEl;
</script>

<div class="input-container">
  {#if label}
    <label class="input-label" for={id}>
      {label}
      {#if required}
        <span class="required">*</span>
      {/if}
    </label>
  {/if}
  <input
    {id}
    bind:this={inputEl}
    {type}
    bind:value
    class="input-field"
    {placeholder}
    {disabled}
  />
</div>

<style>
  .input-container {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
  }

  .input-label {
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.72rem;
    text-transform: uppercase;
  }

  .required {
    color: var(--color-error);
  }

  .input-field {
    width: 100%;
  }

  .input-field:disabled {
    cursor: not-allowed;
    opacity: 0.5;
  }
</style>
