<script setup lang="ts">
import PageHeader from '../components/common/PageHeader.vue'
import RunsActivity from '../components/jobs/RunsActivity.vue'
</script>

<template>
  <VContainer fluid class="pa-4">
    <PageHeader
      title="Events and Activity"
      description="Review worker activity without mixing long-running work into the API."
    />
    <RunsActivity />
  </VContainer>
</template>
