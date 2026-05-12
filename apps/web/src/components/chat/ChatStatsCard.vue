<script setup lang="ts">
import { computed, shallowRef } from 'vue'
import type { ChatConversationStats, ChatStatsStatus } from '../../composables/useChatConversationStats'

type StatsDisplayMode = 'cumulative' | 'lastPrompt'

const props = defineProps<{
  collapsed: boolean
  compact?: boolean
  stats: ChatConversationStats
}>()

const emit = defineEmits<{
  toggle: []
}>()

const displayMode = shallowRef<StatsDisplayMode>('lastPrompt')

const statusMeta = computed(() => {
  const values: Record<ChatStatsStatus, { color: string, icon: string, label: string }> = {
    idle: { color: 'default', icon: 'mdi-clock-outline', label: 'Idle' },
    streaming: { color: 'primary', icon: 'mdi-progress-clock', label: 'Streaming' },
    completed: { color: 'success', icon: 'mdi-check-circle-outline', label: 'Completed' },
    failed: { color: 'error', icon: 'mdi-alert-circle-outline', label: 'Failed' },
  }
  return values[props.stats.status]
})

const summaryItems = computed(() => [
  ...(displayMode.value === 'cumulative'
    ? [
        {
          icon: 'mdi-message-question-outline',
          label: 'Questions',
          value: formatNumber(props.stats.questionCount),
        },
        {
          icon: 'mdi-message-reply-text-outline',
          label: 'Answers',
          value: formatNumber(props.stats.answerCount),
        },
        {
          icon: 'mdi-link-variant',
          label: 'References',
          value: formatNumber(props.stats.referenceCount),
        },
        {
          icon: 'mdi-alert-outline',
          label: 'Errors',
          value: formatNumber(props.stats.errorCount),
        },
      ]
    : [
        {
          icon: 'mdi-timeline-clock-outline',
          label: 'Elapsed',
          value: formatDuration(props.stats.current.elapsedMs),
        },
        {
          icon: 'mdi-file-document-outline',
          label: 'Response',
          value: `${formatCompactNumber(props.stats.current.responseChars)} chars`,
        },
        {
          icon: 'mdi-source-branch',
          label: 'Chunks',
          value: formatNumber(props.stats.current.chunkCount),
        },
        {
          icon: 'mdi-link-variant',
          label: 'References',
          value: formatNumber(props.stats.current.referenceCount),
        },
      ]),
])

const cumulativeRows = computed(() => [
  { label: 'Measured time', value: formatDuration(props.stats.totals.clientElapsedMs) },
  { label: 'Server time', value: formatDuration(props.stats.totals.serverElapsedMs) },
  { label: 'Assistant text', value: `${formatNumber(props.stats.totals.assistantChars)} chars` },
  { label: 'Streamed text', value: `${formatNumber(props.stats.totals.responseChars)} chars` },
  { label: 'History sent', value: `${formatNumber(props.stats.totals.historyMessageCount)} msg` },
  { label: 'History size', value: `${formatNumber(props.stats.totals.historyChars)} chars` },
  { label: 'Stream chunks', value: formatNumber(props.stats.totals.chunkCount) },
  { label: 'Stream events', value: formatNumber(props.stats.totals.streamEventCount) },
])

const liveRows = computed(() => [
  { label: 'Live elapsed', value: formatDuration(props.stats.current.elapsedMs) },
  { label: 'Server elapsed', value: formatOptionalDuration(props.stats.current.serverElapsedMs) },
  { label: 'History sent', value: `${formatNumber(props.stats.current.historyMessageCount)} msg` },
  { label: 'History size', value: `${formatNumber(props.stats.current.historyChars)} chars` },
  { label: 'Response size', value: `${formatNumber(props.stats.current.responseChars)} chars` },
  { label: 'Stream chunks', value: formatNumber(props.stats.current.chunkCount) },
  { label: 'Stream events', value: formatNumber(props.stats.current.streamEventCount) },
])

const activeRows = computed(() =>
  displayMode.value === 'cumulative' ? cumulativeRows.value : liveRows.value,
)

const activeSectionMeta = computed(() =>
  displayMode.value === 'cumulative'
    ? { icon: 'mdi-sigma', label: 'Cumulative stats' }
    : { icon: 'mdi-chart-timeline-variant', label: 'Last prompt' },
)

function formatNumber(value: number): string {
  return value.toLocaleString()
}

function formatCompactNumber(value: number): string {
  const units = [
    { threshold: 1_000_000_000_000, suffix: 'T' },
    { threshold: 1_000_000_000, suffix: 'B' },
    { threshold: 1_000_000, suffix: 'M' },
    { threshold: 1_000, suffix: 'K' },
  ]
  const unit = units.find((candidate) => Math.abs(value) >= candidate.threshold)
  if (!unit) return formatNumber(value)

  const scaledValue = value / unit.threshold
  const maximumFractionDigits = Math.abs(scaledValue) >= 10 ? 0 : 1
  return `${scaledValue.toLocaleString(undefined, { maximumFractionDigits })}${unit.suffix}`
}

function formatDuration(value: number): string {
  if (value <= 0) return '0 ms'
  if (value < 1000) return `${Math.round(value)} ms`
  const seconds = value / 1000
  if (seconds < 60) return `${seconds.toFixed(1)} s`
  const minutes = Math.floor(seconds / 60)
  const remainder = Math.round(seconds % 60)
  return `${minutes}m ${remainder}s`
}

function formatOptionalDuration(value?: number): string {
  return value === undefined ? 'Pending' : formatDuration(value)
}

</script>

<template>
  <section class="stats-panel" data-testid="chat-stats-card">
    <VCard
      :class="['stats-card surface-border', { 'stats-card--collapsed': collapsed }]"
    >
      <div
        v-if="collapsed"
        :class="['stats-rail', { 'stats-rail--compact': compact }]"
      >
        <VBtn
          icon="mdi-chart-box-outline"
          size="small"
          variant="text"
          title="Open conversation stats"
          @click="emit('toggle')"
        />
        <div v-if="!compact" class="stats-rail__text">
          <div class="text-subtitle-2">Conversation</div>
          <div class="text-caption muted-text">{{ activeSectionMeta.label }}</div>
        </div>
        <VBtn
          v-if="!compact"
          icon="mdi-chevron-down"
          size="small"
          variant="text"
          title="Open conversation stats"
          @click="emit('toggle')"
        />
      </div>

      <template v-else>
      <div class="stats-header">
        <div class="stats-header__title">
          <VIcon icon="mdi-chart-box-outline" size="18" />
          <div class="stats-header__text">
            <div class="text-subtitle-2">Conversation</div>
            <div class="text-caption muted-text">{{ activeSectionMeta.label }}</div>
          </div>
        </div>
        <div class="stats-header__actions">
          <VChip
            :color="statusMeta.color"
            :prepend-icon="statusMeta.icon"
            size="x-small"
            variant="tonal"
          >
            {{ statusMeta.label }}
          </VChip>
          <VBtn
            icon="mdi-chevron-up"
            size="small"
            variant="text"
            title="Collapse"
            @click="emit('toggle')"
          />
        </div>
      </div>

      <div class="stats-mode">
        <VBtnToggle
          v-model="displayMode"
          class="stats-mode__toggle"
          density="compact"
          mandatory
          rounded="sm"
          variant="outlined"
        >
          <VBtn
            class="stats-mode__button"
            size="small"
            value="lastPrompt"
          >
            Last prompt
          </VBtn>
          <VBtn
            class="stats-mode__button"
            size="small"
            value="cumulative"
          >
            Cumul
          </VBtn>
        </VBtnToggle>
      </div>

      <div class="stats-summary">
        <div v-for="item in summaryItems" :key="item.label" class="stats-summary__item">
          <VIcon :icon="item.icon" size="16" />
          <div>
            <div class="stats-summary__value">{{ item.value }}</div>
            <div class="stats-summary__label">{{ item.label }}</div>
          </div>
        </div>
      </div>

      <div class="stats-live">
        <div class="stats-live__header">
          <VIcon :icon="activeSectionMeta.icon" size="16" />
          <span>{{ activeSectionMeta.label }}</span>
        </div>
        <dl class="stats-live__rows">
          <div v-for="row in activeRows" :key="row.label" class="stats-live__row">
            <dt>{{ row.label }}</dt>
            <dd>{{ row.value }}</dd>
          </div>
        </dl>
        <div
          v-if="displayMode === 'lastPrompt' && props.stats.current.error"
          class="stats-error"
        >
          <VIcon icon="mdi-alert-circle-outline" size="16" />
          <span>{{ props.stats.current.error }}</span>
        </div>
      </div>
      </template>
    </VCard>
  </section>
</template>

<style scoped>
.stats-panel {
  min-width: 0;
}

.stats-card {
  overflow: hidden;
}

.stats-card--collapsed {
  height: 52px;
}

.stats-rail {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  height: 100%;
  padding: 4px 8px;
}

.stats-rail--compact {
  grid-template-columns: 1fr;
  place-items: center;
}

.stats-rail__text {
  min-width: 0;
}

.stats-rail__text .text-subtitle-2,
.stats-rail__text .text-caption {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stats-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 10px 8px;
  border-bottom: 1px solid #dfe1e6;
}

.stats-header__title {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  min-width: 0;
}

.stats-header__text {
  min-width: 0;
}

.stats-header__text .text-subtitle-2,
.stats-header__text .text-caption {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stats-header__actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

.stats-mode {
  padding: 10px 10px 0;
}

.stats-mode__toggle {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  width: 100%;
}

.stats-mode__button {
  min-width: 0;
}

.stats-mode__button :deep(.v-btn__content) {
  min-width: 0;
  overflow-wrap: anywhere;
  text-transform: none;
  white-space: normal;
}

.stats-summary {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  padding: 10px;
}

.stats-summary__item {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr);
  gap: 6px;
  align-items: center;
  min-width: 0;
  padding: 8px;
  border: 1px solid #dfe1e6;
  border-radius: 6px;
  background: #f8fafc;
  color: #172b4d;
}

.stats-summary__value {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 16px;
  font-weight: 700;
  line-height: 20px;
}

.stats-summary__label {
  color: #626f86;
  font-size: 11px;
  font-weight: 600;
  line-height: 14px;
}

.stats-live {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 10px 10px;
}

.stats-live__header {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #44546f;
  font-size: 12px;
  font-weight: 700;
  line-height: 16px;
}

.stats-live__rows {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin: 0;
}

.stats-live__row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  color: #44546f;
  font-size: 12px;
  line-height: 16px;
}

.stats-live__row dt {
  min-width: 0;
  overflow-wrap: anywhere;
}

.stats-live__row dd {
  flex: 0 0 auto;
  max-width: 52%;
  margin: 0;
  overflow-wrap: anywhere;
  color: #172b4d;
  font-weight: 700;
  text-align: right;
}

.stats-error {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr);
  gap: 6px;
  align-items: start;
  padding: 8px;
  border: 1px solid #ffb8b8;
  border-radius: 6px;
  background: #fff1f0;
  color: #ae2a19;
  font-size: 12px;
  line-height: 16px;
  overflow-wrap: anywhere;
}
</style>
