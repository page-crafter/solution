<script setup lang="ts">
import { computed, onUnmounted, shallowRef, watch } from 'vue'
import { fetchJob } from '../../api/jobs'
import type { JobRead } from '../../types/api'

const FINISHED_STATUSES = new Set(['completed', 'failed', 'canceled', 'cancelled', 'published', 'blocked'])

const props = withDefaults(defineProps<{
  jobId?: string
  title?: string
  pendingLabel?: string
  autoClose?: boolean
  autoCloseDelayMs?: number
}>(), {
  title: 'Processing',
  pendingLabel: 'Starting job',
  autoClose: true,
  autoCloseDelayMs: 900,
})

const emit = defineEmits<{
  closed: []
  finished: [job: JobRead]
}>()

const job = shallowRef<JobRead>()
const visible = shallowRef(false)
const finishedJobId = shallowRef<string>()
let pollTimer: number | undefined
let closeTimer: number | undefined

const isFinished = computed(() => Boolean(job.value && FINISHED_STATUSES.has(job.value.status)))
const statusText = computed(() => job.value?.status ?? 'queued')
const messageText = computed(() => job.value?.message || job.value?.id || props.pendingLabel)
const statusColor = computed(() => {
  if (job.value?.status === 'failed' || job.value?.status === 'blocked') return 'error'
  if (isFinished.value) return 'success'
  return 'primary'
})
const statusIcon = computed(() => {
  if (job.value?.status === 'failed' || job.value?.status === 'blocked') return 'mdi-alert-circle-outline'
  if (isFinished.value) return 'mdi-check-circle-outline'
  return 'mdi-progress-clock'
})

function stopPolling(): void {
  if (!pollTimer) return
  window.clearInterval(pollTimer)
  pollTimer = undefined
}

function clearCloseTimer(): void {
  if (!closeTimer) return
  window.clearTimeout(closeTimer)
  closeTimer = undefined
}

function closeDialog(): void {
  visible.value = false
  emit('closed')
}

function scheduleClose(): void {
  clearCloseTimer()
  closeTimer = window.setTimeout(closeDialog, props.autoCloseDelayMs)
}

async function loadJob(): Promise<void> {
  if (!props.jobId) return
  const currentJobId = props.jobId
  const nextJob = await fetchJob(currentJobId)
  if (props.jobId !== currentJobId) return
  job.value = nextJob
  if (!FINISHED_STATUSES.has(nextJob.status)) return
  stopPolling()
  if (finishedJobId.value !== nextJob.id) {
    finishedJobId.value = nextJob.id
    emit('finished', nextJob)
  }
  const isError = nextJob.status === 'failed' || nextJob.status === 'blocked'
  if (props.autoClose && !isError) {
    scheduleClose()
  }
}

function startPolling(): void {
  stopPolling()
  pollTimer = window.setInterval(loadJob, 1500)
}

watch(
  () => props.jobId,
  (jobId) => {
    stopPolling()
    clearCloseTimer()
    job.value = undefined
    finishedJobId.value = undefined
    visible.value = Boolean(jobId)
    if (!jobId) return
    void loadJob()
    startPolling()
  },
  { immediate: true },
)

onUnmounted(() => {
  stopPolling()
  clearCloseTimer()
})
</script>

<template>
  <VDialog :model-value="visible" persistent width="420">
    <VCard class="job-state-card surface-border">
      <div class="job-state-body">
        <VProgressCircular
          v-if="!isFinished"
          indeterminate
          color="primary"
          size="54"
          width="5"
        />
        <VIcon v-else :icon="statusIcon" :color="statusColor" size="54" />

        <div class="job-state-copy">
          <h2>{{ title }}</h2>
          <VChip :color="statusColor" size="small" variant="tonal">
            {{ statusText }}
          </VChip>
          <p class="muted-text">{{ messageText }}</p>
        </div>
        <VBtn
          v-if="isFinished && (job?.status === 'failed' || job?.status === 'blocked')"
          variant="tonal"
          color="error"
          @click="closeDialog"
        >
          Close
        </VBtn>
      </div>
    </VCard>
  </VDialog>
</template>

<style scoped>
.job-state-card {
  border-radius: 8px;
}

.job-state-body {
  display: grid;
  gap: 18px;
  min-height: 220px;
  padding: 28px;
  place-items: center;
  text-align: center;
}

.job-state-copy {
  display: grid;
  gap: 10px;
  justify-items: center;
  max-width: 320px;
}

h2 {
  margin: 0;
  font-size: 20px;
  line-height: 28px;
}

p {
  margin: 0;
  line-height: 20px;
}
</style>
