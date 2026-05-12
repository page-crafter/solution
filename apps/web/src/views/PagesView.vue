<script setup lang="ts">
import { computed, onMounted, shallowRef } from 'vue'
import { buildPagePath } from '../composables/pagePath'
import {
  createEmptyPage,
  deletePage,
  fetchPage,
  fetchPages,
  movePage,
  refreshPage,
  syncSpace,
} from '../api/pages'
import type { PageMovePosition } from '../api/pages'
import { cancelRun, fetchActivePageEditRun } from '../api/pageEditor'
import ActionValidationDialog from '../components/common/ActionValidationDialog.vue'
import AppSpinner from '../components/common/AppSpinner.vue'
import JobStateDialog from '../components/common/JobStateDialog.vue'
import PageDetailPanel from '../components/pages/PageDetailPanel.vue'
import PageTree from '../components/pages/PageTree.vue'
import type { ConfluencePage, JobRead, PageDetail, PageEditRun } from '../types/api'

interface PageOption {
  title: string
  value: string
}

interface PageMoveIntent {
  page: ConfluencePage
  target?: ConfluencePage
  targetParentId?: string | null
  position: PageMovePosition
}

interface ParentMoveSelection {
  parentId: string | null
  orderId: string
}

interface PageJobState {
  id: string
  title: string
  pendingLabel: string
}

type ValidationTone = 'default' | 'primary' | 'warning' | 'danger'

type PendingValidationAction =
  | {
      kind: 'delete'
      page: ConfluencePage
      title: string
      message: string
      supportingText?: string
      confirmLabel: string
      tone: ValidationTone
      icon: string
    }
  | {
      kind: 'reorder'
      intent: PageMoveIntent
      title: string
      message: string
      supportingText?: string
      confirmLabel: string
      tone: ValidationTone
      icon: string
    }

const ROOT_PARENT_VALUE = '__space_root__'
const FIRST_ORDER_VALUE = '__first__'
const LAST_ORDER_VALUE = '__last__'

const loading = shallowRef(true)
const pages = shallowRef<ConfluencePage[]>([])
const selectedPage = shallowRef<PageDetail>()
const activeRun = shallowRef<PageEditRun | null>(null)
const activePageJob = shallowRef<PageJobState>()
const createDialogOpen = shallowRef(false)
const createTitle = shallowRef('')
const createParentId = shallowRef(ROOT_PARENT_VALUE)
const creatingPage = shallowRef(false)
const moveDialogOpen = shallowRef(false)
const moveCandidate = shallowRef<ConfluencePage>()
const moveParentId = shallowRef(ROOT_PARENT_VALUE)
const moveOrderId = shallowRef(LAST_ORDER_VALUE)
const movingPage = shallowRef(false)
const actionValidationOpen = shallowRef(false)
const actionValidationLoading = shallowRef(false)
const pendingValidationAction = shallowRef<PendingValidationAction>()
const moveError = shallowRef<string | null>(null)

const spaceRootLabel = computed(() => {
  const pageWithSpace = pages.value.find((page) => page.space_name || page.space_key)
  if (pageWithSpace?.space_name) return pageWithSpace.space_name
  if (pageWithSpace?.space_key) return `Space ${pageWithSpace.space_key}`
  return 'Confluence space'
})
const parentOptions = computed(() => [
  { title: spaceRootLabel.value, value: ROOT_PARENT_VALUE },
  ...pages.value.map(pageToOption),
])
const createParentOptions = computed(() => parentOptions.value)
const moveParentOptions = computed(() => {
  const candidate = moveCandidate.value
  if (!candidate) return parentOptions.value
  return [
    { title: spaceRootLabel.value, value: ROOT_PARENT_VALUE },
    ...pages.value
    .filter((page) => page.id !== candidate.id && !isDescendant(page, candidate))
      .map(pageToOption),
  ]
})

const moveSiblings = computed(() => {
  const candidate = moveCandidate.value
  const parentId = normalizeParentSelection(moveParentId.value)
  return pages.value
    .filter((page) => {
      if (page.id === candidate?.id) return false
      if (candidate && isDescendant(page, candidate)) return false
      return normalizedParentId(page) === parentId
    })
    .sort(comparePages)
})

const moveOrderOptions = computed(() => [
  { title: 'First in parent', value: FIRST_ORDER_VALUE },
  ...moveSiblings.value.map((page) => ({ title: `After ${page.title}`, value: page.confluence_id })),
  { title: 'Last in parent', value: LAST_ORDER_VALUE },
])
const createDialogTitle = computed(() => {
  const parentId = normalizeParentSelection(createParentId.value)
  if (!parentId) return 'Create empty page'
  const parent = pages.value.find((page) => page.confluence_id === parentId)
  return parent ? `Create subpage under ${parent.title}` : 'Create empty page'
})
const actionValidationTitle = computed(() => pendingValidationAction.value?.title ?? 'Confirm action')
const actionValidationMessage = computed(() => pendingValidationAction.value?.message ?? '')
const actionValidationSupportingText = computed(() => pendingValidationAction.value?.supportingText)
const actionValidationConfirmLabel = computed(
  () => pendingValidationAction.value?.confirmLabel ?? 'Confirm',
)
const actionValidationTone = computed(() => pendingValidationAction.value?.tone ?? 'default')
const actionValidationIcon = computed(() => pendingValidationAction.value?.icon)

/** Loads the page table from synced Confluence data. */
async function loadPages(): Promise<void> {
  loading.value = true
  pages.value = await fetchPages()
  loading.value = false
}

/** Refreshes page list state after a page-level mutation. */
async function reloadPagesAfterMutation(): Promise<void> {
  pages.value = await fetchPages()
  if (!selectedPage.value) return
  const currentPage = pages.value.find((page) => page.id === selectedPage.value?.id)
  if (!currentPage) {
    selectedPage.value = undefined
    activeRun.value = null
    return
  }
  await selectPage(currentPage)
}

async function finishPageJob(job: JobRead): Promise<void> {
  await reloadPagesAfterMutation()
  const isError = job.status === 'failed' || job.status === 'blocked'
  if (!isError) clearPageJob()
}

function trackPageJob(job: JobRead, title: string, pendingLabel: string): void {
  activePageJob.value = { id: job.id, title, pendingLabel }
}

function clearPageJob(): void {
  activePageJob.value = undefined
}

/** Selects a page and loads its active app draft if present. */
async function selectPage(page: ConfluencePage): Promise<void> {
  selectedPage.value = await fetchPage(page.id)
  activeRun.value = await fetchActivePageEditRun(page.id)
}

/** Queues a full-space sync and displays the job status. */
async function runSync(): Promise<void> {
  const job = await syncSpace()
  trackPageJob(job, 'Syncing space', 'Refreshing the Confluence page tree')
}

/** Opens the page creation dialog for the space root or a page parent. */
function openCreateDialog(parent?: ConfluencePage): void {
  createParentId.value = parent?.confluence_id ?? ROOT_PARENT_VALUE
  createDialogOpen.value = true
}

/** Queues a single-page refresh. */
async function runRefresh(page: ConfluencePage): Promise<void> {
  const job = await refreshPage(page.id)
  trackPageJob(job, 'Refreshing page', `Refreshing ${page.title}`)
}

/** Opens a structured move dialog for a page. */
function openMoveDialog(page: ConfluencePage): void {
  moveCandidate.value = page
  moveParentId.value = page.parent_confluence_id ?? ROOT_PARENT_VALUE
  moveOrderId.value = previousSibling(page)?.confluence_id ?? FIRST_ORDER_VALUE
  moveDialogOpen.value = true
}

/** Queues a page move from the move dialog. */
async function submitMove(): Promise<void> {
  if (!moveCandidate.value) return
  movingPage.value = true
  try {
    const job = await queueMove(moveCandidate.value, {
      parentId: normalizeParentSelection(moveParentId.value),
      orderId: moveOrderId.value,
    })
    if (!job) return
    trackPageJob(job, 'Moving page', `Moving ${moveCandidate.value.title}`)
    moveDialogOpen.value = false
  } finally {
    movingPage.value = false
  }
}

/** Queues a tree reorder action, including drag/drop moves. */
function runReorder(intent: PageMoveIntent): void {
  const description = describeMoveIntent(intent)
  openActionValidation({
    kind: 'reorder',
    intent,
    title: 'Move page',
    message: `Move "${intent.page.title}" ${description}?`,
    supportingText: 'The page hierarchy will be updated in Confluence.',
    confirmLabel: 'Move',
    tone: 'primary',
    icon: 'mdi-file-move-outline',
  })
}

async function confirmReorder(intent: PageMoveIntent): Promise<void> {
  const job = intent.target
    ? await movePage(intent.page.id, intent.target.confluence_id, intent.position)
    : await queueMove(intent.page, { parentId: intent.targetParentId ?? null, orderId: LAST_ORDER_VALUE })
  if (!job) return
  trackPageJob(job, 'Moving page', `Moving ${intent.page.title}`)
}

/** Confirms and queues a page deletion. */
function runDelete(page: ConfluencePage): void {
  openActionValidation({
    kind: 'delete',
    page,
    title: 'Delete page',
    message: `Delete "${page.title}" from Confluence?`,
    supportingText: 'This removes the page from Confluence and clears its local vector data.',
    confirmLabel: 'Delete',
    tone: 'danger',
    icon: 'mdi-delete-outline',
  })
}

async function confirmDelete(page: ConfluencePage): Promise<void> {
  const job = await deletePage(page.id)
  trackPageJob(job, 'Deleting page', `Deleting ${page.title}`)
  if (selectedPage.value?.id === page.id) {
    selectedPage.value = undefined
    activeRun.value = null
  }
}

function openActionValidation(action: PendingValidationAction): void {
  pendingValidationAction.value = action
  actionValidationOpen.value = true
}

async function confirmPendingAction(): Promise<void> {
  const action = pendingValidationAction.value
  if (!action) return
  actionValidationLoading.value = true
  try {
    if (action.kind === 'delete') {
      await confirmDelete(action.page)
    } else {
      await confirmReorder(action.intent)
    }
    actionValidationOpen.value = false
  } finally {
    actionValidationLoading.value = false
  }
}

function clearPendingAction(): void {
  if (actionValidationLoading.value) return
  pendingValidationAction.value = undefined
}

/** Queues a blank Confluence page that can be populated later. */
async function runCreateEmptyPage(): Promise<void> {
  const title = createTitle.value.trim()
  if (!title) return
  creatingPage.value = true
  try {
    const job = await createEmptyPage({
      title,
      parent_id: normalizeParentSelection(createParentId.value),
    })
    trackPageJob(job, 'Creating page', `Creating ${title}`)
    createDialogOpen.value = false
    createTitle.value = ''
    createParentId.value = ROOT_PARENT_VALUE
  } finally {
    creatingPage.value = false
  }
}

/** Cancels the selected page app-side draft. */
async function cancelActiveDraft(): Promise<void> {
  if (!activeRun.value || !selectedPage.value) return
  activeRun.value = await cancelRun(activeRun.value.id)
  await reloadPagesAfterMutation()
}

function pageToOption(page: ConfluencePage): PageOption {
  return {
    title: buildPagePath(page, pages.value),
    value: page.confluence_id,
  }
}

function normalizeParentSelection(value: string): string | null {
  return value === ROOT_PARENT_VALUE ? null : value
}

function normalizedParentId(page: ConfluencePage): string | null {
  const parentId = page.parent_confluence_id ?? null
  return parentId && pages.value.some((candidate) => candidate.confluence_id === parentId)
    ? parentId
    : null
}

function comparePages(left: ConfluencePage, right: ConfluencePage): number {
  if (left.sort_order !== right.sort_order) {
    return left.sort_order - right.sort_order
  }
  return left.title.localeCompare(right.title)
}

function siblingsForParent(parentId: string | null, page: ConfluencePage): ConfluencePage[] {
  return pages.value
    .filter((candidate) => {
      if (candidate.id === page.id) return false
      if (isDescendant(candidate, page)) return false
      return normalizedParentId(candidate) === parentId
    })
    .sort(comparePages)
}

function previousSibling(page: ConfluencePage): ConfluencePage | undefined {
  const siblings = pages.value
    .filter((candidate) => normalizedParentId(candidate) === normalizedParentId(page))
    .sort(comparePages)
  const pageIndex = siblings.findIndex((candidate) => candidate.id === page.id)
  return pageIndex > 0 ? siblings[pageIndex - 1] : undefined
}

async function queueMove(
  page: ConfluencePage,
  selection: ParentMoveSelection,
): Promise<JobRead | undefined> {
  const siblings = siblingsForParent(selection.parentId, page)
  if (selection.orderId !== FIRST_ORDER_VALUE && selection.orderId !== LAST_ORDER_VALUE) {
    return movePage(page.id, selection.orderId, 'after')
  }

  if (selection.orderId === FIRST_ORDER_VALUE) {
    const firstSibling = siblings[0]
    if (firstSibling) {
      return movePage(page.id, firstSibling.confluence_id, 'before')
    }
    if (selection.parentId) {
      return movePage(page.id, selection.parentId, 'append')
    }
    moveError.value = 'A root-level move needs at least one other page in the space root.'
    return undefined
  }

  if (selection.parentId) {
    return movePage(page.id, selection.parentId, 'append')
  }

  const lastSibling = siblings[siblings.length - 1]
  if (lastSibling) {
    return movePage(page.id, lastSibling.confluence_id, 'after')
  }
  window.alert('A root-level move needs at least one other page in the space root.')
  return undefined
}

function describeMoveIntent(intent: PageMoveIntent): string {
  if (!intent.target) return `to the root of "${spaceRootLabel.value}"`
  if (intent.position === 'append') return `under "${intent.target.title}"`
  return `${intent.position} "${intent.target.title}"`
}

function isDescendant(page: ConfluencePage, ancestor: ConfluencePage): boolean {
  let parentId = page.parent_confluence_id
  const seen = new Set<string>()
  while (parentId && !seen.has(parentId)) {
    if (parentId === ancestor.confluence_id) return true
    seen.add(parentId)
    parentId = pages.value.find((candidate) => candidate.confluence_id === parentId)
      ?.parent_confluence_id
  }
  return false
}

onMounted(loadPages)
</script>

<template>
  <VContainer fluid class="pa-4">
    <div class="pages-toolbar">
      <div>
        <h1>Pages</h1>
        <p class="muted-text">Browse synced Confluence pages and manage app-side drafts.</p>
      </div>
      <div class="toolbar-actions">
        <VBtn variant="tonal" prepend-icon="mdi-file-plus-outline" @click="openCreateDialog()">
          New empty page
        </VBtn>
        <VBtn color="primary" prepend-icon="mdi-sync" @click="runSync">Sync space</VBtn>
      </div>
    </div>

    <JobStateDialog
      :job-id="activePageJob?.id"
      :title="activePageJob?.title"
      :pending-label="activePageJob?.pendingLabel"
      :auto-close="false"
      @finished="finishPageJob"
      @closed="clearPageJob"
    />

    <ActionValidationDialog
      v-model="actionValidationOpen"
      :title="actionValidationTitle"
      :message="actionValidationMessage"
      :supporting-text="actionValidationSupportingText"
      :confirm-label="actionValidationConfirmLabel"
      :tone="actionValidationTone"
      :icon="actionValidationIcon"
      :loading="actionValidationLoading"
      persistent
      @confirm="confirmPendingAction"
      @cancel="clearPendingAction"
    />

    <VRow class="content-row">
      <VCol cols="12" lg="8" class="content-col">
        <AppSpinner v-if="loading" label="Loading synced pages" />
        <PageTree
          v-else
          :pages="pages"
          :root-label="spaceRootLabel"
          :selected-id="selectedPage?.id"
          @select="selectPage"
          @create-child="openCreateDialog"
          @refresh="runRefresh"
          @move="openMoveDialog"
          @delete="runDelete"
          @reorder="runReorder"
        />
      </VCol>
      <VCol cols="12" lg="4" class="content-col">
        <PageDetailPanel
          :page="selectedPage"
          :active-run="activeRun"
          :pages="pages"
          @cancel-draft="cancelActiveDraft"
        />
      </VCol>
    </VRow>

    <VDialog v-model="createDialogOpen" max-width="520">
      <VCard class="dialog-card">
        <VCardTitle>{{ createDialogTitle }}</VCardTitle>
        <VCardText class="dialog-body">
          <VTextField
            v-model="createTitle"
            label="Title"
            autofocus
            hide-details
            @keyup.enter="runCreateEmptyPage"
          />
          <VSelect
            v-model="createParentId"
            :items="createParentOptions"
            item-title="title"
            item-value="value"
            label="Parent page"
            hide-details
          />
        </VCardText>
        <VCardActions>
          <VSpacer />
          <VBtn variant="text" @click="createDialogOpen = false">Cancel</VBtn>
          <VBtn
            color="primary"
            :loading="creatingPage"
            :disabled="!createTitle.trim()"
            @click="runCreateEmptyPage"
          >
            Create
          </VBtn>
        </VCardActions>
      </VCard>
    </VDialog>

    <VSnackbar :model-value="moveError !== null" color="error" :timeout="4000" @update:model-value="moveError = $event ? moveError : null">
      {{ moveError }}
    </VSnackbar>

    <VDialog v-model="moveDialogOpen" max-width="560">
      <VCard class="dialog-card">
        <VCardTitle>Organize page</VCardTitle>
        <VCardText class="dialog-body">
          <div v-if="moveCandidate" class="move-page-title">
            {{ moveCandidate.title }}
          </div>
          <VSelect
            v-model="moveParentId"
            :items="moveParentOptions"
            item-title="title"
            item-value="value"
            label="Parent"
            hide-details
            @update:model-value="moveOrderId = LAST_ORDER_VALUE"
          />
          <VSelect
            v-model="moveOrderId"
            :items="moveOrderOptions"
            item-title="title"
            item-value="value"
            label="Order"
            hide-details
          />
        </VCardText>
        <VCardActions>
          <VSpacer />
          <VBtn variant="text" @click="moveDialogOpen = false">Cancel</VBtn>
          <VBtn
            color="primary"
            :loading="movingPage"
            @click="submitMove"
          >
            Move
          </VBtn>
        </VCardActions>
      </VCard>
    </VDialog>
  </VContainer>
</template>

<style scoped>
.pages-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

h1 {
  margin: 0;
  font-size: 24px;
  line-height: 32px;
}

.dialog-card {
  padding-top: 4px;
}

.dialog-body {
  display: grid;
  gap: 14px;
}

.move-page-title {
  overflow: hidden;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.content-row {
  height: calc(100vh - 130px);
}

.content-col {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.content-col > * {
  flex: 1;
  min-height: 0;
}

@media (max-width: 760px) {
  .pages-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .toolbar-actions {
    width: 100%;
    justify-content: flex-start;
  }
}
</style>
