import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import Dashboard from './Dashboard.svelte';
import * as apiModule from '../../api.js';

vi.mock('../../api.js', () => ({
  api: vi.fn(),
  apiPost: vi.fn(),
}));

const mockIdeas = [
  {
    id: '1',
    title: 'AI Cooking App',
    slug: 'ai-cooking-app',
    description: 'An app that suggests recipes',
    current_phase: 'capture',
    composite_score: 7.5,
    created_at: '2024-01-15T10:30:00',
    updated_at: '2024-01-15T10:30:00'
  },
  {
    id: '2',
    title: 'Fitness Tracker',
    slug: 'fitness-tracker',
    description: 'Track your daily workouts',
    current_phase: 'clarify',
    composite_score: 6.0,
    created_at: '2024-01-14T14:20:00',
    updated_at: '2024-01-14T14:20:00'
  }
];

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders dashboard title', () => {
    apiModule.api.mockResolvedValue([]);
    render(Dashboard);
    expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeInTheDocument();
  });

  it('displays idea cards after onMount', async () => {
    apiModule.api.mockResolvedValue(mockIdeas);
    render(Dashboard);

    await waitFor(() => {
      expect(screen.getByText('AI Cooking App')).toBeInTheDocument();
    });
  });

  it('shows New Idea button', () => {
    apiModule.api.mockResolvedValue([]);
    render(Dashboard);
    expect(screen.getAllByRole('button', { name: /new idea/i }).length).toBeGreaterThan(0);
  });

  it('renders multiple idea cards', async () => {
    apiModule.api.mockResolvedValue(mockIdeas);
    render(Dashboard);

    await waitFor(() => {
      expect(screen.getByText('AI Cooking App')).toBeInTheDocument();
      expect(screen.getByText('Fitness Tracker')).toBeInTheDocument();
    });
  });

  it('renders KPI strip labels', () => {
    apiModule.api.mockResolvedValue([]);
    render(Dashboard);
    expect(screen.getByText('Active Ideas')).toBeInTheDocument();
    expect(screen.getByText('Average Score')).toBeInTheDocument();
    expect(screen.getByText('Research Pending')).toBeInTheDocument();
  });
});
