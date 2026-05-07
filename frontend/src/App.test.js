import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import App from './App.svelte';
import * as apiModule from './lib/api.js';

vi.mock('./lib/api.js', () => ({
  api: vi.fn(),
}));

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiModule.api.mockResolvedValue(null);
    window.location.hash = '';
  });

  it('renders the dashboard when ideas returns null', async () => {
    render(App);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeInTheDocument();
    });
  });
});
