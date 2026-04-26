<script>
  import { onMount } from 'svelte'
  import { listen } from '@tauri-apps/api/event'
  import Card from '../UI/Card.svelte'
  import Badge from '../UI/Badge.svelte'
  import { currentJob, jobHistory } from '../../stores.js'

  let jobs = $state([])
  let activeJob = $state(null)

  jobHistory.subscribe(h => jobs = h)
  currentJob.subscribe(j => activeJob = j)

  onMount(() => {
    const unsubs = []
    listen('job-started', (e) => {
      activeJob = e.payload.job
      currentJob.set(activeJob)
    }).then(u => unsubs.push(u))
    listen('job-completed', (e) => {
      jobs = [{ ...e.payload.job, status: 'completed', endedAt: Date.now() }, ...jobs].slice(0, 20)
      jobHistory.set(jobs)
      activeJob = null
      currentJob.set(null)
    }).then(u => unsubs.push(u))
    listen('job-failed', (e) => {
      jobs = [{ ...e.payload.job, status: 'failed', error: e.payload.error, endedAt: Date.now() }, ...jobs].slice(0, 20)
      jobHistory.set(jobs)
      activeJob = null
      currentJob.set(null)
    }).then(u => unsubs.push(u))

    return () => unsubs.forEach(u => u())
  })

  function formatTime(ts) {
    if (!ts) return '—'
    const diff = Math.floor((Date.now() - ts) / 1000)
    if (diff < 60) return `${diff}s ago`
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    return `${Math.floor(diff / 3600)}h ago`
  }

  function statusVariant(s) {
    if (s === 'completed') return 'success'
    if (s === 'failed') return 'error'
    return 'warning'
  }
</script>

<Card title="Job History">
  {#if activeJob}
    <div class="active-job">
      <span class="mono-label">Current Job</span>
      <div class="job-row">
        <Badge variant="warning">{activeJob.job_type}</Badge>
        <span class="job-id">{activeJob.id?.slice(0, 8)}</span>
        <span class="job-status">Running...</span>
      </div>
    </div>
  {/if}

  {#if jobs.length === 0}
    <p class="empty">No jobs processed yet</p>
  {:else}
    <ul class="job-list">
      {#each jobs as job}
        <li class="job-item">
          <div class="job-row">
            <Badge variant={statusVariant(job.status)}>
              {job.status === 'completed' ? '✅' : job.status === 'failed' ? '❌' : '⏳'} {job.job_type}
            </Badge>
            <span class="job-time">{formatTime(job.endedAt)}</span>
          </div>
          {#if job.error}
            <span class="job-error">{job.error}</span>
          {/if}
        </li>
      {/each}
    </ul>
  {/if}
</Card>

<style>
  .active-job {
    background: linear-gradient(180deg, rgba(8, 14, 21, 0.9), rgba(4, 9, 14, 0.82));
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-md);
    margin-bottom: var(--spacing-md);
    padding: var(--spacing-md);
  }

  .job-list {
    list-style: none;
    margin: 0;
    padding: 0;
  }

  .job-item {
    border-bottom: 1px solid rgba(103, 128, 151, 0.14);
    padding: var(--spacing-sm) 0;
  }

  .job-item:last-child {
    border-bottom: 0;
  }

  .job-row {
    align-items: center;
    display: flex;
    gap: var(--spacing-sm);
    justify-content: space-between;
  }

  .job-id {
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.78rem;
  }

  .job-status {
    color: var(--color-warning);
    font-size: 0.85rem;
  }

  .job-time {
    color: var(--color-text-muted);
    font-size: 0.8rem;
  }

  .job-error {
    color: var(--color-error);
    display: block;
    font-size: 0.8rem;
    margin-top: var(--spacing-xs);
  }

  .empty {
    color: var(--color-text-muted);
    text-align: center;
  }
</style>
