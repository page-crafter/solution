<script setup lang="ts">
withDefaults(defineProps<{
  title: string
  description?: string
}>(), {
  description: undefined,
})
</script>

<template>
  <header class="page-header">
    <div class="page-header__copy">
      <h1 class="page-header__title">{{ title }}</h1>
      <p v-if="description" class="page-header__description muted-text">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="page-header__actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.page-header__copy {
  min-width: 0;
}

.page-header__title {
  margin: 0;
  font-size: 24px;
  line-height: 32px;
}

.page-header__description {
  margin: 0;
}

.page-header__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  justify-content: flex-end;
}

@media (max-width: 760px) {
  .page-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .page-header__actions {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
