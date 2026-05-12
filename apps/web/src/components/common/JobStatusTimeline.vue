<script setup lang="ts">
import { shallowRef, watch } from 'vue'
import { fetchJobEvents } from '../../api/jobs'
import type { JobEvent } from '../../types/api'

const props = defineProps<{
  jobId?: string
}>()

const events = shallowRef<JobEvent[]>([])
const loading = shallowRef(false)
const error = shallowRef<string | null>(null)

/** Loads worker progress events for the provided job id. */
async function loadEvents(): Promise<void> {
  if (!props.jobId) {
    events.value = []
    error.value = null
    return
  }
  loading.value = true
  error.value = null
  try {
    events.value = await fetchJobEvents(props.jobId)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unable to load job events'
    events.value = []
  } finally {
    loading.value = false
  }
}

watch(() => props.jobId, loadEvents, { immediate: true })
</script>

<template>
  <div v-if="loading" class="timeline-state muted-text">Loading events...</div>
  <VAlert v-else-if="error" type="error" variant="tonal" density="compact">
    {{ error }}
  </VAlert>
  <VTimeline v-else-if="events.length" density="compact" side="end">
    <VTimelineItem
      v-for="event in events"
      :key="event.id"
      :dot-color="event.level === 'error' ? 'error' : 'primary'"
      size="x-small"
    >
      <div class="text-body-2">{{ event.message }}</div>
      <div class="text-caption muted-text">{{ new Date(event.created_at).toLocaleString() }}</div>
    </VTimelineItem>
  </VTimeline>
  <div v-else-if="jobId" class="timeline-state muted-text">No progress events for this job.</div>
</template>

<style scoped>
.timeline-state {
  padding: 12px 0;
}
</style>
