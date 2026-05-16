import { describe, expect, it } from 'vitest'
import { formatAbsoluteDateTime, formatDurationRange, formatRelativeTime, getTimestamp } from './dateTime'

describe('dateTime utilities', () => {
  it('returns zero for invalid timestamps', () => {
    expect(getTimestamp('not-a-date')).toBe(0)
  })

  it('formats relative time against a supplied clock', () => {
    expect(formatRelativeTime('2026-05-15T10:00:00.000Z', Date.parse('2026-05-15T10:02:00.000Z'))).toBe('2m ago')
  })

  it('formats duration ranges compactly', () => {
    expect(formatDurationRange('2026-05-15T10:00:00.000Z', '2026-05-15T10:01:05.000Z')).toBe('1m 5s')
  })

  it('returns an empty absolute date for missing values', () => {
    expect(formatAbsoluteDateTime(null)).toBe('')
  })
})
