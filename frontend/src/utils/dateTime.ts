/** Returns a safe timestamp in milliseconds for sortable optional date strings. */
export function getTimestamp(value?: string | null): number {
  if (!value) return 0
  const timestamp = new Date(value).getTime()
  return Number.isNaN(timestamp) ? 0 : timestamp
}

/** Formats an optional date as a short relative label using the supplied clock. */
export function formatRelativeTime(value?: string | null, now = Date.now()): string {
  if (!value) return '-'
  const timestamp = getTimestamp(value)
  if (!timestamp) return '-'
  const diffMs = now - timestamp
  const diffSec = Math.floor(diffMs / 1000)
  if (diffSec < 10) return 'just now'
  if (diffSec < 60) return `${diffSec}s ago`
  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour}h ago`
  const diffDay = Math.floor(diffHour / 24)
  if (diffDay === 1) return 'Yesterday'
  if (diffDay < 7) return `${diffDay}d ago`
  return new Date(value).toLocaleDateString()
}

/** Formats an optional date as the browser locale's full date-time label. */
export function formatAbsoluteDateTime(value?: string | null): string {
  if (!value) return ''
  return new Date(value).toLocaleString()
}

/** Formats the elapsed time between two optional date strings. */
export function formatDurationRange(start?: string | null, end?: string | null): string {
  if (!start || !end) return '-'
  const durationMs = Math.max(0, getTimestamp(end) - getTimestamp(start))
  if (durationMs < 1000) return '< 1s'
  const seconds = Math.round(durationMs / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  return `${minutes}m ${seconds % 60}s`
}

/** Formats a millisecond duration for compact metrics displays. */
export function formatDurationMs(value: number): string {
  if (value < 1000) return `${value}ms`
  const seconds = value / 1000
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 1 : 0)}s`
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = Math.round(seconds % 60)
  return `${minutes}m ${remainingSeconds}s`
}
