<script setup lang="ts">
import { computed, shallowRef, watch } from 'vue'
import type { TaskExecution } from '../../types/api'

const props = defineProps<{
  executions: TaskExecution[]
  selectedJobId?: string
}>()

const emit = defineEmits<{
  openTimeline: [jobId: string]
  select: [jobId: string]
}>()

interface TaskExecutionGroup {
  jobId: string
  executions: TaskExecution[]
  status: string
  taskCount: number
  startedAt?: string | null
  lastActivityAt?: string | null
  message?: string | null
  lastActivityMs: number
}

const page = shallowRef(1)
const itemsPerPage = shallowRef(10)
const itemsPerPageOptions = [10, 25, 50]
const expandedJobId = shallowRef<string | null>(null)

const statusMeta: Record<string, { color: string; icon: string }> = {
  queued: { color: 'grey', icon: 'mdi-clock-outline' },
  running: { color: 'info', icon: 'mdi-progress-clock' },
  completed: { color: 'success', icon: 'mdi-check-circle-outline' },
  failed: { color: 'error', icon: 'mdi-alert-circle-outline' },
  cancelled: { color: 'warning', icon: 'mdi-cancel' },
}

const groupedExecutions = computed<TaskExecutionGroup[]>(() => {
  const grouped = new Map<string, TaskExecution[]>()

  for (const execution of props.executions) {
    const executions = grouped.get(execution.job_id) ?? []
    executions.push(execution)
    grouped.set(execution.job_id, executions)
  }

  return Array.from(grouped.entries())
    .map(([jobId, executions]) => {
      const sortedExecutions = [...executions].sort(
        (a, b) => getTimestamp(a.created_at) - getTimestamp(b.created_at),
      )
      const latestExecution = findLatestExecution(sortedExecutions)
      const lastActivityAt = latestExecution?.updated_at ?? latestExecution?.created_at ?? null

      return {
        jobId,
        executions: sortedExecutions,
        status: aggregateStatus(sortedExecutions),
        taskCount: sortedExecutions.length,
        startedAt: findEarliestStart(sortedExecutions),
        lastActivityAt,
        message: latestExecution?.message ?? null,
        lastActivityMs: getTimestamp(lastActivityAt),
      }
    })
    .sort((a, b) => b.lastActivityMs - a.lastActivityMs)
})

const totalPages = computed(() => Math.max(1, Math.ceil(groupedExecutions.value.length / itemsPerPage.value)))

const paginatedGroups = computed(() => {
  const start = (page.value - 1) * itemsPerPage.value
  return groupedExecutions.value.slice(start, start + itemsPerPage.value)
})

const paginationLabel = computed(() => {
  if (groupedExecutions.value.length === 0) return ''
  const start = (page.value - 1) * itemsPerPage.value + 1
  const end = Math.min(start + itemsPerPage.value - 1, groupedExecutions.value.length)
  return `${start}-${end} of ${groupedExecutions.value.length} jobs`
})

watch(totalPages, (nextTotalPages) => {
  if (page.value > nextTotalPages) {
    page.value = nextTotalPages
  }
})

watch(itemsPerPage, () => {
  page.value = 1
})

watch(() => props.executions, () => {
  page.value = 1
})

function formatTaskName(taskName: string): string {
  return taskName.replace('cm_worker.', '').replaceAll('_', ' ')
}

function getTimestamp(value?: string | null): number {
  if (!value) return 0
  const timestamp = new Date(value).getTime()
  return Number.isNaN(timestamp) ? 0 : timestamp
}

function findLatestExecution(executions: TaskExecution[]): TaskExecution | undefined {
  return executions.reduce<TaskExecution | undefined>((latest, execution) => {
    if (!latest) return execution
    const currentTimestamp = getTimestamp(execution.updated_at ?? execution.created_at)
    const latestTimestamp = getTimestamp(latest.updated_at ?? latest.created_at)
    return currentTimestamp > latestTimestamp ? execution : latest
  }, undefined)
}

function findEarliestStart(executions: TaskExecution[]): string | null {
  return executions.reduce<string | null>((earliest, execution) => {
    const current = execution.started_at ?? execution.created_at
    if (!earliest) return current
    return getTimestamp(current) < getTimestamp(earliest) ? current : earliest
  }, null)
}

function aggregateStatus(executions: TaskExecution[]): string {
  if (executions.some((execution) => execution.status === 'running')) return 'running'
  if (executions.some((execution) => execution.status === 'queued')) return 'queued'
  if (executions.some((execution) => execution.status === 'failed')) return 'failed'
  if (executions.every((execution) => execution.status === 'completed')) return 'completed'
  if (executions.every((execution) => execution.status === 'cancelled')) return 'cancelled'
  return findLatestExecution(executions)?.status ?? 'unknown'
}

function statusColor(status: string): string {
  return statusMeta[status]?.color ?? 'grey'
}

function statusIcon(status: string): string {
  return statusMeta[status]?.icon ?? 'mdi-help-circle-outline'
}

function formatDate(value?: string | null): string {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

function formatDurationRange(start?: string | null, end?: string | null): string {
  if (!start || !end) return '-'
  const durationMs = Math.max(0, new Date(end).getTime() - new Date(start).getTime())
  if (durationMs < 1000) return '< 1s'
  const seconds = Math.round(durationMs / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  return `${minutes}m ${seconds % 60}s`
}

function formatExecutionDuration(execution: TaskExecution): string {
  return formatDurationRange(
    execution.started_at ?? execution.created_at,
    execution.finished_at ?? execution.updated_at,
  )
}

function formatGroupDuration(group: TaskExecutionGroup): string {
  return formatDurationRange(group.startedAt, group.lastActivityAt)
}

function formatTaskCount(count: number): string {
  return `${count} task${count === 1 ? '' : 's'}`
}

function isGroupExpanded(group: TaskExecutionGroup): boolean {
  return expandedJobId.value === group.jobId
}

function toggleGroup(group: TaskExecutionGroup): void {
  emit('select', group.jobId)
  expandedJobId.value = expandedJobId.value === group.jobId ? null : group.jobId
}

function selectExecution(execution: TaskExecution): void {
  emit('select', execution.job_id)
}

function openGroupTimeline(group: TaskExecutionGroup): void {
  emit('select', group.jobId)
  emit('openTimeline', group.jobId)
}
</script>

<template>
  <div class="history-table">
    <VTable v-if="paginatedGroups.length" class="job-table" density="comfortable" hover>
      <thead>
        <tr>
          <th class="expand-cell"></th>
          <th>Status</th>
          <th>Job</th>
          <th>Tasks</th>
          <th>Started</th>
          <th>Duration</th>
          <th>Message</th>
          <th class="action-cell"></th>
        </tr>
      </thead>
      <tbody>
        <template v-for="group in paginatedGroups" :key="group.jobId">
          <tr
            class="job-row"
            :class="{
              expanded: isGroupExpanded(group),
              selected: group.jobId === selectedJobId,
            }"
            @click="toggleGroup(group)"
          >
            <td class="expand-cell">
              <VBtn
                :aria-expanded="isGroupExpanded(group)"
                :icon="isGroupExpanded(group) ? 'mdi-chevron-down' : 'mdi-chevron-right'"
                size="x-small"
                :title="isGroupExpanded(group) ? 'Close tasks' : 'Open tasks'"
                variant="text"
                @click.stop="toggleGroup(group)"
              />
            </td>
            <td>
              <VChip
                :color="statusColor(group.status)"
                :prepend-icon="statusIcon(group.status)"
                size="small"
                variant="tonal"
              >
                {{ group.status }}
              </VChip>
            </td>
            <td class="job-cell">
              <span class="mono job-id">{{ group.jobId }}</span>
            </td>
            <td>
              <VChip size="x-small" variant="tonal">{{ formatTaskCount(group.taskCount) }}</VChip>
            </td>
            <td>{{ formatDate(group.startedAt) }}</td>
            <td>{{ formatGroupDuration(group) }}</td>
            <td class="message-cell">{{ group.message ?? '-' }}</td>
            <td class="action-cell">
              <VBtn
                class="timeline-button"
                prepend-icon="mdi-timeline-clock-outline"
                size="small"
                variant="tonal"
                @click.stop="openGroupTimeline(group)"
              >
                Timeline
              </VBtn>
            </td>
          </tr>
          <tr v-if="isGroupExpanded(group)" class="tasks-row">
            <td colspan="8">
              <VTable class="nested-task-table" density="compact" hover>
                <thead>
                  <tr>
                    <th>Status</th>
                    <th>Task</th>
                    <th>Actor</th>
                    <th>Started</th>
                    <th>Duration</th>
                    <th>Message</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="execution in group.executions"
                    :key="execution.id"
                    @click="selectExecution(execution)"
                  >
                    <td>
                      <VChip
                        :color="statusColor(execution.status)"
                        :prepend-icon="statusIcon(execution.status)"
                        size="small"
                        variant="tonal"
                      >
                        {{ execution.status }}
                      </VChip>
                    </td>
                    <td class="task-cell">{{ formatTaskName(execution.task_name) }}</td>
                    <td>{{ execution.actor }}</td>
                    <td>{{ formatDate(execution.started_at ?? execution.created_at) }}</td>
                    <td>{{ formatExecutionDuration(execution) }}</td>
                    <td class="message-cell">{{ execution.message ?? '-' }}</td>
                  </tr>
                </tbody>
              </VTable>
            </td>
          </tr>
        </template>
      </tbody>
    </VTable>

    <div v-else class="empty-row muted-text">No task executions yet.</div>

    <div v-if="groupedExecutions.length > 0" class="history-pagination">
      <div class="pagination-label muted-text">{{ paginationLabel }}</div>
      <VPagination
        v-model="page"
        :length="totalPages"
        density="comfortable"
        rounded="circle"
        size="small"
        total-visible="5"
      />
      <VSelect
        v-model="itemsPerPage"
        :items="itemsPerPageOptions"
        aria-label="Jobs per page"
        class="items-per-page"
        density="compact"
        hide-details
        variant="outlined"
      />
    </div>
  </div>
</template>

<style scoped>
.history-table {
  max-width: 100%;
  overflow-x: auto;
}

.job-table {
  min-width: 1080px;
}

.history-table :deep(th) {
  color: #626f86;
  font-size: 12px;
  font-weight: 700;
}

.history-table :deep(tbody tr) {
  cursor: pointer;
}

.job-row {
  border-bottom: 1px solid #dfe1e6;
}

.job-row.selected {
  background: #eef4ff;
}

.job-row.expanded {
  background: #f7f9fc;
}

.expand-cell {
  width: 44px;
}

.job-cell {
  max-width: 320px;
}

.job-id {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.action-cell {
  width: 132px;
  text-align: end;
}

.tasks-row {
  background: #fafbfc;
}

.tasks-row > td {
  padding: 0 0 10px 44px;
}

.nested-task-table {
  border-left: 2px solid #dfe1e6;
}

.nested-task-table :deep(table) {
  min-width: 840px;
}

.task-cell {
  font-weight: 600;
  text-transform: capitalize;
}

.message-cell {
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-row {
  padding: 24px 0;
  text-align: center;
}

.history-pagination {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 14px;
}

.pagination-label {
  margin-right: auto;
}

.items-per-page {
  max-width: 96px;
}

@media (max-width: 960px) {
  .job-table {
    min-width: 980px;
  }
}
</style>
