<script setup lang="ts">
import { onUnmounted, shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import AdminPageShell from '../components/common/AdminPageShell.vue'
import { useEasterEggs } from '../composables/useEasterEggs'

const router = useRouter()
const { showSecretNotification } = useEasterEggs()
const restoring = shallowRef(false)
let restoreTimer = 0

/** Runs the fake restore flow and returns to the dashboard. */
function restoreArchive(): void {
  if (restoring.value) return
  restoring.value = true
  showSecretNotification('Archive restore queued')
  restoreTimer = window.setTimeout(() => {
    void router.push('/dashboard')
  }, 900)
}

onUnmounted(() => {
  if (restoreTimer) window.clearTimeout(restoreTimer)
})
</script>

<template>
  <AdminPageShell
    title="Archived Confluence page"
    description="This page was moved in 2014 and has been waiting politely ever since."
  >
    <div class="secret-archive">
      <VCard class="secret-archive__panel surface-border" variant="flat">
        <div class="secret-archive__status">
          <VIcon icon="mdi-archive-clock-outline" size="28" color="primary" />
          <div>
            <h2 class="secret-archive__title">DOC-404: Lost Runbook</h2>
            <p class="secret-archive__meta">Space DOC · version 13 · status archived</p>
          </div>
        </div>

        <VDivider />

        <div class="secret-archive__body">
          <p>
            The knowledge engine found a page with excellent formatting, questionable ownership,
            and one unresolved comment from a very old migration.
          </p>
          <VAlert
            density="compact"
            type="info"
            variant="tonal"
            icon="mdi-source-branch"
          >
            Restore simulation only. No Confluence content will be changed.
          </VAlert>
        </div>

        <div class="secret-archive__actions">
          <VBtn
            color="primary"
            prepend-icon="mdi-restore"
            :loading="restoring"
            @click="restoreArchive"
          >
            Restore from archive
          </VBtn>
        </div>
      </VCard>
    </div>
  </AdminPageShell>
</template>

<style scoped>
.secret-archive {
  display: grid;
  min-height: calc(100dvh - 190px);
  place-items: center;
}

.secret-archive__panel {
  display: grid;
  gap: 18px;
  width: min(640px, 100%);
  padding: 22px;
  border-radius: 8px;
  background: #ffffff;
}

.secret-archive__status {
  display: flex;
  gap: 14px;
  align-items: center;
}

.secret-archive__title {
  margin: 0;
  font-size: 20px;
  line-height: 28px;
}

.secret-archive__meta {
  margin: 2px 0 0;
  color: #626f86;
}

.secret-archive__body {
  display: grid;
  gap: 12px;
  line-height: 1.6;
}

.secret-archive__body p {
  margin: 0;
}

.secret-archive__actions {
  display: flex;
  justify-content: flex-end;
}
</style>
