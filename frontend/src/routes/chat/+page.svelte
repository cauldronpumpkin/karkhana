<script>
  import ChatView from '../../lib/components/Chat/ChatView.svelte';
  import AppShell from '../../lib/components/Layout/AppShell.svelte';
  import { onMount } from 'svelte';

  let ideaId = '1'; // This would come from route params in a real implementation

  onMount(() => {
    // In a real implementation, this would come from route params
    console.log('Chat page loaded for idea:', ideaId);
  });
</script>

<AppShell>
  <ChatView {ideaId} />
</AppShell>