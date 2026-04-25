<script>
import { onMount } from 'svelte';
  import {
    ArrowRight,
    BarChart3,
    Bot,
    CheckCircle2,
    Code2,
    FileText,
    RefreshCw,
    Search,
    Target,
    Zap
  } from 'lucide-svelte';
  import { api, apiPost } from '../../api.js';
  import MessageList from './MessageList.svelte';
  import ChatInput from './ChatInput.svelte';
  import PhaseIndicator from './PhaseIndicator.svelte';
  import Badge from '../UI/Badge.svelte';

  let { ideaId = '' } = $props();

  let messages = $state([]);
  let currentMessageId = null;
  let isConnecting = $state(false);
  let error = $state(null);
  let currentPhase = $state('');
  let suggestedPhase = $state(null);
  let idea = $state(null);
  let draftMessage = $state('');
  let contextStatus = $state('idle');
  let aiProviders = $state([]);
  let selectedProvider = $state('');
  let selectedModel = $state('');

  const suggestedPrompts = [
    'Analyze competitors',
    'Price positioning ideas',
    'Go-to-market strategy',
    'Risk assessment'
  ];

  const quickActions = [
    {
      label: 'Run competitor deep dive',
      prompt: 'Run a competitor deep dive for this idea and summarize the sharpest positioning gaps.',
      icon: Search
    },
    {
      label: 'Score my idea',
      prompt: 'Score this idea across the core evaluation dimensions and explain the weakest assumptions.',
      icon: Target
    },
    {
      label: 'Generate build handoff',
      prompt: 'Generate a concise build handoff with implementation steps, risks, and open questions.',
      icon: Code2
    },
    {
      label: 'Create research brief',
      prompt: 'Create a research brief for the next validation pass with sources, questions, and expected outputs.',
      icon: FileText
    }
  ];

  const scoreDimensions = [
    { key: 'tam', label: 'Market Opportunity' },
    { key: 'competition', label: 'Problem Strength' },
    { key: 'feasibility', label: 'Feasibility' },
    { key: 'time_to_mvp', label: 'Time to MVP' },
    { key: 'revenue', label: 'Business Model' },
    { key: 'uniqueness', label: 'Solution Quality' },
    { key: 'personal_fit', label: 'Founder Fit' }
  ];

  let scoreRows = $derived(getScoreRows(idea));
  let compositeScore = $derived(Number(idea?.composite_score || 0));
  let displayScore = $derived(Math.round(compositeScore * 10));
  let availableScoreCount = $derived((idea?.scores || []).length);
  let lastUpdatedLabel = $derived(formatUpdatedAt(idea?.updated_at));

  // Load chat history
  async function loadHistory() {
    try {
      const response = await api(`/api/ideas/${ideaId}/chat/history`);
      messages = response.map(msg => ({
        ...msg,
        timestamp: new Date(msg.timestamp)
      }));
    } catch (err) {
      console.error('Failed to load chat history:', err);
      error = 'Failed to load chat history';
    }
  }

  async function loadIdeaContext() {
    if (!ideaId) return;

    contextStatus = 'loading';
    try {
      idea = await api(`/api/ideas/${ideaId}`);
      if (idea?.current_phase && !currentPhase) {
        currentPhase = idea.current_phase;
      }
      contextStatus = 'ready';
    } catch (err) {
      console.error('Failed to load idea context:', err);
      contextStatus = 'error';
    }
  }

  async function loadAiModels() {
    try {
      const response = await api('/api/ai/models');
      aiProviders = (response.providers || []).filter(provider => (provider.models || []).length > 0);
      const saved = getSavedAiModel();
      const active = saved || response.active || {};
      selectModel(active.provider, active.model);
      if (!selectedProvider || !selectedModel) {
        const firstProvider = aiProviders[0];
        const firstModel = firstProvider?.models?.[0];
        selectModel(firstProvider?.id, firstModel);
      }
    } catch (err) {
      console.error('Failed to load AI models:', err);
      aiProviders = [];
    }
  }

  function selectModel(provider, model) {
    if (!provider || !model) return;
    const providerConfig = aiProviders.find(item => item.id === provider);
    if (providerConfig && !providerConfig.models.includes(model)) return;
    selectedProvider = provider;
    selectedModel = model;
    saveAiModel({ provider, model });
  }

  function getSavedAiModel() {
    try {
      if (typeof localStorage?.getItem !== 'function') return null;
      return JSON.parse(localStorage.getItem('idearefinery:aiModel') || 'null');
    } catch {
      return null;
    }
  }

  function saveAiModel(value) {
    try {
      if (typeof localStorage?.setItem === 'function') {
        localStorage.setItem('idearefinery:aiModel', JSON.stringify(value));
      }
    } catch {
      // Browser storage can be unavailable in private/test contexts.
    }
  }

  // Send message
  async function handleSend(content) {
    const messageId = Date.now().toString();
    currentMessageId = messageId;
    isConnecting = true;
    error = null;

    messages.push({
      id: messageId,
      role: 'user',
      content: content,
      timestamp: new Date(),
      isStreaming: false
    });

    try {
      const response = await apiPost(`/api/ideas/${ideaId}/chat/message`, {
        message: content,
        provider: selectedProvider,
        model: selectedModel
      });
      messages.push({
        id: response.message_id,
        role: 'assistant',
        content: response.content,
        timestamp: new Date(),
        isStreaming: false
      });
      currentMessageId = null;
      await loadIdeaContext();
    } catch (err) {
      console.error('Failed to send message:', err);
      error = 'Failed to send message';
    } finally {
      isConnecting = false;
    }
  }

  function handlePromptChip(prompt) {
    draftMessage = prompt;
  }

  function handleQuickAction(prompt) {
    handleSend(prompt);
  }

  // Handle phase approval
  async function handlePhaseApprove(newPhase) {
    try {
      await apiPost(`/api/ideas/${ideaId}/phase/approve`);
      if (newPhase) currentPhase = newPhase;
      await loadIdeaContext();
    } catch (err) {
      console.error('Failed to approve phase:', err);
    }
  }

  // Handle phase rejection
  async function handlePhaseReject(data) {
    try {
      await apiPost(`/api/ideas/${ideaId}/phase/reject`, { 
        reason: data.reason 
      });
      suggestedPhase = null;
    } catch (err) {
      console.error('Failed to reject phase:', err);
    }
  }

  function getScoreRows(ideaData) {
    const scores = ideaData?.scores || [];

    return scoreDimensions.map(dimension => {
      const score = scores.find(item => item.dimension === dimension.key);
      return {
        ...dimension,
        value: Number(score?.value || 0),
        rationale: score?.rationale || ''
      };
    });
  }

  function scoreLabel(score) {
    if (score >= 8) return 'Strong Potential';
    if (score >= 6) return 'Promising';
    if (score >= 4) return 'Needs Proof';
    return 'Unscored';
  }

  function formatUpdatedAt(value) {
    if (!value) return 'No update yet';

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'No update yet';

    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric'
    });
  }

  onMount(async () => {
    await loadAiModels();
    await loadHistory();
    await loadIdeaContext();
    
    try {
      const phaseResponse = await api(`/api/ideas/${ideaId}/phase`);
      currentPhase = phaseResponse.current_phase;
      suggestedPhase = phaseResponse.suggested_phase;
    } catch (err) {
      console.error('Failed to fetch phase info:', err);
    }
  });

</script>

<section class="chat-workspace" aria-label="Idea Chat">
  <header class="chat-header">
    <div>
      <div class="eyebrow">AI cofounder workspace</div>
      <h1>Idea Chat</h1>
    </div>

    <PhaseIndicator 
      {currentPhase} 
      {suggestedPhase}
      {ideaId}
      connectionState={isConnecting ? 'connecting' : 'online'}
      onapprovePhase={handlePhaseApprove}
      onrejectPhase={handlePhaseReject}
    />
  </header>

  {#if error}
    <div class="error-message">
      {error}
    </div>
  {/if}

  <div class="chat-grid">
    <main class="conversation-panel">
      <div class="chat-container">
        <MessageList {messages} showTimestamps={true} autoScroll={true} />
        
        {#if isConnecting}
          <div class="connecting-message">
            Connecting to chat server...
          </div>
        {/if}
      </div>

      <div class="composer-stack">
        <ChatInput 
          bind:value={draftMessage}
          providers={aiProviders}
          {selectedProvider}
          {selectedModel}
          onmodelChange={({ provider, model }) => selectModel(provider, model)}
          onsend={handleSend}
          disabled={isConnecting}
          placeholder="Ask anything about your idea..."
        />

        <div class="suggested-prompts">
          <div class="section-label">Suggested prompts</div>
          <div class="prompt-chip-row">
            {#each suggestedPrompts as prompt}
              <button class="prompt-chip" type="button" onclick={() => handlePromptChip(prompt)}>
                <Zap size={13} aria-hidden="true" />
                <span>{prompt}</span>
              </button>
            {/each}
            <button class="refresh-chip" type="button" onclick={loadIdeaContext} aria-label="Refresh idea context">
              <RefreshCw size={14} aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>
    </main>

    <aside class="context-rail" aria-label="Idea context">
      <section class="rail-card idea-card">
        <div class="rail-heading">
          <span>Idea context</span>
          <Badge variant={contextStatus === 'ready' ? 'success' : 'muted'} size="sm">
            {contextStatus}
          </Badge>
        </div>
        <h2>{idea?.title || 'Current idea'}</h2>
        <p>{idea?.description || 'Context will appear once the idea loads.'}</p>
        <div class="idea-meta-row">
          <Badge variant="primary" size="sm">
            {currentPhase || idea?.current_phase || 'capture'}
          </Badge>
          <span>Updated {lastUpdatedLabel}</span>
        </div>
      </section>

      <section class="rail-card score-card">
        <div class="rail-heading">
          <span>Score overview</span>
          <BarChart3 size={16} aria-hidden="true" />
        </div>

        <div class="score-hero">
          <div>
            <span class="score-kicker">Overall score</span>
            <strong>{displayScore}</strong>
            <span class="score-max">/100</span>
          </div>
          <Badge variant={displayScore >= 70 ? 'success' : displayScore >= 40 ? 'warning' : 'muted'} size="sm">
            {scoreLabel(compositeScore)}
          </Badge>
        </div>

        <div class="radar-placeholder" aria-hidden="true">
          <div class="radar-grid"></div>
          <div class="radar-shape" style={`clip-path: polygon(50% ${Math.max(10, 64 - displayScore / 2)}%, 88% 40%, 74% 86%, 30% 82%, 12% 42%);`}></div>
        </div>

        <div class="score-breakdown">
          {#each scoreRows as row (row.key)}
            <div class="score-row">
              <span>{row.label}</span>
              <div class="score-track" title={row.rationale || 'Awaiting score'}>
                <div class="score-fill" style={`width: ${row.value * 10}%`}></div>
              </div>
              <strong>{Math.round(row.value * 10)}</strong>
            </div>
          {/each}
        </div>

        {#if availableScoreCount === 0}
          <p class="placeholder-note">Scores will populate after the score phase runs.</p>
        {/if}
      </section>

      <section class="rail-card next-phase-card">
        <div class="rail-heading">
          <span>Suggested next phase</span>
          <Bot size={16} aria-hidden="true" />
        </div>
        <div class="next-phase-content">
          <div>
            <strong>{suggestedPhase || 'Score'}</strong>
            <p>Quantify opportunity and validate assumptions.</p>
          </div>
          <button
            class="phase-jump"
            type="button"
            onclick={() => handleQuickAction('Move this idea toward the next phase and tell me what evidence is missing.')}
            aria-label="Ask about next phase"
          >
            <ArrowRight size={17} aria-hidden="true" />
          </button>
        </div>
      </section>

      <section class="rail-card quick-actions-card">
        <div class="rail-heading">
          <span>Quick actions</span>
          <CheckCircle2 size={16} aria-hidden="true" />
        </div>
        <div class="quick-action-list">
          {#each quickActions as action}
            {@const Icon = action.icon}
            <button
              class="quick-action"
              type="button"
              onclick={() => handleQuickAction(action.prompt)}
              disabled={isConnecting}
            >
              <Icon size={16} aria-hidden="true" />
              <span>{action.label}</span>
            </button>
          {/each}
        </div>
      </section>
    </aside>
  </div>
</section>

<style>
  .chat-workspace {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
    min-height: calc(100vh - 150px);
  }

  .chat-header {
    align-items: center;
    display: flex;
    gap: var(--spacing-lg);
    justify-content: space-between;
  }

  .eyebrow,
  .section-label,
  .rail-heading {
    color: var(--color-text-muted);
    font-family: var(--font-mono);
    font-size: 0.72rem;
    letter-spacing: 0;
    text-transform: uppercase;
  }

  h1 {
    color: var(--color-text);
    font-size: 1.35rem;
    line-height: 1.1;
    margin: 4px 0 0;
  }

  .error-message {
    background-color: rgba(255, 71, 87, 0.1);
    border: 1px solid var(--color-error);
    border-radius: var(--border-radius-sm);
    color: var(--color-error);
    padding: var(--spacing-md);
  }

  .chat-grid {
    display: grid;
    gap: var(--spacing-md);
    grid-template-columns: minmax(0, 1fr) minmax(300px, 360px);
    min-height: 0;
  }

  .conversation-panel,
  .context-rail {
    min-width: 0;
  }

  .conversation-panel {
    background:
      linear-gradient(180deg, rgba(9, 15, 22, 0.92), rgba(4, 8, 13, 0.96)),
      radial-gradient(circle at 0 0, rgba(0, 194, 255, 0.09), transparent 34%);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
    display: flex;
    flex-direction: column;
    min-height: 680px;
    overflow: hidden;
  }

  .chat-container {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-height: 420px;
    position: relative;
  }

  .connecting-message {
    background: rgba(0, 0, 0, 0.34);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-sm);
    bottom: var(--spacing-md);
    color: var(--color-text-secondary);
    left: 50%;
    padding: var(--spacing-sm) var(--spacing-md);
    position: absolute;
    transform: translateX(-50%);
  }

  .composer-stack {
    border-top: 1px solid rgba(103, 128, 151, 0.2);
    padding: var(--spacing-sm);
  }

  .suggested-prompts {
    display: grid;
    gap: var(--spacing-xs);
    margin-top: var(--spacing-sm);
  }

  .prompt-chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-sm);
  }

  .prompt-chip,
  .refresh-chip,
  .quick-action,
  .phase-jump {
    align-items: center;
    background: rgba(7, 13, 19, 0.86);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-sm);
    color: var(--color-text-secondary);
    cursor: pointer;
    display: inline-flex;
    font: inherit;
    gap: var(--spacing-xs);
    min-height: 34px;
    padding: 7px 10px;
  }

  .prompt-chip:hover,
  .refresh-chip:hover,
  .quick-action:hover,
  .phase-jump:hover {
    border-color: var(--color-accent);
    color: var(--color-text);
  }

  .refresh-chip {
    justify-content: center;
    margin-left: auto;
    width: 36px;
  }

  .context-rail {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .rail-card {
    background:
      linear-gradient(180deg, rgba(10, 17, 24, 0.96), rgba(5, 10, 15, 0.94)),
      radial-gradient(circle at 100% 0%, rgba(82, 245, 106, 0.06), transparent 42%);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-lg);
    padding: var(--spacing-md);
  }

  .rail-heading {
    align-items: center;
    display: flex;
    justify-content: space-between;
    margin-bottom: var(--spacing-sm);
  }

  .idea-card h2 {
    color: var(--color-text);
    font-size: 1.05rem;
    margin: 0 0 var(--spacing-sm);
  }

  .idea-card p,
  .next-phase-content p,
  .placeholder-note {
    color: var(--color-text-secondary);
    font-size: 0.9rem;
    line-height: 1.5;
    margin: 0;
  }

  .idea-meta-row {
    align-items: center;
    border-top: 1px solid rgba(103, 128, 151, 0.18);
    color: var(--color-text-muted);
    display: flex;
    font-size: 0.8rem;
    gap: var(--spacing-sm);
    justify-content: space-between;
    margin-top: var(--spacing-md);
    padding-top: var(--spacing-sm);
  }

  .score-hero {
    align-items: flex-end;
    display: flex;
    justify-content: space-between;
    margin-bottom: var(--spacing-md);
  }

  .score-kicker,
  .score-max {
    color: var(--color-text-secondary);
    font-size: 0.78rem;
  }

  .score-hero strong {
    color: var(--color-success);
    font-size: 2.6rem;
    line-height: 1;
    margin-left: 0;
  }

  .radar-placeholder {
    aspect-ratio: 1.75;
    border: 1px solid rgba(82, 245, 106, 0.18);
    border-radius: var(--border-radius-sm);
    display: grid;
    margin-bottom: var(--spacing-md);
    overflow: hidden;
    place-items: center;
    position: relative;
  }

  .radar-grid {
    background:
      linear-gradient(rgba(82, 245, 106, 0.14) 1px, transparent 1px),
      linear-gradient(90deg, rgba(82, 245, 106, 0.14) 1px, transparent 1px);
    background-size: 28px 28px;
    inset: 0;
    opacity: 0.7;
    position: absolute;
  }

  .radar-shape {
    background: rgba(82, 245, 106, 0.24);
    border: 1px solid var(--color-success);
    height: 74%;
    position: relative;
    width: 74%;
  }

  .score-breakdown {
    display: grid;
    gap: var(--spacing-sm);
  }

  .score-row {
    align-items: center;
    display: grid;
    gap: var(--spacing-sm);
    grid-template-columns: minmax(112px, 1fr) minmax(72px, 0.7fr) 32px;
  }

  .score-row span,
  .score-row strong {
    color: var(--color-text-secondary);
    font-size: 0.78rem;
  }

  .score-row strong {
    color: var(--color-text);
    text-align: right;
  }

  .score-track {
    background: rgba(103, 128, 151, 0.22);
    border-radius: 999px;
    height: 4px;
    overflow: hidden;
  }

  .score-fill {
    background: linear-gradient(90deg, var(--color-success), var(--color-accent));
    height: 100%;
    min-width: 2px;
  }

  .placeholder-note {
    border-top: 1px solid rgba(103, 128, 151, 0.18);
    font-size: 0.8rem;
    margin-top: var(--spacing-md);
    padding-top: var(--spacing-sm);
  }

  .next-phase-content {
    align-items: center;
    display: flex;
    gap: var(--spacing-md);
    justify-content: space-between;
  }

  .next-phase-content strong {
    color: var(--color-text);
  }

  .phase-jump {
    background: linear-gradient(180deg, rgba(255, 159, 28, 0.94), rgba(206, 102, 7, 0.94));
    color: #fff;
    justify-content: center;
    min-width: 38px;
  }

  .quick-action-list {
    border: 1px solid rgba(103, 128, 151, 0.2);
    border-radius: var(--border-radius-sm);
    overflow: hidden;
  }

  .quick-action {
    border: 0;
    border-bottom: 1px solid rgba(103, 128, 151, 0.2);
    border-radius: 0;
    justify-content: flex-start;
    width: 100%;
  }

  .quick-action:last-child {
    border-bottom: 0;
  }

  .quick-action:disabled {
    cursor: not-allowed;
    opacity: 0.58;
  }

  @media (max-width: 1180px) {
    .chat-grid {
      grid-template-columns: 1fr;
    }

    .context-rail {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 760px) {
    .chat-header {
      align-items: flex-start;
      flex-direction: column;
    }

    .conversation-panel {
      min-height: 640px;
    }

    .context-rail {
      grid-template-columns: 1fr;
    }

    .refresh-chip {
      margin-left: 0;
    }
  }
</style>
