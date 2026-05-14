<script setup lang="ts">
import { computed } from 'vue'
import type { ConfluencePage } from '../../types/api'
import { buildPagePath } from '../../composables/pagePath'

const selectedPageId = defineModel<number | undefined>({ default: undefined })

const props = defineProps<{
  pages: ConfluencePage[]
  loading?: boolean
}>()

const emit = defineEmits<{
  select: [pageId: number]
}>()

const pageOptions = computed(() =>
  props.pages.map((page) => ({
    title: buildPagePath(page, props.pages),
    value: page.id,
  })),
)
const canSelect = computed(() => Boolean(selectedPageId.value && !props.loading))

/** Emits the selected page id when the picker has a valid selection. */
function submitSelection(): void {
  if (!selectedPageId.value || props.loading) return
  emit('select', selectedPageId.value)
}
</script>

<template>
  <section class="page-picker-shell">
    <div class="page-picker-brand">
      <h2 class="page-picker-brand__title">Documentation Hub</h2>
      <p class="page-picker-brand__sub muted-text">Confluence updater</p>
    </div>
    <VHover v-slot="{ isHovering, props: hoverProps }">
    <form
      v-bind="hoverProps"
      class="page-picker"
      :style="{ boxShadow: isHovering ? '0 8px 28px rgba(9,30,66,0.14), 0 2px 8px rgba(9,30,66,0.08)' : undefined }"
      data-testid="page-editor-picker"
      @submit.prevent="submitSelection"
    >
      <div class="page-picker__header">
        <div class="page-picker__icon" aria-hidden="true">
          <VIcon icon="mdi-file-edit-outline" size="26" color="primary" />
        </div>
        <div class="page-picker__copy">
          <h1>Select a page</h1>
          <p class="muted-text">Choose the Confluence page you want to edit with the AI assistant.</p>
        </div>
      </div>

      <div class="page-picker__field">
        <VAutocomplete
          v-model="selectedPageId"
          :items="pageOptions"
          :loading="props.loading"
          :disabled="props.loading || pageOptions.length === 0"
          item-title="title"
          item-value="value"
          label="Page"
          auto-select-first
          clearable
          hide-details
          data-testid="page-editor-picker-input"
        />
        <div class="page-picker__hint muted-text">
          <VIcon icon="mdi-magnify" size="12" class="mr-1" />
          {{ pageOptions.length }} page{{ pageOptions.length !== 1 ? 's' : '' }} available — type to filter by title or path
        </div>
      </div>

      <VAlert
        v-if="pageOptions.length === 0 && !props.loading"
        type="warning"
        variant="tonal"
        density="compact"
        icon="mdi-alert-outline"
        text="No pages found. Make sure the Confluence sync has completed."
      />

      <VBtn
        type="submit"
        color="primary"
        prepend-icon="mdi-pencil-outline"
        :disabled="!canSelect"
        block
        data-testid="page-editor-picker-submit"
      >
        Start editing
      </VBtn>
    </form>
    </VHover>
  </section>
</template>

<style scoped>
.page-picker-shell {
  display: grid;
  min-height: calc(100vh - 48px);
  min-height: calc(100dvh - 48px);
  place-items: center;
  padding: 24px;
  align-content: center;
  gap: 24px;
}

.page-picker-brand {
  text-align: center;
}

.page-picker-brand__title {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
  color: #172b4d;
}

.page-picker-brand__sub {
  margin: 4px 0 0;
  font-size: 14px;
}

.page-picker {
  display: grid;
  gap: 20px;
  width: min(100%, 520px);
  padding: 24px;
  border-top: 3px solid #0c66e4;
  border-right: 1px solid #dfe1e6;
  border-bottom: 1px solid #dfe1e6;
  border-left: 1px solid #dfe1e6;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 4px 16px rgba(9, 30, 66, 0.08), 0 1px 4px rgba(9, 30, 66, 0.06);
}

.page-picker__header {
  display: flex;
  gap: 14px;
  align-items: center;
}

.page-picker__icon {
  display: grid;
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  place-items: center;
  border: 1px solid #cce0ff;
  border-radius: 8px;
  background: #e9f2ff;
}

.page-picker__copy {
  min-width: 0;
}

.page-picker__copy h1 {
  margin: 0;
  font-size: 20px;
  line-height: 28px;
}

.page-picker__copy p {
  margin: 2px 0 0;
  font-size: 13px;
}

.page-picker__field {
  display: grid;
  gap: 6px;
}

.page-picker__hint {
  font-size: 12px;
}
</style>
