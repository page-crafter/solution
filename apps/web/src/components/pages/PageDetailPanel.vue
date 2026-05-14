<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { ConfluencePage, PageDetail, PageEditRun } from '../../types/api'
import EmptyState from '../common/EmptyState.vue'
import StatusChip from '../common/StatusChip.vue'

const props = defineProps<{
  page?: PageDetail
  activeRun?: PageEditRun | null
  pages?: ConfluencePage[]
}>()

const emit = defineEmits<{
  cancelDraft: []
}>()

const router = useRouter()

const parentTitle = computed(() => {
  if (!props.page?.parent_confluence_id || !props.pages) return null
  const parent = props.pages.find((p) => p.confluence_id === props.page!.parent_confluence_id)
  return parent?.title ?? props.page.parent_confluence_id
})

/** Navigates the selected page into the full editor route. */
function openInEditor(): void {
  void router.push({ path: '/editor', query: { pageId: String(props.page!.id) } })
}
</script>

<template>
  <VCard class="detail-panel surface-border">
    <template v-if="page">
      <div class="detail-header">
        <div>
          <div class="text-caption muted-text">Selected page</div>
          <h2>{{ page.title }}</h2>
        </div>
        <StatusChip :state="page.draft_state" />
      </div>

      <div class="detail-actions">
        <VBtn
          size="small"
          variant="tonal"
          color="primary"
          prepend-icon="mdi-pencil-outline"
          @click="openInEditor"
        >
          Edit
        </VBtn>
        <VBtn
          v-if="page.web_url"
          size="small"
          variant="tonal"
          prepend-icon="mdi-open-in-new"
          :href="page.web_url"
          target="_blank"
          rel="noopener noreferrer"
        >
          Confluence
        </VBtn>
      </div>

      <VDivider class="my-4" />

      <div class="meta-grid">
        <div>
          <div class="text-caption muted-text">Confluence id</div>
          <div class="text-body-2">{{ page.confluence_id }}</div>
        </div>
        <div>
          <div class="text-caption muted-text">Source version</div>
          <div class="text-body-2">{{ page.version_number }}</div>
        </div>
        <div>
          <div class="text-caption muted-text">Space</div>
          <div class="text-body-2">{{ page.space_name || page.space_key }}</div>
        </div>
        <div>
          <div class="text-caption muted-text">Parent</div>
          <div class="text-body-2">{{ parentTitle ?? 'Root' }}</div>
        </div>
        <div>
          <div class="text-caption muted-text">Empty page</div>
          <div class="text-body-2">{{ page.is_placeholder ? 'Yes' : 'No' }}</div>
        </div>
      </div>

      <div v-if="activeRun" class="draft-box">
        <div>
          <div class="text-caption muted-text">Active app draft</div>
          <div class="text-body-2">{{ activeRun.draft_status }} · {{ activeRun.preview_status }}</div>
        </div>
        <VBtn color="error" variant="tonal" size="small" prepend-icon="mdi-close-circle-outline" @click="emit('cancelDraft')">
          Cancel Draft
        </VBtn>
      </div>

      <div class="text-caption muted-text mt-5 mb-2">Extracted text used for search</div>
      <pre class="source-preview">{{ page.extracted_text || 'No indexed text yet.' }}</pre>
    </template>

    <EmptyState
      v-else
      icon="mdi-file-tree-outline"
      title="Pick a page to begin"
      message="Select one from the tree to review its source, drafts, and update status."
      min-height="360px"
    />
  </VCard>
</template>

<style scoped>
.detail-panel {
  height: 100%;
  overflow: auto;
  padding: 16px;
}

.detail-header {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
}

.detail-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

h2 {
  margin: 4px 0 0;
  font-size: 18px;
  line-height: 24px;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.draft-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 16px;
  padding: 12px;
  border-radius: 8px;
  background: #fff7e6;
}

.draft-box--remote {
  background: #ffebe6;
}

.source-preview {
  max-height: 280px;
  overflow: auto;
  padding: 12px;
  border-radius: 8px;
  background: #f4f5f7;
  white-space: pre-wrap;
}

</style>
