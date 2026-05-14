<script setup lang="ts">
import { computed, onMounted, onUnmounted, shallowRef } from 'vue'
import { cancelJob, fetchTaskHistory } from '../../api/jobs'
import JobStatusTimeline from '../common/JobStatusTimeline.vue'
import SectionCard from '../common/SectionCard.vue'
import TaskHistoryTable from './TaskHistoryTable.vue'
import type { TaskExecution } from '../../types/api'
import { formatRelativeTime } from '../../utils/dateTime'

const TASK_HISTORY_LIMIT = 200
const POLL_INTERVAL_MS = 5000
const TICK_INTERVAL_MS = 10000

const jobId = shallowRef('')
const executions = shallowRef<TaskExecution[]>([])
const loading = shallowRef(false)
const error = shallowRef<string | null>(null)
const timelineDialog = shallowRef(false)
const lastUpdatedAt = shallowRef<Date | null>(null)
const nowTick = shallowRef(Date.now())

let pollTimer: ReturnType<typeof setInterval> | null = null
let tickTimer: ReturnType<typeof setInterval> | null = null

const hasActiveJobs = computed(() =>
  executions.value.some((e) => e.status === 'running' || e.status === 'queued'),
)

const updatedAgoLabel = computed(() => {
  if (!lastUpdatedAt.value) return ''
  return formatRelativeTime(lastUpdatedAt.value.toISOString(), nowTick.value)
})

/** Loads recent worker task history and starts polling when active jobs remain. */
async function loadHistory(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    executions.value = await fetchTaskHistory(TASK_HISTORY_LIMIT)
    lastUpdatedAt.value = new Date()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unable to load task history'
  } finally {
    loading.value = false
  }
  schedulePoll()
}

/** Starts polling only while the latest history includes active jobs. */
function schedulePoll(): void {
  clearPoll()
  if (hasActiveJobs.value) {
    pollTimer = setInterval(async () => {
      await loadHistory()
    }, POLL_INTERVAL_MS)
  }
}

/** Stops the active history polling interval. */
function clearPoll(): void {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

/** Stores the selected job id for row highlighting and timeline context. */
function selectJob(selectedJobId: string): void {
  jobId.value = selectedJobId
}

/** Opens the timeline dialog for the selected job id. */
function openTimeline(selectedJobId: string): void {
  jobId.value = selectedJobId
  timelineDialog.value = true
}

/** Cancels a running job and reloads history so the table reflects the new state. */
async function handleCancel(cancelJobId: string): Promise<void> {
  try {
    await cancelJob(cancelJobId)
    await loadHistory()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unable to cancel job'
  }
}

onMounted(() => {
  loadHistory()
  tickTimer = setInterval(() => {
    nowTick.value = Date.now()
  }, TICK_INTERVAL_MS)
})

onUnmounted(() => {
  clearPoll()
  if (tickTimer !== null) clearInterval(tickTimer)
})
</script>

<template>
  <SectionCard title="Recent execution history" icon="mdi-timeline-clock-outline">
    <template #actions>
      <div class="runs-header-actions">
        <div v-if="hasActiveJobs" class="live-badge">
          <span class="live-dot" />
          <span class="text-caption">Live</span>
        </div>
        <span v-if="lastUpdatedAt && !loading" class="text-caption muted-text updated-label">
          {{ updatedAgoLabel }}
        </span>
        <VBtn
          :loading="loading"
          icon="mdi-refresh"
          title="Refresh history"
          variant="text"
          @click="loadHistory"
        />
      </div>
    </template>
    <VAlert v-if="error" type="error" variant="tonal" density="compact" class="mt-4">
      {{ error }}
    </VAlert>
    <div v-if="loading && executions.length === 0" class="history-state muted-text">
      Loading task history...
    </div>
    <TaskHistoryTable
      v-else
      :executions="executions"
      :selected-job-id="jobId"
      class="mt-4"
      @cancel="handleCancel"
      @open-timeline="openTimeline"
      @select="selectJob"
    />

    <VDialog v-model="timelineDialog" max-width="760">
      <VCard class="timeline-dialog">
        <VCardTitle class="timeline-dialog-title">
          <div>
            <div class="text-caption muted-text">Run events</div>
            <div class="text-body-1">Page edit timeline</div>
          </div>
          <VBtn
            icon="mdi-close"
            size="small"
            title="Close timeline"
            variant="text"
            @click="timelineDialog = false"
          />
        </VCardTitle>
        <VCardText>
          <div class="timeline-job">
            <span class="text-caption muted-text">Job</span>
            <span class="mono timeline-job-id">{{ jobId }}</span>
          </div>
          <JobStatusTimeline :job-id="jobId" />
        </VCardText>
      </VCard>
    </VDialog>
  </SectionCard>
</template>

<style scoped>
.runs-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.live-badge {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #22a06b;
}

.live-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22a06b;
  animation: live-pulse 1.6s ease-in-out infinite;
}

@keyframes live-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.75); }
}

.updated-label {
  white-space: nowrap;
}

.history-state {
  padding: 24px 0;
  text-align: center;
}

.timeline-dialog {
  max-height: 86vh;
}

.timeline-dialog-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.timeline-job {
  display: flex;
  min-width: 0;
  align-items: baseline;
  gap: 8px;
  padding-bottom: 12px;
}

.timeline-job-id {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
