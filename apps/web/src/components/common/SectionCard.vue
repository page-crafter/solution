<script setup lang="ts">
withDefaults(defineProps<{
  title?: string
  icon?: string
  iconColor?: string
  padded?: boolean
}>(), {
  title: undefined,
  icon: undefined,
  iconColor: undefined,
  padded: true,
})
</script>

<template>
  <VCard class="section-card surface-border" variant="flat">
    <div v-if="title || $slots.title || $slots.actions" class="section-card__header">
      <div class="section-card__title">
        <VIcon v-if="icon" :icon="icon" :color="iconColor" size="18" />
        <slot name="title">
          <span>{{ title }}</span>
        </slot>
      </div>
      <div v-if="$slots.actions" class="section-card__actions">
        <slot name="actions" />
      </div>
    </div>
    <VDivider v-if="title || $slots.title || $slots.actions" />
    <div :class="['section-card__body', { 'section-card__body--padded': padded }]">
      <slot />
    </div>
  </VCard>
</template>

<style scoped>
.section-card {
  overflow: hidden;
}

.section-card__header {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  min-height: 46px;
  padding: 12px 16px;
}

.section-card__title {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
}

.section-card__actions {
  display: flex;
  gap: 6px;
  align-items: center;
}

.section-card__body--padded {
  padding: 16px;
}
</style>
