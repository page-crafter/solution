<script setup lang="ts">
import { onMounted, shallowRef } from 'vue'
import { fetchTaskHistory } from '../../api/jobs'
import JobStatusTimeline from '../common/JobStatusTimeline.vue'
import TaskHistoryTable from './TaskHistoryTable.vue'
import type { TaskExecution } from '../../types/api'

const TASK_HISTORY_LIMIT = 200

const jobId = shallowRef('')
const executions = shallowRef<TaskExecution[]>([])
const loading = shallowRef(false)
const error = shallowRef<string | null>(null)
const timelineDialog = shallowRef(false)

async function loadHistory(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    executions.value = await fetchTaskHistory(TASK_HISTORY_LIMIT)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unable to load task history'
  } finally {
    loading.value = false
  }
}

function selectJob(selectedJobId: string): void {
  jobId.value = selectedJobId
}

function openTimeline(selectedJobId: string): void {
  jobId.value = selectedJobId
  timelineDialog.value = true
}

onMounted(loadHistory)
</script>

<template>
  <VCard class="runs-card surface-border">
    <div class="runs-header">
      <div>
        <div class="text-caption muted-text">Worker tasks</div>
        <div class="text-body-2">Recent execution history</div>
      </div>
      <VBtn
        :loading="loading"
        icon="mdi-refresh"
        title="Refresh history"
        variant="text"
        @click="loadHistory"
      />
    </div>
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
  </VCard>
</template>

<style scoped>
.runs-card {
  padding: 16px;
}

.runs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
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
