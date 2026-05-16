<script setup lang="ts">
const collapsed = defineModel<boolean>('collapsed', { default: false })

withDefaults(defineProps<{
  icon: string
  title: string
  subtitle?: string
  compact?: boolean
  resetTitle?: string
  collapseTitle?: string
  expandTitle?: string
  showReset?: boolean
}>(), {
  subtitle: undefined,
  compact: false,
  resetTitle: 'Reset',
  collapseTitle: 'Collapse',
  expandTitle: 'Open',
  showReset: true,
})

const emit = defineEmits<{
  reset: []
}>()
</script>

<template>
  <VCard class="collapsible-panel surface-border" variant="flat">
    <div v-if="collapsed" :class="['collapsible-panel__rail', { 'collapsible-panel__rail--compact': compact }]">
      <VBtn :icon="icon" size="small" variant="text" :title="expandTitle" @click="collapsed = false" />
      <div v-if="!compact" class="collapsible-panel__rail-text">
        <div class="text-subtitle-2">{{ title }}</div>
        <div v-if="subtitle" class="text-caption muted-text">{{ subtitle }}</div>
      </div>
      <VBtn
        v-if="!compact"
        icon="mdi-chevron-right"
        size="small"
        variant="text"
        :title="expandTitle"
        @click="collapsed = false"
      />
    </div>

    <template v-else>
      <div class="collapsible-panel__header">
        <div class="collapsible-panel__title">
          <VIcon :icon="icon" size="18" />
          <div class="collapsible-panel__copy">
            <div class="text-subtitle-2">{{ title }}</div>
            <div v-if="subtitle" class="text-caption muted-text">{{ subtitle }}</div>
          </div>
        </div>
        <div class="collapsible-panel__actions">
          <slot name="actions" />
          <VBtn
            v-if="showReset"
            icon="mdi-restore"
            size="small"
            variant="text"
            :title="resetTitle"
            @click="emit('reset')"
          />
          <VBtn
            icon="mdi-chevron-left"
            size="small"
            variant="text"
            :title="collapseTitle"
            @click="collapsed = true"
          />
        </div>
      </div>
      <div class="collapsible-panel__content">
        <slot />
      </div>
    </template>
  </VCard>
</template>

<style scoped>
.collapsible-panel {
  overflow: hidden;
}

.collapsible-panel__rail {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  height: 52px;
  padding: 4px 8px;
}

.collapsible-panel__rail--compact {
  grid-template-columns: 1fr;
  place-items: center;
}

.collapsible-panel__rail-text,
.collapsible-panel__copy {
  min-width: 0;
}

.collapsible-panel__rail-text .text-subtitle-2,
.collapsible-panel__rail-text .text-caption,
.collapsible-panel__copy .text-subtitle-2,
.collapsible-panel__copy .text-caption {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.collapsible-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 10px 8px;
  border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.collapsible-panel__title {
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  min-width: 0;
}

.collapsible-panel__actions {
  display: flex;
  gap: 2px;
}

.collapsible-panel__content {
  display: flex;
  flex-direction: column;
  gap: 9px;
  padding: 10px;
  overflow-y: auto;
  max-height: calc(100vh - 260px);
  max-height: calc(100dvh - 260px);
}
</style>
