<script>
  import { Lightbulb, Plus, X } from 'lucide-svelte';
  import { apiPost } from '../../api.js';
  import Modal from '../UI/Modal.svelte';
  import Input from '../UI/Input.svelte';
  import Button from '../UI/Button.svelte';

  let { onclose, onideaCreated } = $props();

  let title = $state('');
  let description = $state('');

  async function handleSubmit() {
    try {
      const result = await apiPost('/api/ideas', { title, description });
      onideaCreated?.(result);
    } catch (err) {
      console.error('Failed to create idea:', err);
    }
  }

  function handleClose() {
    onclose?.();
  }
</script>

<Modal 
  title="Create New Idea"
  showClose={true}
  {onclose}
>
  <form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
    <div class="create-intro">
      <span><Lightbulb size={22} /></span>
      <div>
        <strong>Capture the raw signal</strong>
        <p>The pipeline will attach phases, scores, and research context after creation.</p>
      </div>
    </div>

    <div class="form-group">
      <label for="title">Title</label>
      <Input 
        id="title" 
        type="text" 
        bind:value={title} 
        required
        placeholder="Enter idea title"
      />
    </div>
    
    <div class="form-group">
      <label for="description">Description</label>
      <textarea 
        id="description" 
        bind:value={description} 
        required
        placeholder="Describe your idea in detail"
        rows="4"
      ></textarea>
    </div>
    
    <div class="modal-footer">
      <Button type="button" variant="secondary" onclick={handleClose}>
        <X size={16} />
        Cancel
      </Button>
      <Button type="submit">
        <Plus size={16} />
        Create Idea
      </Button>
    </div>
  </form>
</Modal>

<style>
  .create-intro {
    align-items: flex-start;
    background: rgba(0, 120, 255, 0.1);
    border: 1px solid rgba(0, 240, 255, 0.24);
    border-radius: var(--border-radius-lg);
    display: flex;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-lg);
    padding: var(--spacing-md);
  }

  .create-intro span {
    align-items: center;
    background: rgba(0, 240, 255, 0.08);
    border: 1px solid rgba(0, 240, 255, 0.28);
    border-radius: var(--border-radius-md);
    color: var(--color-accent);
    display: inline-flex;
    flex: 0 0 auto;
    height: 38px;
    justify-content: center;
    width: 38px;
  }

  .create-intro strong {
    color: var(--color-text);
    display: block;
    margin-bottom: 2px;
  }

  .create-intro p {
    color: var(--color-text-secondary);
    font-size: 0.88rem;
    margin: 0;
  }

  .form-group {
    margin-bottom: var(--spacing-lg);
  }
  
  label {
    display: block;
    margin-bottom: var(--spacing-sm);
    color: var(--color-text-secondary);
    font-size: 0.875rem;
    font-weight: 600;
  }
  
  textarea {
    width: 100%;
    min-height: 120px;
    background-color: var(--color-surface);
    color: var(--color-text);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius-sm);
    padding: var(--spacing-sm);
    font-family: var(--font-sans);
  }

  textarea:focus {
    outline: none;
    border-color: var(--color-accent);
    box-shadow: 0 0 0 2px rgba(233, 69, 96, 0.2);
  }
  
  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: var(--spacing-md);
    margin-top: var(--spacing-lg);
  }

  @media (max-width: 560px) {
    .modal-footer {
      flex-direction: column-reverse;
    }
  }
</style>
