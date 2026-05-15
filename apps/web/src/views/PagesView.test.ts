import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import {
  createEmptyPage,
  deletePage,
  fetchPage,
  fetchPages,
  movePage,
  refreshPage,
  syncSpace,
} from '../api/pages'
import { cancelRun, fetchActivePageEditRun } from '../api/pageEditor'
import { vuetify } from '../plugins/vuetify'
import type { ConfluencePage, PageDetail, PageEditRun } from '../types/api'
import PagesView from './PagesView.vue'

const routerMock = vi.hoisted(() => ({
  push: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => routerMock,
}))

vi.mock('../api/pages', () => ({
  createEmptyPage: vi.fn(),
  deletePage: vi.fn(),
  fetchPage: vi.fn(),
  fetchPages: vi.fn(),
  movePage: vi.fn(),
  refreshPage: vi.fn(),
  syncSpace: vi.fn(),
}))

vi.mock('../api/pageEditor', () => ({
  cancelRun: vi.fn(),
  fetchActivePageEditRun: vi.fn(),
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
    draft_state: 'Preview ready',
    last_synced_at: '2026-05-10T10:00:00Z',
    ...overrides,
  }
}

function makePageDetail(overrides: Partial<PageDetail> = {}): PageDetail {
  return {
    ...makePage(overrides),
    source_storage_xhtml: '<p>Source</p>',
    source_markdown: 'Source',
    extracted_text: 'Source',
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

async function mountPagesView(): Promise<VueWrapper> {
  const wrapper = mount(PagesView, {
    global: {
      plugins: [vuetify],
      stubs: {
        ActionValidationDialog: true,
        AppSpinner: true,
        JobStateDialog: true,
        PageDetailPanel: {
          props: ['page', 'activeRun'],
          emits: ['cancelDraft', 'startUpdate'],
          template: `
            <div data-testid="page-detail">
              <span data-testid="detail-state">{{ page?.draft_state }}</span>
              <button
                v-if="activeRun"
                data-testid="cancel-draft"
                @click="$emit('cancelDraft')"
              >
                Cancel
              </button>
            </div>
          `,
        },
        PageTree: {
          props: ['pages', 'rootLabel', 'selectedId'],
          emits: ['select'],
          template: `
            <div data-testid="page-tree">
              <button
                v-for="page in pages"
                :key="page.id"
                :data-testid="'page-' + page.id"
                @click="$emit('select', page)"
              >
                {{ page.title }} {{ page.draft_state }}
              </button>
            </div>
          `,
        },
      },
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

describe('PagesView', () => {
  beforeEach(() => {
    vi.stubGlobal('ResizeObserver', class ResizeObserver {
      observe(): void {}
      unobserve(): void {}
      disconnect(): void {}
    })
    vi.mocked(createEmptyPage).mockResolvedValue({ id: 'job-1', status: 'queued' })
    vi.mocked(deletePage).mockResolvedValue({ id: 'job-1', status: 'queued' })
    vi.mocked(movePage).mockResolvedValue({ id: 'job-1', status: 'queued' })
    vi.mocked(refreshPage).mockResolvedValue({ id: 'job-1', status: 'queued' })
    vi.mocked(syncSpace).mockResolvedValue({ id: 'job-1', status: 'queued' })
  })

  afterEach(() => {
    vi.clearAllMocks()
    vi.unstubAllGlobals()
  })

  it('refreshes the tree after cancelling the selected page draft', async () => {
    vi.mocked(fetchPages)
      .mockResolvedValueOnce([makePage({ draft_state: 'Preview ready' })])
      .mockResolvedValueOnce([makePage({ draft_state: 'Published' })])
    vi.mocked(fetchPage)
      .mockResolvedValueOnce(makePageDetail({ draft_state: 'Preview ready' }))
      .mockResolvedValueOnce(makePageDetail({ draft_state: 'Published' }))
    vi.mocked(fetchActivePageEditRun)
      .mockResolvedValueOnce(makeRun())
      .mockResolvedValueOnce(null)
    vi.mocked(cancelRun).mockResolvedValue(
      makeRun({ status: 'cancelled', draft_status: 'Published', markdown_draft: null }),
    )

    const wrapper = await mountPagesView()

    expect(wrapper.get('[data-testid="page-tree"]').text()).toContain('Preview ready')

    await clickByTestId(wrapper, 'page-1')
    await clickByTestId(wrapper, 'cancel-draft')

    expect(cancelRun).toHaveBeenCalledWith('run-1')
    expect(fetchPages).toHaveBeenCalledTimes(2)
    expect(fetchPage).toHaveBeenLastCalledWith(1)
    expect(fetchActivePageEditRun).toHaveBeenLastCalledWith(1)
    expect(wrapper.get('[data-testid="page-tree"]').text()).toContain('Published')
    expect(wrapper.get('[data-testid="detail-state"]').text()).toBe('Published')

    wrapper.unmount()
  })
})
