<script>
  import { onMount } from 'svelte';
  import { api } from '../../../lib/api.js';

  let packs = $state([]);
  let loading = $state(true);
  let error = $state('');

  async function loadTemplates() {
    loading = true;
    error = '';
    try {
      const response = await api('/api/templates');
      packs = response.template_packs || [];
    } catch (err) {
      error = err?.message || 'Failed to load template packs';
      packs = [];
    } finally {
      loading = false;
    }
  }

  onMount(loadTemplates);

  function formatList(value) {
    return Array.isArray(value) ? value : [];
  }
</script>

<svelte:head>
  <title>Templates | IdeaRefinery</title>
</svelte:head>

<section class="templates-page">
  <header class="hero">
    <div>
      <p class="eyebrow">Registry</p>
      <h1>Templates</h1>
      <p class="lede">
        Read-only built-in packs with normalized manifests, path guardrails, verification commands, and AGENTS hierarchy references.
      </p>
    </div>
    <div class="hero-metrics">
      <div>
        <strong>{packs.length}</strong>
        <span>Packs seeded</span>
      </div>
      <div>
        <strong>v0</strong>
        <span>Manifest schema</span>
      </div>
    </div>
  </header>

  {#if loading}
    <div class="state-card">Loading template registry...</div>
  {:else if error}
    <div class="state-card error">{error}</div>
  {:else}
    <div class="pack-grid">
      {#each packs as pack}
        <article class="pack-card">
          <div class="pack-header">
            <div>
              <p class="pack-id">{pack.template_id}</p>
              <h2>{pack.display_name}</h2>
              <p class="pack-desc">{pack.description}</p>
            </div>
            <div class="version-pill">v{pack.version}</div>
          </div>

          <div class="detail-row">
            <div>
              <span>Stack</span>
              <strong>{formatList(pack.manifest?.stack?.name).join(' + ') || formatList(pack.default_stack?.stack).join(' + ')}</strong>
            </div>
            <div>
              <span>Package manager</span>
              <strong>{pack.manifest?.stack?.package_manager || pack.default_stack?.package_manager || 'pnpm'}</strong>
            </div>
          </div>

          <div class="pill-group">
            {#each formatList(pack.required_tools) as tool}
              <span class="pill">{tool}</span>
            {/each}
          </div>

          <section>
            <h3>Verification</h3>
            <ul>
              {#each formatList(pack.verification_commands) as command}
                <li>{command}</li>
              {/each}
            </ul>
          </section>

          <section>
            <h3>Artifact refs</h3>
            <div class="artifact-grid">
              {#each formatList(pack.artifact_refs) as artifact}
                <div class="artifact-chip">
                  <strong>{artifact.key}</strong>
                  <span>{artifact.path}</span>
                </div>
              {/each}
            </div>
          </section>

          <section class="two-col">
            <div>
              <h3>Graphify</h3>
              <ul>
                {#each formatList(pack.graphify_expectations?.read_before_task) as item}
                  <li>{item}</li>
                {/each}
                {#each formatList(pack.graphify_expectations?.refresh_after_task) as item}
                  <li>{item}</li>
                {/each}
              </ul>
            </div>
            <div>
              <h3>Guardrails</h3>
              <ul>
                {#each formatList(pack.guardrails) as item}
                  <li>{item}</li>
                {/each}
              </ul>
            </div>
          </section>
        </article>
      {/each}
    </div>
  {/if}
</section>

<style>
  .templates-page {
    display: grid;
    gap: 20px;
  }

  .hero {
    align-items: end;
    background: radial-gradient(circle at top left, rgba(0, 174, 255, 0.18), transparent 40%), linear-gradient(135deg, rgba(7, 12, 18, 0.96), rgba(2, 5, 7, 0.98));
    border: 1px solid var(--color-border);
    border-radius: 22px;
    display: flex;
    justify-content: space-between;
    gap: 18px;
    padding: 24px;
  }

  .eyebrow {
    color: var(--color-success);
    font-family: var(--font-mono);
    letter-spacing: 0.12em;
    margin: 0 0 8px;
    text-transform: uppercase;
  }

  h1 {
    font-size: clamp(2rem, 4vw, 3.2rem);
    line-height: 1;
    margin: 0;
  }

  .lede {
    color: var(--color-text-secondary);
    max-width: 68ch;
    margin: 12px 0 0;
  }

  .hero-metrics {
    display: grid;
    gap: 12px;
    min-width: 170px;
  }

  .hero-metrics div,
  .state-card,
  .pack-card {
    background: rgba(4, 9, 14, 0.9);
    border: 1px solid var(--color-border);
    border-radius: 18px;
  }

  .hero-metrics div {
    padding: 14px 16px;
  }

  .hero-metrics strong {
    display: block;
    font-size: 1.6rem;
  }

  .hero-metrics span {
    color: var(--color-text-muted);
    font-family: var(--font-mono);
    font-size: 0.72rem;
    text-transform: uppercase;
  }

  .state-card {
    color: var(--color-text-secondary);
    padding: 18px 20px;
  }

  .state-card.error {
    color: var(--color-danger, #ff6b6b);
  }

  .pack-grid {
    display: grid;
    gap: 18px;
  }

  .pack-card {
    display: grid;
    gap: 18px;
    padding: 22px;
  }

  .pack-header {
    align-items: start;
    display: flex;
    justify-content: space-between;
    gap: 14px;
  }

  .pack-id {
    color: var(--color-success);
    font-family: var(--font-mono);
    font-size: 0.72rem;
    margin: 0 0 8px;
  }

  .pack-header h2 {
    margin: 0;
  }

  .pack-desc {
    color: var(--color-text-secondary);
    margin: 8px 0 0;
  }

  .version-pill {
    align-items: center;
    background: rgba(0, 174, 255, 0.12);
    border: 1px solid rgba(0, 174, 255, 0.25);
    border-radius: 999px;
    color: var(--color-text);
    display: inline-flex;
    font-family: var(--font-mono);
    font-size: 0.74rem;
    min-height: 30px;
    padding: 0 12px;
  }

  .detail-row,
  .two-col {
    display: grid;
    gap: 14px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .detail-row div {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(103, 128, 151, 0.14);
    border-radius: 14px;
    padding: 14px;
  }

  .detail-row span {
    color: var(--color-text-muted);
    display: block;
    font-family: var(--font-mono);
    font-size: 0.66rem;
    margin-bottom: 6px;
    text-transform: uppercase;
  }

  .detail-row strong {
    color: var(--color-text);
  }

  .pill-group,
  .artifact-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .pill,
  .artifact-chip {
    border-radius: 999px;
    display: inline-flex;
    font-family: var(--font-mono);
    font-size: 0.72rem;
    gap: 8px;
    padding: 8px 12px;
  }

  .pill {
    background: rgba(0, 240, 255, 0.08);
    border: 1px solid rgba(0, 240, 255, 0.2);
  }

  .artifact-chip {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(103, 128, 151, 0.14);
    align-items: center;
    color: var(--color-text-secondary);
  }

  .artifact-chip strong {
    color: var(--color-text);
  }

  section h3 {
    font-size: 0.9rem;
    margin: 0 0 10px;
  }

  ul {
    color: var(--color-text-secondary);
    margin: 0;
    padding-left: 18px;
  }

  li + li {
    margin-top: 6px;
  }

  @media (max-width: 960px) {
    .hero,
    .detail-row,
    .two-col {
      grid-template-columns: 1fr;
      flex-direction: column;
    }

    .hero {
      align-items: start;
    }
  }
</style>
