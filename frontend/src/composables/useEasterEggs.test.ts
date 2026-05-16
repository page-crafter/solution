import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { resetEasterEggsForTest, useEasterEggs } from './useEasterEggs'

describe('useEasterEggs', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    resetEasterEggsForTest()
  })

  afterEach(() => {
    resetEasterEggsForTest()
    vi.useRealTimers()
  })

  it('activates and expires hyperdrive from the Konami sequence', () => {
    const { hyperdriveActive, notificationOpen, recordKonamiKey } = useEasterEggs()

    for (const key of ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'b', 'a']) {
      recordKonamiKey(key)
    }

    expect(hyperdriveActive.value).toBe(true)
    expect(notificationOpen.value).toBe(true)

    vi.advanceTimersByTime(8000)

    expect(hyperdriveActive.value).toBe(false)
  })

  it('shuffles the sidebar after five quick logo activations', () => {
    const { sidebarShuffleActive, registerSidebarLogoActivation } = useEasterEggs()

    for (const offset of [0, 250, 500, 750]) {
      registerSidebarLogoActivation(1000 + offset)
    }

    expect(sidebarShuffleActive.value).toBe(false)

    registerSidebarLogoActivation(2000)

    expect(sidebarShuffleActive.value).toBe(true)

    vi.advanceTimersByTime(1200)

    expect(sidebarShuffleActive.value).toBe(false)
  })
})
