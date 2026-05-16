<script setup lang="ts">
import PageHeader from './PageHeader.vue'

withDefaults(defineProps<{
  title: string
  description?: string
  fill?: boolean
}>(), {
  description: undefined,
  fill: false,
})
</script>

<template>
  <VContainer
    fluid
    :class="['admin-page-shell', { 'admin-page-shell--fill': fill }]"
  >
    <PageHeader :title="title" :description="description">
      <template v-if="$slots.actions" #actions>
        <slot name="actions" />
      </template>
    </PageHeader>

    <div :class="['admin-page-shell__content', { 'admin-page-shell__content--fill': fill }]">
      <slot />
    </div>
  </VContainer>
</template>

<style scoped>
.admin-page-shell {
  display: flex;
  width: 100%;
  max-width: none;
  flex-direction: column;
  padding: 16px !important;
}

.admin-page-shell--fill {
  height: calc(100vh - 48px);
  height: calc(100dvh - 48px);
  min-height: calc(100vh - 48px);
  min-height: calc(100dvh - 48px);
  overflow: hidden;
}

.admin-page-shell__content {
  min-width: 0;
}

.admin-page-shell__content--fill {
  display: flex;
  flex: 1 1 auto;
  min-height: 0;
  flex-direction: column;
}
</style>
