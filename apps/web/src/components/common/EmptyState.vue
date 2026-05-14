<script setup lang="ts">
withDefaults(defineProps<{
  icon?: string
  title: string
  message?: string
  minHeight?: string
}>(), {
  icon: 'mdi-information-outline',
  message: undefined,
  minHeight: '320px',
})
</script>

<template>
  <div class="empty-state" :style="{ minHeight }">
    <div class="empty-state__content">
      <div class="empty-state__icon" aria-hidden="true">
        <VIcon :icon="icon" size="34" color="primary" />
      </div>
      <div class="empty-state__title">{{ title }}</div>
      <div v-if="message" class="empty-state__message">{{ message }}</div>
      <div v-if="$slots.actions" class="empty-state__actions">
        <slot name="actions" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.empty-state {
  display: grid;
  flex: 1;
  place-items: center;
  text-align: center;
}

.empty-state__content {
  display: grid;
  justify-items: center;
  gap: 12px;
  max-width: 320px;
}

.empty-state__icon {
  display: grid;
  width: 72px;
  height: 72px;
  place-items: center;
  border: 1px solid #cce0ff;
  border-radius: 50%;
  background: #e9f2ff;
}

.empty-state__title {
  color: #172b4d;
  font-size: 17px;
  font-weight: 600;
  line-height: 24px;
}

.empty-state__message {
  color: #626f86;
  font-size: 14px;
  line-height: 20px;
}

.empty-state__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}
</style>
