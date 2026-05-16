<script setup lang="ts">
import { computed } from 'vue'
import type { DraftVersion } from '../../types/api'
import AppSpinner from '../common/AppSpinner.vue'

const open = defineModel<boolean>({ default: false })

const props = defineProps<{
  versions: DraftVersion[]
  currentVersionId?: number
  loading?: boolean
  restoring?: boolean
  restoreDisabled?: boolean
}>()

const emit = defineEmits<{
  restoreVersion: [versionId: number]
}>()

const hasVersions = computed(() => props.versions.length > 0)

/** Maps draft version source codes to labels shown in the history list. */
function sourceLabel(source: string): string {
  if (source === 'baseline') return 'Baseline'
  if (source === 'manual') return 'Manual save'
  if (source === 'proposal') return 'Applied proposal'
  if (source === 'restore') return 'Restore'
  return source
}

/** Formats a draft version timestamp while preserving invalid raw values. */
function formatDate(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

/** Builds a compact one-line excerpt for a stored Markdown draft. */
function excerpt(markdown: string): string {
  const condensed = markdown.replace(/\s+/g, ' ').trim()
  return condensed.length > 180 ? `${condensed.slice(0, 180)}...` : condensed
}
</script>

<template>
  <VDialog v-model="open" max-width="820">
    <VCard class="draft-history">
      <div class="draft-history__header">
        <div>
          <div class="text-caption muted-text">Draft history</div>
          <h2>Validated versions</h2>
        </div>
        <VBtn
          icon="mdi-close"
          variant="text"
          title="Close history"
          aria-label="Close history"
          @click="open = false"
        />
      </div>

      <AppSpinner v-if="props.loading" label="Loading draft history" />

      <div v-else-if="!hasVersions" class="draft-history__empty muted-text">
        No validated draft version is available yet.
      </div>

      <div v-else class="draft-history__list">
        <article
          v-for="version in props.versions"
          :key="version.id"
          class="draft-history__item surface-border"
          data-testid="draft-version-row"
        >
          <div class="draft-history__item-main">
            <div class="draft-history__meta">
              <strong>Version {{ version.version_number }}</strong>
              <span>{{ sourceLabel(version.change_source) }}</span>
              <span>{{ formatDate(version.created_at) }}</span>
              <span>{{ version.actor }}</span>
            </div>
            <p>{{ excerpt(version.markdown_draft) }}</p>
          </div>

          <VBtn
            variant="tonal"
            color="primary"
            prepend-icon="mdi-restore"
            :loading="props.restoring"
            :disabled="props.restoreDisabled || props.restoring || version.id === props.currentVersionId"
            data-testid="restore-draft-version-button"
            @click="emit('restoreVersion', version.id)"
          >
            Restore
          </VBtn>
        </article>
      </div>
    </VCard>
  </VDialog>
</template>

<style scoped>
.draft-history {
  padding: 14px;
}

.draft-history__header {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.draft-history__header h2 {
  margin: 0;
  font-size: 18px;
  line-height: 26px;
}

.draft-history__empty {
  display: grid;
  min-height: 180px;
  place-items: center;
  text-align: center;
}

.draft-history__list {
  display: grid;
  gap: 10px;
  max-height: 620px;
  overflow: auto;
}

.draft-history__item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  padding: 12px;
  border-radius: 8px;
  background: #ffffff;
}

.draft-history__item-main {
  min-width: 0;
}

.draft-history__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  color: #626f86;
  font-size: 12px;
  line-height: 16px;
}

.draft-history__meta strong {
  color: #172b4d;
}

.draft-history__item p {
  margin: 6px 0 0;
  overflow-wrap: anywhere;
}

@media (max-width: 640px) {
  .draft-history__item {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
