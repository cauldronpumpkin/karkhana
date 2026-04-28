import { describe, expect, it, vi, beforeEach } from 'vitest';
import { api } from './api.js';

describe('api helper', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns null for empty successful responses', async () => {
    fetch.mockResolvedValue({
      ok: true,
      status: 204,
    });

    await expect(api('/api/ideas/idea-1', { method: 'DELETE' })).resolves.toBeNull();
  });

  it('parses JSON responses after checking status', async () => {
    fetch.mockResolvedValue({
      ok: true,
      status: 200,
      text: vi.fn().mockResolvedValue('{"status":"ok"}'),
    });

    await expect(api('/api/health')).resolves.toEqual({ status: 'ok' });
  });
});
