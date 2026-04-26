import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/svelte';
import LocalWorkers from './LocalWorkers.svelte';
import * as apiModule from '../../api.js';

vi.mock('../../api.js', () => ({
  api: vi.fn(),
  apiPost: vi.fn(),
}));

const dashboard = {
  workers: [
    {
      id: 'worker-1',
      display_name: 'Build Box',
      machine_name: 'WIN-BUILD-1',
      platform: 'Windows',
      engine: 'openclaude',
      status: 'approved',
      capabilities: ['repo_index'],
      last_seen_at: null,
    },
  ],
  requests: [
    {
      id: 'request-1',
      display_name: 'Laptop',
      machine_name: 'LAPTOP-1',
      platform: 'Windows',
      engine: 'openclaude',
      status: 'pending',
      capabilities: ['agent_branch_work'],
    },
  ],
  events: [],
  jobs: [{ id: 'job-1', status: 'queued' }],
  sqs: { commands_configured: true, events_configured: true, region: 'us-east-1' },
};

describe('LocalWorkers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiModule.api.mockResolvedValue(dashboard);
    apiModule.apiPost.mockResolvedValue({ worker: dashboard.workers[0], credentials: { api_token: 'token-1' } });
    Object.assign(navigator, { clipboard: { writeText: vi.fn() } });
  });

  it('renders pending requests, approved workers, and install instructions', async () => {
    render(LocalWorkers);

    await waitFor(() => {
      expect(screen.getByText('Laptop')).toBeInTheDocument();
      expect(screen.getByText('Build Box')).toBeInTheDocument();
    });

    expect(screen.getByText(/install\.ps1 -ApiBase/)).toBeInTheDocument();
    expect(screen.getByText('SQS ready')).toBeInTheDocument();
  });

  it('approves a worker request', async () => {
    render(LocalWorkers);

    const approveButton = await screen.findByRole('button', { name: /approve/i });
    await fireEvent.click(approveButton);

    await waitFor(() => {
      expect(apiModule.apiPost).toHaveBeenCalledWith('/api/local-workers/requests/request-1/approve', {});
      expect(screen.getByText('Newly issued credentials')).toBeInTheDocument();
    });
  });

  it('rotates and revokes approved workers', async () => {
    render(LocalWorkers);

    const rotateButton = await screen.findByRole('button', { name: /rotate/i });
    await fireEvent.click(rotateButton);

    const revokeButton = await screen.findByRole('button', { name: /revoke/i });
    await fireEvent.click(revokeButton);

    await waitFor(() => {
      expect(apiModule.apiPost).toHaveBeenCalledWith('/api/local-workers/worker-1/rotate-credentials', {});
      expect(apiModule.apiPost).toHaveBeenCalledWith('/api/local-workers/worker-1/revoke', {});
    });
  });
});
