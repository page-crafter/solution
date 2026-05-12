import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { describe, expect, it, vi } from 'vitest'
import { vuetify } from '../../plugins/vuetify'
import type { ChatMessage } from '../../types/api'
import ChatMessages from './ChatMessages.vue'

function makeMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: 1,
    session_id: 'session-1',
    role: 'assistant',
    content: '**Bold**\n\n- Item',
    citations_json: '[]',
    ...overrides,
  }
}

async function prepareScroller(
  wrapper: ReturnType<typeof mount>,
  options: { clientHeight?: number, scrollHeight?: number, scrollTop?: number } = {},
): Promise<HTMLElement & { scrollTo: ReturnType<typeof vi.fn> }> {
  await nextTick()
  const scroller = wrapper.get('.chat-messages').element as HTMLElement & {
    scrollTo: ReturnType<typeof vi.fn>
  }

  Object.defineProperties(scroller, {
    clientHeight: { configurable: true, value: options.clientHeight ?? 200 },
    scrollHeight: { configurable: true, value: options.scrollHeight ?? 1000 },
    scrollTop: {
      configurable: true,
      get: () => options.scrollTop ?? 0,
      set: (value: number) => {
        options.scrollTop = value
      },
    },
  })

  scroller.scrollTo = vi.fn((params?: ScrollToOptions) => {
    if (typeof params?.top === 'number') {
      scroller.scrollTop = params.top
    }
  })

  return scroller
}

describe('ChatMessages', () => {
  it('renders markdown as safe HTML', () => {
    const wrapper = mount(ChatMessages, {
      props: {
        messages: [
          makeMessage({
            content: '**Bold**\n\n- Item\n\n<script>alert(1)</script>',
          }),
        ],
      },
      global: { plugins: [vuetify] },
    })

    const bodyHtml = wrapper.get('.message__body').html()

    expect(bodyHtml).toContain('<strong>Bold</strong>')
    expect(bodyHtml).toContain('<li>Item</li>')
    expect(bodyHtml).toContain('&lt;script&gt;alert(1)&lt;/script&gt;')
    expect(bodyHtml).not.toContain('<script>')
  })

  it('links Confluence citations when the API provides a page URL', () => {
    const wrapper = mount(ChatMessages, {
      props: {
        messages: [
          makeMessage({
            citations_json: JSON.stringify([
              {
                confluenceId: '123',
                snippet: 'Relevant paragraph',
                title: 'Setup Guide',
                webUrl: 'http://localhost:8090/display/DOC/Setup+Guide',
              },
            ]),
          }),
        ],
      },
      global: { plugins: [vuetify] },
    })

    const citationLink = wrapper.get('a[href="http://localhost:8090/display/DOC/Setup+Guide"]')

    expect(citationLink.text()).toContain('Setup Guide')
    expect(citationLink.attributes('target')).toBe('_blank')
    expect(citationLink.attributes('rel')).toBe('noopener noreferrer')
  })

  it('turns raw Confluence references in the answer into page links', () => {
    const wrapper = mount(ChatMessages, {
      props: {
        messages: [
          makeMessage({
            content: '## References\n- [1] confluence:DEV:294947',
            citations_json: JSON.stringify([
              {
                confluenceId: '294947',
                filePath: 'confluence:DEV:294947',
                title: 'Docker install',
                webUrl: 'http://localhost:8090/display/DEV/Docker+install',
              },
            ]),
          }),
        ],
      },
      global: { plugins: [vuetify] },
    })

    const bodyHtml = wrapper.get('.message__body').html()
    const referenceLink = wrapper.get('a[href="http://localhost:8090/display/DEV/Docker+install"]')

    expect(referenceLink.text()).toBe('Docker install')
    expect(bodyHtml).not.toContain('confluence:DEV:294947')
  })

  it('shows distinct avatars for user and assistant messages', () => {
    const wrapper = mount(ChatMessages, {
      props: {
        messages: [
          makeMessage({ id: 1, role: 'user', content: 'Hello' }),
          makeMessage({ id: 2, role: 'assistant', content: 'Hi there' }),
        ],
      },
      global: { plugins: [vuetify] },
    })

    expect(wrapper.find('.message__avatar--user').exists()).toBe(true)
    expect(wrapper.find('.message__avatar--assistant').exists()).toBe(true)
  })

  it('copies fenced code block content from the inline copy button', async () => {
    vi.useFakeTimers()
    const originalClipboard = navigator.clipboard
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    })

    const wrapper = mount(ChatMessages, {
      props: {
        messages: [
          makeMessage({
            content: '```ts\nconst value = 1\nconsole.log(value)\n```',
          }),
        ],
      },
      global: { plugins: [vuetify] },
    })

    const copyButton = wrapper.get('.code-copy-button')
    await copyButton.trigger('click')
    await Promise.resolve()

    expect(writeText).toHaveBeenCalledWith('const value = 1\nconsole.log(value)')
    expect(copyButton.text()).toBe('Copied')

    vi.runAllTimers()
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: originalClipboard,
    })
    vi.useRealTimers()
  })

  it('auto-scrolls as streaming content is appended while pinned to the bottom', async () => {
    const wrapper = mount(ChatMessages, {
      props: {
        messages: [makeMessage()],
        streaming: true,
        streamingContent: 'Starting',
      },
      global: { plugins: [vuetify] },
    })
    const scroller = await prepareScroller(wrapper, { scrollTop: 800 })

    await wrapper.setProps({ streamingContent: 'Starting\n\nMore streamed content' })
    await nextTick()

    expect(scroller.scrollTo).toHaveBeenCalledWith({ top: 1000 })
  })

  it('pauses auto-scroll after the user manually scrolls up during streaming', async () => {
    const wrapper = mount(ChatMessages, {
      props: {
        messages: [makeMessage()],
        streaming: true,
        streamingContent: 'Starting',
      },
      global: { plugins: [vuetify] },
    })
    const scroller = await prepareScroller(wrapper, { scrollTop: 800 })

    await wrapper.get('.chat-messages').trigger('wheel')
    scroller.scrollTop = 500
    await wrapper.get('.chat-messages').trigger('scroll')
    scroller.scrollTo.mockClear()

    await wrapper.setProps({ streamingContent: 'Starting\n\nMore streamed content' })
    await nextTick()

    expect(scroller.scrollTo).not.toHaveBeenCalled()
  })
})
