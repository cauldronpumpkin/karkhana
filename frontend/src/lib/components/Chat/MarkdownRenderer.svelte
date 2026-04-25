<script>
  import { marked } from 'marked';
  import DOMPurify from 'dompurify';

  let { content = '' } = $props();

  marked.setOptions({
    breaks: true,
    gfm: true,
    headerIds: false,
    mangle: false
  });

  let sanitizedHtml = $derived(content ? DOMPurify.sanitize(marked.parse(content)) : '');
</script>

<div class="markdown-renderer">{@html sanitizedHtml}</div>

<style>
  .markdown-renderer {
    line-height: 1.6;
    color: var(--color-text);
  }

  .markdown-renderer :global(h1),
  .markdown-renderer :global(h2),
  .markdown-renderer :global(h3),
  .markdown-renderer :global(h4),
  .markdown-renderer :global(h5),
  .markdown-renderer :global(h6) {
    color: var(--color-text);
    margin-top: var(--spacing-lg);
    margin-bottom: var(--spacing-md);
    font-weight: 600;
  }

  .markdown-renderer :global(h1) { font-size: 1.875rem; }
  .markdown-renderer :global(h2) { font-size: 1.5rem; }
  .markdown-renderer :global(h3) { font-size: 1.25rem; }
  .markdown-renderer :global(h4) { font-size: 1.125rem; }

  .markdown-renderer :global(p) {
    margin-bottom: var(--spacing-md);
  }

  .markdown-renderer :global(ul),
  .markdown-renderer :global(ol) {
    margin-left: var(--spacing-lg);
    margin-bottom: var(--spacing-md);
  }

  .markdown-renderer :global(li) {
    margin-bottom: var(--spacing-sm);
  }

  .markdown-renderer :global(blockquote) {
    border-left: 3px solid var(--color-accent);
    margin: var(--spacing-lg) 0;
    padding: var(--spacing-md) var(--spacing-lg);
    background-color: var(--color-bg);
    color: var(--color-text-secondary);
  }

  .markdown-renderer :global(code) {
    background-color: var(--color-surface);
    padding: var(--spacing-xs) var(--spacing-sm);
    border-radius: var(--border-radius-sm);
    font-family: var(--font-mono);
    font-size: 0.875rem;
  }

  .markdown-renderer :global(pre) {
    background-color: var(--color-surface);
    padding: var(--spacing-md);
    border-radius: var(--border-radius-md);
    overflow-x: auto;
    margin: var(--spacing-lg) 0;
  }

  .markdown-renderer :global(pre code) {
    background: none;
    padding: 0;
    border-radius: 0;
  }

  .markdown-renderer :global(strong) {
    font-weight: 600;
  }

  .markdown-renderer :global(em) {
    font-style: italic;
  }

  .markdown-renderer :global(a) {
    color: var(--color-accent);
    text-decoration: none;
  }

  .markdown-renderer :global(a):hover {
    text-decoration: underline;
  }
</style>
