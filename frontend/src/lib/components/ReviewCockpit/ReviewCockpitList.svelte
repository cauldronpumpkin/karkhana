<script>
  import { onMount } from 'svelte';
  import {
    AlertTriangle,
    CheckCircle2,
    Clock,
    Eye,
    Filter,
    Loader2,
    PauseCircle,
    RefreshCw,
    Shield,
    ShieldCheck,
    XCircle
  } from 'lucide-svelte';
  import { listReviewPackets } from '../../api.js';
  import Badge from '../UI/Badge.svelte';
  import Button from '../UI/Button.svelte';

  let packets = $state([]);
  let isLoading = $state(true);
  let error = $state('');
  let activeFilter = $state(null);

  const filters = [
    { key: null, label: 'All' },
    { key: 'active', label: 'Active' },
    { key: 'awaiting_review', label: 'Awaiting Review' },
    { key: 'no_objection', label: 'No Objection' },
    { key: 'complete', label: 'Complete' },
  ];

  const stateTone = (state) => {
    if (state === 'approved') return 'success';
    if (state === 'rejected') return 'error';
    if (state === 'wait_window') return 'warning';
    if (state === 'awaiting_review') return 'accent';
    if (state === 'paused') return 'muted';
    if (state === 'modification_requested') return 'warning';
    if (state === 'no_objection_recorded') return 'success';
    if (state === 'ready_to_continue') return 'success';
    return 'muted';
  };

  const stateLabel = (state) => {
    const labels = {
      awaiting_review: 'Awaiting Review',
      wait_window: 'Wait Window',
      no_objection_recorded: 'No Objection',
      ready_to_continue: 'Ready',
      approved: 'Approved',
      rejected: 'Rejected',
      modification_requested: 'Changes Requested',
      paused: 'Paused',
    };
    return labels[state] || state;
  };

  const impactTone = (impact) => {
    if (impact === 'high') return 'error';
    if (impact === 'medium') return 'warning';
    if (impact === 'low') return 'success';
    return 'muted';
  };

  const councilDecisionTone = (decision) => {
    if (decision === 'ready') return 'success';
    if (decision === 'needs_changes') return 'warning';
    if (decision === 'blocked') return 'error';
    return 'muted';
  };

  function fmtDate(v) {
    return v ? new Date(v).toLocaleString() : 'n/a';
  }

  function shortId(id) {
    return id ? id.slice(0, 8) : 'n/a';
  }

  async function loadPackets() {
    isLoading = true;
    error = '';
    try {
      const data = await listReviewPackets(activeFilter);
      packets = data.review_packets || [];
    } catch (err) {
      error = err.message || 'Failed to load review packets.';
    } finally {
      isLoading = false;
    }
  }

  function viewDetail(packet) {
    window.location.hash = `/review/${packet.run_id}`;
  }

  onMount(loadPackets);
</script>

<div class="review-cockpit">
  <header class="cockpit-header">
    <div>
      <h1>Review Cockpit</h1>
      <p class="subtitle">Wait-Window Factory Run Review Queue</p>
    </div>
    <div class="header-actions">
      <Button size="sm" variant="secondary" onclick={loadPackets}>
        <RefreshCw size={14} /> Refresh
      </Button>
    </div>
  </header>

  <nav class="filter-bar">
    {#each filters as f}
      <button
        class="filter-btn"
        class:active={activeFilter === f.key}
        onclick={() => { activeFilter = f.key; loadPackets(); }}
      >
        {f.label}
      </button>
    {/each}
  </nav>

  {#if isLoading}
    <section class="loading-state">
      <span class="spin"><Loader2 size={22} /></span>
      Loading review packets...
    </section>
  {:else if error}
    <section class="error-state">
      <XCircle size={22} />
      <p>{error}</p>
      <Button size="sm" onclick={loadPackets}><RefreshCw size={14} /> Retry</Button>
    </section>
  {:else if packets.length === 0}
    <section class="empty-state">
      <Eye size={28} />
      <h3>No review packets</h3>
      <p>No factory runs match the current filter.</p>
    </section>
  {:else}
    <div class="packet-list">
      {#each packets as packet}
        <button type="button" class="packet-row" onclick={() => viewDetail(packet)} onkeydown={(e) => { if (e.key === 'Enter') viewDetail(packet); }}>
          <div class="packet-main">
            <div class="packet-id-col">
              <strong class="mono">{shortId(packet.run_id)}</strong>
              <small>{packet.run_status || 'unknown'}</small>
            </div>
            <div class="packet-info-col">
              <p class="promise">{packet.promise || 'No promise set'}</p>
              <div class="meta-row">
                <Badge variant={packet.packet_type === 'research_handoff' ? 'warning' : 'muted'}>
                  {packet.packet_type?.replace(/_/g, ' ') || 'standard'}
                </Badge>
                {#if packet.branch_name}
                  <Badge variant="muted">{packet.branch_name}</Badge>
                {/if}
                {#if packet.worker_display_name}
                  <Badge variant="muted">{packet.worker_display_name}</Badge>
                {/if}
                {#if packet.autonomy_level}
                  <Badge variant="accent">{packet.autonomy_level.replace(/_/g, ' ')}</Badge>
                {/if}
              </div>
            </div>
          </div>
          <div class="packet-badges">
            <Badge variant={stateTone(packet.wait_window_state)}>
              {stateLabel(packet.wait_window_state)}
            </Badge>
            {#if packet.blast_radius?.impact_score}
              <Badge variant={impactTone(packet.blast_radius.impact_score)}>
                {packet.blast_radius.impact_score} impact
              </Badge>
            {/if}
            {#if packet.safety_net_results?.tests_passed}
              <Badge variant="success"><ShieldCheck size={12} /> Tests pass</Badge>
            {:else}
              <Badge variant="error"><AlertTriangle size={12} /> Tests fail</Badge>
            {/if}
            {#if packet.council_summary?.overall_decision}
              <Badge variant={councilDecisionTone(packet.council_summary.overall_decision)}>
                <Shield size={12} /> {packet.council_summary.overall_decision.replace(/_/g, ' ')}
              </Badge>
            {/if}
            <small class="timestamp">{fmtDate(packet.created_at)}</small>
          </div>
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .review-cockpit {
    margin: 0 auto;
    max-width: 1240px;
  }

  .cockpit-header {
    align-items: flex-start;
    display: flex;
    gap: var(--spacing-lg);
    justify-content: space-between;
    margin-bottom: var(--spacing-lg);
  }

  .cockpit-header h1 {
    color: var(--color-text);
    font-size: 1.8rem;
    line-height: 1;
    margin: 0 0 4px;
  }

  .subtitle {
    color: var(--color-text-secondary);
    font-size: 0.85rem;
    margin: 0;
  }

  .header-actions {
    display: flex;
    gap: 8px;
  }

  .filter-bar {
    display: flex;
    gap: 6px;
    margin-bottom: var(--spacing-lg);
    flex-wrap: wrap;
  }

  .filter-btn {
    background: rgba(5, 10, 15, 0.72);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-md);
    color: var(--color-text-secondary);
    cursor: pointer;
    font-size: 0.82rem;
    padding: 6px 14px;
    transition: all 0.15s;
  }

  .filter-btn:hover {
    border-color: rgba(0, 174, 255, 0.28);
    color: var(--color-text);
  }

  .filter-btn.active {
    background: linear-gradient(90deg, rgba(0, 120, 255, 0.16), rgba(0, 240, 255, 0.04));
    border-color: rgba(0, 174, 255, 0.28);
    color: var(--color-text);
  }

  .loading-state,
  .error-state,
  .empty-state {
    align-items: center;
    background: rgba(5, 10, 15, 0.72);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
    color: var(--color-text-secondary);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
    justify-content: center;
    min-height: 180px;
    text-align: center;
  }

  .error-state {
    color: var(--color-error);
  }

  .packet-list {
    display: grid;
    gap: 8px;
  }

  .packet-row {
    align-items: center;
    background: rgba(5, 10, 15, 0.6);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-md);
    cursor: pointer;
    display: flex;
    gap: var(--spacing-md);
    justify-content: space-between;
    padding: var(--spacing-md);
    transition: background 0.15s;
  }

  .packet-row:hover {
    background: rgba(0, 120, 255, 0.04);
    border-color: rgba(0, 174, 255, 0.2);
  }

  .packet-main {
    display: flex;
    gap: var(--spacing-md);
    flex: 1;
    min-width: 0;
  }

  .packet-id-col {
    flex: 0 0 100px;
  }

  .packet-id-col strong {
    color: var(--color-text);
    display: block;
    font-size: 0.92rem;
  }

  .packet-id-col small {
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.72rem;
  }

  .packet-info-col {
    flex: 1;
    min-width: 0;
  }

  .promise {
    color: var(--color-text);
    font-size: 0.88rem;
    margin: 0 0 6px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .meta-row {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }

  .packet-badges {
    align-items: center;
    display: flex;
    flex: 0 0 auto;
    gap: 8px;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .timestamp {
    color: var(--color-text-secondary);
    font-family: var(--font-mono);
    font-size: 0.68rem;
  }

  .mono {
    font-family: var(--font-mono);
  }

  .spin {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  @media (max-width: 768px) {
    .packet-row {
      flex-direction: column;
      align-items: flex-start;
    }

    .packet-badges {
      width: 100%;
      justify-content: flex-start;
    }
  }
</style>
