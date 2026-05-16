<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useEasterEggs } from '../../composables/useEasterEggs'
import ParticleBackground from './ParticleBackground.vue'

const {
  hyperdriveActive,
  notification,
  notificationOpen,
  recordKonamiKey,
  dismissSecretNotification,
  clearEasterEggTimers,
} = useEasterEggs()

/** Keeps the global key listener from reacting while users type in editable controls. */
function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  return Boolean(target.closest('input, textarea, select, [contenteditable="true"]'))
}

/** Routes global key presses into the easter egg sequence detector. */
function handleKeydown(event: KeyboardEvent): void {
  if (isEditableTarget(event.target)) return
  recordKonamiKey(event.key)
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  clearEasterEggTimers()
})
</script>

<template>
  <div class="easter-egg-layer" aria-live="polite">
    <ParticleBackground
      v-if="hyperdriveActive"
      class="easter-egg-layer__particles"
      particle-color="#0c66e4"
      :speed="2.4"
      :density="5200"
      :max-distance="150"
    />

    <VSnackbar
      :model-value="notificationOpen"
      location="bottom center"
      color="primary"
      :timeout="3600"
      @update:model-value="dismissSecretNotification"
    >
      {{ notification?.message }}
    </VSnackbar>
  </div>
</template>

<style scoped>
.easter-egg-layer {
  pointer-events: none;
}

.easter-egg-layer__particles {
  position: fixed !important;
  inset: 0;
  z-index: 90;
  opacity: 0.3;
  mix-blend-mode: multiply;
}

.easter-egg-layer :deep(.v-snackbar) {
  pointer-events: auto;
}
</style>
