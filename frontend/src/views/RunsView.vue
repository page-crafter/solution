<script setup lang="ts">
import AdminPageShell from '../components/common/AdminPageShell.vue'
import RunsActivity from '../components/jobs/RunsActivity.vue'
</script>

<template>
  <AdminPageShell
    title="Events and Activity"
    description="Review worker activity without mixing long-running work into the API."
  >
    <RunsActivity />
  </AdminPageShell>
</template>
