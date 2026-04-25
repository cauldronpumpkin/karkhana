<script>
  import { onMount } from 'svelte';
  import { Filter, GitBranch, Grid2X2, List, Plus, Search, SlidersHorizontal } from 'lucide-svelte';
  import { api } from '../../api.js';
  import Button from '../UI/Button.svelte';
  import IdeaCard from './IdeaCard.svelte';
  import CreateIdea from './CreateIdea.svelte';
  import ImportProject from './ImportProject.svelte';

  let ideas = $state([]);
  let showCreateModal = $state(false);
  let showImportModal = $state(false);
  let searchTerm = $state('');
  let phaseFilter = $state('all');
  let scoreFilter = $state('all');
  let sortMode = $state('updated');
  let viewMode = $state('grid');

  onMount(async () => {
    try {
      const data = await api('/api/ideas');
      ideas = data;
    } catch (err) {
      console.error('Failed to load ideas:', err);
      ideas = [];
    }
  });

  function handleNewIdea() {
    showCreateModal = true;
  }

  function handleImportProject() {
    showImportModal = true;
  }

  function handleIdeaCreated(newIdea) {
    ideas = [...ideas, newIdea];
    showCreateModal = false;
    if (newIdea?.id) {
      localStorage.setItem('idearefinery:activeIdeaId', newIdea.id);
      window.location.hash = `/chat/${newIdea.id}`;
    }
  }

  function handleProjectImported(result) {
    const newIdea = result?.idea;
    if (newIdea) {
      ideas = [...ideas, newIdea];
      showImportModal = false;
      localStorage.setItem('idearefinery:activeIdeaId', newIdea.id);
      window.location.hash = `/project/${newIdea.id}`;
    }
  }

  const scoreToPercent = (score = 0) => Math.round(Math.min(100, Math.max(0, score <= 10 ? score * 10 : score)));

  const getPhaseLabel = (phase = '') => phase
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase()) || 'Capture';

  const getUpdatedTime = (idea) => new Date(idea.updated_at || idea.created_at || 0).getTime();

  let activeIdeas = $derived(ideas.filter((idea) => idea.status !== 'archived'));
  let averageScore = $derived(activeIdeas.length
    ? Math.round(activeIdeas.reduce((sum, idea) => sum + scoreToPercent(idea.composite_score || 0), 0) / activeIdeas.length)
    : 0);
  let buildReady = $derived(activeIdeas.filter((idea) => ['build', 'handoff', 'prometheus'].includes((idea.current_phase || '').toLowerCase())).length);
  let researchPending = $derived(activeIdeas.filter((idea) => !['build', 'handoff', 'prometheus'].includes((idea.current_phase || '').toLowerCase())).length * 3);
  let phaseOptions = $derived(['all', ...new Set(activeIdeas.map((idea) => idea.current_phase).filter(Boolean))]);
  let filteredIdeas = $derived(
    activeIdeas
      .filter((idea) => {
        const query = searchTerm.trim().toLowerCase();
        const matchesSearch = !query
          || idea.title?.toLowerCase().includes(query)
          || idea.description?.toLowerCase().includes(query);
        const score = scoreToPercent(idea.composite_score || 0);
        const matchesPhase = phaseFilter === 'all' || idea.current_phase === phaseFilter;
        const matchesScore = scoreFilter === 'all'
          || (scoreFilter === 'high' && score >= 75)
          || (scoreFilter === 'medium' && score >= 50 && score < 75)
          || (scoreFilter === 'low' && score < 50);

        return matchesSearch && matchesPhase && matchesScore;
      })
      .sort((a, b) => {
        if (sortMode === 'score') return scoreToPercent(b.composite_score || 0) - scoreToPercent(a.composite_score || 0);
        if (sortMode === 'title') return (a.title || '').localeCompare(b.title || '');
        return getUpdatedTime(b) - getUpdatedTime(a);
      })
  );

  const kpis = $derived([
    {
      label: 'Active Ideas',
      value: activeIdeas.length,
      note: `${Math.max(0, ideas.length - activeIdeas.length)} archived`,
      tone: 'primary',
      bars: [28, 34, 30, 42, 31, 37, 29, 35]
    },
    {
      label: 'Average Score',
      value: averageScore,
      suffix: '/100',
      note: activeIdeas.length ? 'Portfolio health' : 'Awaiting scores',
      tone: 'success',
      bars: [20, 25, 38, 30, 44, 36, 40, 48]
    },
    {
      label: 'Research Pending',
      value: researchPending,
      note: `Across ${activeIdeas.length} ideas`,
      tone: 'warning',
      bars: [18, 30, 22, 46, 36, 28, 40, 24]
    },
    {
      label: 'Ready To Build',
      value: buildReady,
      note: 'Handoff ready',
      tone: 'success',
      bars: [16, 42, 30, 20, 50, 24, 18, 38]
    }
  ]);
</script>

<div class="dashboard">
  <div class="dashboard-header">
    <div>
      <p class="mono-label">Overview</p>
      <h1>Dashboard</h1>
      <p>Overview of your ideas, scores, and AI research pipeline.</p>
    </div>
    <div class="header-actions">
      <Button variant="secondary" onclick={handleImportProject}>
        <GitBranch size={17} />
        Import Project
      </Button>
      <Button onclick={handleNewIdea}>
        <Plus size={17} />
        New Idea
      </Button>
    </div>
  </div>

  <section class="kpi-strip" aria-label="Dashboard metrics">
    {#each kpis as kpi}
      <article class="kpi-card {kpi.tone}">
        <div>
          <p><span class="kpi-dot"></span>{kpi.label}</p>
          <strong>{kpi.value}<small>{kpi.suffix || ''}</small></strong>
          <span>{kpi.note}</span>
        </div>
        <div class="spark-bars" aria-hidden="true">
          {#each kpi.bars as bar}
            <i style={`height: ${bar}px`}></i>
          {/each}
        </div>
      </article>
    {/each}
  </section>

  <section class="dashboard-controls" aria-label="Idea controls">
    <label class="search-control">
      <Search size={17} />
      <input bind:value={searchTerm} type="search" placeholder="Search ideas..." />
    </label>

    <div class="filter-row">
      <label>
        <Filter size={15} />
        <select bind:value={phaseFilter} aria-label="Filter by phase">
          {#each phaseOptions as phase}
            <option value={phase}>{phase === 'all' ? 'All Phases' : getPhaseLabel(phase)}</option>
          {/each}
        </select>
      </label>
      <label>
        <SlidersHorizontal size={15} />
        <select bind:value={scoreFilter} aria-label="Filter by score">
          <option value="all">All Scores</option>
          <option value="high">75+ Score</option>
          <option value="medium">50-74 Score</option>
          <option value="low">Below 50</option>
        </select>
      </label>
      <label>
        <select bind:value={sortMode} aria-label="Sort ideas">
          <option value="updated">Last Updated</option>
          <option value="score">Top Score</option>
          <option value="title">Title</option>
        </select>
      </label>
      <div class="view-toggle" aria-label="View mode">
        <button type="button" class:active={viewMode === 'grid'} aria-label="Grid view" onclick={() => viewMode = 'grid'}><Grid2X2 size={16} /></button>
        <button type="button" class:active={viewMode === 'list'} aria-label="List view" onclick={() => viewMode = 'list'}><List size={16} /></button>
      </div>
    </div>
  </section>

  <div class:list-view={viewMode === 'list'} class="ideas-grid">
    {#each filteredIdeas as idea}
      <IdeaCard 
        {idea}
        onclick={() => {
          localStorage.setItem('idearefinery:activeIdeaId', idea.id);
          window.location.hash = idea.source_type === 'github_project' ? `/project/${idea.id}` : `/chat/${idea.id}`;
        }}
      />
    {/each}

    <button class="add-card" type="button" onclick={handleNewIdea}>
      <span><Plus size={22} /></span>
      <strong>New Idea</strong>
      <small>Capture a new idea and let AI evaluate its potential.</small>
    </button>
  </div>

  {#if !filteredIdeas.length}
    <section class="empty-state">
      <div class="empty-mark"><Plus size={26} /></div>
      <h2>{activeIdeas.length ? 'No matching ideas' : 'No ideas captured yet'}</h2>
      <p>{activeIdeas.length ? 'Try another search or filter combination.' : 'Start with one strong raw concept. The scoring pipeline can take it from there.'}</p>
      <Button onclick={handleNewIdea}>
        <Plus size={17} />
        New Idea
      </Button>
    </section>
  {/if}
  
  {#if showCreateModal}
    <CreateIdea 
      onclose={() => showCreateModal = false}
      onideaCreated={handleIdeaCreated}
    />
  {/if}

  {#if showImportModal}
    <ImportProject
      onclose={() => showImportModal = false}
      onimported={handleProjectImported}
    />
  {/if}
</div>

<style>
  .dashboard {
    margin: 0 auto;
    max-width: 1320px;
  }
  
  .dashboard-header {
    align-items: center;
    display: flex;
    gap: var(--spacing-lg);
    justify-content: space-between;
    margin-bottom: var(--spacing-lg);
  }

  .header-actions {
    display: flex;
    gap: var(--spacing-sm);
  }
  
  .dashboard-header h1 {
    color: var(--color-text);
    font-size: 2rem;
    font-weight: 800;
    line-height: 1;
    margin: 4px 0 var(--spacing-sm);
  }

  .dashboard-header p:not(.mono-label) {
    color: var(--color-text-secondary);
    margin: 0;
  }

  .kpi-strip {
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    margin-bottom: var(--spacing-md);
    overflow: hidden;
  }

  .kpi-card {
    align-items: center;
    background: rgba(5, 10, 15, 0.68);
    display: flex;
    justify-content: space-between;
    min-height: 118px;
    padding: var(--spacing-md) var(--spacing-lg);
    position: relative;
  }

  .kpi-card + .kpi-card {
    border-left: 1px solid var(--color-border);
  }

  .kpi-card p {
    align-items: center;
    color: var(--color-text-secondary);
    display: flex;
    font-family: var(--font-mono);
    font-size: 0.68rem;
    gap: 8px;
    margin: 0 0 var(--spacing-sm);
    text-transform: uppercase;
  }

  .kpi-dot {
    background: var(--color-primary);
    border-radius: 999px;
    display: inline-flex;
    height: 6px;
    width: 6px;
  }

  .kpi-card.success .kpi-dot,
  .kpi-card.success .spark-bars i {
    background: var(--color-success);
  }

  .kpi-card.warning .kpi-dot,
  .kpi-card.warning .spark-bars i {
    background: var(--color-warning);
  }

  .kpi-card strong {
    color: var(--color-text);
    display: block;
    font-size: 2rem;
    line-height: 1;
  }

  .kpi-card small {
    color: var(--color-text-secondary);
    font-size: 0.92rem;
    font-weight: 500;
    margin-left: 4px;
  }

  .kpi-card span:not(.kpi-dot) {
    color: var(--color-text-secondary);
    display: block;
    font-size: 0.78rem;
    margin-top: var(--spacing-sm);
  }

  .spark-bars {
    align-items: flex-end;
    display: flex;
    gap: 7px;
    height: 54px;
    opacity: 0.72;
  }

  .spark-bars i {
    background: var(--color-primary);
    border-radius: 999px 999px 0 0;
    box-shadow: 0 0 16px currentColor;
    display: block;
    width: 3px;
  }

  .dashboard-controls {
    align-items: center;
    display: flex;
    gap: var(--spacing-md);
    justify-content: space-between;
    margin-bottom: var(--spacing-md);
  }

  .search-control,
  .filter-row label {
    align-items: center;
    background: rgba(4, 9, 14, 0.88);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-md);
    color: var(--color-text-secondary);
    display: flex;
    gap: 8px;
    min-height: 38px;
    padding: 0 10px;
  }

  .search-control {
    flex: 1;
    max-width: 330px;
  }

  .search-control input,
  .filter-row select {
    background: transparent;
    border: 0;
    box-shadow: none;
    color: var(--color-text);
    min-height: 36px;
    padding: 0;
  }

  .search-control input {
    width: 100%;
  }

  .filter-row {
    align-items: center;
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    justify-content: flex-end;
  }

  .filter-row select {
    min-width: 130px;
  }
  
  .ideas-grid {
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(auto-fill, minmax(282px, 1fr));
  }

  .ideas-grid.list-view {
    grid-template-columns: 1fr;
  }

  .ideas-grid.list-view :global(.idea-card) {
    max-width: 100%;
  }

  .view-toggle {
    align-items: center;
    background: rgba(4, 9, 14, 0.88);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-md);
    display: inline-flex;
    overflow: hidden;
  }

  .view-toggle button {
    background: transparent;
    border: 0;
    border-radius: 0;
    color: var(--color-text-secondary);
    min-height: 36px;
    min-width: 40px;
    padding: 8px;
  }

  .view-toggle .active {
    background: rgba(0, 120, 255, 0.72);
    color: white;
  }

  .add-card,
  .empty-state {
    background:
      linear-gradient(180deg, rgba(5, 10, 15, 0.8), rgba(3, 7, 11, 0.9)),
      linear-gradient(90deg, transparent, rgba(0, 240, 255, 0.08), transparent);
    border: 1px dashed rgba(154, 168, 184, 0.58);
    border-radius: var(--border-radius-lg);
    color: var(--color-text);
  }

  .add-card {
    align-items: flex-start;
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
    justify-content: center;
    min-height: 210px;
    padding: var(--spacing-xl);
    text-align: left;
  }

  .add-card span,
  .empty-mark {
    align-items: center;
    color: var(--color-primary-2);
    display: inline-flex;
    justify-content: center;
  }

  .add-card strong,
  .empty-state h2 {
    font-size: 1.12rem;
    margin: 0;
  }

  .add-card small,
  .empty-state p {
    color: var(--color-text-secondary);
  }

  .empty-state {
    align-items: center;
    display: grid;
    justify-items: center;
    margin-top: var(--spacing-md);
    padding: var(--spacing-xl);
    text-align: center;
  }

  @media (max-width: 1120px) {
    .kpi-strip {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .kpi-card:nth-child(3) {
      border-left: 0;
      border-top: 1px solid var(--color-border);
    }

    .kpi-card:nth-child(4) {
      border-top: 1px solid var(--color-border);
    }
  }

  @media (max-width: 760px) {
    .dashboard-header,
    .dashboard-controls {
      align-items: stretch;
      flex-direction: column;
    }

    .header-actions {
      flex-direction: column;
    }

    .search-control {
      max-width: none;
    }

    .filter-row {
      justify-content: stretch;
    }

    .filter-row label,
    .filter-row select {
      flex: 1;
      min-width: 0;
    }

    .kpi-strip {
      grid-template-columns: 1fr;
    }

    .kpi-card + .kpi-card,
    .kpi-card:nth-child(3),
    .kpi-card:nth-child(4) {
      border-left: 0;
      border-top: 1px solid var(--color-border);
    }
  }
</style>
