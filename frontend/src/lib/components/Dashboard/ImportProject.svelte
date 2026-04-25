<script>
  import { GitBranch, GitFork, Loader2, RefreshCw, X } from 'lucide-svelte';
  import { api, apiPost } from '../../api.js';
  import Button from '../UI/Button.svelte';
  import Input from '../UI/Input.svelte';
  import Modal from '../UI/Modal.svelte';

  let { onclose, onimported } = $props();

  let repos = $state([]);
  let isLoadingRepos = $state(false);
  let isSubmitting = $state(false);
  let error = $state('');
  let selectedRepoKey = $state('');
  let manualFullName = $state('');
  let installationId = $state('');
  let defaultBranch = $state('main');
  let deployUrl = $state('');
  let currentStatus = $state('');
  let desiredOutcome = $state('');

  let selectedRepo = $derived(repos.find((repo) => repo.repo_full_name === selectedRepoKey) || null);

  async function loadRepos() {
    isLoadingRepos = true;
    error = '';
    try {
      const data = await api('/api/github/installations/repos');
      repos = data.repos || [];
      if (repos.length && !selectedRepoKey) {
        selectedRepoKey = repos[0].repo_full_name;
        installationId = repos[0].installation_id;
        defaultBranch = repos[0].default_branch || 'main';
      }
    } catch (err) {
      error = err.message || 'Unable to load GitHub repositories.';
      repos = [];
    } finally {
      isLoadingRepos = false;
    }
  }

  function handleRepoSelect() {
    if (!selectedRepo) return;
    installationId = selectedRepo.installation_id;
    defaultBranch = selectedRepo.default_branch || 'main';
  }

  async function submitImport() {
    error = '';
    isSubmitting = true;
    try {
      const repoFullName = selectedRepo?.repo_full_name || manualFullName.trim();
      const [owner, repo] = repoFullName.split('/');
      const result = await apiPost('/api/ideas/import/github', {
        installation_id: installationId,
        owner,
        repo,
        repo_full_name: repoFullName,
        repo_url: selectedRepo?.repo_url || (repoFullName ? `https://github.com/${repoFullName}` : ''),
        clone_url: selectedRepo?.clone_url || (repoFullName ? `https://github.com/${repoFullName}.git` : ''),
        default_branch: selectedRepo?.default_branch || defaultBranch || 'main',
        deploy_url: deployUrl || null,
        current_status: currentStatus || null,
        desired_outcome: desiredOutcome || null
      });
      onimported?.(result);
    } catch (err) {
      error = err.message || 'Project import failed.';
    } finally {
      isSubmitting = false;
    }
  }
</script>

<Modal title="Import Existing Project" showClose={true} {onclose}>
  <form onsubmit={(event) => { event.preventDefault(); submitImport(); }}>
    <div class="intro">
      <span><GitFork size={22} /></span>
      <div>
        <strong>GitHub project twin</strong>
        <p>Import an existing repo as an Idea with a persistent local-worker queue and codebase index.</p>
      </div>
    </div>

    <div class="repo-actions">
      <Button type="button" variant="secondary" onclick={loadRepos} disabled={isLoadingRepos}>
        {#if isLoadingRepos}
          <span class="spin"><Loader2 size={15} /></span>
          Loading
        {:else}
          <RefreshCw size={15} />
          Load GitHub Repos
        {/if}
      </Button>
      <small>{repos.length ? `${repos.length} GitHub App repos available` : 'Manual entry works after GitHub App install id is known.'}</small>
    </div>

    {#if repos.length}
      <label class="form-group">
        Repository
        <select bind:value={selectedRepoKey} onchange={handleRepoSelect}>
          {#each repos as repo}
            <option value={repo.repo_full_name}>{repo.repo_full_name}</option>
          {/each}
        </select>
      </label>
    {:else}
      <label class="form-group">
        Repository full name
        <Input bind:value={manualFullName} placeholder="owner/repo" required />
      </label>
    {/if}

    <div class="split">
      <label class="form-group">
        Installation ID
        <Input bind:value={installationId} placeholder="GitHub App installation id" required />
      </label>
      <label class="form-group">
        Default branch
        <Input bind:value={defaultBranch} placeholder="main" />
      </label>
    </div>

    <label class="form-group">
      Deployed URL
      <Input bind:value={deployUrl} placeholder="https://your-app.example.com" />
    </label>

    <label class="form-group">
      Current status
      <textarea bind:value={currentStatus} rows="3" placeholder="What already works, what is incomplete, known production issues"></textarea>
    </label>

    <label class="form-group">
      Desired outcome
      <textarea bind:value={desiredOutcome} rows="3" placeholder="What should Idea Refinery help finish first?"></textarea>
    </label>

    {#if error}
      <div class="error" role="alert">{error}</div>
    {/if}

    <div class="footer">
      <Button type="button" variant="secondary" onclick={onclose}>
        <X size={16} />
        Cancel
      </Button>
      <Button type="submit" disabled={isSubmitting}>
        {#if isSubmitting}
          <span class="spin"><Loader2 size={16} /></span>
          Importing
        {:else}
          <GitBranch size={16} />
          Import Project
        {/if}
      </Button>
    </div>
  </form>
</Modal>

<style>
  .intro {
    align-items: flex-start;
    background: rgba(0, 120, 255, 0.1);
    border: 1px solid rgba(0, 240, 255, 0.24);
    border-radius: var(--border-radius-lg);
    display: flex;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-lg);
    padding: var(--spacing-md);
  }

  .intro span {
    align-items: center;
    border: 1px solid rgba(0, 240, 255, 0.28);
    border-radius: var(--border-radius-md);
    color: var(--color-accent);
    display: inline-flex;
    height: 38px;
    justify-content: center;
    width: 38px;
  }

  .intro p,
  .repo-actions small {
    color: var(--color-text-secondary);
    margin: 4px 0 0;
  }

  .repo-actions {
    align-items: center;
    display: flex;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-md);
  }

  .form-group {
    color: var(--color-text-secondary);
    display: grid;
    font-size: 0.875rem;
    font-weight: 600;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-md);
  }

  .split {
    display: grid;
    gap: var(--spacing-md);
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  select,
  textarea {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-sm);
    color: var(--color-text);
    font: inherit;
    padding: var(--spacing-sm);
  }

  textarea {
    min-height: 86px;
    resize: vertical;
  }

  .error {
    background: rgba(255, 61, 79, 0.1);
    border: 1px solid rgba(255, 61, 79, 0.32);
    border-radius: var(--border-radius-md);
    color: var(--color-error);
    margin-bottom: var(--spacing-md);
    padding: var(--spacing-md);
  }

  .footer {
    display: flex;
    gap: var(--spacing-md);
    justify-content: flex-end;
  }

  .spin {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  @media (max-width: 560px) {
    .split {
      grid-template-columns: 1fr;
    }

    .repo-actions,
    .footer {
      align-items: stretch;
      flex-direction: column;
    }
  }
</style>
