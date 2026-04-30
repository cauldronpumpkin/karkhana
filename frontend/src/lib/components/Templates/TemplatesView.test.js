import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import TemplatesView from './TemplatesView.svelte';
import * as apiModule from '../../../lib/api.js';

vi.mock('../../../lib/api.js', () => ({
  api: vi.fn(),
}));

const mockPacks = [
  {
    template_id: 'template-pack-1',
    display_name: 'Template Pack One',
    description: 'Dense operational template pack',
    status: 'active',
    channel: 'stable',
    version: '1.2.3',
    default_stack: {
      stack: ['SvelteKit', 'Supabase', 'Stripe'],
      package_manager: 'pnpm',
    },
    required_tools: ['node', 'pnpm'],
    verification_commands: ['pnpm run check', 'graphify update .'],
    artifact_refs: [
      { key: 'AGENTS.md', path: '.', kind: 'prompt' },
      { key: '.spec.md', path: 'docs', kind: 'spec' },
    ],
    graphify_expectations: {
      read_before_task: ['graphify-out/GRAPH_REPORT.md'],
      refresh_after_task: ['graphify update .'],
    },
    guardrails: ['Stay inside allowed paths'],
    manifest: {
      schema_version: 'v0',
      stack: {
        name: ['SvelteKit', 'Supabase', 'Stripe'],
        package_manager: 'pnpm',
      },
      capabilities: ['repo_index', 'build_task_plan'],
      modules: ['frontend', 'backend'],
      context_cards: [
        { key: 'AGENTS.md', path: '.', kind: 'prompt' },
        { key: '.spec.md', path: 'docs', kind: 'spec' },
      ],
      validation: {
        status: 'pass',
        result: 'ready',
      },
      promotion: {
        status: 'ready',
        target: 'stable',
      },
      token_profile: {
        status: 'balanced',
        target_context: '4k',
      },
    },
    review_metadata: {
      status: 'operational',
      validation: {
        checked: 2,
      },
    },
    opencode_worker: {
      required_capabilities: ['repo_index'],
      modules: ['templates'],
    },
  },
];

describe('TemplatesView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiModule.api.mockResolvedValue({ template_packs: mockPacks });
  });

  it('renders template pack status, context cards, and telemetry sections', async () => {
    render(TemplatesView);

    await waitFor(() => {
      expect(screen.getByText('Template Pack One')).toBeInTheDocument();
    });

    expect(screen.getByText('active')).toBeInTheDocument();
    expect(screen.getAllByText('stable').length).toBeGreaterThan(0);
    expect(screen.getByText('v1.2.3')).toBeInTheDocument();
    expect(screen.getByText('Stack')).toBeInTheDocument();
    expect(screen.getAllByText('Context cards').length).toBeGreaterThan(0);
    expect(screen.getByText('Validation')).toBeInTheDocument();
    expect(screen.getByText('Promotion')).toBeInTheDocument();
    expect(screen.getByText('Token profile')).toBeInTheDocument();
    expect(screen.getAllByText('AGENTS.md').length).toBeGreaterThan(0);
    expect(screen.getAllByText('.spec.md').length).toBeGreaterThan(0);
    expect(screen.getAllByText('repo_index').length).toBeGreaterThan(0);
    expect(screen.getAllByText('frontend').length).toBeGreaterThan(0);
    expect(screen.getByText('Stay inside allowed paths')).toBeInTheDocument();
    expect(screen.getByText('graphify-out/GRAPH_REPORT.md')).toBeInTheDocument();
    expect(screen.getByText('pnpm run check')).toBeInTheDocument();
  });
});
