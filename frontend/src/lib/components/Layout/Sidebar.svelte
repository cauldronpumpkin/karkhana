<script>
  import {
    BarChart3,
    Blocks,
    Box,
    FileText,
    GitBranch,
    LayoutDashboard,
    MessageCircle,
    Plug,
    Settings,
    TerminalSquare,
    UploadCloud
  } from 'lucide-svelte';

  let { currentRoute = 'dashboard', activeIdeaId = '' } = $props();

  const navItems = [
    { name: 'Dashboard', route: 'dashboard', icon: LayoutDashboard, requiresIdea: false },
    { name: 'Chat', route: 'chat', icon: MessageCircle, requiresIdea: true },
    { name: 'Project Twin', route: 'project', icon: GitBranch, requiresIdea: true },
    { name: 'Reports', route: 'reports', icon: FileText, requiresIdea: true },
    { name: 'Research Actions', route: 'actions', icon: BarChart3, requiresIdea: true }
  ];

  const resources = [
    { name: 'Templates', icon: Blocks },
    { name: 'Prompt Library', icon: TerminalSquare },
    { name: 'Integrations', icon: Plug },
    { name: 'Settings', icon: Settings }
  ];

  function navHref(item) {
    if (!item.requiresIdea) return '#/dashboard';
    return activeIdeaId ? `#/${item.route}/${activeIdeaId}` : '#/dashboard';
  }
</script>

<nav class="sidebar" aria-label="Primary navigation">
  <a class="brand" href="#/dashboard" aria-label="IdeaRefinery dashboard">
    <span class="brand-mark"><Box size={23} /></span>
    <span>IdeaRefinery</span>
    <span class="prompt">&gt;_</span>
  </a>

  <div class="nav-section">
    <p>Main</p>
    {#each navItems as item}
      {@const Icon = item.icon}
      <a
        href={navHref(item)}
        class:active={currentRoute === item.route}
        class="nav-link"
        aria-disabled={item.requiresIdea && !activeIdeaId}
        title={item.requiresIdea && !activeIdeaId ? 'Create an idea first' : item.name}
      >
        <Icon size={16} />
        <span>{item.name}</span>
      </a>
    {/each}
  </div>

  <div class="nav-section workspace-picker">
    <p>Workspace</p>
    <button type="button" class="workspace-button" disabled title="Workspace switching is not wired yet">
      <UploadCloud size={15} />
      <span>Acme Ventures</span>
      <span>⌄</span>
    </button>
  </div>

  <div class="nav-section">
    <p>Tools</p>
    {#each resources as item}
      {@const Icon = item.icon}
      <a href="#/dashboard" class="nav-link subtle">
        <Icon size={16} />
        <span>{item.name}</span>
      </a>
    {/each}
  </div>

  <div class="command-log">
    <div class="log-header">
      <span><span class="status-dot"></span> Command log</span>
      <strong>Live</strong>
    </div>
    <p>10:42:13 <span>System online</span></p>
    <p>10:42:14 <span>Agents 5/5</span></p>
    <p>10:42:18 <span>Research queue updated</span></p>
    <p>10:42:21 <span>2 handoffs ready</span></p>
    <small>&gt;_</small>
  </div>

  <div class="user-card">
    <span class="avatar">JD</span>
    <span>
      <strong>John Doe</strong>
      <small>Founder</small>
    </span>
    <span>⌄</span>
  </div>
</nav>

<style>
  .sidebar {
    background: linear-gradient(180deg, rgba(2, 5, 7, 0.98), rgba(4, 9, 14, 0.98));
    border-right: 1px solid var(--color-border);
    bottom: 0;
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
    left: 0;
    overflow-y: auto;
    padding: var(--spacing-md) 14px;
    position: fixed;
    top: 0;
    width: var(--sidebar-width);
    z-index: 80;
  }

  .brand {
    align-items: center;
    border-bottom: 1px solid var(--color-border);
    color: var(--color-text);
    display: flex;
    font-size: 1.18rem;
    font-weight: 800;
    gap: 10px;
    min-height: 48px;
    padding-bottom: var(--spacing-md);
  }

  .brand-mark {
    align-items: center;
    border: 1px solid var(--color-accent);
    border-radius: 8px;
    color: var(--color-accent);
    display: inline-flex;
    height: 34px;
    justify-content: center;
    width: 34px;
  }

  .prompt {
    color: var(--color-success);
    font-family: var(--font-mono);
    margin-left: auto;
  }

  .nav-section {
    border-bottom: 1px solid rgba(103, 128, 151, 0.16);
    display: grid;
    gap: 7px;
    padding-bottom: var(--spacing-md);
  }

  .nav-section p {
    color: var(--color-text-muted);
    font-family: var(--font-mono);
    font-size: 0.68rem;
    margin: 0 0 var(--spacing-xs);
    text-transform: uppercase;
  }

  .nav-link,
  .workspace-button {
    align-items: center;
    background: transparent;
    border: 1px solid transparent;
    border-radius: var(--border-radius-md);
    color: var(--color-text-secondary);
    display: flex;
    font-size: 0.92rem;
    gap: 11px;
    min-height: 38px;
    padding: 9px 10px;
    text-align: left;
  }

  .nav-link:hover,
  .workspace-button:hover,
  .nav-link.active {
    background: linear-gradient(90deg, rgba(0, 120, 255, 0.16), rgba(0, 240, 255, 0.04));
    border-color: rgba(0, 174, 255, 0.28);
    color: var(--color-text);
    text-decoration: none;
  }

  .nav-link.active {
    box-shadow: inset -2px 0 0 var(--color-primary-2);
  }

  .subtle {
    color: #8995a3;
  }

  .workspace-button {
    justify-content: space-between;
    width: 100%;
  }

  .command-log {
    background: rgba(4, 9, 14, 0.88);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
    color: var(--color-text-muted);
    font-family: var(--font-mono);
    font-size: 0.68rem;
    margin-top: auto;
    padding: var(--spacing-md);
  }

  .log-header {
    align-items: center;
    color: var(--color-text);
    display: flex;
    justify-content: space-between;
    margin-bottom: var(--spacing-sm);
    text-transform: uppercase;
  }

  .log-header span {
    align-items: center;
    display: inline-flex;
    gap: 7px;
  }

  .log-header strong,
  .command-log span,
  .command-log small {
    color: var(--color-success);
  }

  .command-log p {
    margin: 7px 0;
  }

  .user-card {
    align-items: center;
    border-top: 1px solid var(--color-border);
    display: flex;
    gap: var(--spacing-sm);
    padding-top: var(--spacing-md);
  }

  .avatar {
    align-items: center;
    background: linear-gradient(180deg, rgba(26, 33, 42, 0.95), rgba(11, 16, 22, 0.95));
    border: 1px solid var(--color-border);
    border-radius: 999px;
    display: inline-flex;
    flex: 0 0 auto;
    height: 42px;
    justify-content: center;
    width: 42px;
  }

  .user-card span:nth-child(2) {
    display: grid;
    flex: 1;
  }

  .user-card small {
    color: var(--color-text-secondary);
  }

  @media (max-width: 820px) {
    .sidebar {
      bottom: auto;
      flex-direction: row;
      min-height: 64px;
      overflow-x: auto;
      overflow-y: hidden;
      padding: 10px;
      right: 0;
      width: 100%;
    }

    .brand {
      border-bottom: 0;
      min-width: max-content;
      padding-bottom: 0;
    }

    .nav-section {
      align-items: center;
      border-bottom: 0;
      display: flex;
      padding-bottom: 0;
    }

    .nav-section p,
    .workspace-picker,
    .command-log,
    .user-card,
    .subtle {
      display: none;
    }

    .nav-link {
      min-width: max-content;
    }
  }
</style>
