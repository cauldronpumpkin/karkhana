import { describe, expect, it, vi, beforeEach } from 'vitest';
import { api, createFactoryRun, createResearchArtifact } from './api.js';

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

  it('includes intent when creating a factory run', async () => {
    fetch.mockResolvedValue({
      ok: true,
      status: 200,
      text: vi.fn().mockResolvedValue('{"factory_run":{"id":"run-1"}}'),
    });

    await createFactoryRun('project-1', {
      template_id: 'template-1',
      intent: { summary: 'Ship the MVP' },
    });

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/projects/project-1/factory-runs'),
      expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('"intent":{"summary":"Ship the MVP"}'),
      }),
    );
  });

  it('posts research artifacts to the factory run endpoint', async () => {
    fetch.mockResolvedValue({
      ok: true,
      status: 200,
      text: vi.fn().mockResolvedValue('{"research_artifact":{"id":"artifact-1"}}'),
    });

    await createResearchArtifact('run-1', {
      title: 'Research note',
      source: 'docs',
      raw_content: 'Some content',
    });

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/factory-runs/run-1/research-artifacts'),
      expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('"title":"Research note"'),
      }),
    );
  });
});
