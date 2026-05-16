<script setup lang="ts">
defineProps<{
  label?: string
  compact?: boolean
}>()
</script>

<template>
  <div :class="['app-spinner', { 'app-spinner--compact': compact }]">
    <VProgressCircular indeterminate color="primary" :size="compact ? 22 : 36" />
    <span v-if="label" class="text-body-2 muted-text">{{ label }}</span>
  </div>
</template>

<style scoped>
.app-spinner {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: center;
  min-height: 180px;
}

.app-spinner--compact {
  min-height: 0;
  justify-content: flex-start;
}
</style>

