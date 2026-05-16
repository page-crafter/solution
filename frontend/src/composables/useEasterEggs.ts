import { readonly, shallowRef } from 'vue'

const HYPERDRIVE_DURATION_MS = 8000
const SIDEBAR_SHUFFLE_DURATION_MS = 1200
const NOTICE_DURATION_MS = 3600
const SIDEBAR_CLICK_WINDOW_MS = 3000
const SIDEBAR_CLICK_TARGET = 5
const KONAMI_SEQUENCE = [
  'ArrowUp',
  'ArrowUp',
  'ArrowDown',
  'ArrowDown',
  'ArrowLeft',
  'ArrowRight',
  'ArrowLeft',
  'ArrowRight',
  'b',
  'a',
]

interface SecretNotification {
  id: number
  message: string
}

const hyperdriveActive = shallowRef(false)
const sidebarShuffleActive = shallowRef(false)
const notificationOpen = shallowRef(false)
const notification = shallowRef<SecretNotification | null>(null)

let notificationId = 0
let hyperdriveTimer = 0
let sidebarShuffleTimer = 0
let notificationTimer = 0
let konamiIndex = 0
let sidebarActivations: number[] = []

/** Clears a browser timer id when it has been set. */
function clearTimer(timerId: number): void {
  if (timerId) window.clearTimeout(timerId)
}

/** Shows a short-lived secret notification without creating app-wide toast plumbing. */
function showSecretNotification(message: string): void {
  clearTimer(notificationTimer)
  notification.value = { id: ++notificationId, message }
  notificationOpen.value = true
  notificationTimer = window.setTimeout(() => {
    notificationOpen.value = false
  }, NOTICE_DURATION_MS)
}

/** Activates the temporary dashboard hyperdrive state. */
function activateHyperdrive(): void {
  clearTimer(hyperdriveTimer)
  hyperdriveActive.value = true
  showSecretNotification('Indexing hyperdrive engaged')
  hyperdriveTimer = window.setTimeout(() => {
    hyperdriveActive.value = false
  }, HYPERDRIVE_DURATION_MS)
}

/** Activates the temporary sidebar shuffle animation. */
function activateSidebarShuffle(): void {
  clearTimer(sidebarShuffleTimer)
  sidebarShuffleActive.value = true
  showSecretNotification('Hierarchy temporarily unsynced')
  sidebarShuffleTimer = window.setTimeout(() => {
    sidebarShuffleActive.value = false
  }, SIDEBAR_SHUFFLE_DURATION_MS)
}

/** Normalizes keydown event keys for the Konami sequence. */
function normalizeKonamiKey(key: string): string {
  if (key.length === 1) return key.toLowerCase()
  return key
}

/** Records a key press and activates hyperdrive when the Konami sequence completes. */
function recordKonamiKey(key: string): void {
  const normalizedKey = normalizeKonamiKey(key)
  const expectedKey = KONAMI_SEQUENCE[konamiIndex]

  if (normalizedKey === expectedKey) {
    konamiIndex += 1
    if (konamiIndex === KONAMI_SEQUENCE.length) {
      konamiIndex = 0
      activateHyperdrive()
    }
    return
  }

  konamiIndex = normalizedKey === KONAMI_SEQUENCE[0] ? 1 : 0
}

/** Records one logo activation and shuffles the sidebar after five quick hits. */
function registerSidebarLogoActivation(now = Date.now()): void {
  sidebarActivations = [...sidebarActivations, now]
    .filter((activationAt) => now - activationAt <= SIDEBAR_CLICK_WINDOW_MS)

  if (sidebarActivations.length < SIDEBAR_CLICK_TARGET) return
  sidebarActivations = []
  activateSidebarShuffle()
}

/** Closes the current secret notification. */
function dismissSecretNotification(): void {
  notificationOpen.value = false
}

/** Clears active easter egg timers and transient state. */
function clearEasterEggTimers(): void {
  clearTimer(hyperdriveTimer)
  clearTimer(sidebarShuffleTimer)
  clearTimer(notificationTimer)
  hyperdriveTimer = 0
  sidebarShuffleTimer = 0
  notificationTimer = 0
}

/** Test-only reset hook for shared module state. */
export function resetEasterEggsForTest(): void {
  clearEasterEggTimers()
  hyperdriveActive.value = false
  sidebarShuffleActive.value = false
  notificationOpen.value = false
  notification.value = null
  konamiIndex = 0
  sidebarActivations = []
}

export function useEasterEggs() {
  return {
    hyperdriveActive: readonly(hyperdriveActive),
    sidebarShuffleActive: readonly(sidebarShuffleActive),
    notification: readonly(notification),
    notificationOpen: readonly(notificationOpen),
    activateHyperdrive,
    registerSidebarLogoActivation,
    recordKonamiKey,
    showSecretNotification,
    dismissSecretNotification,
    clearEasterEggTimers,
  }
}
