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
      latest_index: {
        file_inventory: [{ path: 'package.json' }],
        manifests: [{ path: 'package.json' }],
        route_map: [],
        todos: [],
        risks: [],
      },
      index_summary: {
        file_count: 1,
        manifest_count: 1,
        route_hint_count: 0,
        todo_count: 0,
        detected_stack: ['node'],
        manifest_paths: ['package.json'],
        test_commands: ['npm test'],
        build_commands: ['npm run build'],
        route_hints: [],
        deploy_hints: ['vercel'],
        actionable_metadata: {
          package_manifests: [{ path: 'package.json', kind: 'package.json', scripts: ['build', 'test'], has_test: true, has_build: true }],
          likely_test_commands: ['npm test'],
          likely_build_commands: ['npm run build'],
          deployment_hints: ['vercel'],
          route_hints: [],
          dependency_risks: [],
          todo_markers: [],
          index_status: { is_stale: false, freshness: 'fresh', project_status: 'indexed' },
          next_action_hints: ['Validate with: npm test', 'Build with: npm run build'],
        },
      },
      health_summary: {
        status: 'healthy',
        summary: 'fresh index',
        index_freshness: { state: 'fresh', reason: 'Index matches the latest known commit.' },
        missing_info: [],
        dependency_risks: [],
      },
      factory_runs: [],
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
        payload: { prompt: 'Fix the worker bridge' },
        error: 'worker command failed',
        debug_prompt: 'Debug this failed Idea Refinery local-worker job in OpenCode.',
        result: { agent_output: 'partial output' },
      }],
    });
    getBuildNextActions.mockResolvedValue({
      status_summary: { current_phase: 'build', current_step: 'backend', project_attached: true },
      next_actions: [{ title: 'Advance', priority: 1, suggested_owner: 'local-worker', reason: 'Next', opencode_prompt: 'copy me', opencode_command: 'opencode run <prompt>', codex_prompt: 'copy me' }],
    });
  });

  it('shows success feedback when clipboard copy works', async () => {
    navigator.clipboard.writeText = vi.fn().mockResolvedValue(undefined);

    render(ProjectTwinView, { props: { ideaId: 'idea-1' } });

    const copyButton = await screen.findByRole('button', { name: /copy opencode prompt/i });
    await fireEvent.click(copyButton);

    await waitFor(() => expect(screen.getByText(/prompt copied to clipboard/i)).toBeInTheDocument());
  });

  it('falls back to execCommand when clipboard copy is blocked', async () => {
    navigator.clipboard.writeText = vi.fn().mockRejectedValue(new Error('blocked'));
    document.execCommand = vi.fn().mockReturnValue(true);

    render(ProjectTwinView, { props: { ideaId: 'idea-1' } });

    const copyButton = await screen.findByRole('button', { name: /copy opencode prompt/i });
    await fireEvent.click(copyButton);

    await waitFor(() => expect(screen.getByText(/prompt copied to clipboard/i)).toBeInTheDocument());
    expect(document.execCommand).toHaveBeenCalledWith('copy');
  });

  it('shows failure feedback when clipboard fallback is unavailable', async () => {
    navigator.clipboard.writeText = undefined;
    document.execCommand = vi.fn().mockReturnValue(false);

    render(ProjectTwinView, { props: { ideaId: 'idea-1' } });

    const copyButton = await screen.findByRole('button', { name: /copy opencode prompt/i });
    await fireEvent.click(copyButton);

    await waitFor(() => expect(screen.getByText(/clipboard fallback unavailable/i)).toBeInTheDocument());
  });

  it('renders actionable project twin planning metadata', async () => {
    render(ProjectTwinView, { props: { ideaId: 'idea-1' } });

    expect(await screen.findByText(/planning metadata/i)).toBeInTheDocument();
    expect(screen.getByText(/opencode run <prompt>/i)).toBeInTheDocument();
    expect(screen.getByText(/1 package manifests/i)).toBeInTheDocument();
    expect(screen.getByText(/validate with: npm test/i)).toBeInTheDocument();
    expect(screen.getByText(/build with: npm run build/i)).toBeInTheDocument();
  });

  it('renders OpenCode worker job diagnostics', async () => {
    render(ProjectTwinView, { props: { ideaId: 'idea-1' } });

    expect(await screen.findByText('agent_branch_work')).toBeInTheDocument();
    expect(screen.getByText(/OpenCode: opencode · gpt-test · build/i)).toBeInTheDocument();
    expect(screen.getByText(/Branch: factory\/job-1\/fix/i)).toBeInTheDocument();
    expect(screen.getByText(/worker command failed/i)).toBeInTheDocument();
    expect(screen.getByText(/OpenCode command/i)).toBeInTheDocument();
    expect(screen.getByText(/Debug follow-up/i)).toBeInTheDocument();
    expect(screen.getByText(/Suggested OpenCode retry prompt/i)).toBeInTheDocument();
  });
});
