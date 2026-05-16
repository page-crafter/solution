export const ACTIVE_JOB_STATUSES = new Set(['queued', 'running'])
export const FINISHED_JOB_STATUSES = new Set([
  'blocked',
  'canceled',
  'cancelled',
  'completed',
  'failed',
  'finished',
  'published',
  'success',
])

const JOB_STATUS_META: Record<string, { color: string; icon: string }> = {
  blocked: { color: 'error', icon: 'mdi-alert-circle-outline' },
  canceled: { color: 'warning', icon: 'mdi-cancel' },
  cancelled: { color: 'warning', icon: 'mdi-cancel' },
  completed: { color: 'success', icon: 'mdi-check-circle-outline' },
  failed: { color: 'error', icon: 'mdi-alert-circle-outline' },
  finished: { color: 'success', icon: 'mdi-check-circle-outline' },
  published: { color: 'success', icon: 'mdi-check-circle-outline' },
  queued: { color: 'grey', icon: 'mdi-clock-outline' },
  running: { color: 'info', icon: 'mdi-progress-clock' },
  success: { color: 'success', icon: 'mdi-check-circle-outline' },
}

/** Returns whether a backend job status still represents active work. */
export function isActiveJobStatus(status: string): boolean {
  return ACTIVE_JOB_STATUSES.has(status)
}

/** Returns whether a backend job status represents a terminal state. */
export function isFinishedJobStatus(status?: string | null): boolean {
  return Boolean(status && FINISHED_JOB_STATUSES.has(status))
}

/** Returns whether a backend job status should be presented as an error. */
export function isErrorJobStatus(status?: string | null): boolean {
  return status === 'failed' || status === 'blocked'
}

/** Resolves the Vuetify color used to present a backend job status. */
export function jobStatusColor(status?: string | null): string {
  if (!status) return 'grey'
  return JOB_STATUS_META[status]?.color ?? 'grey'
}

/** Resolves the Material Design icon used to present a backend job status. */
export function jobStatusIcon(status?: string | null): string {
  if (!status) return 'mdi-help-circle-outline'
  return JOB_STATUS_META[status]?.icon ?? 'mdi-help-circle-outline'
}

/** Converts a worker task name into a compact user-facing label. */
export function formatTaskName(taskName: string): string {
  return taskName.replace('page_crafter.', '').replaceAll('_', ' ')
}
