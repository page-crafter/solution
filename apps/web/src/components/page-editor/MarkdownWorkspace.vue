<script setup lang="ts">
import { DiffModeEnum, DiffView } from '@git-diff-view/vue'
import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'
import { computed, shallowRef, watch } from 'vue'
import type { DraftVersion, PageDetail, PageProposal, PageEditRun } from '../../types/api'
import { normalizeConfluenceStorageHtml } from '../../utils/confluencePreview'
import ActionValidationDialog from '../common/ActionValidationDialog.vue'
import EmptyState from '../common/EmptyState.vue'
import DraftHistoryDialog from './DraftHistoryDialog.vue'
import MarkdownEditor from './MarkdownEditor.vue'
import XhtmlCodeBlock from './XhtmlCodeBlock.vue'

type WorkspaceMode = 'source' | 'preview' | 'xhtml' | 'changes'

const draft = defineModel<string>({ default: '' })

const props = defineProps<{
  page?: PageDetail
  run?: PageEditRun
  proposal?: PageProposal
  draftVersions?: DraftVersion[]
  loading?: boolean
  saving?: boolean
  applying?: boolean
  loadingDraftVersions?: boolean
  restoringDraftVersion?: boolean
  resettingDraft?: boolean
  disabled?: boolean
}>()

const emit = defineEmits<{
  saveDraft: []
  restoreDraftVersion: [versionId: number]
  resetDraft: []
}>()

const markdownRenderer = new MarkdownIt({
  breaks: true,
  html: false,
  linkify: true,
})

const activeMode = shallowRef<WorkspaceMode>('source')
const historyDialogOpen = shallowRef(false)
const resetDialogOpen = shallowRef(false)
const hasDraft = computed(() => Boolean(props.run?.markdown_draft || draft.value.trim()))
const baseMarkdown = computed(() => props.page?.extracted_text ?? '')
const currentStorageXhtml = computed(() => props.page?.source_storage_xhtml?.trim() ?? '')
const generatedStorageXhtml = computed(() => props.run?.generated_storage_xhtml?.trim() ?? '')
const visibleStorageXhtml = computed(() => generatedStorageXhtml.value || currentStorageXhtml.value)
const hasStorageXhtml = computed(() => visibleStorageXhtml.value.length > 0)
const xhtmlLabel = computed(() => (generatedStorageXhtml.value ? 'Generated XHTML' : 'Current XHTML'))
const renderedCurrentPageHtml = computed(() => {
  const storageHtml = currentStorageXhtml.value
  if (storageHtml) {
    return DOMPurify.sanitize(normalizeConfluenceStorageHtml(storageHtml))
  }
  return DOMPurify.sanitize(markdownRenderer.render(baseMarkdown.value))
})
const visibleMarkdown = computed(() => (hasDraft.value ? draft.value : baseMarkdown.value))
const renderedMarkdown = computed(() => DOMPurify.sanitize(markdownRenderer.render(visibleMarkdown.value)))
const isDraftDirty = computed(() => hasDraft.value && draft.value !== (props.run?.markdown_draft ?? ''))
const shouldUseConfluencePreview = computed(() =>
  Boolean(props.run?.preview_html && hasDraft.value && !isDraftDirty.value),
)
const renderedPreviewHtml = computed(() =>
  hasDraft.value ? renderedMarkdown.value : renderedCurrentPageHtml.value,
)
const sourceLabel = computed(() => (hasDraft.value ? 'Markdown' : 'Current page'))
const canSaveDraft = computed(() =>
  Boolean(hasDraft.value && draft.value.trim() && !props.saving && !props.disabled),
)
const currentDraftVersionId = computed(() => {
  const currentMarkdown = props.run?.markdown_draft
  if (!currentMarkdown) return undefined
  return props.draftVersions?.find((version) => version.markdown_draft === currentMarkdown)?.id
})
const canRestoreDraftVersion = computed(() =>
  Boolean(!props.disabled && !props.saving && !props.applying && !isDraftDirty.value),
)
const proposalReady = computed(() => props.proposal?.status === 'ready')
const proposalTerminal = computed(() =>
  props.proposal?.status === 'applied' || props.proposal?.status === 'rejected',
)
const readyProposal = computed(() => (proposalReady.value ? props.proposal : undefined))
const showingProposalDiff = computed(() =>
  Boolean(readyProposal.value?.diff_text),
)
const diffText = computed(() =>
  readyProposal.value ? (readyProposal.value.diff_text ?? '') : (props.run?.diff_text ?? ''),
)
const hasChanges = computed(() => diffText.value.length > 0)
const diffData = computed(() => ({
  oldFile: showingProposalDiff.value
    ? { fileName: readyProposal.value?.base_source === 'draft' ? 'current-draft.md' : 'current-page.txt', fileLang: 'markdown', content: '' }
    : { fileName: 'current-storage.xhtml', fileLang: 'xml', content: '' },
  newFile: showingProposalDiff.value
    ? { fileName: 'proposed-draft.md', fileLang: 'markdown', content: '' }
    : { fileName: 'generated-storage.xhtml', fileLang: 'xml', content: '' },
  hunks: hasChanges.value ? [diffText.value] : [],
}))

watch(proposalReady, (isReady) => {
  if (isReady) activeMode.value = 'changes'
})
</script>

<template>
  <section class="markdown-workspace surface-border">
    <Transition name="workspace-overlay">
      <div v-if="props.loading" class="workspace-loading-overlay">
        <VProgressLinear indeterminate color="primary" height="2" absolute location="top" />
        <VChip color="primary" variant="tonal" size="small" prepend-icon="mdi-creation">Processing</VChip>
        <span class="text-caption muted-text">Editor locked during AI processing</span>
      </div>
    </Transition>

    <div class="markdown-workspace__header">
      <div class="text-caption muted-text">{{ sourceLabel }}</div>

      <div class="markdown-workspace__controls">
        <VBtnToggle
          v-model="activeMode"
          color="primary"
          density="compact"
          divided
          mandatory
          variant="outlined"
        >
          <VBtn value="source" v-tooltip="'Markdown source'" prepend-icon="mdi-pencil-outline">Edit</VBtn>
          <VBtn value="preview" v-tooltip="'Confluence preview'" prepend-icon="mdi-eye-outline">Preview</VBtn>
          <VBtn value="xhtml" v-tooltip="'Storage XHTML'" prepend-icon="mdi-code-tags" :disabled="!hasStorageXhtml">XHTML</VBtn>
          <VBtn value="changes" v-tooltip="'Diff / changes'" :disabled="!hasChanges">
            <VBadge :model-value="proposalReady && activeMode !== 'changes'" color="error" dot floating>
              <VIcon icon="mdi-swap-horizontal" size="18" />
            </VBadge>
            <span class="ml-1">Changes</span>
          </VBtn>
        </VBtnToggle>
        <div v-if="props.run?.markdown_draft" class="markdown-workspace__draft-actions">
          <VTooltip location="bottom" text="Draft history">
            <template #activator="{ props: tp }">
              <VBtn
                v-bind="tp"
                icon="mdi-history"
                variant="tonal"
                size="small"
                aria-label="Open draft history"
                :disabled="props.loadingDraftVersions"
                data-testid="open-draft-history-button"
                @click="historyDialogOpen = true"
              />
            </template>
          </VTooltip>
          <VTooltip location="bottom" text="Reset draft">
            <template #activator="{ props: tp }">
              <VBtn
                v-bind="tp"
                icon="mdi-restore"
                variant="tonal"
                size="small"
                color="error"
                aria-label="Reset draft"
                :disabled="props.disabled || props.saving || props.resettingDraft"
                data-testid="reset-draft-button"
                @click="resetDialogOpen = true"
              />
            </template>
          </VTooltip>
        </div>
        <div v-if="hasDraft" class="markdown-workspace__draft-actions">
          <VBtn
            color="primary"
            prepend-icon="mdi-content-save-outline"
            :disabled="!canSaveDraft"
            data-testid="save-draft-button"
            @click="emit('saveDraft')"
          >
            Save
          </VBtn>
        </div>
      </div>
    </div>

    <VAlert
      v-if="props.proposal?.status === 'failed'"
      type="error"
      variant="tonal"
      density="compact"
      :text="props.proposal.error_message || 'Proposal generation failed.'"
    />

    <VAlert
      v-else-if="proposalTerminal"
      type="info"
      variant="tonal"
      density="compact"
      :text="props.proposal?.status === 'applied' ? 'Proposal applied to the draft.' : 'Proposal rejected.'"
    />

    <VAlert
      v-if="proposalReady"
      type="info"
      variant="tonal"
      density="compact"
      icon="mdi-creation"
      border="start"
      border-color="primary"
      rounded="0"
    >
      <template #title>{{ props.proposal?.summary || 'A Markdown update is ready.' }}</template>
      Review the Changes tab, then apply or reject the proposal in the chat.
    </VAlert>

    <VWindow v-model="activeMode" class="markdown-workspace__body">
      <VWindowItem value="source" class="markdown-workspace__pane">
        <MarkdownEditor
          v-if="hasDraft"
          v-model="draft"
          :disabled="props.disabled || props.saving || props.applying"
        />
        <div v-else class="current-page">
          <div class="current-page__meta">
            <VIcon icon="mdi-file-document-outline" color="primary" size="16" />
            <span class="text-caption">Version {{ props.page?.version_number ?? '-' }}</span>
          </div>
          <article
            v-if="renderedCurrentPageHtml"
            class="markdown-preview markdown-preview--embedded"
            v-html="renderedCurrentPageHtml"
          />
          <EmptyState
            v-else
            icon="mdi-file-document-outline"
            title="No extracted page text"
            message="No extracted page text is available."
          />
        </div>
      </VWindowItem>

      <VWindowItem value="preview" class="markdown-workspace__pane">
        <iframe
          v-if="shouldUseConfluencePreview"
          class="preview-frame"
          sandbox=""
          :srcdoc="props.run?.preview_html ?? ''"
          title="Confluence rendered preview"
        />
        <article v-else class="markdown-preview" v-html="renderedPreviewHtml" />
      </VWindowItem>

      <VWindowItem value="xhtml" class="markdown-workspace__pane">
        <XhtmlCodeBlock v-if="hasStorageXhtml" :code="visibleStorageXhtml" :label="xhtmlLabel" />
        <EmptyState
          v-else
          icon="mdi-code-tags"
          title="No Storage XHTML"
          message="No Storage XHTML is available yet."
        />
      </VWindowItem>

      <VWindowItem value="changes" class="markdown-workspace__pane">
        <DiffView
          v-if="hasChanges"
          :data="diffData"
          :diff-view-mode="DiffModeEnum.Unified"
          :diff-view-highlight="true"
          diff-view-theme="light"
          :diff-view-wrap="true"
        />
        <EmptyState
          v-else
          icon="mdi-source-branch"
          title="No changes"
          message="No changes to review yet."
        />
      </VWindowItem>
    </VWindow>

    <DraftHistoryDialog
      v-model="historyDialogOpen"
      :versions="props.draftVersions ?? []"
      :current-version-id="currentDraftVersionId"
      :loading="props.loadingDraftVersions"
      :restoring="props.restoringDraftVersion"
      :restore-disabled="!canRestoreDraftVersion"
      @restore-version="emit('restoreDraftVersion', $event)"
    />

    <ActionValidationDialog
      v-model="resetDialogOpen"
      title="Reset draft"
      message="Reset the draft and discard all changes?"
      supporting-text="The editor will return to the original page content. This cannot be undone."
      confirm-label="Reset"
      tone="danger"
      icon="mdi-restore"
      :loading="props.resettingDraft"
      @confirm="emit('resetDraft'); resetDialogOpen = false"
    />
  </section>
</template>

<style scoped>
.markdown-workspace {
  position: relative;
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  gap: 0;
  box-sizing: border-box;
  min-width: 0;
  min-height: 0;
  height: 100%;
  max-height: 100%;
  overflow: hidden;
  border-radius: 8px;
  background: #ffffff;
}

.markdown-workspace__header {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid #dfe1e6;
}

.markdown-workspace__controls {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.markdown-workspace__draft-actions {
  display: flex;
  gap: 6px;
  align-items: center;
  padding-left: 6px;
  border-left: 1px solid #dfe1e6;
}


.current-page__meta {
  display: flex;
  gap: 6px;
  align-items: center;
}

.markdown-workspace__body {
  min-height: 0;
  overflow-x: hidden;
  overflow-y: scroll;
  padding: 14px;
  scrollbar-gutter: stable;
  scrollbar-color: #a6b1c2 #f7f8fa;
  scrollbar-width: thin;
}

.markdown-workspace__body::-webkit-scrollbar {
  width: 10px;
}

.markdown-workspace__body::-webkit-scrollbar-track {
  background: #f7f8fa;
  border-radius: 999px;
}

.markdown-workspace__body::-webkit-scrollbar-thumb {
  border: 2px solid #f7f8fa;
  border-radius: 999px;
  background: #a6b1c2;
}

.markdown-workspace__body :deep(.v-window__container),
.markdown-workspace__pane {
  min-height: 100%;
}

.current-page,
.markdown-preview {
  min-height: 560px;
  overflow: visible;
  border: 1px solid #dfe1e6;
  border-radius: 8px;
  background: #ffffff;
}

.current-page {
  padding: 14px;
}

.current-page__meta {
  margin-bottom: 12px;
  color: #626f86;
}

.markdown-preview {
  padding: 18px 22px;
  line-height: 1.65;
}

.preview-frame {
  width: 100%;
  min-height: 560px;
  border: 1px solid #dfe1e6;
  border-radius: 8px;
  background: #ffffff;
}

.markdown-preview--embedded {
  min-height: 0;
  max-height: none;
  overflow: visible;
  border: 0;
  padding: 0;
}

.markdown-preview :deep(h1),
.markdown-preview :deep(h2),
.markdown-preview :deep(h3) {
  margin-top: 1.15em;
  margin-bottom: 0.45em;
  line-height: 1.25;
}

.markdown-preview :deep(pre) {
  overflow: auto;
  padding: 12px;
  border-radius: 6px;
  background: #f1f2f4;
}

.workspace-loading-overlay {
  position: absolute;
  inset: 0;
  z-index: 10;
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(3px);
}

.workspace-overlay-enter-active,
.workspace-overlay-leave-active {
  transition: opacity 0.18s ease;
}

.workspace-overlay-enter-from,
.workspace-overlay-leave-to {
  opacity: 0;
}

@media (max-width: 980px) {
  .markdown-workspace__header {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }

  .markdown-workspace__controls {
    justify-content: flex-start;
  }
}
</style>
