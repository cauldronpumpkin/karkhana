<script>
  let { variant = 'primary', size = 'sm', children } = $props();
</script>

<span class="badge badge-{variant} badge-{size}">
  {@render children?.()}
</span>

<style>
  .badge {
    align-items: center;
    border: 1px solid currentColor;
    border-radius: var(--border-radius-sm);
    display: inline-flex;
    font-family: var(--font-mono);
    font-weight: 700;
    gap: 6px;
    line-height: 1;
    text-transform: uppercase;
    white-space: nowrap;
  }

  .badge-sm {
    font-size: 0.66rem;
    padding: 5px 7px;
  }

  .badge-md {
    font-size: 0.75rem;
    padding: 7px 10px;
  }

  .badge-lg {
    font-size: 0.86rem;
    padding: 9px 12px;
  }

  .badge-primary {
    background: rgba(0, 120, 255, 0.13);
    color: #36a7ff;
  }

  .badge-accent {
    background: rgba(0, 240, 255, 0.12);
    color: var(--color-accent);
  }

  .badge-success {
    background: rgba(82, 245, 106, 0.12);
    color: var(--color-success);
  }

  .badge-warning {
    background: rgba(255, 159, 28, 0.13);
    color: var(--color-warning);
  }

  .badge-error {
    background: rgba(255, 61, 79, 0.13);
    color: var(--color-error);
  }

  .badge-muted {
    background: rgba(115, 130, 145, 0.1);
    color: var(--color-text-muted);
  }
</style>
