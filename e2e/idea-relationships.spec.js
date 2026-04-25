import { test, expect } from '@playwright/test';

/**
 * E2E tests for idea relationships:
 * Create related ideas, merge, split, derive
 */

test.describe('Idea Relationships', () => {
  test('create relationship between two ideas', async ({ page, request }) => {
    // Create two ideas
    const createA = await request.post('/api/ideas', {
      data: {
        title: 'Source Idea',
        description: 'The source idea for relationship testing.',
      },
    });
    expect(createA.ok()).toBeTruthy();
    const ideaA = await createA.json();

    const createB = await request.post('/api/ideas', {
      data: {
        title: 'Target Idea',
        description: 'The target idea for relationship testing.',
      },
    });
    expect(createB.ok()).toBeTruthy();
    const ideaB = await createB.json();

    // Create a relationship
    const relResponse = await request.post(`/api/ideas/${ideaA.id}/relationships`, {
      data: {
        target_id: ideaB.id,
        relation_type: 'reference',
        description: 'Source references target',
      },
    });
    expect(relResponse.ok()).toBeTruthy();
    const rel = await relResponse.json();
    expect(rel.source_idea_id).toBe(ideaA.id);
    expect(rel.target_idea_id).toBe(ideaB.id);
    expect(rel.relation_type).toBe('reference');

    // Verify relationship is retrievable
    const getRelsResponse = await request.get(`/api/ideas/${ideaA.id}/relationships`);
    expect(getRelsResponse.ok()).toBeTruthy();
    const relsResult = await getRelsResponse.json();
    expect(relsResult.relationships).toBeTruthy();
    expect(relsResult.relationships.length).toBeGreaterThanOrEqual(1);
    const found = relsResult.relationships.find(
      r => r.target_idea_id === ideaB.id && r.relation_type === 'reference'
    );
    expect(found).toBeTruthy();

    // Cleanup
    await request.delete(`/api/ideas/${ideaA.id}`);
    await request.delete(`/api/ideas/${ideaB.id}`);
  });

  test('merge two ideas into one', async ({ page, request }) => {
    // Create two ideas
    const createA = await request.post('/api/ideas', {
      data: {
        title: 'Merge Idea A',
        description: 'First idea to merge.',
      },
    });
    expect(createA.ok()).toBeTruthy();
    const ideaA = await createA.json();

    const createB = await request.post('/api/ideas', {
      data: {
        title: 'Merge Idea B',
        description: 'Second idea to merge.',
      },
    });
    expect(createB.ok()).toBeTruthy();
    const ideaB = await createB.json();

    // Merge them
    const mergeResponse = await request.post(`/api/ideas/${ideaA.id}/merge`, {
      data: {
        target_id: ideaB.id,
        merged_title: 'Merged Idea AB',
        merged_description: 'Combined description from both ideas.',
      },
    });
    expect(mergeResponse.ok()).toBeTruthy();
    const merged = await mergeResponse.json();
    expect(merged.title).toBe('Merged Idea AB');
    expect(merged.description).toBe('Combined description from both ideas.');
    expect(merged.status).toBe('active');
    const mergedId = merged.id;

    // Verify originals are archived
    const getA = await request.get(`/api/ideas/${ideaA.id}`);
    expect(getA.status()).toBe(404);

    const getB = await request.get(`/api/ideas/${ideaB.id}`);
    expect(getB.status()).toBe(404);

    // Verify merged idea exists
    const getMerged = await request.get(`/api/ideas/${mergedId}`);
    expect(getMerged.ok()).toBeTruthy();
    const mergedDetail = await getMerged.json();
    expect(mergedDetail.title).toBe('Merged Idea AB');

    // Cleanup
    await request.delete(`/api/ideas/${mergedId}`);
  });

  test('split an idea into two new ideas', async ({ page, request }) => {
    // Create an idea
    const createResponse = await request.post('/api/ideas', {
      data: {
        title: 'Split Me',
        description: 'An idea that will be split into two.',
      },
    });
    expect(createResponse.ok()).toBeTruthy();
    const original = await createResponse.json();
    const originalId = original.id;

    // Split it
    const splitResponse = await request.post(`/api/ideas/${originalId}/split`, {
      data: {
        idea_a: {
          title: 'Split Part A',
          description: 'First part of the split.',
        },
        idea_b: {
          title: 'Split Part B',
          description: 'Second part of the split.',
        },
        messages_a: [],
        messages_b: [],
      },
    });
    expect(splitResponse.ok()).toBeTruthy();
    const splitResult = await splitResponse.json();
    expect(splitResult.idea_a).toBeTruthy();
    expect(splitResult.idea_b).toBeTruthy();
    expect(splitResult.idea_a.title).toBe('Split Part A');
    expect(splitResult.idea_b.title).toBe('Split Part B');

    const ideaAId = splitResult.idea_a.id;
    const ideaBId = splitResult.idea_b.id;

    // Verify original is archived
    const getOriginal = await request.get(`/api/ideas/${originalId}`);
    expect(getOriginal.status()).toBe(404);

    // Verify both new ideas exist
    const getA = await request.get(`/api/ideas/${ideaAId}`);
    expect(getA.ok()).toBeTruthy();
    const detailA = await getA.json();
    expect(detailA.title).toBe('Split Part A');

    const getB = await request.get(`/api/ideas/${ideaBId}`);
    expect(getB.ok()).toBeTruthy();
    const detailB = await getB.json();
    expect(detailB.title).toBe('Split Part B');

    // Cleanup
    await request.delete(`/api/ideas/${ideaAId}`);
    await request.delete(`/api/ideas/${ideaBId}`);
  });

  test('derive a new idea from an existing one', async ({ page, request }) => {
    // Create source idea
    const createResponse = await request.post('/api/ideas', {
      data: {
        title: 'Source for Derivation',
        description: 'The original idea to derive from.',
      },
    });
    expect(createResponse.ok()).toBeTruthy();
    const source = await createResponse.json();
    const sourceId = source.id;

    // Derive a new idea
    const deriveResponse = await request.post(`/api/ideas/${sourceId}/derive`, {
      data: {
        new_title: 'Derived Idea',
        new_description: 'A new idea derived from the source.',
      },
    });
    expect(deriveResponse.ok()).toBeTruthy();
    const derived = await deriveResponse.json();
    expect(derived.title).toBe('Derived Idea');
    expect(derived.description).toBe('A new idea derived from the source.');
    expect(derived.status).toBe('active');
    const derivedId = derived.id;

    // Verify source still exists
    const getSource = await request.get(`/api/ideas/${sourceId}`);
    expect(getSource.ok()).toBeTruthy();

    // Verify derived idea exists
    const getDerived = await request.get(`/api/ideas/${derivedId}`);
    expect(getDerived.ok()).toBeTruthy();
    const derivedDetail = await getDerived.json();
    expect(derivedDetail.title).toBe('Derived Idea');

    // Verify relationship exists
    const relsResponse = await request.get(`/api/ideas/${sourceId}/relationships`);
    expect(relsResponse.ok()).toBeTruthy();
    const relsResult = await relsResponse.json();
    const deriveRel = relsResult.relationships.find(
      r => r.target_idea_id === derivedId && r.relation_type === 'derive'
    );
    expect(deriveRel).toBeTruthy();

    // Cleanup
    await request.delete(`/api/ideas/${sourceId}`);
    await request.delete(`/api/ideas/${derivedId}`);
  });

  test('create multiple relationship types', async ({ page, request }) => {
    // Create three ideas
    const ideas = [];
    const titles = ['Rel Type A', 'Rel Type B', 'Rel Type C'];
    for (const title of titles) {
      const resp = await request.post('/api/ideas', {
        data: { title, description: `Description for ${title}` },
      });
      expect(resp.ok()).toBeTruthy();
      ideas.push(await resp.json());
    }

    // Create different relationship types
    const types = ['reference', 'merge', 'split', 'derive'];
    for (let i = 1; i < ideas.length; i++) {
      const type = types[i - 1] || 'reference';
      const relResp = await request.post(`/api/ideas/${ideas[0].id}/relationships`, {
        data: {
          target_id: ideas[i].id,
          relation_type: type,
          description: `${type} relationship`,
        },
      });
      expect(relResp.ok()).toBeTruthy();
      const rel = await relResp.json();
      expect(rel.relation_type).toBe(type);
    }

    // Verify all relationships
    const relsResp = await request.get(`/api/ideas/${ideas[0].id}/relationships`);
    expect(relsResp.ok()).toBeTruthy();
    const relsResult = await relsResp.json();
    expect(relsResult.relationships.length).toBe(ideas.length - 1);

    // Cleanup
    for (const idea of ideas) {
      await request.delete(`/api/ideas/${idea.id}`);
    }
  });
});
