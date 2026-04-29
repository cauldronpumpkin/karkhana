import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/svelte';
import ChatView from './ChatView.svelte';
import * as apiModule from '../../api.js';

vi.mock('../../api.js', () => ({
  api: vi.fn(),
  apiPost: vi.fn(),
  apiPut: vi.fn(),
  apiDelete: vi.fn(),
}));

describe('ChatView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.removeItem?.('idearefinery:aiModel');
  });

  function mockApiDefaults() {
    apiModule.api.mockImplementation(async (path) => {
      if (path === '/api/ai/models') {
        return {
          active: { provider: 'codex-lb', model: 'gpt-5.5' },
          providers: [
            {
              id: 'codex-lb',
              name: 'Codex LB',
              models: ['gpt-5.5'],
            },
          ],
        };
      }
      if (path.includes('/chat/history')) return [];
      if (path.includes('/phase')) return { current_phase: 'capture', suggested_phase: null };
      return { id: 'test-idea', title: 'Test Idea', current_phase: 'capture', scores: [] };
    });
  }

  it('renders chat container with title', async () => {
    mockApiDefaults();

    render(ChatView, { props: { ideaId: 'test-idea' } });

    expect(screen.getByText('Idea Chat')).toBeInTheDocument();
  });

  it('sends chat over the REST endpoint', async () => {
    mockApiDefaults();
    apiModule.apiPost.mockResolvedValue({ message_id: 'assistant-1', content: 'Mock reply' });

    render(ChatView, { props: { ideaId: 'test-idea' } });

    const textarea = screen.getByRole('textbox');
    await fireEvent.input(textarea, { target: { value: 'Hello' } });
    await fireEvent.submit(textarea.closest('form'));

    await vi.waitFor(() => {
      expect(apiModule.apiPost).toHaveBeenCalledWith('/api/ideas/test-idea/chat/message', {
        message: 'Hello',
        provider: 'codex-lb',
        model: 'gpt-5.5',
      });
      expect(screen.getByText('Mock reply')).toBeInTheDocument();
    });
  });

  it('displays error message when API fails', async () => {
    apiModule.api.mockRejectedValue(new Error('Network error'));

    render(ChatView, { props: { ideaId: 'test-idea' } });

    await vi.waitFor(() => {
      expect(screen.getByText(/Failed to load chat history|Connecting to chat server/)).toBeInTheDocument();
    });
  });

  it('renders chat input component', async () => {
    mockApiDefaults();

    render(ChatView, { props: { ideaId: 'test-idea' } });

    const textarea = screen.getByRole('textbox');
    expect(textarea).toBeInTheDocument();
  });
});
