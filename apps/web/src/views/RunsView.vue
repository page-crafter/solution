<script setup lang="ts">
import RunsActivity from '../components/jobs/RunsActivity.vue'
</script>

<template>
  <VContainer fluid class="pa-4">
    <div class="runs-heading">
      <h1>Runs and Activity</h1>
      <p class="muted-text">Review worker activity without mixing long-running work into the API.</p>
    </div>
    <RunsActivity />
  </VContainer>
</template>

<style scoped>
.runs-heading {
  margin-bottom: 14px;
}

h1 {
  margin: 0;
  font-size: 24px;
  line-height: 32px;
}
</style>

