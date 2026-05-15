<script setup lang="ts">
import { computed, onMounted, onUnmounted, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { buildPagePath } from '../composables/pagePath'
import { fetchPage, fetchPages, refreshPage } from '../api/pages'
import {
  applyProposal,
  createProposal,
  createManualDraftRun,
  createPageEditRun,
  fetchActivePageEditRun,
  fetchDraftVersions,
  fetchProposal,
  fetchPageEditRun,
  publishRun,
  rejectProposal,
  resetPageDraft,
  restoreDraftVersion,
  saveDraft,
} from '../api/pageEditor'
import type { CreateProposalOptions } from '../api/pageEditor'
import ParticleBackground from '../components/common/ParticleBackground.vue'
import ActionValidationDialog from '../components/common/ActionValidationDialog.vue'
import AppSpinner from '../components/common/AppSpinner.vue'
import StatusChip from '../components/common/StatusChip.vue'
import EditChatPanel from '../components/page-editor/EditChatPanel.vue'
import MarkdownWorkspace from '../components/page-editor/MarkdownWorkspace.vue'
import PageEditorPagePicker from '../components/page-editor/PageEditorPagePicker.vue'
import type {
  ConfluencePage,
  DraftVersion,
  PageDetail,
  PageProposal,
  PageEditRun,
} from '../types/api'

interface EditChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
}

const POLLING_STATUSES = new Set(['queued', 'generating', 'converting', 'previewing', 'publishing'])
const PROPOSAL_POLLING_STATUSES = new Set(['queued', 'generating'])
const RENDERABLE_DRAFT_STATUSES = new Set(['draft_ready', 'converted', 'preview_ready'])
const PROPOSAL_POLLING_TIMEOUT_MS = 120_000

const route = useRoute()
const router = useRouter()
const pages = shallowRef<ConfluencePage[]>([])
const pickerPageId = shallowRef<number>()
const selectedPageId = shallowRef<number>()
const selectedPageDetail = shallowRef<PageDetail>()
const run = shallowRef<PageEditRun>()
const proposal = shallowRef<PageProposal>()
const draftVersions = shallowRef<DraftVersion[]>([])
const draft = shallowRef('')
const draftManuallyEdited = shallowRef(false)
const chatDraft = shallowRef('')
const chatMessages = shallowRef<EditChatMessage[]>([])
const loading = shallowRef(true)
const loadingPage = shallowRef(false)
const creatingDraft = shallowRef(false)
const creatingProposal = shallowRef(false)
const savingDraft = shallowRef(false)
const applyingProposal = shallowRef(false)
const rejectingProposal = shallowRef(false)
const loadingDraftVersions = shallowRef(false)
const restoringDraftVersion = shallowRef(false)
const resettingDraft = shallowRef(false)
const publishDialogOpen = shallowRef(false)
const publishLoading = shallowRef(false)
const appendedProposalMessages = new Set<string>()
const appendedRunMessages = new Set<string>()
let runTimer: number | undefined
let proposalTimer: number | undefined
let proposalPollingStartedAt: number | undefined
let pageRequestId = 0
let draftVersionsRequestId = 0

const selectedPage = computed(() => pages.value.find((page) => page.id === selectedPageId.value))
const pageOptions = computed(() =>
  pages.value.map((page) => ({
    title: buildPagePath(page, pages.value),
    value: page.id,
  })),
)
const isRunBusy = computed(() => Boolean(run.value && POLLING_STATUSES.has(run.value.status)))
const isProposalBusy = computed(() =>
  Boolean(proposal.value && PROPOSAL_POLLING_STATUSES.has(proposal.value.status)),
)
const shouldCreateInitialDraft = computed(() =>
  Boolean(!run.value?.markdown_draft && !draft.value.trim()),
)
const hasReviewArtifacts = computed(() =>
  Boolean(run.value?.preview_html && run.value.diff_text != null),
)
const savedDraftMarkdown = computed(() =>
  run.value?.markdown_draft ?? selectedPageDetail.value?.source_markdown ?? '',
)
const isDraftDirty = computed(() => draft.value !== savedDraftMarkdown.value)
const hasManualDraftChanges = computed(() =>
  Boolean(draftManuallyEdited.value && draft.value.trim() && isDraftDirty.value),
)
const isReviewReady = computed(() => hasReviewArtifacts.value && !isDraftDirty.value)
const pendingProposalDecision = computed(() => proposal.value?.status === 'ready')
const canPublish = computed(() =>
  Boolean(
    run.value?.preview_status === 'ready'
    && run.value.status !== 'published'
    && isReviewReady.value
    && !isRunBusy.value,
  ),
)
const isChatBusy = computed(() =>
  Boolean(
    creatingDraft.value
    || creatingProposal.value
    || savingDraft.value
    || applyingProposal.value
    || rejectingProposal.value
    || restoringDraftVersion.value
    || resettingDraft.value
    || publishLoading.value
    || isRunBusy.value
    || isProposalBusy.value,
  ),
)
const canSubmitEditRequest = computed(() =>
  Boolean(selectedPageId.value && chatDraft.value.trim() && !isChatBusy.value && !pendingProposalDecision.value),
)
const workspaceDisabled = computed(() => isChatBusy.value || pendingProposalDecision.value)
const canSaveDraft = computed(() =>
  Boolean(hasManualDraftChanges.value && !savingDraft.value && !workspaceDisabled.value),
)
const chatBusyLabel = computed(() => {
  if (creatingDraft.value || run.value?.status === 'queued' || run.value?.status === 'generating') {
    return 'Generating draft'
  }
  if (creatingProposal.value || isProposalBusy.value) return 'Preparing proposal'
  if (applyingProposal.value) return 'Applying proposal'
  if (rejectingProposal.value) return 'Rejecting proposal'
  if (restoringDraftVersion.value) return 'Restoring draft'
  if (savingDraft.value || run.value?.status === 'converting' || run.value?.status === 'previewing') {
    return 'Rendering preview'
  }
  if (publishLoading.value || run.value?.status === 'publishing') return 'Publishing'
  return 'Working'
})
const publishMessage = computed(() =>
  selectedPage.value
    ? `Publish "${selectedPage.value.title}" to Confluence?`
    : 'Publish this update to Confluence?',
)
const publishTooltip = computed(() => {
  if (run.value?.status === 'published') return 'Already published'
  if (isDraftDirty.value) return 'Save the draft before publishing'
  if (!hasReviewArtifacts.value) return 'Generate a preview first'
  if (isRunBusy.value || isProposalBusy.value) return 'Wait for processing to finish'
  return ''
})

/** Clears run and proposal polling timers when page context changes or unmounts. */
function clearEditorTimers(): void {
  if (runTimer) window.clearInterval(runTimer)
  if (proposalTimer) window.clearInterval(proposalTimer)
  runTimer = undefined
  proposalTimer = undefined
  proposalPollingStartedAt = undefined
}

/** Resets page-specific editor, draft, proposal, and chat state. */
function resetEditorState(): void {
  clearEditorTimers()
  selectedPageDetail.value = undefined
  run.value = undefined
  proposal.value = undefined
  draft.value = ''
  draftManuallyEdited.value = false
  chatDraft.value = ''
  chatMessages.value = []
  draftVersions.value = []
  loadingPage.value = false
  appendedProposalMessages.clear()
  appendedRunMessages.clear()
}

/** Reads and validates the pageId query parameter against the loaded page list. */
function routePageId(): number | undefined {
  const queryPageId = Number(route.query.pageId)
  if (!Number.isFinite(queryPageId) || queryPageId <= 0) return undefined
  return pages.value.some((page) => page.id === queryPageId) ? queryPageId : undefined
}

/** Navigates the editor to a selected page id. */
function selectPageForEditing(pageId?: number | null): void {
  if (!pageId) return
  void router.push({ path: '/editor', query: { pageId: String(pageId) } })
}

/** Marks that the currently visible Markdown was edited by the user. */
function markDraftManuallyEdited(): void {
  draftManuallyEdited.value = true
}

/** Returns whether an older draft run needs preview rendering queued. */
function needsDraftRender(pageEditRun?: PageEditRun | null): pageEditRun is PageEditRun {
  return Boolean(
    pageEditRun?.markdown_draft
    && !pageEditRun.preview_html
    && RENDERABLE_DRAFT_STATUSES.has(pageEditRun.status),
  )
}


/** Appends a local editor-chat message without mutating the existing array. */
function appendChatMessage(role: EditChatMessage['role'], content: string): void {
  chatMessages.value = [
    ...chatMessages.value,
    {
      id: Date.now() + chatMessages.value.length,
      role,
      content,
    },
  ]
}

/** Adds a one-time assistant message when a proposal reaches a visible state. */
function appendProposalMessage(nextProposal: PageProposal): void {
  const key = `${nextProposal.id}:${nextProposal.status}`
  if (appendedProposalMessages.has(key)) return
  if (nextProposal.status === 'ready') {
    appendedProposalMessages.add(key)
    appendChatMessage('assistant', nextProposal.summary || 'I prepared a Markdown proposal.')
  }
  if (nextProposal.status === 'failed') {
    appendedProposalMessages.add(key)
    appendChatMessage('assistant', nextProposal.error_message || 'I could not prepare the proposal.')
  }
}

/** Adds a one-time assistant message when a run reaches an important state. */
function appendRunMessage(nextRun: PageEditRun): void {
  const key = `${nextRun.id}:${nextRun.status}:${nextRun.preview_status}`
  if (appendedRunMessages.has(key)) return
  if (nextRun.status === 'preview_ready' && nextRun.preview_status === 'ready') {
    appendedRunMessages.add(key)
    appendChatMessage('assistant', 'The draft and Confluence preview are ready. Review the preview, XHTML, and changes before publishing.')
  }
  if (nextRun.status === 'failed') {
    appendedRunMessages.add(key)
    appendChatMessage('assistant', nextRun.error_message || 'The page editor failed.')
  }
  if (nextRun.status === 'published') {
    appendedRunMessages.add(key)
    appendChatMessage('assistant', nextRun.error_message ? `Published to Confluence. ${nextRun.error_message}` : 'Published to Confluence.')
  }
}

/** Extracts an API detail message from thrown errors, falling back to user-safe copy. */
function errorMessage(error: unknown, fallback: string): string {
  if (!(error instanceof Error) || !error.message) return fallback
  try {
    const parsed = JSON.parse(error.message) as { detail?: unknown }
    if (typeof parsed.detail === 'string') return parsed.detail
  } catch {
    return error.message
  }
  return error.message
}

/** Appends an API failure message into the editor chat stream. */
function appendErrorMessage(error: unknown, fallback: string): void {
  appendChatMessage('assistant', errorMessage(error, fallback))
}

/** Marks the current proposal failed locally when polling times out or refresh fails. */
function failCurrentProposal(message: string): void {
  if (!proposal.value) {
    appendChatMessage('assistant', message)
    return
  }
  proposal.value = {
    ...proposal.value,
    status: 'failed',
    error_message: message,
    updated_at: new Date().toISOString(),
  }
}

/** Builds the base markdown context used for the next proposal request. */
function currentProposalBase(): CreateProposalOptions {
  const baseMarkdown = draft.value.trim()
    ? draft.value
    : (run.value?.markdown_draft ?? selectedPageDetail.value?.source_markdown ?? '')
  const base: CreateProposalOptions = { baseMarkdown: baseMarkdown || undefined }
  if (run.value?.id) base.baseRunId = run.value.id
  return base
}

/** Loads pages and applies the optional page id query parameter. */
async function initialize(): Promise<void> {
  pages.value = await fetchPages()
  const pageId = routePageId()
  pickerPageId.value = pageId
  selectedPageId.value = pageId
  if (selectedPageId.value) {
    await loadSelectedPage(selectedPageId.value)
  } else {
    resetEditorState()
  }
  loading.value = false
}

/** Loads validated draft versions for the active run. */
async function loadDraftVersions(runId = run.value?.id): Promise<void> {
  const requestId = ++draftVersionsRequestId
  if (!runId) {
    draftVersions.value = []
    loadingDraftVersions.value = false
    return
  }
  loadingDraftVersions.value = true
  try {
    const versions = await fetchDraftVersions(runId)
    if (requestId !== draftVersionsRequestId || run.value?.id !== runId) return
    draftVersions.value = versions
  } catch (error) {
    appendErrorMessage(error, 'Could not load the draft history.')
  } finally {
    if (requestId === draftVersionsRequestId) {
      loadingDraftVersions.value = false
    }
  }
}

/** Loads the selected page detail and reuses an active draft when one exists. */
async function loadSelectedPage(pageId = selectedPageId.value): Promise<void> {
  const requestId = ++pageRequestId
  if (!pageId) {
    selectedPageDetail.value = undefined
    run.value = undefined
    draft.value = ''
    draftManuallyEdited.value = false
    draftVersions.value = []
    proposal.value = undefined
    return
  }

  loadingPage.value = true
  proposal.value = undefined
  draftVersions.value = []
  chatMessages.value = []
  appendedProposalMessages.clear()
  appendedRunMessages.clear()
  try {
    const [pageDetail, activeRun] = await Promise.all([
      fetchPage(pageId),
      fetchActivePageEditRun(pageId),
    ])
    if (requestId !== pageRequestId || selectedPageId.value !== pageId) return
    selectedPageDetail.value = pageDetail
    run.value = activeRun ?? undefined
    draft.value = activeRun?.markdown_draft ?? pageDetail.source_markdown ?? ''
    draftManuallyEdited.value = false
    if (activeRun?.id) {
      loadDraftVersions(activeRun.id).catch((err) => appendErrorMessage(err, 'Could not load draft versions.'))
    }
    if (needsDraftRender(activeRun)) {
      renderCurrentDraft(activeRun).catch((err) => appendErrorMessage(err, 'Could not render draft.'))
    }
  } finally {
    if (requestId === pageRequestId) {
      loadingPage.value = false
    }
  }
}

/** Reloads the current page edit run while worker tasks progress. */
async function reloadRun(): Promise<void> {
  if (!run.value) return
  try {
    const updatedRun = await fetchPageEditRun(run.value.id)
    run.value = updatedRun
    draft.value = updatedRun.markdown_draft ?? draft.value
    draftManuallyEdited.value = false
    if (needsDraftRender(updatedRun)) {
      void renderCurrentDraft(updatedRun)
    }
  } catch (error) {
    if (runTimer) window.clearInterval(runTimer)
    runTimer = undefined
    appendErrorMessage(error, 'Could not refresh the editor status.')
  }
}

/** Reloads the current proposal while the LLM prepares it. */
async function reloadProposal(): Promise<void> {
  if (!proposal.value) return
  if (
    proposalPollingStartedAt
    && Date.now() - proposalPollingStartedAt > PROPOSAL_POLLING_TIMEOUT_MS
  ) {
    failCurrentProposal('The proposal is taking too long to prepare. Please check the worker status or try again.')
    return
  }
  try {
    const updatedProposal = await fetchProposal(proposal.value.id)
    proposal.value = updatedProposal
    appendProposalMessage(updatedProposal)
  } catch (error) {
    if (proposalTimer) window.clearInterval(proposalTimer)
    proposalTimer = undefined
    failCurrentProposal(errorMessage(error, 'Could not refresh the proposal.'))
  }
}

/** Queues preview rendering for a draft that predates automatic rendering. */
async function renderCurrentDraft(pageEditRun: PageEditRun): Promise<void> {
  try {
    const renderedRun = await saveDraft(pageEditRun.id, pageEditRun.markdown_draft ?? '')
    if (run.value?.id !== pageEditRun.id) return
    run.value = renderedRun
    draftManuallyEdited.value = false
  } catch (error) {
    appendErrorMessage(error, 'Could not render the current draft.')
  }
}

/** Saves manual Markdown changes into the app-side draft. */
async function saveCurrentDraft(): Promise<void> {
  if (!canSaveDraft.value) return
  const pageId = selectedPageId.value
  if (!run.value && !pageId) return
  savingDraft.value = true
  try {
    if (run.value) {
      run.value = await saveDraft(run.value.id, draft.value)
    } else if (pageId) {
      run.value = await createManualDraftRun(pageId, draft.value)
    }
    draft.value = run.value?.markdown_draft ?? draft.value
    draftManuallyEdited.value = false
    if (run.value?.id) {
      loadDraftVersions(run.value.id).catch((err) => appendErrorMessage(err, 'Could not load draft versions.'))
    }
  } catch (error) {
    appendErrorMessage(error, 'Could not save the draft.')
  } finally {
    savingDraft.value = false
  }
}

/** Starts the first draft, then uses later chat prompts as reviewable proposals. */
async function submitEditRequest(): Promise<void> {
  const pageId = selectedPageId.value
  const message = chatDraft.value.trim()
  if (!pageId || !message || !canSubmitEditRequest.value) return
  appendChatMessage('user', message)
  chatDraft.value = ''

  if (shouldCreateInitialDraft.value) {
    creatingDraft.value = true
    proposal.value = undefined
    try {
      run.value = await createPageEditRun(pageId, message)
      draft.value = run.value.markdown_draft ?? ''
      draftManuallyEdited.value = false
    } catch (error) {
      appendErrorMessage(error, 'Could not start the page editor.')
    } finally {
      creatingDraft.value = false
    }
    return
  }

  creatingProposal.value = true
  try {
    proposal.value = await createProposal(pageId, message, currentProposalBase())
  } catch (error) {
    appendErrorMessage(error, 'Could not prepare a proposal.')
  } finally {
    creatingProposal.value = false
  }
}

/** Applies a ready proposal and turns it into the real Markdown draft. */
async function applyCurrentProposal(): Promise<void> {
  if (!proposal.value || proposal.value.status !== 'ready') return
  applyingProposal.value = true
  try {
    const response = await applyProposal(proposal.value.id)
    proposal.value = response.proposal
    run.value = response.run
    draft.value = response.run.markdown_draft ?? draft.value
    draftManuallyEdited.value = false
    void loadDraftVersions(response.run.id)
    appendChatMessage('assistant', 'Applied the proposal to the draft and queued the preview.')
  } catch (error) {
    appendErrorMessage(error, 'Could not apply the proposal.')
  } finally {
    applyingProposal.value = false
  }
}

/** Rejects the active proposal without changing the page draft. */
async function rejectCurrentProposal(): Promise<void> {
  if (!proposal.value || proposal.value.status === 'applied') return
  rejectingProposal.value = true
  try {
    proposal.value = await rejectProposal(proposal.value.id)
    appendChatMessage('assistant', 'Rejected the proposal. The draft was not changed.')
  } catch (error) {
    appendErrorMessage(error, 'Could not reject the proposal.')
  } finally {
    rejectingProposal.value = false
  }
}

/** Restores a validated draft version and queues a fresh preview render. */
async function restoreCurrentDraftVersion(versionId: number): Promise<void> {
  if (!run.value || restoringDraftVersion.value || isDraftDirty.value || pendingProposalDecision.value) return
  restoringDraftVersion.value = true
  try {
    const restoredRun = await restoreDraftVersion(run.value.id, versionId)
    run.value = restoredRun
    draft.value = restoredRun.markdown_draft ?? draft.value
    draftManuallyEdited.value = false
    void loadDraftVersions(restoredRun.id)
    appendChatMessage('assistant', 'Restored the selected draft version and queued the preview.')
  } catch (error) {
    appendErrorMessage(error, 'Could not restore the draft version.')
  } finally {
    restoringDraftVersion.value = false
  }
}

/** Resets the selected page's app-side draft and clears local draft/proposal state. */
async function resetCurrentDraft(): Promise<void> {
  if (!selectedPageId.value) return
  resettingDraft.value = true
  clearEditorTimers()
  try {
    await resetPageDraft(selectedPageId.value)
    run.value = undefined
    draft.value = selectedPageDetail.value?.source_markdown ?? ''
    draftManuallyEdited.value = false
    draftVersions.value = []
    proposal.value = undefined
  } finally {
    resettingDraft.value = false
  }
}

/** Opens the publish confirmation only when the current draft is publishable. */
function openPublishDialog(): void {
  if (!canPublish.value) return
  publishDialogOpen.value = true
}

/** Queues final publication to Confluence. */
async function confirmPublish(): Promise<void> {
  if (!run.value || !canPublish.value) return
  const pageId = selectedPageId.value
  publishLoading.value = true
  try {
    await publishRun(run.value.id)
    publishDialogOpen.value = false
    if (pageId) {
      await Promise.all([resetPageDraft(pageId), refreshPage(pageId)])
      resetEditorState()
      await loadSelectedPage(pageId)
    }
  } catch (error) {
    appendErrorMessage(error, 'Could not publish the update.')
  } finally {
    publishLoading.value = false
  }
}

watch(run, () => {
  if (runTimer) window.clearInterval(runTimer)
  runTimer = undefined
  if (run.value && POLLING_STATUSES.has(run.value.status)) {
    runTimer = window.setInterval(reloadRun, 2500)
  }
  if (run.value) {
    appendRunMessage(run.value)
  }
})

watch(proposal, () => {
  if (proposalTimer) window.clearInterval(proposalTimer)
  proposalTimer = undefined
  if (proposal.value && PROPOSAL_POLLING_STATUSES.has(proposal.value.status)) {
    proposalPollingStartedAt ??= Date.now()
    proposalTimer = window.setInterval(reloadProposal, 1800)
  } else {
    proposalPollingStartedAt = undefined
  }
  if (proposal.value) {
    appendProposalMessage(proposal.value)
  }
})

watch(() => route.query.pageId, () => {
  if (loading.value) return
  const pageId = routePageId()
  pickerPageId.value = pageId
  if (pageId === selectedPageId.value) return
  selectedPageId.value = pageId
  if (pageId) {
    void loadSelectedPage(pageId)
  } else {
    resetEditorState()
  }
})

onMounted(initialize)
onUnmounted(clearEditorTimers)
</script>

<template>
  <div class="page-editor-root">
    <ParticleBackground particle-color="#b0b8c4" :speed="0.4" :density="8000" :max-distance="120" />
    <AppSpinner v-if="loading" label="Loading pages" />
    <template v-else>
      <PageEditorPagePicker
        v-if="!selectedPageId"
        v-model="pickerPageId"
        :pages="pages"
        @select="selectPageForEditing"
      />
      <template v-else>
        <div class="page-editor-header">
          <div class="page-editor-header__page">
            <VBtn
              icon
              variant="text"
              size="small"
              density="compact"
              title="Back to editor"
              aria-label="Back to editor"
              :to="{ path: '/editor' }"
            >
              <VIcon icon="mdi-arrow-left" size="18" />
            </VBtn>
            <VDivider vertical style="height:18px;align-self:center" class="mx-1 flex-shrink-0" />
            <VIcon icon="mdi-file-document-outline" size="16" color="secondary" class="flex-shrink-0" />
            <VTooltip location="bottom" :text="selectedPage?.title ?? 'Page Editor'">
              <template #activator="{ props: tp }">
                <span v-bind="tp" class="page-editor-page-title">{{ selectedPage?.title ?? 'Page Editor' }}</span>
              </template>
            </VTooltip>
            <StatusChip v-if="run" :state="run.draft_status" class="flex-shrink-0" />
            <VChip v-else-if="selectedPageDetail" size="small" variant="tonal" color="secondary" class="flex-shrink-0">No draft</VChip>
          </div>
          <Transition name="fade">
            <div v-if="isChatBusy" class="page-editor-header__status">
              <VProgressCircular indeterminate size="14" width="2" color="primary" />
              <span class="text-caption muted-text" style="white-space:nowrap">{{ chatBusyLabel }}</span>
            </div>
          </Transition>

          <div class="page-editor-header__actions">
            <VTooltip location="bottom" :disabled="canPublish" :text="publishTooltip">
              <template #activator="{ props: tp }">
                <span v-bind="tp">
                  <VBtn
                    color="primary"
                    prepend-icon="mdi-publish"
                    :disabled="!canPublish"
                    data-testid="publish-run-button"
                    @click="openPublishDialog"
                  >
                    Publish
                  </VBtn>
                </span>
              </template>
            </VTooltip>
          </div>
        </div>

        <AppSpinner v-if="loadingPage" label="Loading selected page" />
        <div v-else class="page-editor-workspace">
          <MarkdownWorkspace
            v-model="draft"
            :page="selectedPageDetail"
            :run="run"
            :proposal="proposal"
            :draft-versions="draftVersions"
            :saving="savingDraft"
            :applying="applyingProposal"
            :loading-draft-versions="loadingDraftVersions"
            :restoring-draft-version="restoringDraftVersion"
            :resetting-draft="resettingDraft"
            :loading="isChatBusy"
            :disabled="workspaceDisabled"
            :can-save-draft="canSaveDraft"
            @markdown-manual-change="markDraftManuallyEdited"
            @save-draft="saveCurrentDraft"
            @restore-draft-version="restoreCurrentDraftVersion"
            @reset-draft="resetCurrentDraft"
          />

          <EditChatPanel
            v-model="chatDraft"
            :messages="chatMessages"
            :proposal="proposal"
            :busy="isChatBusy"
            :busy-label="chatBusyLabel"
            :applying-proposal="applyingProposal"
            :rejecting-proposal="rejectingProposal"
            :disabled="!selectedPageId"
            @apply-proposal="applyCurrentProposal"
            @reject-proposal="rejectCurrentProposal"
            @submit="submitEditRequest"
          />
        </div>
      </template>
    </template>

    <ActionValidationDialog
      v-model="publishDialogOpen"
      title="Publish update"
      :message="publishMessage"
      supporting-text="The reviewed draft will replace the current Confluence page content."
      confirm-label="Publish"
      tone="primary"
      icon="mdi-publish"
      :loading="publishLoading"
      :disabled="!canPublish"
      persistent
      @confirm="confirmPublish"
    />
  </div>
</template>

<style scoped>
.page-editor-root {
  position: relative;
  display: flex;
  flex-direction: column;
  height: calc(100dvh - 48px); /* 48px = VAppBar height */
  overflow: hidden;
  padding: 16px;
  box-sizing: border-box;
  background-color: #f5f5f5;
}

.page-editor-root > :not(canvas) {
  position: relative;
  z-index: 1;
}

.page-editor-header {
  position: relative;
  z-index: 1;
  display: flex;
  flex-shrink: 0;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
  padding: 10px 16px;
  border: 1px solid #dfe1e6;
  border-radius: 8px;
  background: #ffffff;
}

.page-editor-header__page {
  display: flex;
  gap: 8px;
  align-items: center;
  min-width: 0;
  flex: 1;
  overflow: hidden;
}

.page-editor-page-title {
  font-size: 14px;
  font-weight: 600;
  color: #172b4d;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.page-editor-header__status {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-shrink: 0;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.page-editor-header__actions {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-shrink: 0;
}

.page-editor-workspace {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(340px, 420px);
  gap: 14px;
  align-items: stretch;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

@media (max-width: 1100px) {
  .page-editor-root {
    overflow: auto;
  }

  .page-editor-header {
    flex-wrap: wrap;
  }

  .page-editor-workspace {
    grid-template-columns: 1fr;
    flex: none;
    overflow: visible;
  }
}

@media (max-width: 720px) {
  .page-editor-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .page-editor-header__actions {
    width: 100%;
    flex-wrap: wrap;
  }
}
</style>
