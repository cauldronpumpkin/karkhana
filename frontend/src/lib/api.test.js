import { describe, expect, it, vi, beforeEach } from 'vitest';
import { api, apiPost, buildApiUrl } from './api.js';

function mockResponse({ ok = true, status = 200, body = '', contentType = 'application/json' } = {}) {
  return {
    ok,
    status,
    headers: {
      get(name) {
        return name.toLowerCase() === 'content-type' ? contentType : null;
      },
    },
    text: vi.fn().mockResolvedValue(body),
  };
}

describe('api helper', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('omits JSON content-type on GET requests', async () => {
    fetch.mockResolvedValue(mockResponse({ body: '{"ok":true}' }));

    await api('/api/ideas');

    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch.mock.calls[0][0]).toBe('/api/ideas');
    expect(fetch.mock.calls[0][1]).toMatchObject({
      method: 'GET',
      headers: undefined,
    });
  });

  it('serializes JSON POST bodies and sets JSON content-type', async () => {
    fetch.mockResolvedValue(mockResponse({ body: '{"ok":true}' }));

    await apiPost('/api/ideas', { title: 'Ship it' });

    expect(fetch.mock.calls[0][0]).toBe('/api/ideas');
    expect(fetch.mock.calls[0][1]).toMatchObject({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{"title":"Ship it"}',
    });
  });

  it('preserves FormData bodies without forcing JSON headers', async () => {
    const formData = new FormData();
    formData.append('file', 'demo');
    fetch.mockResolvedValue(mockResponse({ body: '{"ok":true}' }));

    await api('/api/upload', {
      method: 'POST',
      body: formData,
      headers: { 'Content-Type': 'application/json' },
    });

    expect(fetch.mock.calls[0][1]).toMatchObject({
      method: 'POST',
      headers: undefined,
      body: formData,
    });
  });

  it('returns null for empty successful responses', async () => {
    fetch.mockResolvedValue(mockResponse({ status: 204, body: '' }));

    await expect(api('/api/ideas/idea-1', { method: 'DELETE' })).resolves.toBeNull();
  });

  it('surfaces JSON error details through ApiError', async () => {
    fetch.mockResolvedValue(
      mockResponse({
        ok: false,
        status: 400,
        body: '{"detail":"Missing required title"}',
      }),
    );

    await expect(api('/api/ideas', { method: 'POST', body: { title: '' } })).rejects.toMatchObject({
      name: 'ApiError',
      status: 400,
      detail: 'Missing required title',
      message: 'Missing required title',
    });
  });

  it('falls back to a stable message for HTML error bodies', async () => {
    fetch.mockResolvedValue(
      mockResponse({
        ok: false,
        status: 500,
        contentType: 'text/html',
        body: '<html><body>Server Error</body></html>',
      }),
    );

    await expect(api('/api/ideas')).rejects.toMatchObject({
      name: 'ApiError',
      status: 500,
      detail: null,
      message: 'Request failed with status 500',
    });
  });

  it('joins trailing and leading slashes when building API URLs', () => {
    expect(buildApiUrl('/api/ideas', null, 'https://api.example.com/')).toBe('https://api.example.com/api/ideas');
    expect(buildApiUrl('api/ideas', { filter: 'recent' }, 'https://api.example.com')).toBe('https://api.example.com/api/ideas?filter=recent');
  });

  it('returns text bodies when the response is not JSON', async () => {
    fetch.mockResolvedValue(
      mockResponse({
        body: 'plain-text body',
        contentType: 'text/plain',
      }),
    );

    await expect(api('/api/health')).resolves.toBe('plain-text body');
  });
});
