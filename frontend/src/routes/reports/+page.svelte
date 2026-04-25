<script>
  import AppShell from '../../lib/components/Layout/AppShell.svelte';
  import Reports from '../../lib/components/Reports/Reports.svelte';
  import { page } from '$app/stores';

  let ideaId = $page.params.ideaId;
</script>

<AppShell>
  <Reports {ideaId} />
</AppShell>