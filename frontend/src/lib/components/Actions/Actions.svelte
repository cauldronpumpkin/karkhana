<script>
  import { onMount } from 'svelte';
  import { FileText, FlaskConical, Loader2, Plus, UploadCloud } from 'lucide-svelte';
  import { api, apiPost } from '../../api.js';
  import Button from '../UI/Button.svelte';
  import ResearchTaskCard from './ResearchTaskCard.svelte';
  import FileUpload from './FileUpload.svelte';
  import Modal from '../UI/Modal.svelte';
  import BuildQueue from './BuildQueue.svelte';

  let { ideaId = '' } = $props();

  let tasks = $state({ pending: [], completed: [] });
  let isLoading = $state(false);
  let isTasksLoading = $state(true);
  let showFileUpload = $state(false);
  let selectedTask = $state(null);
  let loadError = $state('');

  let pendingCount = $derived(tasks.pending?.length || 0);
  let completedCount = $derived(tasks.completed?.length || 0);
  let totalCount = $derived(pendingCount + completedCount);

  async function loadTasks() {
    if (!ideaId) {
      isTasksLoading = false;
      return;
    }
    isTasksLoading = true;
    loadError = '';
    try {
      const data = await api(`/api/ideas/${ideaId}/research/tasks`);
      tasks = data || { pending: [], completed: [] };
    } catch (error) {
      console.error('Failed to load tasks:', error);
      tasks = { pending: [], completed: [] };
      loadError = 'Research tasks could not be loaded. Check the API connection and try again.';
    } finally {
      isTasksLoading = false;
    }
  }

  async function generateNewTasks() {
    if (!ideaId) return;
    isLoading = true;
    try {
      await apiPost(`/api/ideas/${ideaId}/research/generate`);
      await loadTasks();
    } catch (error) {
      console.error('Failed to generate tasks:', error);
    } finally {
      isLoading = false;
    }
  }

  function openFileUpload(task) {
    selectedTask = task;
    showFileUpload = true;
  }

  function closeFileUpload() {
    showFileUpload = false;
    selectedTask = null;
  }

  async function handleUploadComplete() {
    closeFileUpload();
    await loadTasks();
  }

  onMount(() => {
    loadTasks();
  });
</script>

<div class="actions-container">
  <div class="actions-hero">
    <div>
      <span class="mono-label"><span class="status-dot"></span> Research queue</span>
      <h1>Research Actions</h1>
      <p class="subtitle">Generate focused Deep Research prompts, track evidence, and fold completed findings back into the idea.</p>
    </div>

    <Button onclick={generateNewTasks} disabled={isLoading || !ideaId}>
      {#if isLoading}
        <span class="spin"><Loader2 size={16} /></span>
        Generating
      {:else}
        <Plus size={16} />
        Generate Tasks
      {/if}
    </Button>
  </div>

  <div class="status-strip" aria-label="Research action status">
    <div class="status-panel status-panel-pending">
      <span class="mono-label">Pending</span>
      <strong>{pendingCount}</strong>
      <span>Awaiting evidence upload</span>
    </div>
    <div class="status-panel status-panel-completed">
      <span class="mono-label">Completed</span>
      <strong>{completedCount}</strong>
      <span>Ready for integration review</span>
    </div>
    <div class="status-panel">
      <span class="mono-label">Total</span>
      <strong>{totalCount}</strong>
      <span>Research actions in this idea</span>
    </div>
  </div>

  {#if loadError}
    <div class="notice error" role="alert">{loadError}</div>
  {/if}

  <BuildQueue {ideaId} />

  {#if isTasksLoading}
    <div class="loading-panel">
      <span class="spin"><Loader2 size={20} /></span>
      <span>Loading research actions...</span>
    </div>
  {:else if totalCount === 0}
    <section class="empty-state">
      <div class="empty-icon"><FlaskConical size={42} /></div>
      <h2>No research actions yet</h2>
      <p>Create a task set when the idea needs market, competitor, feasibility, or evidence-backed validation.</p>
      <Button onclick={generateNewTasks} disabled={isLoading || !ideaId}>
        <Plus size={16} />
        Generate First Tasks
      </Button>
    </section>
  {:else}
    <section class="tasks-section">
      <div class="section-heading">
        <div>
          <span class="mono-label"><UploadCloud size={14} /> Evidence needed</span>
          <h2>Pending Tasks</h2>
        </div>
        <span class="section-count">{pendingCount}</span>
      </div>
      {#if pendingCount}
        <div class="tasks-grid">
          {#each tasks.pending as task}
            <ResearchTaskCard {ideaId} {task} onupload={openFileUpload} onintegrated={loadTasks} />
          {/each}
        </div>
      {:else}
        <div class="notice success">All generated research tasks have evidence attached.</div>
      {/if}
    </section>

    <section class="tasks-section">
      <div class="section-heading">
        <div>
          <span class="mono-label"><FileText size={14} /> Evidence captured</span>
          <h2>Completed Tasks</h2>
        </div>
        <span class="section-count">{completedCount}</span>
      </div>
      {#if completedCount}
        <div class="tasks-grid">
          {#each tasks.completed as task}
            <ResearchTaskCard {ideaId} {task} onupload={openFileUpload} onintegrated={loadTasks} />
          {/each}
        </div>
      {:else}
        <div class="notice">Completed research will appear here after an upload is accepted.</div>
      {/if}
    </section>
  {/if}
</div>

{#if showFileUpload && selectedTask}
  <Modal title="Upload Research File" onclose={closeFileUpload}>
    <FileUpload {ideaId} task={selectedTask} onclose={closeFileUpload} onuploaded={handleUploadComplete} />
  </Modal>
{/if}

<style>
  .actions-container {
    max-width: 1240px;
    margin: 0 auto;
    padding: var(--spacing-lg);
  }

  .actions-hero {
    align-items: flex-start;
    display: flex;
    gap: var(--spacing-lg);
    justify-content: space-between;
    margin-bottom: var(--spacing-lg);
  }

  .actions-hero h1 {
    color: var(--color-text);
    font-size: clamp(2rem, 5vw, 3.1rem);
    line-height: 1;
    margin: var(--spacing-sm) 0;
  }

  .subtitle {
    color: var(--color-text-secondary);
    margin: 0;
    max-width: 680px;
  }

  .mono-label {
    align-items: center;
    display: inline-flex;
    gap: 8px;
  }

  .status-strip {
    display: grid;
    gap: var(--spacing-md);
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin-bottom: var(--spacing-xl);
  }

  .status-panel {
    background:
      linear-gradient(180deg, rgba(10, 18, 26, 0.94), rgba(4, 9, 14, 0.92));
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
    padding: var(--spacing-md);
    position: relative;
    overflow: hidden;
  }

  .status-panel::after {
    background: linear-gradient(90deg, transparent, rgba(0, 240, 255, 0.28), transparent);
    content: "";
    height: 1px;
    left: 12px;
    position: absolute;
    right: 12px;
    top: 0;
  }

  .status-panel strong {
    color: var(--color-text);
    display: block;
    font-size: 2.15rem;
    line-height: 1;
    margin: 12px 0 6px;
  }

  .status-panel span:last-child {
    color: var(--color-text-secondary);
    font-size: 0.9rem;
  }

  .status-panel-pending strong {
    color: var(--color-warning);
  }

  .status-panel-completed strong {
    color: var(--color-success);
  }

  .tasks-section {
    margin-bottom: var(--spacing-lg);
  }

  .section-heading {
    align-items: center;
    display: flex;
    justify-content: space-between;
    margin-bottom: var(--spacing-md);
  }

  .section-heading h2 {
    color: var(--color-text);
    font-size: 1.25rem;
    margin: 6px 0 0;
  }

  .section-count {
    border: 1px solid var(--color-border);
    border-radius: 999px;
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.82rem;
    padding: 5px 10px;
  }

  .tasks-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 360px), 1fr));
    gap: var(--spacing-md);
  }

  .loading-panel,
  .empty-state,
  .notice {
    background: linear-gradient(180deg, rgba(8, 14, 21, 0.95), rgba(4, 9, 14, 0.9));
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
  }

  .loading-panel {
    align-items: center;
    color: var(--color-text-secondary);
    display: flex;
    gap: var(--spacing-sm);
    justify-content: center;
    min-height: 180px;
  }

  .empty-state {
    align-items: center;
    display: flex;
    flex-direction: column;
    min-height: 360px;
    justify-content: center;
    padding: var(--spacing-xl);
    text-align: center;
  }

  .empty-icon {
    align-items: center;
    border: 1px dashed rgba(0, 240, 255, 0.45);
    border-radius: var(--border-radius-lg);
    color: var(--color-accent);
    display: flex;
    height: 86px;
    justify-content: center;
    margin-bottom: var(--spacing-lg);
    width: 86px;
  }

  .empty-state h2 {
    margin: 0 0 var(--spacing-sm);
  }

  .empty-state p {
    color: var(--color-text-secondary);
    margin: 0 0 var(--spacing-lg);
    max-width: 520px;
  }

  .notice {
    color: var(--color-text-secondary);
    padding: var(--spacing-md);
  }

  .notice.success {
    border-color: rgba(82, 245, 106, 0.3);
    color: var(--color-success);
  }

  .notice.error {
    border-color: rgba(255, 61, 79, 0.4);
    color: var(--color-error);
    margin-bottom: var(--spacing-lg);
  }

  .spin {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  @media (max-width: 760px) {
    .actions-hero,
    .section-heading {
      align-items: stretch;
      flex-direction: column;
    }

    .status-strip {
      grid-template-columns: 1fr;
    }
  }
</style>
