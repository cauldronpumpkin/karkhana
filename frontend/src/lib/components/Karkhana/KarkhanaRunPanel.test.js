import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import KarkhanaRunPanel from './KarkhanaRunPanel.svelte';
import * as apiModule from '../../api.js';

vi.mock('../../api.js', () => ({
  createResearchArtifact: vi.fn(),
  createResearchHandoff: vi.fn(),
  getFactoryRun: vi.fn(),
}));

const mockBundle = {
  factory_run: {
    id: 'run-1234567890',
    status: 'running',
    correlation_id: 'corr-1',
    template_id: 'template-pack-1',
  },
  factory_state: {
    handoff_status: 'approved',
    intent_summary: 'Inspect template pack telemetry',
  },
  intent: {
    id: 'intent-1',
    summary: 'Inspect template pack telemetry',
  },
  tracking_summary: {
    run_status: 'running',
    phase_progress: { in_progress: 1, completed: 2, total: 3 },
    batch_progress: { completed: 4, total: 5 },
    verification_state: { status: 'passed' },
    worker_queue_state: { status: 'running', active_worker_id: 'worker-1' },
    active_role: 'worker',
    token_economy_totals: {
      input_tokens_total: 12345,
      output_tokens: 6789,
      input_tokens_cached: 4321,
      cache_hit_rate: 0.73,
      cost_estimate_usd: 1.2345,
      template_assets_used: ['AGENTS.md', 'docs/spec.md'],
      context_cards_used: ['AGENTS.md', '.spec.md'],
    },
    duplicate_work_count: 2,
  },
  tracking_manifest: {
    run_status: 'running',
  },
  phases: [],
  batches: [],
  verifications: [],
  research_artifacts: [],
  research_artifact_count: 0,
};

describe('KarkhanaRunPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiModule.getFactoryRun.mockResolvedValue(mockBundle);
  });

  it('renders token economy telemetry from the tracking summary', async () => {
    render(KarkhanaRunPanel, { props: { factoryRunId: 'run-1234567890', autonomyLevel: 'autonomous_development' } });

    await waitFor(() => {
      expect(screen.getByText('Factory Run')).toBeInTheDocument();
    });

    expect(screen.getByText('Token economy')).toBeInTheDocument();
    expect(screen.getByText('Input tokens')).toBeInTheDocument();
    expect(screen.getByText('12345')).toBeInTheDocument();
    expect(screen.getByText('6789')).toBeInTheDocument();
    expect(screen.getByText('4321')).toBeInTheDocument();
    expect(screen.getByText('73%')).toBeInTheDocument();
    expect(screen.getByText('$1.2345')).toBeInTheDocument();
    expect(screen.getByText('AGENTS.md, docs/spec.md')).toBeInTheDocument();
    expect(screen.getByText('AGENTS.md, .spec.md')).toBeInTheDocument();
    expect(screen.getByText('Duplicate work')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });
});
