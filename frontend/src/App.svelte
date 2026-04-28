<script>
  import { onMount } from 'svelte';
  import AppShell from './lib/components/Layout/AppShell.svelte';
  import Dashboard from './lib/components/Dashboard/Dashboard.svelte';
  import ChatView from './lib/components/Chat/ChatView.svelte';
  import Reports from './lib/components/Reports/Reports.svelte';
  import Actions from './lib/components/Actions/Actions.svelte';
  import ProjectTwinView from './lib/components/ProjectTwin/ProjectTwinView.svelte';
  import KarkhanaRunPanel from './lib/components/Karkhana/KarkhanaRunPanel.svelte';
  import LocalWorkers from './lib/components/LocalWorkers/LocalWorkers.svelte';
  import CreateIdea from './lib/components/Dashboard/CreateIdea.svelte';
  import { api } from './lib/api.js';

  let currentRoute = $state('dashboard');
  let routeParams = $state({});
  let activeIdeaId = $state('');
  let showCreateIdea = $state(false);

  const ACTIVE_IDEA_KEY = 'idearefinery:activeIdeaId';

  async function loadActiveIdea() {
    try {
      const ideas = await api('/api/ideas');
      const storedIdeaId = localStorage.getItem(ACTIVE_IDEA_KEY) || '';
      const storedIdea = ideas.find((idea) => idea.id === storedIdeaId);
      const firstIdea = ideas.find((idea) => idea.status !== 'archived') || ideas[0];
      activeIdeaId = storedIdea?.id || firstIdea?.id || '';
    } catch (err) {
      console.error('Failed to load active idea:', err);
      activeIdeaId = localStorage.getItem(ACTIVE_IDEA_KEY) || '';
    }
  }

  function setActiveIdea(ideaId) {
    if (!ideaId) return;
    activeIdeaId = ideaId;
    localStorage.setItem(ACTIVE_IDEA_KEY, ideaId);
  }

  function parseHash() {
    const hash = window.location.hash.slice(1) || '/dashboard';
    const parts = hash.split('/').filter(Boolean);
    
    if (parts[0] === 'chat' && parts[1]) {
      currentRoute = 'chat';
      routeParams = { ideaId: parts[1] };
      setActiveIdea(parts[1]);
    } else if (parts[0] === 'reports' && parts[1]) {
      currentRoute = 'reports';
      routeParams = { ideaId: parts[1], phase: parts[2] || null };
      setActiveIdea(parts[1]);
    } else if (parts[0] === 'actions' && parts[1]) {
      currentRoute = 'actions';
      routeParams = { ideaId: parts[1] };
      setActiveIdea(parts[1]);
    } else if (parts[0] === 'project' && parts[1]) {
      currentRoute = 'project';
      routeParams = { ideaId: parts[1] };
      setActiveIdea(parts[1]);
    } else if (parts[0] === 'karkhana' && parts[1]) {
      currentRoute = 'karkhana';
      routeParams = { ideaId: parts[1], runId: parts[2] || '' };
      setActiveIdea(parts[1]);
    } else if (parts[0] === 'workers') {
      currentRoute = 'workers';
      routeParams = {};
    } else {
      currentRoute = 'dashboard';
      routeParams = {};
    }
  }

  function handleNewIdea() {
    showCreateIdea = true;
  }

  function handleIdeaCreated(newIdea) {
    showCreateIdea = false;
    if (newIdea?.id) {
      setActiveIdea(newIdea.id);
      window.location.hash = `/chat/${newIdea.id}`;
    } else {
      loadActiveIdea();
    }
  }

  onMount(() => {
    loadActiveIdea();
    parseHash();
    window.addEventListener('hashchange', parseHash);
    return () => window.removeEventListener('hashchange', parseHash);
  });
</script>

<AppShell {currentRoute} {activeIdeaId} onnewIdea={handleNewIdea}>
  {#if currentRoute === 'dashboard'}
    <Dashboard />
  {:else if currentRoute === 'chat'}
    <ChatView ideaId={routeParams.ideaId} />
  {:else if currentRoute === 'reports'}
    <Reports ideaId={routeParams.ideaId} phase={routeParams.phase} />
  {:else if currentRoute === 'actions'}
    <Actions ideaId={routeParams.ideaId} />
  {:else if currentRoute === 'project'}
    <ProjectTwinView ideaId={routeParams.ideaId} />
  {:else if currentRoute === 'karkhana'}
    <KarkhanaRunPanel factoryRunId={routeParams.runId} autonomyLevel="autonomous_development" />
  {:else if currentRoute === 'workers'}
    <LocalWorkers />
  {/if}
</AppShell>

{#if showCreateIdea}
  <CreateIdea
    onclose={() => showCreateIdea = false}
    onideaCreated={handleIdeaCreated}
  />
{/if}
