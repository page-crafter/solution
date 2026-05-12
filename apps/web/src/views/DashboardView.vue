<script setup lang="ts">
import { onMounted, shallowRef, computed } from 'vue'
import { fetchKpis } from '../api/kpis'
import { fetchSpaces } from '../api/spaces'
import { fetchLightRagStatus } from '../api/lightrag'
import { fetchTaskHistory } from '../api/jobs'
import AppSpinner from '../components/common/AppSpinner.vue'
import KpiCard from '../components/dashboard/KpiCard.vue'
import type { KpiCard as KpiCardType, SpaceStat, LightRagStatus, TaskExecution } from '../types/api'

const loading = shallowRef(true)
const cards = shallowRef<KpiCardType[]>([])
const spaces = shallowRef<SpaceStat[]>([])
const lightrag = shallowRef<LightRagStatus | null>(null)
const recentJobs = shallowRef<TaskExecution[]>([])

const activeSpace = computed<SpaceStat | null>(() => spaces.value[0] ?? null)

async function loadDashboard(): Promise<void> {
  loading.value = true
  const [kpis, spaceData, lrStatus, jobs] = await Promise.allSettled([
    fetchKpis(),
    fetchSpaces(),
    fetchLightRagStatus(),
    fetchTaskHistory(10),
  ])
  if (kpis.status === 'fulfilled') cards.value = kpis.value
  if (spaceData.status === 'fulfilled') spaces.value = spaceData.value
  if (lrStatus.status === 'fulfilled') lightrag.value = lrStatus.value
  if (jobs.status === 'fulfilled') recentJobs.value = jobs.value
  loading.value = false
}

function coverageColor(pct: number): string {
  if (pct >= 90) return 'success'
  if (pct >= 60) return 'warning'
  return 'error'
}

function jobStatusIcon(status: string): string {
  if (status === 'success' || status === 'finished') return 'mdi-check-circle'
  if (status === 'failed') return 'mdi-alert-circle'
  if (status === 'running') return 'mdi-progress-clock'
  return 'mdi-clock-outline'
}

function jobStatusColor(status: string): string {
  if (status === 'success' || status === 'finished') return 'success'
  if (status === 'failed') return 'error'
  if (status === 'running') return 'warning'
  return 'grey'
}

function timeAgo(iso: string | null | undefined): string {
  if (!iso) return '—'
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return `${Math.floor(diff / 86400)}d ago`
}

function friendlyTaskName(name: string): string {
  return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

onMounted(loadDashboard)
</script>

<template>
  <VContainer fluid class="pa-6">
    <div class="page-heading">
      <div>
        <h1>Documentation dashboard</h1>
        <p class="muted-text">Track sync, indexing, draft, and publishing readiness.</p>
      </div>
      <VBtn
        variant="tonal"
        prepend-icon="mdi-refresh"
        size="small"
        :loading="loading"
        @click="loadDashboard"
      >
        Refresh
      </VBtn>
    </div>

    <AppSpinner v-if="loading" label="Loading documentation metrics" />

    <template v-else>
      <!-- Status bar -->
      <VCard class="status-bar surface-border mb-6 pa-3" variant="flat">
        <div class="status-row">
          <template v-if="lightrag">
            <VIcon
              :icon="lightrag.healthy ? 'mdi-circle' : 'mdi-circle'"
              :color="lightrag.healthy ? 'success' : 'error'"
              size="12"
            />
            <span class="status-label">Knowledge engine</span>
            <VChip size="x-small" :color="lightrag.healthy ? 'success' : 'error'" variant="tonal">
              {{ lightrag.healthy ? 'healthy' : 'unreachable' }}
            </VChip>
            <span class="status-sep">·</span>
            <span class="muted-text text-caption">{{ lightrag.core_version }}</span>
            <span class="status-sep">·</span>
            <span class="muted-text text-caption">{{ lightrag.llm_model }}</span>
            <span class="status-sep">·</span>
            <span class="muted-text text-caption">{{ lightrag.embedding_model }}</span>
            <span class="status-sep">·</span>
            <VChip
              size="x-small"
              :color="lightrag.pipeline.busy ? 'warning' : 'default'"
              variant="tonal"
            >
              {{ lightrag.pipeline.busy ? `Indexing (${lightrag.pipeline.cur_batch}/${lightrag.pipeline.batchs})` : 'Pipeline idle' }}
            </VChip>
            <template v-if="lightrag.doc_counts.failed > 0">
              <span class="status-sep">·</span>
              <VChip size="x-small" color="error" variant="tonal">
                {{ lightrag.doc_counts.failed }} docs failed
              </VChip>
            </template>
          </template>
          <template v-else>
            <VIcon icon="mdi-circle" color="grey" size="12" />
            <span class="muted-text text-caption">Knowledge engine unavailable</span>
          </template>
        </div>
      </VCard>

      <!-- Active space header -->
      <VCard v-if="activeSpace" class="space-header surface-border mb-6" variant="flat">
        <div class="space-header-inner">
          <div class="space-identity">
            <VIcon icon="mdi-layers-outline" size="20" class="mr-2 muted-text" />
            <span class="space-name">{{ activeSpace.space_name }}</span>
            <VChip size="x-small" variant="tonal" class="ml-2">{{ activeSpace.space_key }}</VChip>
          </div>
          <div class="space-stats">
            <div class="space-stat">
              <span class="muted-text text-caption">Pages</span>
              <span class="stat-val">{{ activeSpace.page_count }}</span>
            </div>
            <div class="space-stat">
              <span class="muted-text text-caption">Indexed</span>
              <span class="stat-val">{{ activeSpace.indexed_count }}</span>
            </div>
            <div class="space-stat space-stat--coverage">
              <span class="muted-text text-caption">Coverage</span>
              <div class="coverage-row">
                <VProgressLinear
                  :model-value="activeSpace.coverage_pct"
                  :color="coverageColor(activeSpace.coverage_pct)"
                  height="6"
                  rounded
                  class="coverage-bar"
                />
                <span class="text-caption coverage-pct">{{ activeSpace.coverage_pct }}%</span>
              </div>
            </div>
            <div class="space-stat">
              <span class="muted-text text-caption">Open drafts</span>
              <VChip
                v-if="activeSpace.open_drafts > 0"
                size="x-small"
                color="orange"
                variant="tonal"
              >{{ activeSpace.open_drafts }}</VChip>
              <span v-else class="stat-val muted-text">—</span>
            </div>
            <div class="space-stat">
              <span class="muted-text text-caption">Last sync</span>
              <span class="stat-val">{{ timeAgo(activeSpace.last_synced_at) }}</span>
            </div>
          </div>
        </div>
      </VCard>

      <!-- KPI cards -->
      <VRow class="mb-6">
        <VCol v-for="card in cards" :key="card.label" cols="6" sm="4" lg="auto" class="flex-grow-1">
          <KpiCard :card="card" />
        </VCol>
      </VRow>

      <!-- Recent jobs -->
      <VRow>
        <VCol cols="12">
          <VCard class="surface-border" variant="flat">
            <VCardTitle class="section-title">
              <VIcon icon="mdi-history" size="18" class="mr-2" />
              Recent jobs
            </VCardTitle>
            <VDivider />
            <VList density="compact" class="py-0">
              <VListItem
                v-for="job in recentJobs"
                :key="job.id"
                class="job-item"
              >
                <template #prepend>
                  <VIcon
                    :icon="jobStatusIcon(job.status)"
                    :color="jobStatusColor(job.status)"
                    size="18"
                  />
                </template>
                <VListItemTitle class="text-body-2">
                  {{ friendlyTaskName(job.task_name) }}
                </VListItemTitle>
                <VListItemSubtitle class="text-caption">
                  {{ job.message || job.status }}
                </VListItemSubtitle>
                <template #append>
                  <span class="text-caption muted-text">{{ timeAgo(job.created_at) }}</span>
                </template>
              </VListItem>
              <VListItem v-if="recentJobs.length === 0">
                <VListItemTitle class="text-caption muted-text">No jobs yet</VListItemTitle>
              </VListItem>
            </VList>
          </VCard>
        </VCol>
      </VRow>
    </template>
  </VContainer>
</template>

<style scoped>
.page-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}

h1 {
  margin: 0;
  font-size: 24px;
  line-height: 32px;
}

.status-bar {
  border-radius: 8px;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.status-label {
  font-size: 13px;
  font-weight: 500;
}

.status-sep {
  color: var(--v-theme-on-surface);
  opacity: 0.3;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  padding: 12px 16px;
  display: flex;
  align-items: center;
}

/* Space header */
.space-header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  gap: 24px;
  flex-wrap: wrap;
}

.space-identity {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.space-name {
  font-size: 15px;
  font-weight: 600;
  text-transform: capitalize;
}

.space-stats {
  display: flex;
  align-items: center;
  gap: 28px;
  flex-wrap: wrap;
}

.space-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.space-stat--coverage {
  min-width: 160px;
}

.stat-val {
  font-size: 14px;
  font-weight: 600;
}

.coverage-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 2px;
}

.coverage-bar {
  flex: 1;
  min-width: 80px;
}

.coverage-pct {
  width: 38px;
  text-align: right;
  flex-shrink: 0;
  font-weight: 500;
}

/* Jobs list */
.job-item {
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.job-item:last-child {
  border-bottom: none;
}
</style>
