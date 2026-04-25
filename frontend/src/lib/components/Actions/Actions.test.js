import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/svelte';
import Actions from './Actions.svelte';
import * as apiModule from '../../api.js';

vi.mock('../../api.js', () => ({
  api: vi.fn(),
  apiPost: vi.fn(),
}));

const mockTasks = {
  idea_id: 'idea-1',
  pending: [
    {
      id: 'task-1',
      idea_id: 'idea-1',
      prompt_text: 'Validate buyer urgency\nFind evidence from credible sources.',
      status: 'pending',
      result_file_path: null,
      created_at: '2026-04-20T10:30:00Z',
      completed_at: null,
    },
  ],
  completed: [
    {
      id: 'task-2',
      idea_id: 'idea-1',
      prompt_text: 'Competitor pricing scan',
      status: 'completed',
      result_file_path: 'task-2-result.md',
      created_at: '2026-04-20T09:00:00Z',
      completed_at: '2026-04-20T11:00:00Z',
    },
  ],
};

describe('Actions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loads and renders pending and completed research actions', async () => {
    apiModule.api.mockImplementation((path) => Promise.resolve(path.endsWith('/jobs') ? { jobs: [] } : mockTasks));

    render(Actions, { ideaId: 'idea-1' });

    await waitFor(() => {
      expect(screen.getByText('Validate buyer urgency')).toBeInTheDocument();
      expect(screen.getAllByText('Competitor pricing scan').length).toBeGreaterThan(0);
    });

    expect(screen.getByText('Awaiting evidence file')).toBeInTheDocument();
    expect(screen.getByText('task-2-result.md')).toBeInTheDocument();
  });

  it('opens the upload modal from a pending card', async () => {
    apiModule.api.mockImplementation((path) => Promise.resolve(path.endsWith('/jobs') ? { jobs: [] } : mockTasks));

    render(Actions, { ideaId: 'idea-1' });

    const uploadButton = await screen.findByRole('button', { name: /upload evidence/i });
    await fireEvent.click(uploadButton);

    expect(screen.getByText('Upload Research File')).toBeInTheDocument();
    expect(screen.getByText('Target task')).toBeInTheDocument();
  });

  it('generates new tasks and reloads the list', async () => {
    apiModule.api.mockImplementation((path) => Promise.resolve(path.endsWith('/jobs') ? { jobs: [] } : mockTasks));
    apiModule.apiPost.mockResolvedValue({ prompts: [] });

    render(Actions, { ideaId: 'idea-1' });

    const generateButton = await screen.findByRole('button', { name: /generate tasks/i });
    await fireEvent.click(generateButton);

    await waitFor(() => {
      expect(apiModule.apiPost).toHaveBeenCalledWith('/api/ideas/idea-1/research/generate');
      expect(apiModule.api).toHaveBeenCalledWith('/api/ideas/idea-1/research/tasks');
      expect(apiModule.api).toHaveBeenCalledWith('/api/ideas/idea-1/jobs');
    });
  });
});
