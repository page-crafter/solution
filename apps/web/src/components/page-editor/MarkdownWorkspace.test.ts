import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { vuetify } from '../../plugins/vuetify'
import type { PageDetail, PageEditRun, PageProposal } from '../../types/api'
import MarkdownWorkspace from './MarkdownWorkspace.vue'

vi.mock('@git-diff-view/vue', () => ({
  DiffModeEnum: { Unified: 'unified' },
  DiffView: {
    name: 'DiffView',
    props: ['data'],
    template: '<div data-testid="diff-view">Diff view</div>',
  },
}))

function makePage(overrides: Partial<PageDetail> = {}): PageDetail {
  return {
    id: 1,
    confluence_id: '123',
    space_key: 'DOC',
    space_name: 'Documentation',
    parent_confluence_id: null,
    sort_order: 1,
    title: 'Setup Guide',
    status: 'current',
    version_number: 7,
    web_url: null,
    edit_url: null,
    tiny_url: null,
    is_placeholder: false,
    draft_state: 'Published',
    last_synced_at: '2026-05-10T10:00:00Z',
    source_storage_xhtml: '<p>Current page</p>',
    extracted_text: 'Current page text',
    ...overrides,
  }
}

function makeRun(overrides: Partial<PageEditRun> = {}): PageEditRun {
  return {
    id: 'run-1',
    page_id: 1,
    instruction: 'Update docs',
    status: 'preview_ready',
    draft_status: 'Preview ready',
    preview_status: 'ready',
    source_version: 7,
    markdown_draft: '# Draft',
    generated_storage_xhtml: '<h1>Draft</h1><p>Body</p>',
    preview_html: '<p>Preview</p>',
    diff_text: 'diff',
    created_at: '2026-05-10T10:00:00Z',
    updated_at: '2026-05-10T10:00:00Z',
    ...overrides,
  }
}

function makeProposal(overrides: Partial<PageProposal> = {}): PageProposal {
  return {
    id: 'proposal-1',
    page_id: 1,
    run_id: 'run-1',
    instruction: 'Update docs',
    base_markdown: '# Draft',
    base_source: 'draft',
    status: 'ready',
    proposed_markdown: '# Proposed draft',
    diff_text: 'proposal diff',
    summary: 'Prepared an update.',
    error_message: null,
    created_at: '2026-05-10T10:00:00Z',
    updated_at: '2026-05-10T10:00:00Z',
    ...overrides,
  }
}

async function mountWorkspace(
  props: Partial<InstanceType<typeof MarkdownWorkspace>['$props']> = {},
): Promise<VueWrapper> {
  const run = props.run as PageEditRun | undefined
  const wrapper = mount(MarkdownWorkspace, {
    props: {
      page: makePage(),
      modelValue: run?.markdown_draft ?? '',
      ...props,
    },
    global: {
      plugins: [vuetify],
      stubs: {
        MarkdownEditor: {
          props: ['modelValue'],
          emits: ['update:modelValue'],
          template: '<textarea data-testid="markdown-editor" :value="modelValue" />',
        },
      },
    },
  })

  await flushPromises()
  await nextTick()
  return wrapper
}

async function clickMode(wrapper: VueWrapper, label: string): Promise<void> {
  const button = wrapper.findAll('button').find((candidate) => candidate.text().includes(label))
  expect(button).toBeTruthy()
  await button?.trigger('click')
  await flushPromises()
  await nextTick()
}

describe('MarkdownWorkspace', () => {
  it('shows generated Storage XHTML in a formatted text view', async () => {
    const wrapper = await mountWorkspace({
      run: makeRun({
        generated_storage_xhtml: '<h1>Draft</h1><ac:structured-macro ac:name="toc" />',
      }),
    })

    await clickMode(wrapper, 'XHTML')

    expect(wrapper.text()).toContain('Generated XHTML')
    expect(wrapper.text()).toContain('<h1>Draft</h1>')
    expect(wrapper.text()).toContain('<ac:structured-macro ac:name="toc"/>')
  })

  it('uses the Confluence-rendered preview iframe when it is available', async () => {
    const wrapper = await mountWorkspace({ run: makeRun() })

    await clickMode(wrapper, 'Preview')

    const iframe = wrapper.get('iframe[title="Confluence rendered preview"]')
    expect(iframe.attributes('srcdoc')).toBe('<p>Preview</p>')
  })

  it('falls back to sanitized local Markdown rendering before preview is ready', async () => {
    const wrapper = await mountWorkspace({
      modelValue: '# Local draft\n<script>alert("x")</script>',
      run: makeRun({
        markdown_draft: '# Local draft\n<script>alert("x")</script>',
        generated_storage_xhtml: null,
        preview_html: null,
        diff_text: null,
      }),
    })

    await clickMode(wrapper, 'Preview')

    expect(wrapper.find('iframe[title="Confluence rendered preview"]').exists()).toBe(false)
    expect(wrapper.find('script').exists()).toBe(false)
    expect(wrapper.html()).toContain('<h1>Local draft</h1>')
  })

  it('keeps pending proposal diffs hidden until the proposal is ready', async () => {
    const wrapper = await mountWorkspace({
      run: makeRun({ diff_text: 'run diff' }),
      proposal: makeProposal({ status: 'generating', diff_text: 'proposal diff' }),
    })

    await clickMode(wrapper, 'Changes')

    expect(wrapper.getComponent({ name: 'DiffView' }).props('data')).toMatchObject({
      newFile: { fileName: 'generated-storage.xhtml' },
      hunks: ['run diff'],
    })

    await wrapper.setProps({
      proposal: makeProposal({ status: 'ready', diff_text: 'proposal diff' }),
    })
    await flushPromises()
    await nextTick()

    expect(wrapper.getComponent({ name: 'DiffView' }).props('data')).toMatchObject({
      newFile: { fileName: 'proposed-draft.md' },
      hunks: ['proposal diff'],
    })
  })
})
