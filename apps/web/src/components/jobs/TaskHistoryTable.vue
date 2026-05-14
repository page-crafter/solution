<script setup lang="ts">
import { computed, onMounted, onUnmounted, shallowRef, watch } from 'vue'
import type { TaskExecution } from '../../types/api'
import { formatAbsoluteDateTime, formatDurationRange, formatRelativeTime, getTimestamp } from '../../utils/dateTime'
import { formatTaskName, isActiveJobStatus } from '../../utils/jobStatus'
import JobStatusChip from '../common/JobStatusChip.vue'

const props = defineProps<{
  executions: TaskExecution[]
  selectedJobId?: string
}>()

const emit = defineEmits<{
  cancel: [jobId: string]
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
const statusFilter = shallowRef<string>('all')
const nowTick = shallowRef(Date.now())

let tickTimer: ReturnType<typeof setInterval> | null = null

const filterOptions = computed(() => {
  const counts: Record<string, number> = { all: allGroups.value.length }
  for (const group of allGroups.value) {
    counts[group.status] = (counts[group.status] ?? 0) + 1
  }
  return [
    { key: 'all', label: 'All', count: counts.all ?? 0 },
    { key: 'running', label: 'Running', count: counts.running ?? 0 },
    { key: 'queued', label: 'Queued', count: counts.queued ?? 0 },
    { key: 'completed', label: 'Completed', count: counts.completed ?? 0 },
    { key: 'failed', label: 'Failed', count: counts.failed ?? 0 },
  ].filter((opt) => opt.key === 'all' || opt.count > 0)
})

const allGroups = computed<TaskExecutionGroup[]>(() => {
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

const groupedExecutions = computed<TaskExecutionGroup[]>(() => {
  if (statusFilter.value === 'all') return allGroups.value
  return allGroups.value.filter((g) => g.status === statusFilter.value)
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

watch(statusFilter, () => {
  page.value = 1
})

onMounted(() => {
  tickTimer = setInterval(() => {
    nowTick.value = Date.now()
  }, 30000)
})

onUnmounted(() => {
  if (tickTimer !== null) clearInterval(tickTimer)
})

/** Finds the most recently updated task execution inside a grouped job. */
function findLatestExecution(executions: TaskExecution[]): TaskExecution | undefined {
  return executions.reduce<TaskExecution | undefined>((latest, execution) => {
    if (!latest) return execution
    const currentTimestamp = getTimestamp(execution.updated_at ?? execution.created_at)
    const latestTimestamp = getTimestamp(latest.updated_at ?? latest.created_at)
    return currentTimestamp > latestTimestamp ? execution : latest
  }, undefined)
}

/** Finds the earliest start timestamp in a grouped job. */
function findEarliestStart(executions: TaskExecution[]): string | null {
  return executions.reduce<string | null>((earliest, execution) => {
    const current = execution.started_at ?? execution.created_at
    if (!earliest) return current
    return getTimestamp(current) < getTimestamp(earliest) ? current : earliest
  }, null)
}

/** Collapses task-level statuses into the single status shown for a job group. */
function aggregateStatus(executions: TaskExecution[]): string {
  if (executions.some((execution) => execution.status === 'running')) return 'running'
  if (executions.some((execution) => execution.status === 'queued')) return 'queued'
  if (executions.some((execution) => execution.status === 'failed')) return 'failed'
  if (executions.every((execution) => execution.status === 'completed')) return 'completed'
  if (executions.every((execution) => execution.status === 'cancelled')) return 'cancelled'
  return findLatestExecution(executions)?.status ?? 'unknown'
}

/** Formats a task timestamp relative to the component's ticking clock. */
function formatRelative(value?: string | null): string {
  return formatRelativeTime(value, nowTick.value)
}

/** Formats a task timestamp for tooltip display. */
function formatAbsolute(value?: string | null): string {
  return formatAbsoluteDateTime(value)
}

/** Formats the duration of one task execution row. */
function formatExecutionDuration(execution: TaskExecution): string {
  return formatDurationRange(
    execution.started_at ?? execution.created_at,
    execution.finished_at ?? execution.updated_at,
  )
}

/** Formats the duration between the first and latest task in a grouped job. */
function formatGroupDuration(group: TaskExecutionGroup): string {
  return formatDurationRange(group.startedAt, group.lastActivityAt)
}

/** Formats the grouped task count with a singular/plural label. */
function formatTaskCount(count: number): string {
  return `${count} task${count === 1 ? '' : 's'}`
}

/** Returns whether the provided group is currently expanded in the table. */
function isGroupExpanded(group: TaskExecutionGroup): boolean {
  return expandedJobId.value === group.jobId
}

/** Toggles a job group and emits selection for parent-level context. */
function toggleGroup(group: TaskExecutionGroup): void {
  emit('select', group.jobId)
  expandedJobId.value = expandedJobId.value === group.jobId ? null : group.jobId
}

/** Emits selection for a nested task execution row. */
function selectExecution(execution: TaskExecution): void {
  emit('select', execution.job_id)
}

/** Selects a grouped job and requests its timeline dialog. */
function openGroupTimeline(group: TaskExecutionGroup): void {
  emit('select', group.jobId)
  emit('openTimeline', group.jobId)
}

/** Returns whether a status is cancellable active work. */
function isActive(status: string): boolean {
  return isActiveJobStatus(status)
}
</script>

<template>
  <div class="history-table">
    <div v-if="filterOptions.length > 1" class="filter-bar">
      <VChip
        v-for="opt in filterOptions"
        :key="opt.key"
        :color="statusFilter === opt.key ? 'primary' : undefined"
        :variant="statusFilter === opt.key ? 'tonal' : 'outlined'"
        class="filter-chip"
        size="small"
        @click="statusFilter = opt.key"
      >
        {{ opt.label }}
        <VBadge
          v-if="opt.key !== 'all'"
          :content="opt.count"
          class="filter-badge"
          inline
        />
      </VChip>
    </div>

    <VTable v-if="paginatedGroups.length" class="job-table" density="comfortable" hover>
      <thead>
        <tr>
          <th class="expand-cell"></th>
          <th>Status</th>
          <th>Job</th>
          <th class="col-tasks">Tasks</th>
          <th class="col-started">Started</th>
          <th class="col-duration">Duration</th>
          <th class="col-message">Message</th>
          <th class="action-cell"></th>
        </tr>
      </thead>
      <tbody>
        <template v-for="group in paginatedGroups" :key="group.jobId">
          <tr
            class="job-row"
            :class="{
              expanded: isGroupExpanded(group),
              running: group.status === 'running',
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
              <JobStatusChip :status="group.status" />
            </td>
            <td class="job-cell">
              <span class="mono job-id">{{ group.jobId }}</span>
            </td>
            <td class="col-tasks">
              <VChip size="x-small" variant="tonal">{{ formatTaskCount(group.taskCount) }}</VChip>
            </td>
            <td class="col-started">
              <VTooltip :text="formatAbsolute(group.startedAt)" location="top">
                <template #activator="{ props: tooltipProps }">
                  <span v-bind="tooltipProps">{{ formatRelative(group.startedAt) }}</span>
                </template>
              </VTooltip>
            </td>
            <td class="col-duration">{{ formatGroupDuration(group) }}</td>
            <td class="col-message message-cell">
              <VTooltip
                v-if="group.message"
                :text="group.message"
                location="top"
                max-width="400"
              >
                <template #activator="{ props: tooltipProps }">
                  <span v-bind="tooltipProps">{{ group.message }}</span>
                </template>
              </VTooltip>
              <span v-else>-</span>
            </td>
            <td class="action-cell">
              <div class="action-buttons">
                <VBtn
                  v-if="isActive(group.status)"
                  class="cancel-button"
                  icon="mdi-stop-circle-outline"
                  size="small"
                  title="Cancel job"
                  variant="text"
                  color="error"
                  @click.stop="emit('cancel', group.jobId)"
                />
                <VBtn
                  class="timeline-button"
                  prepend-icon="mdi-timeline-clock-outline"
                  size="small"
                  variant="tonal"
                  title="Timeline"
                  @click.stop="openGroupTimeline(group)"
                >
                  <span class="btn-label">Timeline</span>
                </VBtn>
              </div>
            </td>
          </tr>
          <tr v-if="isGroupExpanded(group)" class="tasks-row">
            <td colspan="8">
              <VTable class="nested-task-table" density="compact" hover>
                <thead>
                  <tr>
                    <th>Status</th>
                    <th>Task</th>
                    <th class="col-actor">Actor</th>
                    <th class="col-started">Started</th>
                    <th class="col-duration">Duration</th>
                    <th class="col-message">Message</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="execution in group.executions"
                    :key="execution.id"
                    @click="selectExecution(execution)"
                  >
                    <td>
                      <JobStatusChip :status="execution.status" />
                    </td>
                    <td class="task-cell">{{ formatTaskName(execution.task_name) }}</td>
                    <td class="col-actor">{{ execution.actor }}</td>
                    <td class="col-started">
                      <VTooltip
                        :text="formatAbsolute(execution.started_at ?? execution.created_at)"
                        location="top"
                      >
                        <template #activator="{ props: tooltipProps }">
                          <span v-bind="tooltipProps">{{ formatRelative(execution.started_at ?? execution.created_at) }}</span>
                        </template>
                      </VTooltip>
                    </td>
                    <td class="col-duration">{{ formatExecutionDuration(execution) }}</td>
                    <td class="col-message message-cell">
                      <VTooltip
                        v-if="execution.message"
                        :text="execution.message"
                        location="top"
                        max-width="400"
                      >
                        <template #activator="{ props: tooltipProps }">
                          <span v-bind="tooltipProps">{{ execution.message }}</span>
                        </template>
                      </VTooltip>
                      <span v-else>-</span>
                    </td>
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

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding-bottom: 12px;
}

.filter-chip {
  cursor: pointer;
}

.filter-badge {
  margin-left: 4px;
}

.job-table {
  width: 100%;
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

.job-row.running {
  border-left: 3px solid transparent;
  animation: running-pulse 2s ease-in-out infinite;
}

@keyframes running-pulse {
  0%, 100% { border-left-color: #0c66e4; }
  50% { border-left-color: transparent; }
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
  width: 160px;
  text-align: end;
}

.action-buttons {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
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
  width: 100%;
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

/* < 1280px: hide message column */
@media (max-width: 1279px) {
  .col-message {
    display: none;
  }
}

/* < 960px: hide tasks + actor, icon-only timeline button */
@media (max-width: 959px) {
  .col-tasks,
  .col-actor {
    display: none;
  }

  .btn-label {
    display: none;
  }

  .job-cell {
    max-width: 200px;
  }
}

/* < 720px: hide duration */
@media (max-width: 719px) {
  .col-duration {
    display: none;
  }
}

/* < 600px: hide started, items-per-page */
@media (max-width: 599px) {
  .col-started {
    display: none;
  }

  .items-per-page {
    display: none;
  }

  .job-cell {
    max-width: 120px;
  }
}
</style>
