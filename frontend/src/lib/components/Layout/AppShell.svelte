<script>
  import { Bell, Command, Plus, Zap } from 'lucide-svelte';
  import Sidebar from './Sidebar.svelte';

  let { currentRoute, activeIdeaId = '', onnewIdea, children } = $props();

  const routeTitles = {
    dashboard: 'Dashboard',
    chat: 'Chat',
    project: 'Project Twin',
    reports: 'Reports',
    actions: 'Research Actions',
    workers: 'Local Workers',
    templates: 'Templates'
  };

  function navigateActive(route) {
    if (activeIdeaId) {
      window.location.hash = `/${route}/${activeIdeaId}`;
      return;
    }
    window.location.hash = '/dashboard';
  }
</script>

<div class="app-shell">
  <Sidebar {currentRoute} {activeIdeaId} />
  <div class="workspace">
    <header class="topbar">
      <div class="route-status">
        <span class="status-dot"></span>
        <span class="mono-label">{routeTitles[currentRoute] || 'Command Center'}</span>
      </div>
      <div class="topbar-actions">
        <div class="agents">
          <span>Agents online</span>
          <strong>5 / 5</strong>
        </div>
        <button class="command-button" type="button" onclick={() => navigateActive('chat')} disabled={!activeIdeaId}>
          <Command size={16} />
          Open Command Center
        </button>
        <button class="icon-button" type="button" aria-label="Notifications unavailable" title="Notifications are not wired yet" disabled>
          <Bell size={17} />
          <span class="notification-dot">3</span>
        </button>
        <button class="new-idea" type="button" onclick={() => onnewIdea?.()}>
          <Plus size={17} />
          New Idea
        </button>
      </div>
    </header>

    <main class="main-content">
      {@render children()}
    </main>

    <footer class="app-footer">
      <span>© 2025 IdeaRefinery. All systems operational.</span>
      <span class="footer-pulse"><Zap size={13} /> v1.0.0</span>
    </footer>
  </div>
</div>

<style>
  .app-shell {
    display: flex;
    min-height: 100vh;
  }

  .workspace {
    display: flex;
    flex: 1;
    flex-direction: column;
    margin-left: var(--sidebar-width);
    min-height: 100vh;
    min-width: 0;
  }

  .topbar {
    align-items: center;
    backdrop-filter: blur(16px);
    background: rgba(2, 5, 7, 0.78);
    border-bottom: 1px solid var(--color-border);
    display: flex;
    gap: var(--spacing-md);
    justify-content: space-between;
    min-height: 62px;
    padding: 0 var(--spacing-lg);
    position: sticky;
    top: 0;
    z-index: 50;
  }

  .route-status {
    align-items: center;
    display: flex;
    gap: 10px;
  }

  .topbar-actions {
    align-items: center;
    display: flex;
    gap: 12px;
  }

  .agents {
    color: var(--color-success);
    display: grid;
    font-family: var(--font-mono);
    font-size: 0.68rem;
    line-height: 1.25;
    text-transform: uppercase;
  }

  .agents strong {
    color: var(--color-success);
    font-size: 0.86rem;
  }

  .command-button,
  .icon-button {
    background: rgba(5, 10, 15, 0.86);
    border-color: var(--color-border);
    color: var(--color-text);
  }

  .command-button {
    min-width: 210px;
  }

  .icon-button {
    min-height: 38px;
    min-width: 40px;
    padding: 8px;
    position: relative;
  }

  .notification-dot {
    align-items: center;
    background: var(--color-primary);
    border-radius: 999px;
    display: inline-flex;
    font-size: 0.62rem;
    height: 16px;
    justify-content: center;
    position: absolute;
    right: -5px;
    top: -5px;
    width: 16px;
  }

  .new-idea {
    min-width: 128px;
  }

  .main-content {
    flex: 1;
    padding: var(--spacing-lg) var(--spacing-xl) var(--spacing-xl);
  }

  .app-footer {
    align-items: center;
    border-top: 1px solid var(--color-border);
    color: var(--color-text-muted);
    display: flex;
    font-size: 0.78rem;
    justify-content: space-between;
    padding: var(--spacing-md) var(--spacing-xl);
  }

  .footer-pulse {
    align-items: center;
    color: var(--color-success);
    display: inline-flex;
    gap: 7px;
  }

  @media (max-width: 980px) {
    .topbar {
      align-items: flex-start;
      flex-direction: column;
      padding: var(--spacing-md);
    }

    .topbar-actions {
      flex-wrap: wrap;
      width: 100%;
    }
  }

  @media (max-width: 820px) {
    .workspace {
      margin-left: 0;
    }

    .main-content {
      padding: var(--spacing-md);
      padding-top: 84px;
    }

    .app-footer {
      align-items: flex-start;
      flex-direction: column;
      gap: var(--spacing-sm);
      padding: var(--spacing-md);
    }

    .command-button,
    .agents {
      display: none;
    }
  }
</style>
