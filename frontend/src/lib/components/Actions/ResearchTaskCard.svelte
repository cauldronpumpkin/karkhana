<script>
  import {
    CheckCircle2,
    Clipboard,
    Clock3,
    ExternalLink,
    FileCheck2,
    FileText,
    Loader2,
    UploadCloud
  } from 'lucide-svelte';
  import { apiPost } from '../../api.js';
  import Badge from '../UI/Badge.svelte';
  import Button from '../UI/Button.svelte';

  let { ideaId = '', task, onupload, onintegrated } = $props();
  let isExpanded = $state(false);
  let isIntegrating = $state(false);
  let integration = $state(null);
  let integrationError = $state('');

  let promptText = $derived(task.prompt_text || task.prompt || '');
  let taskTitle = $derived(task.title || extractTitle(promptText));
  let createdLabel = $derived(formatDate(task.created_at));
  let completedLabel = $derived(formatDate(task.completed_at));
  let sourceLabel = $derived(task.result_file_path ? formatSource(task.result_file_path) : 'Awaiting evidence file');
  let isCompleted = $derived(task.status === 'completed');

  const getStatusVariant = (status) => {
    switch (status) {
      case 'pending': return 'warning';
      case 'submitted': return 'primary';
      case 'completed': return 'success';
      default: return 'primary';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'pending': return 'Pending';
      case 'submitted': return 'Submitted';
      case 'completed': return 'Completed';
      default: return status;
    }
  };

  function extractTitle(text) {
    const firstLine = text.split('\n').find((line) => line.trim()) || 'Research Task';
    return firstLine.replace(/^#+\s*/, '').slice(0, 86);
  }

  function formatDate(value) {
    if (!value) return 'Not recorded';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Not recorded';
    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  function formatSource(path) {
    const filename = String(path).split(/[\\/]/).filter(Boolean).pop();
    return filename || 'Evidence uploaded';
  }

  function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
      console.log('Copied to clipboard');
    }).catch(err => {
      console.error('Failed to copy:', err);
    });
  }

  function handleOpenFileUpload() {
    onupload?.(task);
  }

  async function integrateResearch() {
    if (!ideaId || !task.id || isIntegrating) return;
    isIntegrating = true;
    integrationError = '';
    try {
      const result = await apiPost(`/api/ideas/${ideaId}/research/${task.id}/integrate`);
      integration = result.integration;
    } catch (error) {
      integrationError = error.message || 'Integration failed.';
      console.error('Failed to integrate research:', error);
    } finally {
      isIntegrating = false;
    }
  }
</script>

<article class:completed={isCompleted} class="research-task-card">
  <div class="task-header">
    <div class="title-stack">
      <span class="mono-label">
        {#if isCompleted}
          <CheckCircle2 size={14} />
          Research complete
        {:else}
          <Clock3 size={14} />
          Evidence pending
        {/if}
      </span>
      <h3 class="task-title">{taskTitle}</h3>
    </div>
    <Badge variant={getStatusVariant(task.status)} size="sm">{getStatusText(task.status)}</Badge>
  </div>

  <div class="metadata-grid">
    <div>
      <span class="metadata-label">Created</span>
      <strong>{createdLabel}</strong>
    </div>
    <div>
      <span class="metadata-label">{isCompleted ? 'Completed' : 'Status'}</span>
      <strong>{isCompleted ? completedLabel : 'Open'}</strong>
    </div>
  </div>

  <div class="source-panel">
    <FileCheck2 size={17} />
    <div>
      <span class="metadata-label">Source / Evidence</span>
      <strong>{sourceLabel}</strong>
    </div>
  </div>

  <div class="prompt-container">
    <div class="prompt-header">
      <span class="mono-label"><FileText size={14} /> Research prompt</span>
      <Button size="sm" variant="ghost" onclick={() => isExpanded = !isExpanded}>
        {isExpanded ? 'Hide' : 'Show'}
      </Button>
    </div>

    {#if isExpanded}
      <div class="prompt-text">{promptText}</div>
    {:else}
      <p class="prompt-preview">{promptText}</p>
    {/if}
  </div>

  {#if integration}
    <div class="integration-panel">
      <span class="mono-label"><ExternalLink size={14} /> Integration summary</span>
      <p>{integration.summary}</p>
    </div>
  {/if}

  {#if integrationError}
    <div class="task-error" role="alert">{integrationError}</div>
  {/if}

  <div class="task-actions">
    {#if task.status === 'pending' || task.status === 'submitted'}
      <Button variant="primary" onclick={handleOpenFileUpload}>
        <UploadCloud size={16} />
        Upload Evidence
      </Button>
    {/if}

    {#if isCompleted}
      <Button variant="secondary" onclick={integrateResearch} disabled={isIntegrating}>
        {#if isIntegrating}
          <span class="spin"><Loader2 size={16} /></span>
          Integrating
        {:else}
          <CheckCircle2 size={16} />
          Integrate Research
        {/if}
      </Button>
    {/if}

    <Button variant="ghost" onclick={() => copyToClipboard(promptText)}>
      <Clipboard size={16} />
      Copy Prompt
    </Button>
  </div>
</article>

<style>
  .research-task-card {
    background:
      linear-gradient(180deg, rgba(9, 17, 25, 0.96), rgba(3, 8, 13, 0.94));
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
    min-height: 100%;
    overflow: hidden;
    padding: var(--spacing-md);
    position: relative;
  }

  .research-task-card::before {
    background: linear-gradient(180deg, var(--color-warning), transparent);
    content: "";
    left: 0;
    opacity: 0.78;
    position: absolute;
    top: 0;
    bottom: 0;
    width: 2px;
  }

  .research-task-card.completed::before {
    background: linear-gradient(180deg, var(--color-success), transparent);
  }

  .task-header {
    align-items: flex-start;
    display: flex;
    justify-content: space-between;
    gap: var(--spacing-md);
  }

  .title-stack {
    min-width: 0;
  }

  .task-title {
    color: var(--color-text);
    line-height: 1.25;
    margin: 7px 0 0;
    font-size: 1.125rem;
    overflow-wrap: anywhere;
  }

  .mono-label {
    align-items: center;
    display: inline-flex;
    gap: 7px;
  }

  .metadata-grid {
    display: grid;
    gap: var(--spacing-sm);
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .metadata-grid > div,
  .source-panel {
    background: rgba(255, 255, 255, 0.025);
    border: 1px solid rgba(103, 128, 151, 0.18);
    border-radius: var(--border-radius-md);
    padding: 10px 12px;
  }

  .metadata-label {
    color: var(--color-text-muted);
    display: block;
    font-family: var(--font-mono);
    font-size: 0.66rem;
    text-transform: uppercase;
  }

  .metadata-grid strong,
  .source-panel strong {
    color: var(--color-text);
    display: block;
    font-size: 0.88rem;
    font-weight: 600;
    margin-top: 3px;
    overflow-wrap: anywhere;
  }

  .source-panel {
    align-items: flex-start;
    color: var(--color-accent);
    display: flex;
    gap: 10px;
  }

  .prompt-container {
    border-top: 1px solid rgba(103, 128, 151, 0.18);
    padding-top: var(--spacing-md);
  }

  .prompt-header {
    align-items: center;
    display: flex;
    justify-content: space-between;
    margin-bottom: var(--spacing-sm);
  }

  .prompt-preview {
    color: var(--color-text-secondary);
    font-size: 0.875rem;
    line-height: 1.55;
    margin: 0;
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
  }

  .prompt-text {
    background:
      linear-gradient(180deg, rgba(0, 120, 255, 0.08), rgba(0, 0, 0, 0.18)),
      var(--color-bg);
    border: 1px solid rgba(0, 240, 255, 0.16);
    border-radius: var(--border-radius-sm);
    padding: var(--spacing-md);
    font-family: var(--font-mono);
    font-size: 0.82rem;
    white-space: pre-wrap;
    color: var(--color-text);
    max-height: 260px;
    overflow: auto;
  }

  .integration-panel {
    background: rgba(82, 245, 106, 0.06);
    border: 1px solid rgba(82, 245, 106, 0.22);
    border-radius: var(--border-radius-md);
    padding: var(--spacing-md);
  }

  .integration-panel p {
    color: var(--color-text-secondary);
    margin: var(--spacing-sm) 0 0;
    white-space: pre-wrap;
  }

  .task-error {
    background: rgba(255, 61, 79, 0.1);
    border: 1px solid rgba(255, 61, 79, 0.32);
    border-radius: var(--border-radius-md);
    color: var(--color-error);
    padding: var(--spacing-sm) var(--spacing-md);
  }

  .task-actions {
    display: flex;
    gap: var(--spacing-sm);
    flex-wrap: wrap;
    margin-top: auto;
  }

  .spin {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  @media (max-width: 520px) {
    .task-header,
    .metadata-grid {
      grid-template-columns: 1fr;
    }

    .task-header {
      flex-direction: column;
    }
  }
</style>
