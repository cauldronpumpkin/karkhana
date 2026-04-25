import { test, expect } from '@playwright/test';

/**
 * E2E tests for the research workflow:
 * Generate prompts → Upload result → Integration
 */

test.describe('Research Flow', () => {
  test('generate research prompts, list tasks, upload result, and integrate', async ({ page, request }) => {
    // Step 1: Create an idea
    const createResponse = await request.post('/api/ideas', {
      data: {
        title: 'Research Flow Test Idea',
        description: 'A test idea for the research workflow E2E test.',
      },
    });
    expect(createResponse.ok()).toBeTruthy();
    const idea = await createResponse.json();
    const ideaId = idea.id;
    const slug = idea.slug;

    // Step 2: Generate research prompts
    const generateResponse = await request.post(`/api/ideas/${ideaId}/research/generate`);
    expect(generateResponse.ok()).toBeTruthy();
    const generateResult = await generateResponse.json();
    expect(generateResult.prompts).toBeTruthy();
    expect(Array.isArray(generateResult.prompts)).toBeTruthy();
    expect(generateResult.prompts.length).toBeGreaterThan(0);

    // Step 3: List research tasks — should show pending tasks
    const tasksResponse = await request.get(`/api/ideas/${ideaId}/research/tasks`);
    expect(tasksResponse.ok()).toBeTruthy();
    const tasksResult = await tasksResponse.json();
    expect(tasksResult.pending).toBeTruthy();
    expect(Array.isArray(tasksResult.pending)).toBeTruthy();
    expect(tasksResult.pending.length).toBeGreaterThan(0);

    // Get the first pending task
    const pendingTask = tasksResult.pending[0];
    const taskId = pendingTask.id;
    expect(taskId).toBeTruthy();

    // Step 4: Upload a research result file
    const researchContent = `# Research Result for Task: ${taskId}\n\nThis is a test research result file.\n\n## Findings\n- Finding 1: Test data shows positive correlation.\n- Finding 2: Market analysis indicates strong demand.\n\n## Conclusion\nThe idea has merit and should proceed to validation.`;

    const uploadResponse = await request.post(`/api/ideas/${ideaId}/research/${taskId}/upload`, {
      multipart: {
        file: {
          name: 'research-result.md',
          mimeType: 'text/markdown',
          buffer: Buffer.from(researchContent),
        },
      },
    });
    expect(uploadResponse.ok()).toBeTruthy();
    const uploadResult = await uploadResponse.json();
    expect(uploadResult.result_path).toBeTruthy();

    // Step 5: Verify task is no longer pending
    const tasksAfterUpload = await request.get(`/api/ideas/${ideaId}/research/tasks`);
    expect(tasksAfterUpload.ok()).toBeTruthy();
    const tasksAfterResult = await tasksAfterUpload.json();
    const stillPending = tasksAfterResult.pending.find(t => t.id === taskId);
    expect(stillPending).toBeFalsy();

    // Step 6: Integrate the research
    const integrateResponse = await request.post(`/api/ideas/${ideaId}/research/${taskId}/integrate`);
    expect(integrateResponse.ok()).toBeTruthy();
    const integrateResult = await integrateResponse.json();
    expect(integrateResult.integration).toBeTruthy();
    expect(integrateResult.integration.summary).toBeTruthy();

    // Step 7: Verify completed tasks list
    const finalTasksResponse = await request.get(`/api/ideas/${ideaId}/research/tasks`);
    expect(finalTasksResponse.ok()).toBeTruthy();
    const finalTasksResult = await finalTasksResponse.json();
    expect(finalTasksResult.completed).toBeTruthy();
    const completedTask = finalTasksResult.completed.find(t => t.id === taskId);
    expect(completedTask).toBeTruthy();

    // Cleanup: archive the idea
    const deleteResponse = await request.delete(`/api/ideas/${ideaId}`);
    expect(deleteResponse.ok()).toBeTruthy();
  });

  test('reject invalid file extension on upload', async ({ page, request }) => {
    // Create an idea
    const createResponse = await request.post('/api/ideas', {
      data: {
        title: 'Invalid Upload Test',
        description: 'Testing invalid file upload rejection.',
      },
    });
    expect(createResponse.ok()).toBeTruthy();
    const idea = await createResponse.json();
    const ideaId = idea.id;

    // Generate prompts to create tasks
    const generateResponse = await request.post(`/api/ideas/${ideaId}/research/generate`);
    expect(generateResponse.ok()).toBeTruthy();
    const generateResult = await generateResponse.json();
    const taskId = generateResult.prompts[0].id;

    // Try uploading an invalid file type
    const invalidUploadResponse = await request.post(`/api/ideas/${ideaId}/research/${taskId}/upload`, {
      multipart: {
        file: {
          name: 'invalid-file.pdf',
          mimeType: 'application/pdf',
          buffer: Buffer.from('fake pdf content'),
        },
      },
    });
    expect(invalidUploadResponse.status()).toBe(400);

    // Cleanup
    const deleteResponse = await request.delete(`/api/ideas/${ideaId}`);
    expect(deleteResponse.ok()).toBeTruthy();
  });

  test('research flow with multiple prompts', async ({ page, request }) => {
    // Create an idea
    const createResponse = await request.post('/api/ideas', {
      data: {
        title: 'Multi-Prompt Research Idea',
        description: 'Testing research flow with multiple prompts.',
      },
    });
    expect(createResponse.ok()).toBeTruthy();
    const idea = await createResponse.json();
    const ideaId = idea.id;

    // Generate prompts
    const generateResponse = await request.post(`/api/ideas/${ideaId}/research/generate`);
    expect(generateResponse.ok()).toBeTruthy();
    const generateResult = await generateResponse.json();
    expect(generateResult.prompts.length).toBeGreaterThanOrEqual(1);

    // Upload results for all pending tasks
    const tasksResponse = await request.get(`/api/ideas/${ideaId}/research/tasks`);
    const tasksResult = await tasksResponse.json();

    for (const task of tasksResult.pending) {
      const uploadResponse = await request.post(`/api/ideas/${ideaId}/research/${task.id}/upload`, {
        multipart: {
          file: {
            name: `result-${task.id}.md`,
            mimeType: 'text/markdown',
            buffer: Buffer.from(`# Research for task ${task.id}\n\nContent here.`),
          },
        },
      });
      expect(uploadResponse.ok()).toBeTruthy();
    }

    // Verify all tasks are completed
    const finalTasksResponse = await request.get(`/api/ideas/${ideaId}/research/tasks`);
    const finalTasksResult = await finalTasksResponse.json();
    expect(finalTasksResult.pending.length).toBe(0);
    expect(finalTasksResult.completed.length).toBe(generateResult.prompts.length);

    // Integrate each task
    for (const task of finalTasksResult.completed) {
      const integrateResponse = await request.post(`/api/ideas/${ideaId}/research/${task.id}/integrate`);
      expect(integrateResponse.ok()).toBeTruthy();
    }

    // Cleanup
    const deleteResponse = await request.delete(`/api/ideas/${ideaId}`);
    expect(deleteResponse.ok()).toBeTruthy();
  });
});
