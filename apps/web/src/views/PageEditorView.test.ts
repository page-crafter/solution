import { flushPromises, mount, type Stubs, type VueWrapper } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { fetchPage, fetchPages } from '../api/pages'
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
  restoreDraftVersion,
  saveDraft,
} from '../api/pageEditor'
import EditChatPanel from '../components/page-editor/EditChatPanel.vue'
import { vuetify } from '../plugins/vuetify'
import type {
  ApplyProposalResponse,
  ConfluencePage,
  DraftVersion,
  PageDetail,
  PageProposal,
  PageEditRun,
} from '../types/api'
import PageEditorView from './PageEditorView.vue'

const routeMock = vi.hoisted(() => ({
  query: {} as Record<string, string>,
}))
const routerPushMock = vi.hoisted(() => vi.fn())

vi.mock('vue-router', () => ({
  useRoute: () => routeMock,
  useRouter: () => ({ push: routerPushMock }),
}))

vi.mock('../api/pages', () => ({
  fetchPage: vi.fn(),
  fetchPages: vi.fn(),
}))

vi.mock('../api/pageEditor', () => ({
  applyProposal: vi.fn(),
  createProposal: vi.fn(),
  createManualDraftRun: vi.fn(),
  createPageEditRun: vi.fn(),
  fetchActivePageEditRun: vi.fn(),
  fetchDraftVersions: vi.fn(),
  fetchProposal: vi.fn(),
  fetchPageEditRun: vi.fn(),
  publishRun: vi.fn(),
  rejectProposal: vi.fn(),
  restoreDraftVersion: vi.fn(),
  saveDraft: vi.fn(),
}))

function makePage(overrides: Partial<ConfluencePage> = {}): ConfluencePage {
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
    ...overrides,
  }
}

function makePageDetail(overrides: Partial<PageDetail> = {}): PageDetail {
  return {
    ...makePage(overrides),
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
    generated_storage_xhtml: '<p>Draft</p>',
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
    run_id: null,
    instruction: 'Update the setup',
    base_markdown: 'Current page text',
    base_source: 'page',
    status: 'ready',
    proposed_markdown: '# Updated draft',
    diff_text: 'diff',
    summary: 'Prepared an update.',
    error_message: null,
    created_at: '2026-05-10T10:00:00Z',
    updated_at: '2026-05-10T10:00:00Z',
    ...overrides,
  }
}

function makeDraftVersion(overrides: Partial<DraftVersion> = {}): DraftVersion {
  return {
    id: 1,
    run_id: 'run-1',
    version_number: 1,
    markdown_draft: '# Draft',
    change_source: 'manual',
    actor: 'editor@example.com',
    proposal_id: null,
    restored_from_version_id: null,
    created_at: '2026-05-10T10:00:00Z',
    ...overrides,
  }
}

async function mountPageEditorView(options: { realEditChat?: boolean } = {}): Promise<VueWrapper> {
  const editChatStub = {
    name: 'EditChatPanel',
    props: [
      'modelValue',
      'messages',
      'proposal',
      'busy',
      'busyLabel',
      'disabled',
      'applyingProposal',
      'rejectingProposal',
    ],
    emits: ['applyProposal', 'rejectProposal', 'submit', 'update:modelValue'],
    template: `
      <div data-testid="edit-chat">
        <span data-testid="message-count">{{ messages.length }}</span>
        <span v-if="busy" data-testid="busy-label">{{ busyLabel }}</span>
        <span
          v-for="message in messages"
          :key="message.id"
          data-testid="chat-message"
        >
          {{ message.content }}
        </span>
        <div v-if="proposal?.status === 'ready'" data-testid="proposal-decision-actions">
          <button data-testid="reject-proposal-button" @click="$emit('rejectProposal')">Reject</button>
          <button data-testid="apply-proposal-button" @click="$emit('applyProposal')">Apply</button>
        </div>
        <button
          data-testid="send-edit-request-button"
          :disabled="disabled || busy || proposal?.status === 'ready'"
          @click="$emit('update:modelValue', 'Update docs'); $emit('submit')"
        >
          Send
        </button>
      </div>
    `,
  }

  const stubs: Stubs = {
    ActionValidationDialog: {
      props: ['modelValue', 'message'],
      emits: ['confirm'],
      template: `
        <div v-if="modelValue" data-testid="publish-dialog">
          <span>{{ message }}</span>
          <button data-testid="confirm-publish" @click="$emit('confirm')">Confirm</button>
        </div>
      `,
    },
    MarkdownWorkspace: {
      name: 'MarkdownWorkspace',
      props: ['modelValue', 'page', 'run', 'proposal', 'draftVersions'],
      emits: ['restoreDraftVersion', 'saveDraft', 'update:modelValue'],
      template: `
        <div data-testid="markdown-workspace">
          <span data-testid="workspace-page">{{ page?.extracted_text }}</span>
          <span data-testid="workspace-draft">{{ modelValue }}</span>
          <span data-testid="workspace-proposal">{{ proposal?.status }}</span>
          <span data-testid="draft-version-count">{{ draftVersions?.length ?? 0 }}</span>
          <button data-testid="restore-draft-version-button" @click="$emit('restoreDraftVersion', 1)">Restore</button>
          <button data-testid="save-draft-button" @click="$emit('saveDraft')">Save</button>
        </div>
      `,
    },
    PageEditorPagePicker: {
      props: ['modelValue', 'pages'],
      emits: ['select', 'update:modelValue'],
      template: `
        <div data-testid="page-editor-picker">
          <button
            data-testid="choose-page-button"
            @click="$emit('update:modelValue', 1); $emit('select', 1)"
          >
            Choose page
          </button>
        </div>
      `,
    },
    StatusChip: true,
  }

  if (!options.realEditChat) {
    stubs.EditChatPanel = editChatStub
  }

  const wrapper = mount(PageEditorView, {
    global: {
      plugins: [vuetify],
      stubs,
    },
  })

  await flushPromises()
  await nextTick()
  return wrapper
}

async function clickByTestId(wrapper: VueWrapper, testId: string): Promise<void> {
  await wrapper.get(`[data-testid="${testId}"]`).trigger('click')
  await flushPromises()
  await nextTick()
}

describe('PageEditorView', () => {
  beforeEach(() => {
    vi.stubGlobal('ResizeObserver', class ResizeObserver {
      observe(): void {}
      unobserve(): void {}
      disconnect(): void {}
    })
    routeMock.query = { pageId: '1' }
    vi.mocked(fetchPages).mockResolvedValue([makePage()])
    vi.mocked(fetchPage).mockResolvedValue(makePageDetail())
    vi.mocked(fetchActivePageEditRun).mockResolvedValue(null)
    vi.mocked(fetchDraftVersions).mockResolvedValue([])
    vi.mocked(fetchProposal).mockResolvedValue(makeProposal())
    vi.mocked(fetchPageEditRun).mockResolvedValue(makeRun())
    vi.mocked(createPageEditRun).mockResolvedValue(makeRun({
      status: 'queued',
      draft_status: 'Draft in progress',
      preview_status: 'not_started',
      markdown_draft: null,
      generated_storage_xhtml: null,
      preview_html: null,
      diff_text: null,
    }))
    vi.mocked(createProposal).mockResolvedValue(makeProposal({ status: 'queued' }))
    vi.mocked(createManualDraftRun).mockResolvedValue(makeRun({
      status: 'converting',
      draft_status: 'Draft generated',
      preview_status: 'rendering',
      markdown_draft: 'Current page text',
      generated_storage_xhtml: null,
      preview_html: null,
      diff_text: null,
    }))
    vi.mocked(rejectProposal).mockResolvedValue(makeProposal({ status: 'rejected' }))
    vi.mocked(saveDraft).mockResolvedValue(makeRun())
    vi.mocked(publishRun).mockResolvedValue(makeRun({ status: 'publishing' }))
    vi.mocked(restoreDraftVersion).mockResolvedValue(makeRun({ markdown_draft: '# Restored draft' }))
    const appliedResponse: ApplyProposalResponse = {
      proposal: makeProposal({ status: 'applied', run_id: 'run-1' }),
      run: makeRun({ markdown_draft: '# Updated draft' }),
    }
    vi.mocked(applyProposal).mockResolvedValue(appliedResponse)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllMocks()
    vi.unstubAllGlobals()
  })

  it('shows the page picker without loading a page when no page id is in the URL', async () => {
    routeMock.query = {}
    const wrapper = await mountPageEditorView()

    expect(wrapper.find('[data-testid="page-editor-picker"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="markdown-workspace"]').exists()).toBe(false)
    expect(fetchPage).not.toHaveBeenCalled()
    expect(fetchActivePageEditRun).not.toHaveBeenCalled()

    wrapper.unmount()
  })

  it('navigates to the selected page from the picker', async () => {
    routeMock.query = {}
    const wrapper = await mountPageEditorView()

    await clickByTestId(wrapper, 'choose-page-button')

    expect(routerPushMock).toHaveBeenCalledWith({ path: '/editor', query: { pageId: '1' } })

    wrapper.unmount()
  })

  it('loads the current page into the Markdown editor without creating a run', async () => {
    const wrapper = await mountPageEditorView()

    expect(fetchPage).toHaveBeenCalledWith(1)
    expect(fetchActivePageEditRun).toHaveBeenCalledWith(1)
    expect(createPageEditRun).not.toHaveBeenCalled()
    expect(createManualDraftRun).not.toHaveBeenCalled()
    expect(createProposal).not.toHaveBeenCalled()
    expect(saveDraft).not.toHaveBeenCalled()
    expect(wrapper.get('[data-testid="workspace-page"]').text()).toBe('Current page text')
    expect(wrapper.get('[data-testid="workspace-draft"]').text()).toBe('Current page text')

    wrapper.unmount()
  })

  it('creates a manual draft run from the default Markdown on first save', async () => {
    const wrapper = await mountPageEditorView()

    await clickByTestId(wrapper, 'save-draft-button')

    expect(createManualDraftRun).toHaveBeenCalledWith(1, 'Current page text')
    expect(createPageEditRun).not.toHaveBeenCalled()
    expect(createProposal).not.toHaveBeenCalled()
    expect(saveDraft).not.toHaveBeenCalled()
    expect(wrapper.get('[data-testid="workspace-draft"]').text()).toBe('Current page text')

    wrapper.unmount()
  })

  it('loads draft history for an active run and refreshes after restore', async () => {
    vi.mocked(fetchActivePageEditRun).mockResolvedValue(makeRun())
    vi.mocked(fetchDraftVersions).mockResolvedValue([makeDraftVersion()])
    const wrapper = await mountPageEditorView()

    expect(fetchDraftVersions).toHaveBeenCalledWith('run-1')
    expect(wrapper.get('[data-testid="draft-version-count"]').text()).toBe('1')

    await clickByTestId(wrapper, 'restore-draft-version-button')

    expect(restoreDraftVersion).toHaveBeenCalledWith('run-1', 1)
    expect(wrapper.get('[data-testid="workspace-draft"]').text()).toBe('# Restored draft')
    expect(fetchDraftVersions).toHaveBeenCalledTimes(2)

    wrapper.unmount()
  })

  it('creates a proposal from the first chat prompt using the default Markdown', async () => {
    const wrapper = await mountPageEditorView()

    await clickByTestId(wrapper, 'send-edit-request-button')

    expect(createPageEditRun).not.toHaveBeenCalled()
    expect(createProposal).toHaveBeenCalledWith(1, 'Update docs', {
      baseMarkdown: 'Current page text',
    })
    expect(createManualDraftRun).not.toHaveBeenCalled()
    expect(wrapper.get('[data-testid="message-count"]').text()).toBe('1')

    wrapper.unmount()
  })

  it('creates a proposal from later chat prompts once a draft exists', async () => {
    vi.mocked(fetchActivePageEditRun).mockResolvedValue(makeRun())
    const wrapper = await mountPageEditorView()

    await clickByTestId(wrapper, 'send-edit-request-button')

    expect(createPageEditRun).not.toHaveBeenCalled()
    expect(createProposal).toHaveBeenCalledWith(1, 'Update docs', {
      baseRunId: 'run-1',
      baseMarkdown: '# Draft',
    })

    wrapper.unmount()
  })

  it('blocks the next chat prompt while a ready proposal awaits a decision', async () => {
    vi.mocked(fetchActivePageEditRun).mockResolvedValue(makeRun())
    vi.mocked(createProposal).mockResolvedValue(makeProposal())
    const wrapper = await mountPageEditorView()

    await clickByTestId(wrapper, 'send-edit-request-button')
    await clickByTestId(wrapper, 'send-edit-request-button')

    expect(wrapper.find('[data-testid="proposal-decision-actions"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="send-edit-request-button"]').attributes('disabled')).toBeDefined()
    expect(createProposal).toHaveBeenCalledTimes(1)
    expect(createProposal).toHaveBeenCalledWith(1, 'Update docs', {
      baseRunId: 'run-1',
      baseMarkdown: '# Draft',
    })

    wrapper.unmount()
  })

  it('uses the applied draft as the base for the next chat prompt', async () => {
    vi.mocked(fetchActivePageEditRun).mockResolvedValue(makeRun())
    vi.mocked(createProposal).mockResolvedValue(makeProposal())
    const wrapper = await mountPageEditorView()

    await clickByTestId(wrapper, 'send-edit-request-button')
    await clickByTestId(wrapper, 'apply-proposal-button')
    await clickByTestId(wrapper, 'send-edit-request-button')

    expect(createProposal).toHaveBeenNthCalledWith(2, 1, 'Update docs', {
      baseRunId: 'run-1',
      baseMarkdown: '# Updated draft',
    })

    wrapper.unmount()
  })

  it('applies a ready proposal and updates the draft model', async () => {
    vi.mocked(fetchActivePageEditRun).mockResolvedValue(makeRun())
    vi.mocked(createProposal).mockResolvedValue(makeProposal())
    const wrapper = await mountPageEditorView()

    await clickByTestId(wrapper, 'send-edit-request-button')
    await clickByTestId(wrapper, 'apply-proposal-button')

    expect(applyProposal).toHaveBeenCalledWith('proposal-1')
    expect(wrapper.get('[data-testid="workspace-draft"]').text()).toBe('# Updated draft')

    wrapper.unmount()
  })

  it('rejects a proposal without saving a draft', async () => {
    vi.mocked(fetchActivePageEditRun).mockResolvedValue(makeRun())
    vi.mocked(createProposal).mockResolvedValue(makeProposal())
    const wrapper = await mountPageEditorView()

    await clickByTestId(wrapper, 'send-edit-request-button')
    await clickByTestId(wrapper, 'reject-proposal-button')

    expect(rejectProposal).toHaveBeenCalledWith('proposal-1')
    expect(saveDraft).not.toHaveBeenCalled()
    expect(wrapper.get('[data-testid="workspace-proposal"]').text()).toBe('rejected')

    wrapper.unmount()
  })

  it('surfaces page editor API errors in the chat', async () => {
    vi.mocked(createProposal).mockRejectedValue(new Error('Proposal service unavailable'))
    const wrapper = await mountPageEditorView()

    await clickByTestId(wrapper, 'send-edit-request-button')

    expect(wrapper.text()).toContain('Proposal service unavailable')
    expect(wrapper.findAll('[data-testid="chat-message"]')).toHaveLength(2)

    wrapper.unmount()
  })

  it('stops the proposal spinner when proposal polling fails', async () => {
    vi.useFakeTimers()
    vi.mocked(fetchActivePageEditRun).mockResolvedValue(makeRun())
    vi.mocked(createProposal).mockResolvedValue(makeProposal({ status: 'queued' }))
    vi.mocked(fetchProposal).mockRejectedValue(new Error('Proposal worker unavailable'))
    const wrapper = await mountPageEditorView()

    await clickByTestId(wrapper, 'send-edit-request-button')

    expect(wrapper.find('[data-testid="busy-label"]').text()).toBe('Preparing proposal')

    await vi.advanceTimersByTimeAsync(1800)
    await flushPromises()
    await nextTick()

    expect(wrapper.text()).toContain('Proposal worker unavailable')
    expect(wrapper.find('[data-testid="busy-label"]').exists()).toBe(false)

    wrapper.unmount()
  })

  it('shows only the chat spinner during an active workflow', async () => {
    const wrapper = await mountPageEditorView({ realEditChat: true })

    const chat = wrapper.getComponent(EditChatPanel)
    chat.vm.$emit('update:modelValue', 'Update docs')
    await nextTick()
    chat.vm.$emit('submit')
    await flushPromises()
    await nextTick()

    expect(createProposal).toHaveBeenCalledWith(1, 'Update docs', {
      baseMarkdown: 'Current page text',
    })
    expect(createPageEditRun).not.toHaveBeenCalled()
    expect(wrapper.findAll('.app-spinner')).toHaveLength(1)
    expect(wrapper.text()).toContain('Preparing proposal')

    wrapper.unmount()
  })

  it('opens publish confirmation before calling publish', async () => {
    vi.mocked(fetchActivePageEditRun).mockResolvedValue(makeRun())
    const wrapper = await mountPageEditorView()

    await clickByTestId(wrapper, 'publish-run-button')

    expect(publishRun).not.toHaveBeenCalled()
    expect(wrapper.get('[data-testid="publish-dialog"]').text()).toContain('Setup Guide')

    await clickByTestId(wrapper, 'confirm-publish')

    expect(publishRun).toHaveBeenCalledWith('run-1')

    wrapper.unmount()
  })
})
