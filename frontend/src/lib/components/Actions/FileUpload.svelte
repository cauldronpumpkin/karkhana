<script>
  import { CheckCircle2, FileText, Loader2, UploadCloud, XCircle } from 'lucide-svelte';
  import Button from '../UI/Button.svelte';
  import { API_BASE } from '../../api.js';

  let { ideaId, task, onclose, onuploaded } = $props();

  let fileInput;
  let isDragging = $state(false);
  let uploadProgress = $state(0);
  let uploadStatus = $state('');
  let uploadError = $state('');
  let selectedFileName = $state('');
  let isUploading = $state(false);

  let promptTitle = $derived((task.prompt_text || task.prompt || 'Research evidence').split('\n').find(Boolean) || 'Research evidence');

  const handleDragOver = (e) => {
    e.preventDefault();
    isDragging = true;
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    isDragging = false;
  };

  const handleDrop = (e) => {
    e.preventDefault();
    isDragging = false;
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFile(files[0]);
    }
  };

  const handleFileSelect = (e) => {
    const files = e.target.files;
    if (files.length > 0) {
      handleFile(files[0]);
    }
  };

  function browseFiles() {
    fileInput?.click();
  }

  const handleFile = async (file) => {
    const validTypes = ['.md', '.txt', '.markdown'];
    const fileExtension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    
    if (!validTypes.includes(fileExtension)) {
      uploadError = 'Please upload only .md, .txt, or .markdown files';
      return;
    }

    selectedFileName = file.name;
    uploadError = '';
    uploadStatus = 'Uploading evidence...';
    uploadProgress = 0;
    isUploading = true;

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(
        `${API_BASE}/api/ideas/${ideaId}/research/${task.id}/upload`,
        { method: 'POST', body: formData }
      );
      
      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Upload failed');
      }
      
      uploadStatus = 'Evidence uploaded successfully.';
      uploadProgress = 100;
      setTimeout(() => onuploaded?.(), 800);
    } catch (error) {
      uploadError = error.message || 'Upload failed. Please try again.';
      console.error('Upload error:', error);
    } finally {
      isUploading = false;
    }
  };
</script>

<div class="file-upload-modal">
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="task-context">
    <span class="mono-label"><FileText size={14} /> Target task</span>
    <strong>{promptTitle}</strong>
  </div>

  <div class="upload-area"
       role="button"
       tabindex="0"
       ondragover={handleDragOver}
       ondragleave={handleDragLeave}
       ondrop={handleDrop}
       onclick={browseFiles}
       onkeydown={(event) => { if (event.key === 'Enter' || event.key === ' ') browseFiles(); }}
       class:dragging={isDragging}>
    
    <div class="upload-content">
      <div class="upload-icon">
        {#if uploadProgress === 100}
          <CheckCircle2 size={58} />
        {:else if isUploading}
          <span class="spin"><Loader2 size={58} /></span>
        {:else}
          <UploadCloud size={58} />
        {/if}
      </div>
      
      <h3>{selectedFileName || 'Drop evidence here'}</h3>
      <p>Markdown or text files up to 5MB</p>
      <Button size="sm" variant="secondary" onclick={(event) => { event.stopPropagation(); browseFiles(); }}>
        Browse Files
      </Button>
      
      <input 
        type="file" 
        bind:this={fileInput}
        onchange={handleFileSelect}
        accept=".md,.txt,.markdown"
        class="file-input"
      />
    </div>
  </div>

  {#if uploadStatus}
    <div class="upload-status">
      <CheckCircle2 size={18} />
      <p>{uploadStatus}</p>
      <div class="progress-bar">
        <div class="progress" style="width: {uploadProgress}%"></div>
      </div>
    </div>
  {/if}

  {#if uploadError}
    <div class="upload-error">
      <XCircle size={18} />
      <p>{uploadError}</p>
    </div>
  {/if}

  <div class="upload-footer">
    <Button variant="secondary" onclick={() => onclose?.()}>Cancel</Button>
  </div>
</div>

<style>
  .file-upload-modal {
    max-width: 560px;
    width: 100%;
  }

  .task-context {
    background: rgba(0, 120, 255, 0.06);
    border: 1px solid rgba(0, 240, 255, 0.18);
    border-radius: var(--border-radius-lg);
    margin-bottom: var(--spacing-md);
    padding: var(--spacing-md);
  }

  .task-context strong {
    color: var(--color-text);
    display: block;
    line-height: 1.35;
    margin-top: 6px;
    overflow-wrap: anywhere;
  }

  .mono-label {
    align-items: center;
    display: inline-flex;
    gap: 7px;
  }

  .upload-area {
    background:
      radial-gradient(circle at 50% 8%, rgba(0, 240, 255, 0.12), transparent 32%),
      linear-gradient(180deg, rgba(9, 17, 25, 0.95), rgba(3, 8, 13, 0.95));
    border: 1px dashed rgba(103, 128, 151, 0.54);
    border-radius: var(--border-radius-lg);
    min-height: 260px;
    padding: var(--spacing-xl) var(--spacing-lg);
    position: relative;
    text-align: center;
    transition: all 0.3s ease;
    cursor: pointer;
    overflow: hidden;
  }

  .upload-area::before {
    background-image:
      linear-gradient(rgba(43, 206, 255, 0.08) 1px, transparent 1px),
      linear-gradient(90deg, rgba(43, 206, 255, 0.08) 1px, transparent 1px);
    background-size: 22px 22px;
    content: "";
    inset: 0;
    opacity: 0.52;
    pointer-events: none;
    position: absolute;
  }

  .upload-area.dragging {
    border-color: var(--color-accent);
    box-shadow: var(--shadow-glow);
    transform: translateY(-1px);
  }

  .upload-content {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 200px;
  }

  .upload-icon {
    align-items: center;
    border: 1px solid rgba(0, 240, 255, 0.34);
    border-radius: var(--border-radius-lg);
    color: var(--color-accent);
    display: flex;
    height: 84px;
    justify-content: center;
    margin-bottom: var(--spacing-lg);
    width: 84px;
  }

  .upload-area h3 {
    color: var(--color-text);
    font-size: 1.15rem;
    margin: 0 0 var(--spacing-xs);
    overflow-wrap: anywhere;
  }

  .upload-area p {
    color: var(--color-text-secondary);
    margin: 0 0 var(--spacing-md);
  }

  .file-input {
    display: none;
  }

  .upload-status {
    align-items: center;
    background: rgba(82, 245, 106, 0.08);
    border: 1px solid rgba(82, 245, 106, 0.22);
    border-radius: var(--border-radius-md);
    color: var(--color-success);
    display: grid;
    gap: var(--spacing-sm);
    grid-template-columns: auto 1fr;
    margin-top: var(--spacing-lg);
    padding: var(--spacing-md);
  }

  .upload-status p {
    color: var(--color-text);
    margin: 0;
  }

  .progress-bar {
    grid-column: 1 / -1;
    width: 100%;
    height: 4px;
    background-color: rgba(82, 245, 106, 0.12);
    border-radius: var(--border-radius-sm);
    overflow: hidden;
  }

  .progress {
    height: 100%;
    background: linear-gradient(90deg, var(--color-success), var(--color-accent));
    transition: width 0.3s ease;
  }

  .upload-error {
    align-items: flex-start;
    display: flex;
    gap: var(--spacing-sm);
    margin-top: var(--spacing-lg);
    padding: var(--spacing-md);
    background-color: rgba(255, 71, 87, 0.1);
    border: 1px solid rgba(255, 61, 79, 0.3);
    border-radius: var(--border-radius-sm);
    color: var(--color-error);
  }

  .upload-error p {
    margin: 0;
  }

  .upload-footer {
    display: flex;
    justify-content: flex-end;
    margin-top: var(--spacing-lg);
  }

  .spin {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
