import { readable } from 'svelte/store';

export const page = readable({
  params: { id: 'test-idea-id', ideaId: 'test-idea-id', phase: null },
  url: new URL('http://localhost/'),
  route: { id: null },
});

export const navigating = readable(null);
export const updated = readable({ check: async () => false });
