<script>
  let { title = '', subtitle = '', padding = 'var(--spacing-lg)', border = true, children } = $props();
</script>

<section class="card" class:borderless={!border} style="padding: {padding};">
  {#if title || subtitle}
    <header class="card-header">
      {#if title}
        <h3 class="card-title">{title}</h3>
      {/if}
      {#if subtitle}
        <p class="card-subtitle">{subtitle}</p>
      {/if}
    </header>
  {/if}
  <div class="card-content">
    {@render children?.()}
  </div>
</section>

<style>
  .card {
    background:
      linear-gradient(180deg, rgba(10, 17, 24, 0.96), rgba(5, 10, 15, 0.94)),
      radial-gradient(circle at 100% 0%, rgba(0, 194, 255, 0.1), transparent 34%);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
    box-shadow: var(--shadow-sm);
    margin-bottom: var(--spacing-lg);
    overflow: hidden;
    position: relative;
  }

  .card::before {
    background: linear-gradient(90deg, transparent, rgba(0, 240, 255, 0.2), transparent);
    content: "";
    height: 1px;
    left: 0;
    opacity: 0.55;
    position: absolute;
    right: 0;
    top: 0;
  }

  .borderless {
    border: 0;
  }

  .card-header {
    border-bottom: 1px solid rgba(103, 128, 151, 0.2);
    margin: calc(var(--spacing-lg) * -1) calc(var(--spacing-lg) * -1) var(--spacing-md);
    padding: var(--spacing-md) var(--spacing-lg);
  }

  .card-title {
    color: var(--color-text);
    font-size: 1.05rem;
    font-weight: 700;
    margin: 0 0 var(--spacing-xs);
  }

  .card-subtitle {
    color: var(--color-text-secondary);
    font-size: 0.86rem;
    margin: 0;
  }

  .card-content {
    color: var(--color-text);
  }
</style>
