import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import ProjectTwinView from './ProjectTwinView.svelte';

vi.mock('../../api.js', () => ({
  api: vi.fn(),
  apiPost: vi.fn(),
  getBuildNextActions: vi.fn(),
}));

import { api, getBuildNextActions } from '../../api.js';

describe('ProjectTwinView clipboard handling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.mockResolvedValue({
      project: { id: 'project-1', repo_full_name: 'acme/factory-app', index_status: 'indexed', health_status: 'healthy', default_branch: 'main' },
      latest_index: null,
      factory_runs: [],
      jobs: [],
    });
    getBuildNextActions.mockResolvedValue({
      status_summary: { current_phase: 'build', current_step: 'backend', project_attached: true },
      next_actions: [{ title: 'Advance', priority: 1, suggested_owner: 'local-worker', reason: 'Next', codex_prompt: 'copy me' }],
    });
  });

  it('shows success feedback when clipboard copy works', async () => {
    navigator.clipboard.writeText = vi.fn().mockResolvedValue(undefined);

    render(ProjectTwinView, { props: { ideaId: 'idea-1' } });

    const copyButton = await screen.findByRole('button', { name: /copy prompt/i });
    await fireEvent.click(copyButton);

    await waitFor(() => expect(screen.getByText(/prompt copied to clipboard/i)).toBeInTheDocument());
  });

  it('falls back to execCommand when clipboard copy is blocked', async () => {
    navigator.clipboard.writeText = vi.fn().mockRejectedValue(new Error('blocked'));
    document.execCommand = vi.fn().mockReturnValue(true);

    render(ProjectTwinView, { props: { ideaId: 'idea-1' } });

    const copyButton = await screen.findByRole('button', { name: /copy prompt/i });
    await fireEvent.click(copyButton);

    await waitFor(() => expect(screen.getByText(/prompt copied to clipboard/i)).toBeInTheDocument());
    expect(document.execCommand).toHaveBeenCalledWith('copy');
  });

  it('shows failure feedback when clipboard fallback is unavailable', async () => {
    navigator.clipboard.writeText = undefined;
    document.execCommand = vi.fn().mockReturnValue(false);

    render(ProjectTwinView, { props: { ideaId: 'idea-1' } });

    const copyButton = await screen.findByRole('button', { name: /copy prompt/i });
    await fireEvent.click(copyButton);

    await waitFor(() => expect(screen.getByText(/clipboard fallback unavailable/i)).toBeInTheDocument());
  });
});
