<script setup lang="ts">
import { Compartment, EditorState } from '@codemirror/state'
import { EditorView } from '@codemirror/view'
import { markdown } from '@codemirror/lang-markdown'
import { basicSetup } from 'codemirror'
import { computed, onBeforeUnmount, onMounted, shallowRef, useTemplateRef, watch } from 'vue'

const model = defineModel<string>({ default: '' })

const props = defineProps<{
  disabled?: boolean
}>()

const editorHost = useTemplateRef<HTMLDivElement>('editorHost')
const editorView = shallowRef<EditorView>()
const editableCompartment = new Compartment()
const canEdit = computed(() => !props.disabled)

function syncExternalValue(value: string): void {
  const view = editorView.value
  if (!view) return
  const currentValue = view.state.doc.toString()
  if (currentValue === value) return
  view.dispatch({
    changes: { from: 0, to: view.state.doc.length, insert: value },
  })
}

function insertMarkdown(prefix: string, suffix = ''): void {
  const view = editorView.value
  if (!view || !canEdit.value) return
  const selection = view.state.selection.main
  const selectedText = view.state.sliceDoc(selection.from, selection.to)
  view.dispatch({
    changes: {
      from: selection.from,
      to: selection.to,
      insert: `${prefix}${selectedText || 'text'}${suffix}`,
    },
    selection: {
      anchor: selection.from + prefix.length,
      head: selection.from + prefix.length + (selectedText || 'text').length,
    },
  })
  view.focus()
}

function insertLinePrefix(prefix: string): void {
  const view = editorView.value
  if (!view || !canEdit.value) return
  const selection = view.state.selection.main
  const line = view.state.doc.lineAt(selection.from)
  view.dispatch({
    changes: { from: line.from, insert: prefix },
    selection: { anchor: selection.from + prefix.length, head: selection.to + prefix.length },
  })
  view.focus()
}

function insertBlock(template: string, cursorOffset: number): void {
  const view = editorView.value
  if (!view || !canEdit.value) return
  const selection = view.state.selection.main
  view.dispatch({
    changes: { from: selection.from, to: selection.to, insert: template },
    selection: { anchor: selection.from + cursorOffset },
  })
  view.focus()
}

onMounted(() => {
  if (!editorHost.value) return
  editorView.value = new EditorView({
    parent: editorHost.value,
    state: EditorState.create({
      doc: model.value,
      extensions: [
        basicSetup,
        markdown(),
        EditorView.lineWrapping,
        editableCompartment.of(EditorView.editable.of(canEdit.value)),
        EditorView.updateListener.of((update) => {
          if (!update.docChanged) return
          model.value = update.state.doc.toString()
        }),
      ],
    }),
  })
})

watch(model, syncExternalValue)

watch(canEdit, (nextCanEdit) => {
  editorView.value?.dispatch({
    effects: editableCompartment.reconfigure(EditorView.editable.of(nextCanEdit)),
  })
})

onBeforeUnmount(() => {
  editorView.value?.destroy()
})
</script>

<template>
  <div class="markdown-editor">
    <div class="markdown-editor__toolbar" aria-label="Markdown tools">
      <VBtnGroup variant="text" density="compact" divided>
        <VTooltip location="bottom" text="Heading 1">
          <template #activator="{ props: tp }">
            <VBtn v-bind="tp" size="small" :disabled="!canEdit" aria-label="Heading 1" @click="insertLinePrefix('# ')">
              <VIcon icon="mdi-format-header-1" size="18" />
            </VBtn>
          </template>
        </VTooltip>
        <VTooltip location="bottom" text="Heading 2">
          <template #activator="{ props: tp }">
            <VBtn v-bind="tp" size="small" :disabled="!canEdit" aria-label="Heading 2" @click="insertLinePrefix('## ')">
              <VIcon icon="mdi-format-header-2" size="18" />
            </VBtn>
          </template>
        </VTooltip>
        <VTooltip location="bottom" text="Heading 3">
          <template #activator="{ props: tp }">
            <VBtn v-bind="tp" size="small" :disabled="!canEdit" aria-label="Heading 3" @click="insertLinePrefix('### ')">
              <VIcon icon="mdi-format-header-3" size="18" />
            </VBtn>
          </template>
        </VTooltip>
      </VBtnGroup>

      <VDivider vertical class="toolbar-group-sep" />

      <VBtnGroup variant="text" density="compact" divided>
        <VTooltip location="bottom" text="Bold (Ctrl+B)">
          <template #activator="{ props: tp }">
            <VBtn v-bind="tp" size="small" :disabled="!canEdit" aria-label="Bold" @click="insertMarkdown('**', '**')">
              <VIcon icon="mdi-format-bold" size="18" />
            </VBtn>
          </template>
        </VTooltip>
        <VTooltip location="bottom" text="Italic (Ctrl+I)">
          <template #activator="{ props: tp }">
            <VBtn v-bind="tp" size="small" :disabled="!canEdit" aria-label="Italic" @click="insertMarkdown('_', '_')">
              <VIcon icon="mdi-format-italic" size="18" />
            </VBtn>
          </template>
        </VTooltip>
        <VTooltip location="bottom" text="Strikethrough">
          <template #activator="{ props: tp }">
            <VBtn v-bind="tp" size="small" :disabled="!canEdit" aria-label="Strikethrough" @click="insertMarkdown('~~', '~~')">
              <VIcon icon="mdi-format-strikethrough" size="18" />
            </VBtn>
          </template>
        </VTooltip>
      </VBtnGroup>

      <VDivider vertical class="toolbar-group-sep" />

      <VBtnGroup variant="text" density="compact" divided>
        <VTooltip location="bottom" text="Bulleted list">
          <template #activator="{ props: tp }">
            <VBtn v-bind="tp" size="small" :disabled="!canEdit" aria-label="Bulleted list" @click="insertLinePrefix('- ')">
              <VIcon icon="mdi-format-list-bulleted" size="18" />
            </VBtn>
          </template>
        </VTooltip>
        <VTooltip location="bottom" text="Numbered list">
          <template #activator="{ props: tp }">
            <VBtn v-bind="tp" size="small" :disabled="!canEdit" aria-label="Numbered list" @click="insertLinePrefix('1. ')">
              <VIcon icon="mdi-format-list-numbered" size="18" />
            </VBtn>
          </template>
        </VTooltip>
        <VTooltip location="bottom" text="Block quote">
          <template #activator="{ props: tp }">
            <VBtn v-bind="tp" size="small" :disabled="!canEdit" aria-label="Quote" @click="insertLinePrefix('> ')">
              <VIcon icon="mdi-format-quote-open" size="18" />
            </VBtn>
          </template>
        </VTooltip>
      </VBtnGroup>

      <VDivider vertical class="toolbar-group-sep" />

      <VBtnGroup variant="text" density="compact" divided>
        <VTooltip location="bottom" text="Inline code">
          <template #activator="{ props: tp }">
            <VBtn v-bind="tp" size="small" :disabled="!canEdit" aria-label="Inline code" @click="insertMarkdown('`', '`')">
              <VIcon icon="mdi-code-tags" size="18" />
            </VBtn>
          </template>
        </VTooltip>
        <VTooltip location="bottom" text="Code block">
          <template #activator="{ props: tp }">
            <VBtn v-bind="tp" size="small" :disabled="!canEdit" aria-label="Code block" @click="insertBlock('```\n\n```', 4)">
              <VIcon icon="mdi-code-block-tags" size="18" />
            </VBtn>
          </template>
        </VTooltip>
        <VTooltip location="bottom" text="Link">
          <template #activator="{ props: tp }">
            <VBtn v-bind="tp" size="small" :disabled="!canEdit" aria-label="Link" @click="insertMarkdown('[', '](url)')">
              <VIcon icon="mdi-link-variant" size="18" />
            </VBtn>
          </template>
        </VTooltip>
        <VTooltip location="bottom" text="Horizontal rule">
          <template #activator="{ props: tp }">
            <VBtn v-bind="tp" size="small" :disabled="!canEdit" aria-label="Horizontal rule" @click="insertBlock('\n---\n', 5)">
              <VIcon icon="mdi-minus" size="18" />
            </VBtn>
          </template>
        </VTooltip>
      </VBtnGroup>
    </div>
    <div ref="editorHost" class="markdown-editor__host" />
  </div>
</template>

<style scoped>
.markdown-editor {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  min-height: 0;
  border: 1px solid #dfe1e6;
  border-radius: 8px;
  overflow: hidden;
  background: #ffffff;
}

.markdown-editor__toolbar {
  display: flex;
  gap: 4px;
  align-items: center;
  min-height: 36px;
  padding: 3px 8px;
  border-bottom: 1px solid #c8d0e0;
  background: #f7f8fa;
}

.toolbar-group-sep {
  height: 18px;
  align-self: center;
  margin: 0 2px;
  flex-shrink: 0;
}

.markdown-editor__host {
  min-height: 0;
}

.markdown-editor__host :deep(.cm-editor) {
  height: 100%;
  min-height: 520px;
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
  font-size: 13px;
}

.markdown-editor__host :deep(.cm-scroller) {
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
}
</style>
