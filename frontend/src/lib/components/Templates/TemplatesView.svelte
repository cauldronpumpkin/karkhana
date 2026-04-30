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

  function asList(value) {
    return Array.isArray(value) ? value.filter((item) => item !== null && item !== undefined && `${item}`.trim() !== '') : [];
  }

  function asText(value, fallback = 'n/a') {
    if (value === null || value === undefined || value === '') return fallback;
    return typeof value === 'object' ? JSON.stringify(value) : String(value);
  }

  function joinList(value, fallback = 'n/a') {
    const items = asList(value).map((item) => (typeof item === 'string' ? item : asText(item)));
    return items.length ? items.join(' + ') : fallback;
  }

  function pickFirst(...values) {
    for (const value of values) {
      if (Array.isArray(value) && value.length) return value;
      if (value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length) return value;
      if (typeof value === 'string' && value.trim()) return value;
      if (typeof value === 'number' && Number.isFinite(value)) return value;
      if (typeof value === 'boolean') return value;
    }
    return null;
  }

  function listPreview(items, limit = 3) {
    return asList(items).slice(0, limit);
  }

  function formatFieldValue(value) {
    if (Array.isArray(value)) return value.join(', ');
    if (value && typeof value === 'object') return JSON.stringify(value);
    return asText(value);
  }

  function collectPackStatus(pack) {
    return pickFirst(pack.status, pack.review_metadata?.status, pack.manifest?.status, pack.manifest?.validation_state) || 'unknown';
  }

  function collectPackChannel(pack) {
    return pickFirst(pack.channel, pack.review_metadata?.channel, pack.manifest?.channel) || 'unknown';
  }

  function collectStack(pack) {
    const stack = pack.manifest?.stack || {};
    const stackName = pickFirst(stack.name, stack.framework, pack.default_stack?.stack, pack.default_stack?.framework);
    return joinList(stackName, 'n/a');
  }

  function collectCapabilities(pack) {
    return [
      ...asList(pack.manifest?.capabilities),
      ...asList(pack.manifest?.required_capabilities),
      ...asList(pack.review_metadata?.capabilities),
      ...asList(pack.opencode_worker?.required_capabilities)
    ];
  }

  function collectModules(pack) {
    return [
      ...asList(pack.manifest?.modules),
      ...asList(pack.manifest?.files_or_modules),
      ...asList(pack.review_metadata?.modules),
      ...asList(pack.opencode_worker?.modules)
    ];
  }

  function collectContextCards(pack) {
    return asList(pack.manifest?.context_cards || pack.context_cards || pack.artifact_refs);
  }

  function collectValidation(pack) {
    return pickFirst(pack.validation, pack.manifest?.validation, pack.review_metadata?.validation);
  }

  function collectPromotion(pack) {
    return pickFirst(pack.promotion, pack.manifest?.promotion, pack.review_metadata?.promotion);
  }

  function collectTokenProfile(pack) {
    return pickFirst(pack.token_profile, pack.manifest?.token_profile, pack.review_metadata?.token_profile);
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
        Read-only packs with normalized manifests, guardrails, verification commands, and context-card telemetry.
      </p>
    </div>
    <div class="hero-metrics">
      <div>
        <strong>{packs.length}</strong>
        <span>Packs seeded</span>
      </div>
      <div>
        <strong>{packs.length ? collectPackChannel(packs[0]) : 'n/a'}</strong>
        <span>Primary channel</span>
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
            <div class="header-pills">
              <div class="version-pill">{collectPackStatus(pack)}</div>
              <div class="version-pill">{collectPackChannel(pack)}</div>
              <div class="version-pill">v{pack.version}</div>
            </div>
          </div>

          <div class="detail-row">
            <div>
              <span>Stack</span>
              <strong>{collectStack(pack)}</strong>
            </div>
            <div>
              <span>Package manager</span>
              <strong>{pack.manifest?.stack?.package_manager || pack.default_stack?.package_manager || 'pnpm'}</strong>
            </div>
            <div>
              <span>Schema</span>
              <strong>{pack.manifest?.schema_version || 'n/a'}</strong>
            </div>
            <div>
              <span>Context cards</span>
              <strong>{collectContextCards(pack).length}</strong>
            </div>
          </div>

          <section>
            <h3>Capabilities</h3>
            {#if collectCapabilities(pack).length}
              <div class="pill-group">
                {#each collectCapabilities(pack) as capability}
                  <span class="pill">{capability}</span>
                {/each}
              </div>
            {:else}
              <p class="empty-inline">No capabilities declared.</p>
            {/if}
          </section>

          <section>
            <h3>Modules</h3>
            {#if collectModules(pack).length}
              <div class="pill-group">
                {#each collectModules(pack) as module}
                  <span class="pill">{module}</span>
                {/each}
              </div>
            {:else}
              <p class="empty-inline">No modules declared.</p>
            {/if}
          </section>

          <section>
            <div class="section-head">
              <h3>Context cards</h3>
              <span>{collectContextCards(pack).length} cards</span>
            </div>
            {#if collectContextCards(pack).length}
              <div class="context-grid">
                {#each listPreview(collectContextCards(pack), 4) as artifact}
                  <article class="context-card">
                    <strong>{artifact.key || artifact.artifact_key || 'card'}</strong>
                    <small>{artifact.kind || artifact.content_type || 'card'} &middot; {artifact.path || artifact.uri || 'n/a'}</small>
                  </article>
                {/each}
              </div>
              {#if collectContextCards(pack).length > 4}
                <p class="preview-note">+ {collectContextCards(pack).length - 4} more cards</p>
              {/if}
            {:else}
              <p class="empty-inline">No context cards available.</p>
            {/if}
          </section>

          {#if collectValidation(pack) || collectPromotion(pack) || collectTokenProfile(pack)}
            <section class="detail-grid">
              {#if collectValidation(pack)}
                <article>
                  <h3>Validation</h3>
                  {#each Object.entries(collectValidation(pack)) as [key, value]}
                    <div class="field-row">
                      <span>{key}</span>
                      <strong>{formatFieldValue(value)}</strong>
                    </div>
                  {/each}
                </article>
              {/if}
              {#if collectPromotion(pack)}
                <article>
                  <h3>Promotion</h3>
                  {#each Object.entries(collectPromotion(pack)) as [key, value]}
                    <div class="field-row">
                      <span>{key}</span>
                      <strong>{formatFieldValue(value)}</strong>
                    </div>
                  {/each}
                </article>
              {/if}
              {#if collectTokenProfile(pack)}
                <article>
                  <h3>Token profile</h3>
                  {#each Object.entries(collectTokenProfile(pack)) as [key, value]}
                    <div class="field-row">
                      <span>{key}</span>
                      <strong>{formatFieldValue(value)}</strong>
                    </div>
                  {/each}
                </article>
              {/if}
            </section>
          {/if}

          <section>
            <h3>Required tools</h3>
            <div class="pill-group">
              {#each asList(pack.required_tools) as tool}
                <span class="pill">{tool}</span>
              {/each}
            </div>
          </section>

          <section>
            <h3>Verification</h3>
            <ul>
              {#each asList(pack.verification_commands) as command}
                <li>{command}</li>
              {/each}
            </ul>
          </section>

          <section>
            <h3>Artifact refs</h3>
            <div class="artifact-grid">
              {#each asList(pack.artifact_refs) as artifact}
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
                {#each asList(pack.graphify_expectations?.read_before_task) as item}
                  <li>{item}</li>
                {/each}
                {#each asList(pack.graphify_expectations?.refresh_after_task) as item}
                  <li>{item}</li>
                {/each}
              </ul>
            </div>
            <div>
              <h3>Guardrails</h3>
              <ul>
                {#each asList(pack.guardrails) as item}
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

  .header-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: flex-end;
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

  .section-head {
    align-items: baseline;
    display: flex;
    gap: 10px;
    justify-content: space-between;
  }

  .section-head span,
  .preview-note,
  .empty-inline {
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.72rem;
    margin: 0;
  }

  .context-grid,
  .detail-grid {
    display: grid;
    gap: 10px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .context-card,
  .detail-grid article {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(103, 128, 151, 0.14);
    border-radius: 14px;
    padding: 12px;
  }

  .context-card strong,
  .field-row strong {
    display: block;
    line-height: 1.2;
    word-break: break-word;
  }

  .context-card small {
    color: var(--color-text-secondary);
    display: block;
    font-size: 0.72rem;
    margin-top: 4px;
    word-break: break-word;
  }

  .field-row + .field-row {
    margin-top: 8px;
  }

  .field-row span {
    color: var(--color-text-muted);
    display: block;
    font-family: var(--font-mono);
    font-size: 0.65rem;
    text-transform: uppercase;
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
    .two-col,
    .context-grid,
    .detail-grid {
      grid-template-columns: 1fr;
      flex-direction: column;
    }

    .hero {
      align-items: start;
    }

    .pack-header {
      flex-direction: column;
    }

    .header-pills {
      justify-content: flex-start;
    }
  }
</style>
