import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import FileUpload from './FileUpload.svelte';
import * as apiModule from '../../api.js';

vi.mock('../../api.js', () => ({
  api: vi.fn(),
  buildApiUrl: vi.fn((path) => path),
}));

describe('FileUpload', () => {
  const task = {
    id: 'task-1',
    prompt_text: 'Gather evidence',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    apiModule.api.mockResolvedValue({ ok: true });
  });

  it('uploads files through the shared API helper with FormData', async () => {
    const onuploaded = vi.fn();
    render(FileUpload, {
      props: {
        ideaId: 'idea-1',
        task,
        onclose: vi.fn(),
        onuploaded,
      },
    });

    const input = document.querySelector('input[type="file"]');
    expect(input).toBeInTheDocument();
    const file = new File(['demo'], 'notes.md', { type: 'text/markdown' });
    await fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(apiModule.buildApiUrl).toHaveBeenCalledWith('/api/ideas/idea-1/research/task-1/upload');
      expect(apiModule.api).toHaveBeenCalledWith('/api/ideas/idea-1/research/task-1/upload', expect.objectContaining({
        method: 'POST',
        body: expect.any(Object),
      }));
      expect(screen.getByText(/Evidence uploaded successfully\./i)).toBeInTheDocument();
    });

    const requestBody = apiModule.api.mock.calls[0][1].body;
    expect(requestBody.append).toHaveBeenCalledWith('file', file);
  });

  it('shows JSON error details from the API helper', async () => {
    apiModule.api.mockRejectedValueOnce({ detail: 'Upload rejected: unsupported file' });

    render(FileUpload, {
      props: {
        ideaId: 'idea-1',
        task,
        onclose: vi.fn(),
        onuploaded: vi.fn(),
      },
    });

    const input = document.querySelector('input[type="file"]');
    expect(input).toBeInTheDocument();
    const file = new File(['demo'], 'notes.md', { type: 'text/markdown' });
    await fireEvent.change(input, { target: { files: [file] } });

    expect(await screen.findByText(/Upload rejected: unsupported file/i)).toBeInTheDocument();
  });

  it('falls back to a stable message for 500-style failures', async () => {
    apiModule.api.mockRejectedValueOnce(new Error('Request failed with status 500'));

    render(FileUpload, {
      props: {
        ideaId: 'idea-1',
        task,
        onclose: vi.fn(),
        onuploaded: vi.fn(),
      },
    });

    const input = document.querySelector('input[type="file"]');
    expect(input).toBeInTheDocument();
    const file = new File(['demo'], 'notes.md', { type: 'text/markdown' });
    await fireEvent.change(input, { target: { files: [file] } });

    expect(await screen.findByText(/Request failed with status 500/i)).toBeInTheDocument();
  });
});
