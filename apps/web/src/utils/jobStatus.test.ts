import { describe, expect, it } from 'vitest'
import {
  formatTaskName,
  isActiveJobStatus,
  isErrorJobStatus,
  isFinishedJobStatus,
  jobStatusColor,
  jobStatusIcon,
} from './jobStatus'

describe('jobStatus utilities', () => {
  it('classifies active, finished, and error statuses', () => {
    expect(isActiveJobStatus('running')).toBe(true)
    expect(isFinishedJobStatus('completed')).toBe(true)
    expect(isErrorJobStatus('blocked')).toBe(true)
  })

  it('resolves status presentation metadata', () => {
    expect(jobStatusColor('failed')).toBe('error')
    expect(jobStatusIcon('running')).toBe('mdi-progress-clock')
  })

  it('formats worker task names for display', () => {
    expect(formatTaskName('cm_worker.sync_pages')).toBe('sync pages')
  })
})
