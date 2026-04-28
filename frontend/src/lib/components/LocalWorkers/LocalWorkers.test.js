import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/svelte';
import LocalWorkers from './LocalWorkers.svelte';

vi.mock('../../api.js', () => ({
  API_BASE: '',
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
    fetch.mockImplementation((url, options = {}) => {
      if (url === '/api/local-workers' && !options.method) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(dashboard) });
      }
      if (url.startsWith('/api/worker/invite-link')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ invite_link: 'idearefinery://connect?api_base=http%3A%2F%2Flocalhost' }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    });
    Object.assign(navigator, { clipboard: { writeText: vi.fn() } });
  });

  it('renders pending requests and approved workers', async () => {
    render(LocalWorkers);

    await waitFor(() => {
      expect(screen.getByText('Laptop')).toBeInTheDocument();
      expect(screen.getByText('Build Box')).toBeInTheDocument();
    });

    expect(screen.getByText('Worker management')).toBeInTheDocument();
  });

  it('approves a worker request', async () => {
    render(LocalWorkers);

    const approveButton = await screen.findByRole('button', { name: /approve/i });
    await fireEvent.click(approveButton);

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        '/api/local-workers/requests/request-1/approve',
        expect.objectContaining({ method: 'POST', body: '{}' })
      );
    });
  });

  it('rotates and revokes approved workers', async () => {
    render(LocalWorkers);

    const rotateButton = await screen.findByRole('button', { name: /rotate/i });
    await fireEvent.click(rotateButton);

    const revokeButton = await screen.findByRole('button', { name: /revoke/i });
    await fireEvent.click(revokeButton);

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        '/api/local-workers/worker-1/rotate-credentials',
        expect.objectContaining({ method: 'POST', body: '{}' })
      );
      expect(fetch).toHaveBeenCalledWith(
        '/api/local-workers/worker-1/revoke',
        expect.objectContaining({ method: 'POST', body: '{}' })
      );
    });
  });
});
