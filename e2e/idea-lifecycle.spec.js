import { test, expect } from '@playwright/test';

/**
 * E2E tests for the full idea lifecycle:
 * Create → Chat → Advance Phases → Score → Build Prompts
 */

test.describe('Full Idea Lifecycle', () => {
  test('create idea, chat, advance phases, score, and get build prompts', async ({ page, request }) => {
    // Step 1: Create an idea via API
    const createResponse = await request.post('/api/ideas', {
      data: {
        title: 'E2E Lifecycle Test Idea',
        description: 'A test idea for the full lifecycle E2E test.',
      },
    });
    expect(createResponse.ok()).toBeTruthy();
    const idea = await createResponse.json();
    expect(idea.title).toBe('E2E Lifecycle Test Idea');
    expect(idea.slug).toBe('e2e-lifecycle-test-idea');
    expect(idea.current_phase).toBe('capture');
    const ideaId = idea.id;

    // Step 2: Verify idea appears in GET /api/ideas
    const listResponse = await request.get('/api/ideas');
    expect(listResponse.ok()).toBeTruthy();
    const ideas = await listResponse.json();
    expect(Array.isArray(ideas)).toBeTruthy();
    const found = ideas.find(i => i.id === ideaId);
    expect(found).toBeTruthy();
    expect(found.title).toBe('E2E Lifecycle Test Idea');

    // Step 3: Chat with the idea (REST endpoint)
    const chatResponse = await request.post(`/api/ideas/${ideaId}/chat/message`, {
      data: { message: 'Tell me more about this idea.' },
    });
    expect(chatResponse.ok()).toBeTruthy();
    const chatResult = await chatResponse.json();
    expect(chatResult.content).toBeTruthy();
    expect(typeof chatResult.content).toBe('string');
    expect(chatResult.content.length).toBeGreaterThan(0);
    expect(chatResult.message_id).toBeTruthy();

    // Step 4: Verify chat history is persisted
    const historyResponse = await request.get(`/api/ideas/${ideaId}/chat/history`);
    expect(historyResponse.ok()).toBeTruthy();
    const history = await historyResponse.json();
    expect(Array.isArray(history)).toBeTruthy();
    expect(history.length).toBeGreaterThanOrEqual(2); // user + assistant
    const userMsg = history.find(m => m.role === 'user');
    expect(userMsg).toBeTruthy();
    expect(userMsg.content).toBe('Tell me more about this idea.');

    // Step 5: Suggest phase advancement
    const suggestResponse = await request.post(`/api/ideas/${ideaId}/phase/suggest`);
    expect(suggestResponse.ok()).toBeTruthy();
    const suggestResult = await suggestResponse.json();
    expect(suggestResult.ready).toBeTruthy();
    expect(suggestResult.next_phase).toBeTruthy();

    // Step 6: Approve phase advancement
    const approveResponse = await request.post(`/api/ideas/${ideaId}/phase/approve`);
    expect(approveResponse.ok()).toBeTruthy();
    const approveResult = await approveResponse.json();
    expect(approveResult.new_phase).toBeTruthy();

    // Step 7: Verify phase changed in idea detail
    const detailResponse = await request.get(`/api/ideas/${ideaId}`);
    expect(detailResponse.ok()).toBeTruthy();
    const detail = await detailResponse.json();
    expect(detail.current_phase).not.toBe('capture');

    // Step 8: Score the idea
    const scoreResponse = await request.post(`/api/ideas/${ideaId}/score`);
    expect(scoreResponse.ok()).toBeTruthy();
    const scoreResult = await scoreResponse.json();
    expect(scoreResult.scores).toBeTruthy();
    expect(typeof scoreResult.scores).toBe('object');
    expect(Object.keys(scoreResult.scores).length).toBeGreaterThan(0);

    // Step 9: Verify scores are retrievable
    const scoresResponse = await request.get(`/api/ideas/${ideaId}/scores`);
    expect(scoresResponse.ok()).toBeTruthy();
    const scoresResult = await scoresResponse.json();
    expect(scoresResult.scores).toBeTruthy();
    expect(scoresResult.scores.length).toBeGreaterThan(0);

    // Step 10: Get composite score
    const compositeResponse = await request.get(`/api/ideas/${ideaId}/scores/composite`);
    expect(compositeResponse.ok()).toBeTruthy();
    const compositeResult = await compositeResponse.json();
    expect(compositeResult.composite_score).toBeTruthy();
    expect(typeof compositeResult.composite_score).toBe('number');

    // Step 11: Get build prompts
    const buildResponse = await request.get(`/api/ideas/${ideaId}/build/prompts`);
    expect(buildResponse.ok()).toBeTruthy();
    const buildResult = await buildResponse.json();
    expect(buildResult.prometheus_prompt).toBeTruthy();
    expect(buildResult.step_prompts).toBeTruthy();

    // Step 12: Verify idea detail includes scores
    const finalDetailResponse = await request.get(`/api/ideas/${ideaId}`);
    expect(finalDetailResponse.ok()).toBeTruthy();
    const finalDetail = await finalDetailResponse.json();
    expect(finalDetail.scores).toBeTruthy();
    expect(finalDetail.composite_score).toBeGreaterThan(0);

    // Step 13: Archive (delete) the idea
    const deleteResponse = await request.delete(`/api/ideas/${ideaId}`);
    expect(deleteResponse.ok()).toBeTruthy();

    // Step 14: Verify idea is no longer in active list
    const finalListResponse = await request.get('/api/ideas');
    expect(finalListResponse.ok()).toBeTruthy();
    const finalIdeas = await finalListResponse.json();
    const stillActive = finalIdeas.find(i => i.id === ideaId);
    expect(stillActive).toBeFalsy();
  });

  test('create multiple ideas and verify listing', async ({ page, request }) => {
    // Create 3 ideas
    const ideas = [];
    for (let i = 1; i <= 3; i++) {
      const response = await request.post('/api/ideas', {
        data: {
          title: `Multi Idea ${i}`,
          description: `Description for multi idea ${i}`,
        },
      });
      expect(response.ok()).toBeTruthy();
      ideas.push(await response.json());
    }

    // Verify all appear in listing
    const listResponse = await request.get('/api/ideas');
    expect(listResponse.ok()).toBeTruthy();
    const list = await listResponse.json();
    const ids = list.map(i => i.id);
    for (const idea of ideas) {
      expect(ids).toContain(idea.id);
    }

    // Cleanup: archive all
    for (const idea of ideas) {
      const deleteResponse = await request.delete(`/api/ideas/${idea.id}`);
      expect(deleteResponse.ok()).toBeTruthy();
    }
  });

  test('update idea title and description', async ({ page, request }) => {
    // Create idea
    const createResponse = await request.post('/api/ideas', {
      data: {
        title: 'Original Title',
        description: 'Original description',
      },
    });
    expect(createResponse.ok()).toBeTruthy();
    const idea = await createResponse.json();
    const ideaId = idea.id;

    // Update title
    const updateResponse = await request.patch(`/api/ideas/${ideaId}`, {
      data: {
        title: 'Updated Title',
        description: 'Updated description',
      },
    });
    expect(updateResponse.ok()).toBeTruthy();
    const updated = await updateResponse.json();
    expect(updated.title).toBe('Updated Title');
    expect(updated.description).toBe('Updated description');
    expect(updated.slug).toBe('updated-title');

    // Cleanup
    const deleteResponse = await request.delete(`/api/ideas/${ideaId}`);
    expect(deleteResponse.ok()).toBeTruthy();
  });
});
