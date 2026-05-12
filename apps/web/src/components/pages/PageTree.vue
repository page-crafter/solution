<script setup lang="ts">
import { computed, reactive, shallowRef, watch } from 'vue'
import type { PageMovePosition } from '../../api/pages'
import type { ConfluencePage } from '../../types/api'
import StatusChip from '../common/StatusChip.vue'

interface PageTreeNode {
  page: ConfluencePage
  depth: number
  childCount: number
  hasChildren: boolean
  continuationDepths: number[]
  previousSibling?: ConfluencePage
  nextSibling?: ConfluencePage
}

interface PageMoveIntent {
  page: ConfluencePage
  target?: ConfluencePage
  targetParentId?: string | null
  position: PageMovePosition
}

type DropIntent =
  | { kind: 'page', pageId: number, position: PageMovePosition }
  | { kind: 'root' }

const props = defineProps<{
  pages: ConfluencePage[]
  rootLabel: string
  selectedId?: number
}>()

const emit = defineEmits<{
  select: [page: ConfluencePage]
  createChild: [page: ConfluencePage]
  refresh: [page: ConfluencePage]
  move: [page: ConfluencePage]
  delete: [page: ConfluencePage]
  reorder: [intent: PageMoveIntent]
}>()

const filterQuery = shallowRef('')
const expandedIds = reactive(new Set<number>())
const rootExpanded = shallowRef(true)
const draggedPageId = shallowRef<number>()
const dropIntent = shallowRef<DropIntent>()
let expandTimer: number | undefined

const pageByConfluenceId = computed(() => {
  return new Map(props.pages.map((page) => [page.confluence_id, page]))
})

const pageById = computed(() => {
  return new Map(props.pages.map((page) => [page.id, page]))
})

const pagesByParentId = computed(() => {
  const groups = new Map<string | null, ConfluencePage[]>()
  for (const page of props.pages) {
    const parentId = normalizedParentId(page)
    const siblings = groups.get(parentId) ?? []
    siblings.push(page)
    groups.set(parentId, siblings)
  }
  for (const siblings of groups.values()) {
    siblings.sort(comparePages)
  }
  return groups
})

const rootPages = computed(() => pagesByParentId.value.get(null) ?? [])

const filterActive = computed(() => filterQuery.value.trim().length > 0)

const matchingConfluenceIds = computed(() => {
  if (!filterActive.value) return null
  const q = filterQuery.value.trim().toLowerCase()
  const matched = new Set<string>()
  for (const page of props.pages) {
    if (page.title.toLowerCase().includes(q)) {
      matched.add(page.confluence_id)
      let parentId = page.parent_confluence_id
      while (parentId && !matched.has(parentId)) {
        matched.add(parentId)
        parentId = pageByConfluenceId.value.get(parentId)?.parent_confluence_id ?? null
      }
    }
  }
  return matched
})

const showsSyntheticRoot = computed(() => {
  const normalizedRootLabel = normalizeTreeLabel(props.rootLabel)
  if (!normalizedRootLabel) return true
  return !rootPages.value.some((page) => normalizeTreeLabel(page.title) === normalizedRootLabel)
})

const visibleNodes = computed(() => {
  const nodes: PageTreeNode[] = []
  const matched = matchingConfluenceIds.value

  function appendNode(
    page: ConfluencePage,
    depth: number,
    siblings: ConfluencePage[],
    continuationDepths: number[],
  ): void {
    if (matched && !matched.has(page.confluence_id)) return
    const children = pagesByParentId.value.get(page.confluence_id) ?? []
    const visibleSiblings = matched ? siblings.filter((s) => matched.has(s.confluence_id)) : siblings
    const siblingIndex = visibleSiblings.findIndex((sibling) => sibling.id === page.id)
    const nextSibling = visibleSiblings[siblingIndex + 1]
    nodes.push({
      page,
      depth,
      childCount: children.length,
      hasChildren: children.length > 0,
      continuationDepths,
      previousSibling: visibleSiblings[siblingIndex - 1],
      nextSibling,
    })

    const expanded = filterActive.value || expandedIds.has(page.id)
    if (!expanded) return
    const childContinuationDepths = nextSibling
      ? [...continuationDepths, depth]
      : continuationDepths
    for (const child of children) {
      appendNode(child, depth + 1, children, childContinuationDepths)
    }
  }

  const roots = pagesByParentId.value.get(null) ?? []
  for (const page of roots) {
    appendNode(page, 0, roots, [])
  }
  return nodes
})

const displayedNodes = computed(() => {
  if (!showsSyntheticRoot.value) return visibleNodes.value
  return rootExpanded.value ? visibleNodes.value : []
})

function normalizeTreeLabel(label: string): string {
  return label.trim().toLowerCase()
}

function normalizedParentId(page: ConfluencePage): string | null {
  const parentId = page.parent_confluence_id ?? null
  return parentId && pageByConfluenceId.value.has(parentId) ? parentId : null
}

function comparePages(left: ConfluencePage, right: ConfluencePage): number {
  if (left.sort_order !== right.sort_order) {
    return left.sort_order - right.sort_order
  }
  return left.title.localeCompare(right.title)
}

function toggleNode(page: ConfluencePage): void {
  if (expandedIds.has(page.id)) {
    expandedIds.delete(page.id)
    return
  }
  expandedIds.add(page.id)
}

function isDescendant(page: ConfluencePage, ancestor: ConfluencePage): boolean {
  let parentId = page.parent_confluence_id ?? null
  while (parentId) {
    if (parentId === ancestor.confluence_id) return true
    parentId = pageByConfluenceId.value.get(parentId)?.parent_confluence_id ?? null
  }
  return false
}

function startDrag(event: DragEvent, page: ConfluencePage): void {
  draggedPageId.value = page.id
  event.dataTransfer?.setData('text/plain', String(page.id))
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
  }
}

function canDropOn(page: ConfluencePage): boolean {
  const draggedPage = draggedPageId.value ? pageById.value.get(draggedPageId.value) : undefined
  return Boolean(draggedPage && draggedPage.id !== page.id && !isDescendant(page, draggedPage))
}

function resolveDropPosition(event: DragEvent): PageMovePosition {
  const row = event.currentTarget as HTMLElement | null
  if (!row) return 'append'
  const rect = row.getBoundingClientRect()
  const offset = event.clientY - rect.top
  if (offset < rect.height * 0.28) return 'before'
  if (offset > rect.height * 0.72) return 'after'
  return 'append'
}

function scheduleExpand(node: PageTreeNode, position: PageMovePosition): void {
  if (expandTimer) window.clearTimeout(expandTimer)
  if (position !== 'append' || !node.hasChildren || expandedIds.has(node.page.id)) return
  expandTimer = window.setTimeout(() => {
    expandedIds.add(node.page.id)
  }, 550)
}

function markDropTarget(event: DragEvent, node: PageTreeNode): void {
  if (!canDropOn(node.page)) {
    dropIntent.value = undefined
    return
  }
  const position = resolveDropPosition(event)
  dropIntent.value = { kind: 'page', pageId: node.page.id, position }
  scheduleExpand(node, position)
}

function markRootDropTarget(): void {
  if (!draggedPageId.value) {
    dropIntent.value = undefined
    return
  }
  dropIntent.value = { kind: 'root' }
}

function clearDropIfLeaving(event: DragEvent): void {
  const row = event.currentTarget as HTMLElement | null
  const relatedTarget = event.relatedTarget as Node | null
  if (row?.contains(relatedTarget)) return
  dropIntent.value = undefined
}

function clearDrag(): void {
  if (expandTimer) window.clearTimeout(expandTimer)
  expandTimer = undefined
  draggedPageId.value = undefined
  dropIntent.value = undefined
}

function dropOn(node: PageTreeNode): void {
  const draggedPage = draggedPageId.value ? pageById.value.get(draggedPageId.value) : undefined
  if (!draggedPage || !canDropOn(node.page)) {
    clearDrag()
    return
  }
  const pageDropIntent = dropIntent.value?.kind === 'page' ? dropIntent.value : undefined
  const position = pageDropIntent?.pageId === node.page.id
    ? pageDropIntent.position
    : 'append'
  emit('reorder', { page: draggedPage, target: node.page, position })
  if (position === 'append') {
    expandedIds.add(node.page.id)
  }
  clearDrag()
}

function dropOnRoot(): void {
  const draggedPage = draggedPageId.value ? pageById.value.get(draggedPageId.value) : undefined
  if (!draggedPage) {
    clearDrag()
    return
  }
  emit('reorder', { page: draggedPage, targetParentId: null, position: 'append' })
  rootExpanded.value = true
  clearDrag()
}

function isDropPosition(node: PageTreeNode, position: PageMovePosition): boolean {
  return (
    dropIntent.value?.kind === 'page'
    && dropIntent.value.pageId === node.page.id
    && dropIntent.value.position === position
  )
}

function isRootDropTarget(): boolean {
  return dropIntent.value?.kind === 'root'
}

function isMergedRootPage(page: ConfluencePage): boolean {
  return (
    !showsSyntheticRoot.value
    && normalizedParentId(page) === null
    && normalizeTreeLabel(page.title) === normalizeTreeLabel(props.rootLabel)
  )
}

function nodeIcon(node: PageTreeNode): string {
  if (isMergedRootPage(node.page)) return 'mdi-folder-home-outline'
  return node.hasChildren ? 'mdi-file-tree-outline' : 'mdi-file-document-outline'
}

function nodeIconColor(node: PageTreeNode): string {
  return isMergedRootPage(node.page) ? 'primary' : 'secondary'
}

function moveBefore(node: PageTreeNode): void {
  if (!node.previousSibling) return
  emit('reorder', { page: node.page, target: node.previousSibling, position: 'before' })
}

function moveAfter(node: PageTreeNode): void {
  if (!node.nextSibling) return
  emit('reorder', { page: node.page, target: node.nextSibling, position: 'after' })
}

function hasVisibleChildren(node: PageTreeNode): boolean {
  return node.hasChildren && expandedIds.has(node.page.id)
}

function siblingLineLeft(depth: number): number {
  return Math.max(0, depth - 1) * 34 + 22
}

function continuationStyle(depth: number): { left: string } {
  return {
    left: `${siblingLineLeft(depth)}px`,
  }
}

function rowStyle(depth: number): {
  paddingLeft: string
  '--tree-branch-left': string
  '--tree-branch-width': string
  '--tree-child-tail-left': string
} {
  const indent = depth * 34
  const branchLeft = siblingLineLeft(depth)
  const branchWidth = Math.max(0, indent + 8 - branchLeft)
  return {
    paddingLeft: `${indent + 8}px`,
    '--tree-branch-left': `${branchLeft}px`,
    '--tree-branch-width': `${branchWidth}px`,
    '--tree-child-tail-left': `${indent + 22}px`,
  }
}

watch(
  () => props.pages,
  (pages) => {
    const parentIds = new Set(pages.map((page) => page.parent_confluence_id).filter(Boolean))
    for (const page of pages) {
      if (parentIds.has(page.confluence_id)) {
        expandedIds.add(page.id)
      }
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="page-tree surface-border">
    <div class="tree-search">
      <VIcon icon="mdi-magnify" size="16" class="tree-search-icon" />
      <input
        v-model="filterQuery"
        class="tree-search-input"
        placeholder="Filter pages…"
        type="search"
      />
      <button v-if="filterQuery" class="tree-search-clear" aria-label="Clear filter" @click="filterQuery = ''">
        <VIcon icon="mdi-close" size="14" />
      </button>
    </div>
    <VDivider />
    <div class="tree-list" role="tree">
      <div
        v-if="showsSyntheticRoot"
        class="tree-row tree-row--root"
        :class="{ 'tree-row--drop-inside': isRootDropTarget() }"
        role="treeitem"
        @dragover.prevent="markRootDropTarget"
        @dragleave="clearDropIfLeaving"
        @drop.prevent="dropOnRoot"
      >
        <VBtn
          :icon="rootExpanded ? 'mdi-chevron-down' : 'mdi-chevron-right'"
          size="x-small"
          variant="text"
          class="toggle-button"
          @click.stop="rootExpanded = !rootExpanded"
        />
        <VIcon icon="mdi-folder-home-outline" size="19" color="primary" />
        <div class="tree-title">
          <span class="tree-title-text">{{ rootLabel }}</span>
          <span class="tree-meta">{{ pages.length }} pages</span>
        </div>
      </div>

      <div v-if="showsSyntheticRoot && rootExpanded && pages.length === 0" class="empty-state">
        <VIcon icon="mdi-file-tree-outline" size="36" color="secondary" />
        <div class="text-body-2 muted-text">No synced pages.</div>
      </div>

      <div v-if="filterActive && displayedNodes.length === 0 && pages.length > 0" class="empty-state">
        <VIcon icon="mdi-file-search-outline" size="36" color="secondary" />
        <div class="text-body-2 muted-text">No pages match "{{ filterQuery }}"</div>
      </div>

      <div
        v-for="node in displayedNodes"
        :key="node.page.id"
        class="tree-row"
        :class="{
          'tree-row--active': node.page.id === selectedId,
          'tree-row--drop-before': isDropPosition(node, 'before'),
          'tree-row--drop-inside': isDropPosition(node, 'append'),
          'tree-row--drop-after': isDropPosition(node, 'after'),
        }"
        :style="rowStyle(node.depth)"
        role="treeitem"
        draggable="true"
        @click="emit('select', node.page)"
        @dragstart="startDrag($event, node.page)"
        @dragover.prevent="markDropTarget($event, node)"
        @dragleave="clearDropIfLeaving"
        @drop.prevent="dropOn(node)"
        @dragend="clearDrag"
      >
        <span
          v-for="continuationDepth in node.continuationDepths"
          :key="continuationDepth"
          class="tree-continuation"
          :style="continuationStyle(continuationDepth)"
        />
        <span
          v-if="node.depth > 0"
          class="tree-branch"
          :class="{ 'tree-branch--continues': node.nextSibling }"
        />
        <span v-if="hasVisibleChildren(node)" class="tree-child-tail" />

        <VBtn
          v-if="node.hasChildren"
          :icon="expandedIds.has(node.page.id) ? 'mdi-chevron-down' : 'mdi-chevron-right'"
          size="x-small"
          variant="text"
          class="toggle-button"
          @click.stop="toggleNode(node.page)"
        />
        <span v-else class="toggle-spacer" />

        <VIcon
          :icon="nodeIcon(node)"
          size="19"
          :color="nodeIconColor(node)"
        />

        <div class="tree-title">
          <span class="tree-title-text">{{ node.page.title }}</span>
          <span class="tree-meta">
            v{{ node.page.version_number }}
            <template v-if="node.childCount">· {{ node.childCount }} subpages</template>
          </span>
        </div>

        <VChip v-if="node.page.is_placeholder" size="x-small" color="info" variant="tonal">
          Empty
        </VChip>
        <StatusChip :state="node.page.draft_state" />

        <div class="tree-actions" @click.stop>
          <VTooltip text="Move up" location="top">
            <template #activator="{ props: tooltipProps }">
              <VBtn
                v-bind="tooltipProps"
                icon="mdi-arrow-up"
                size="x-small"
                variant="text"
                :disabled="!node.previousSibling"
                @click="moveBefore(node)"
              />
            </template>
          </VTooltip>

          <VTooltip text="Move down" location="top">
            <template #activator="{ props: tooltipProps }">
              <VBtn
                v-bind="tooltipProps"
                icon="mdi-arrow-down"
                size="x-small"
                variant="text"
                :disabled="!node.nextSibling"
                @click="moveAfter(node)"
              />
            </template>
          </VTooltip>

          <VMenu location="bottom end">
            <template #activator="{ props: menuProps }">
              <VBtn v-bind="menuProps" icon="mdi-dots-vertical" size="x-small" variant="text" />
            </template>
            <VList density="compact">
              <VListItem
                title="New subpage"
                prepend-icon="mdi-file-plus-outline"
                @click="emit('createChild', node.page)"
              />
              <VListItem
                title="Refresh"
                prepend-icon="mdi-refresh"
                @click="emit('refresh', node.page)"
              />
              <VListItem
                title="Move"
                prepend-icon="mdi-file-move-outline"
                @click="emit('move', node.page)"
              />
              <VListItem
                title="Delete"
                prepend-icon="mdi-delete-outline"
                base-color="error"
                @click="emit('delete', node.page)"
              />
            </VList>
          </VMenu>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-tree {
  height: 100%;
  display: flex;
  flex-direction: column;
  border-radius: 8px;
  background: #ffffff;
}

.tree-search {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  flex-shrink: 0;
}

.tree-search-icon {
  color: #626f86;
  flex-shrink: 0;
}

.tree-search-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 13px;
  color: inherit;
  min-width: 0;
}

.tree-search-input::placeholder {
  color: #8993a5;
}

.tree-search-input::-webkit-search-cancel-button {
  display: none;
}

.tree-search-clear {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border: none;
  border-radius: 50%;
  background: #dfe1e6;
  color: #44546f;
  cursor: pointer;
  padding: 0;
  flex-shrink: 0;
}

.tree-search-clear:hover {
  background: #c1c7d0;
}

.tree-list {
  flex: 1;
  overflow: auto;
  display: grid;
  align-content: start;
  padding: 6px;
}

.tree-row {
  position: relative;
  display: grid;
  grid-template-columns: 28px 22px minmax(160px, 1fr) auto auto auto;
  gap: 8px;
  align-items: center;
  min-height: 42px;
  border: 1px solid transparent;
  border-radius: 6px;
  cursor: pointer;
}

.tree-row:hover {
  background: #f4f5f7;
}

.tree-row--root {
  margin-bottom: 4px;
  background: #f7f8fa;
  font-weight: 700;
}

.tree-row--root .tree-title {
  grid-column: 3 / -1;
}

.tree-row--active {
  border-color: #85b8ff;
  background: #f1f7ff;
}

.tree-row--drop-inside {
  border-color: #0c66e4;
  background: #e9f2ff;
}

.tree-row--drop-before::before,
.tree-row--drop-after::after {
  position: absolute;
  right: 8px;
  left: 8px;
  height: 2px;
  border-radius: 2px;
  background: #0c66e4;
  content: "";
}

.tree-row--drop-before::before {
  top: -2px;
}

.tree-row--drop-after::after {
  bottom: -2px;
}

.tree-row--drop-inside .tree-title-text {
  color: #0c66e4;
}

.tree-continuation {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: #d8dee8;
  pointer-events: none;
}

.tree-branch {
  position: absolute;
  top: 0;
  bottom: 0;
  left: var(--tree-branch-left);
  width: var(--tree-branch-width);
  pointer-events: none;
}

.tree-branch::before {
  position: absolute;
  top: 0;
  bottom: 50%;
  left: 0;
  width: 1px;
  background: #d8dee8;
  content: "";
}

.tree-branch--continues::before {
  bottom: 0;
}

.tree-branch::after {
  position: absolute;
  top: 50%;
  right: 0;
  left: 0;
  height: 1px;
  background: #d8dee8;
  content: "";
}

.tree-child-tail {
  position: absolute;
  top: calc(50% + 12px);
  bottom: 0;
  left: var(--tree-child-tail-left);
  width: 1px;
  background: #d8dee8;
  pointer-events: none;
}

.toggle-button,
.toggle-spacer {
  width: 24px;
  height: 24px;
}

.toggle-spacer {
  display: block;
}

.tree-title {
  display: flex;
  gap: 8px;
  align-items: baseline;
  min-width: 0;
}

.tree-title-text {
  overflow: hidden;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tree-meta {
  flex: 0 0 auto;
  color: #626f86;
  font-size: 12px;
}

.tree-actions {
  display: flex;
  gap: 2px;
  justify-content: flex-end;
  opacity: 0;
  transition: opacity 0.1s;
}

.tree-row:hover .tree-actions,
.tree-row--active .tree-actions {
  opacity: 1;
}

.empty-state {
  display: grid;
  gap: 12px;
  min-height: 360px;
  place-items: center;
  align-content: center;
  text-align: center;
}

@media (max-width: 760px) {
  .tree-row {
    grid-template-columns: 28px 22px minmax(110px, 1fr) auto;
  }

  .tree-row :deep(.v-chip) {
    display: none;
  }
}
</style>
