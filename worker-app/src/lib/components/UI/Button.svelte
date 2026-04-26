<script>
  let {
    variant = 'primary',
    size = 'md',
    disabled = false,
    type = 'button',
    onclick,
    children
  } = $props();
</script>

<button
  class="button button-{variant} button-{size}"
  {type}
  {disabled}
  {onclick}
>
  {@render children?.()}
</button>

<style>
  .button {
    white-space: nowrap;
  }

  .button-sm {
    font-size: 0.8rem;
    min-height: 32px;
    padding: 7px 10px;
  }

  .button-lg {
    font-size: 1rem;
    min-height: 46px;
    padding: 12px 18px;
  }

  .button-secondary {
    background: rgba(7, 13, 19, 0.9);
    border-color: var(--color-border);
    color: var(--color-text);
  }

  .button-ghost {
    background: transparent;
    border-color: rgba(109, 127, 146, 0.26);
    color: var(--color-text-secondary);
  }

  .button-danger {
    background: linear-gradient(180deg, rgba(255, 61, 79, 0.92), rgba(157, 25, 40, 0.92));
    border-color: rgba(255, 100, 113, 0.55);
  }

  .button-warning {
    background: linear-gradient(180deg, rgba(255, 159, 28, 0.92), rgba(177, 94, 7, 0.92));
    border-color: rgba(255, 183, 77, 0.55);
  }
</style>
