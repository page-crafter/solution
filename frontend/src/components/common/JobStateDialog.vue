<script setup lang="ts">
import { computed, onUnmounted, shallowRef, watch } from 'vue'
import { fetchJob } from '../../api/jobs'
import type { JobRead } from '../../types/api'
import { isErrorJobStatus, isFinishedJobStatus, jobStatusColor, jobStatusIcon } from '../../utils/jobStatus'
import JobStatusChip from './JobStatusChip.vue'

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

const isFinished = computed(() => isFinishedJobStatus(job.value?.status))
const statusText = computed(() => job.value?.status ?? 'queued')
const messageText = computed(() => job.value?.message || job.value?.id || props.pendingLabel)
const statusColor = computed(() => jobStatusColor(statusText.value))
const statusIcon = computed(() => jobStatusIcon(statusText.value))

/** Stops job polling when the dialog closes or reaches a terminal state. */
function stopPolling(): void {
  if (!pollTimer) return
  window.clearInterval(pollTimer)
  pollTimer = undefined
}

/** Clears a pending auto-close timer before scheduling a new one. */
function clearCloseTimer(): void {
  if (!closeTimer) return
  window.clearTimeout(closeTimer)
  closeTimer = undefined
}

/** Hides the status dialog and notifies the parent that it was closed. */
function closeDialog(): void {
  visible.value = false
  emit('closed')
}

/** Schedules automatic dialog close for successful jobs when enabled. */
function scheduleClose(): void {
  clearCloseTimer()
  closeTimer = window.setTimeout(closeDialog, props.autoCloseDelayMs)
}

/** Loads the current job state, emits completion once, and manages polling closeout. */
async function loadJob(): Promise<void> {
  if (!props.jobId) return
  const currentJobId = props.jobId
  const nextJob = await fetchJob(currentJobId)
  if (props.jobId !== currentJobId) return
  job.value = nextJob
  if (!isFinishedJobStatus(nextJob.status)) return
  stopPolling()
  if (finishedJobId.value !== nextJob.id) {
    finishedJobId.value = nextJob.id
    emit('finished', nextJob)
  }
  const isError = isErrorJobStatus(nextJob.status)
  if (props.autoClose && !isError) {
    scheduleClose()
  }
}

/** Starts interval polling for the active job id. */
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
          <JobStatusChip :status="statusText" />
          <p class="muted-text">{{ messageText }}</p>
        </div>
        <VBtn
          v-if="isFinished && isErrorJobStatus(job?.status)"
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
