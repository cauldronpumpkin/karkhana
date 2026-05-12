import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/svelte';
import LocalWorkers from './LocalWorkers.svelte';
import * as apiModule from '../../api.js';

vi.mock('../../api.js', () => ({
  api: vi.fn(),
  buildApiUrl: vi.fn((path, query = null, base = '') => {
    const url = base ? `${base.replace(/\/$/, '')}/${path.replace(/^\/+/, '')}` : path;
    if (!query) return url;

    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(query)) {
      if (value === undefined || value === null || value === '') continue;
      params.set(key, String(value));
    }

    const search = params.toString();
    return search ? `${url}?${search}` : url;
  }),
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
    {
      id: 'worker-revoked',
      display_name: 'Old Build Box',
      machine_name: 'WIN-OLD-1',
      platform: 'Windows',
      engine: 'openclaude',
      status: 'revoked',
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
  jobs: [{
    id: 'job-1',
    job_type: 'agent_branch_work',
    status: 'failed_retryable',
    priority: 40,
    retry_count: 1,
    worker_state: { worker_id: 'worker-1' },
    engine: 'opencode',
    model: 'gpt-test',
    agent_name: 'build',
    command: 'opencode run --dangerously-skip-permissions <prompt>',
    branch_name: 'factory/job-1/fix',
    draft_pr: {
      html_url: 'https://github.com/acme/factory/pull/12',
      url: 'https://api.github.com/repos/acme/factory/pulls/12',
      number: 12,
      state: 'open',
      draft: true,
    },
    payload: { prompt: 'Fix the worker bridge' },
    error: 'worker command failed',
    debug_prompt: 'Debug this failed Idea Refinery local-worker job in OpenCode.',
    logs_tail: 'tail log line 1\ntail log line 2',
    verification_results: [
      { command: 'pnpm test', status: 'passed', summary: 'test suite passed' },
      { command: 'graphify update .', status: 'failed', summary: 'graphify update was skipped' },
    ],
    graphify_updated: false,
    graphify_status: 'required',
    needs_human_review: true,
    review_reason: 'Graphify update was not completed.',
    result: {
      agent_output: 'partial output',
      verification_results: [
        { command: 'pnpm test', status: 'passed', summary: 'test suite passed' },
        { command: 'graphify update .', status: 'failed', summary: 'graphify update was skipped' },
      ],
      graphify_updated: false,
      graphify_status: 'required',
      draft_pr: {
        html_url: 'https://github.com/acme/factory/pull/12',
        url: 'https://api.github.com/repos/acme/factory/pulls/12',
        number: 12,
        state: 'open',
        draft: true,
      },
      review_reason: 'Graphify update was not completed.',
    },
  }],
  sqs: { commands_configured: true, events_configured: true, region: 'us-east-1' },
};

const dashboardWithNoJobs = {
  ...dashboard,
  jobs: [],
};

function mockDashboardApi(response = dashboard) {
  apiModule.api.mockImplementation(async (path, options = {}) => {
    if (path === '/api/local-workers' && (!options.method || options.method === 'GET')) {
      return response;
    }

    if (path.startsWith('/api/worker/invite-link')) {
      return { invite_link: 'idearefinery://connect?api_base=http%3A%2F%2Flocalhost' };
    }

    if (options.method === 'POST') {
      return {};
    }

    return {};
  });
}

describe('LocalWorkers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockDashboardApi();
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

  it('renders OpenCode job diagnostics and Level 1 autonomy inspection state', async () => {
    render(LocalWorkers);

    expect((await screen.findAllByText('agent_branch_work')).length).toBeGreaterThan(0);
    expect(screen.getByText(/OpenCode: opencode .* gpt-test .* build/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Branch: factory\/job-1\/fix/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Needs human review/i)).toBeInTheDocument();
    expect(screen.getByText(/Reason: Graphify update was not completed\./i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /draft pr/i })).toHaveAttribute('href', 'https://github.com/acme/factory/pull/12');
    expect(screen.getByText(/1\/2 verifications passed/i)).toBeInTheDocument();
    expect(screen.getAllByText((_, element) => element?.textContent?.includes('Graphify: required')).length).toBeGreaterThan(0);
    expect(screen.getByText(/worker command failed/i)).toBeInTheDocument();
    expect(screen.getByText(/OpenCode command/i)).toBeInTheDocument();
    expect(screen.getByText(/Debug follow-up/i)).toBeInTheDocument();
    expect(screen.getByText(/^Logs$/i)).toBeInTheDocument();
    expect(screen.getByText(/tail log line 1/i)).toBeInTheDocument();
    expect(screen.getByText(/failed or retryable job/i)).toBeInTheDocument();
  });

  it('renders draft PR links from nested draft_pr metadata', async () => {
    render(LocalWorkers);

    expect(await screen.findByRole('link', { name: /draft pr/i })).toHaveAttribute('href', 'https://github.com/acme/factory/pull/12');
  });

  it('renders an actionable empty state when no worker jobs are queued', async () => {
    mockDashboardApi(dashboardWithNoJobs);

    render(LocalWorkers);

    expect(await screen.findByText('No worker jobs are waiting')).toBeInTheDocument();
    await waitFor(() => {
      expect(document.body.textContent).toContain('1 approved worker ready when a build job is queued.');
    });
  });

  it('renders an actionable error state when the worker dashboard fails to load', async () => {
    apiModule.api.mockImplementation(async (path) => {
      if (path === '/api/local-workers') {
        throw new Error('Request failed with status 503');
      }
      return {};
    });

    render(LocalWorkers);

    expect(await screen.findByText('Worker dashboard could not load')).toBeInTheDocument();
    expect(screen.getByText('Request failed with status 503')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });

  it('generates invite links through the shared URL builder', async () => {
    render(LocalWorkers);

    const input = await screen.findByPlaceholderText(/worker id/i);
    await fireEvent.input(input, { target: { value: 'worker-42' } });
    await fireEvent.click(screen.getByRole('button', { name: /generate link/i }));

    await waitFor(() => {
      expect(apiModule.buildApiUrl).toHaveBeenCalledWith(
        '/api/worker/invite-link',
        {
          api_base: window.location.origin,
          worker_id: 'worker-42',
        },
      );
      expect(apiModule.api).toHaveBeenCalledWith(
        `/api/worker/invite-link?api_base=${encodeURIComponent(window.location.origin)}&worker_id=worker-42`,
      );
      expect(screen.getByText(/idearefinery:\/\/connect/i)).toBeInTheDocument();
    });
  });

  it('approves a worker request', async () => {
    render(LocalWorkers);

    const approveButton = await screen.findByRole('button', { name: /approve/i });
    await fireEvent.click(approveButton);

    await waitFor(() => {
      expect(apiModule.api).toHaveBeenCalledWith(
        '/api/local-workers/requests/request-1/approve',
        expect.objectContaining({ method: 'POST', body: {} }),
      );
    });
  });

  it('rotates and revokes approved workers', async () => {
    render(LocalWorkers);

    const rotateButton = (await screen.findAllByRole('button', { name: /^rotate$/i })).find((button) => !button.disabled);
    await fireEvent.click(rotateButton);

    const revokeButton = (await screen.findAllByRole('button', { name: /^revoke$/i })).find((button) => !button.disabled);
    await fireEvent.click(revokeButton);

    await waitFor(() => {
      expect(apiModule.api).toHaveBeenCalledWith(
        '/api/local-workers/worker-1/rotate-credentials',
        expect.objectContaining({ method: 'POST', body: {} }),
      );
      expect(apiModule.api).toHaveBeenCalledWith(
        '/api/local-workers/worker-1/revoke',
        expect.objectContaining({ method: 'POST', body: {} }),
      );
    });
  });

  it('purges revoked workers', async () => {
    render(LocalWorkers);

    const purgeButton = await screen.findByRole('button', { name: /reset revocations/i });
    await fireEvent.click(purgeButton);

    await waitFor(() => {
      expect(apiModule.api).toHaveBeenCalledWith(
        '/api/local-workers/purge-revoked',
        expect.objectContaining({ method: 'POST', body: {} }),
      );
    });
  });
});
