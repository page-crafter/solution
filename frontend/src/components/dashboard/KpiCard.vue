<script setup lang="ts">
import type { KpiCard } from '../../types/api'

defineProps<{
  card: KpiCard
}>()
</script>

<template>
  <VCard class="kpi-card surface-border" :class="`accent-${card.tone}`">
    <div class="kpi-top">
      <span class="kpi-label muted-text">{{ card.label }}</span>
      <div
        class="kpi-icon-wrap"
        :style="`background: rgba(var(--v-theme-${card.tone}), 0.12)`"
      >
        <VIcon icon="mdi-chart-box-outline" :color="card.tone" size="18" />
      </div>
    </div>
    <div class="text-h4 kpi-value mt-2">{{ card.value }}</div>
    <div class="text-caption muted-text mt-1">{{ card.trend }}</div>
  </VCard>
</template>

<style scoped>
.kpi-card {
  padding: 14px 20px 16px;
  border-left: 3px solid transparent;
  transition: box-shadow 0.15s ease, transform 0.15s ease;
}

.kpi-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  transform: translateY(-1px);
}

.accent-success { border-left-color: rgb(var(--v-theme-success)); }
.accent-warning { border-left-color: rgb(var(--v-theme-warning)); }
.accent-error   { border-left-color: rgb(var(--v-theme-error));   }
.accent-info    { border-left-color: rgb(var(--v-theme-info));    }
.accent-primary { border-left-color: rgb(var(--v-theme-primary)); }
.accent-grey    { border-left-color: rgba(var(--v-border-color), 0.4); }

.kpi-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.kpi-label {
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-weight: 600;
  line-height: 1.4;
}

.kpi-icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  flex-shrink: 0;
}

.kpi-value {
  font-weight: 700;
  line-height: 1.1;
}
</style>
