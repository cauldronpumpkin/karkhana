import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import Reports from './Reports.svelte';
import * as apiModule from '../../api.js';

vi.mock('../../api.js', () => ({
  api: vi.fn()
}));

const mockReports = [
  {
    id: 'report-1',
    phase: 'capture',
    title: 'Market Opportunity Brief',
    content: '# Executive Summary\n\nMarket signal is strong.\n\n## Evidence',
    generated_at: '2025-05-14T10:42:00Z'
  }
];

describe('Reports', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders reports workspace shell', () => {
    apiModule.api.mockResolvedValue({ reports: [] });

    render(Reports, { props: { ideaId: 'idea-1' } });

    expect(document.querySelector('.reports-container')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Reports' })).toBeInTheDocument();
  });

  it('loads report API response and renders browser plus briefing', async () => {
    apiModule.api.mockResolvedValue({ reports: mockReports });

    render(Reports, { props: { ideaId: 'idea-1' } });

    expect(screen.getByText('Loading reports')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getAllByText('Market Opportunity Brief').length).toBeGreaterThan(0);
    });

    expect(screen.getAllByText('Executive Summary').length).toBeGreaterThan(0);
    expect(screen.getByText('Report Details')).toBeInTheDocument();
    expect(apiModule.api).toHaveBeenCalledWith('/api/ideas/idea-1/reports');
  });

  it('supports legacy bare-array report responses', async () => {
    apiModule.api.mockResolvedValue(mockReports);

    render(Reports, { props: { ideaId: 'idea-1' } });

    await waitFor(() => {
      expect(screen.getAllByText('Market Opportunity Brief').length).toBeGreaterThan(0);
    });
  });
});
