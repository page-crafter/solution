import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { describe, expect, it, vi } from 'vitest'
import { vuetify } from '../../plugins/vuetify'
import EditChatPanel from './EditChatPanel.vue'

function makeMessage(id: number, content: string, role: 'user' | 'assistant' = 'assistant') {
  return { id, role, content }
}

async function prepareScroller(
  wrapper: ReturnType<typeof mount>,
  options: { clientHeight?: number, scrollHeight?: number, scrollTop?: number } = {},
): Promise<HTMLElement & { scrollTo: ReturnType<typeof vi.fn> }> {
  await nextTick()
  const scroller = wrapper.get('.edit-chat__messages').element as HTMLElement & {
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

describe('EditChatPanel', () => {
  it('uses a single-line prompt input', () => {
    const wrapper = mount(EditChatPanel, {
      props: { messages: [], modelValue: '' },
      global: { plugins: [vuetify] },
    })

    expect(wrapper.find('input').exists()).toBe(true)
    expect(wrapper.find('textarea').exists()).toBe(false)
  })

  it('auto-scrolls when chat content changes', async () => {
    const wrapper = mount(EditChatPanel, {
      props: {
        messages: [makeMessage(1, 'Starting')],
        modelValue: '',
      },
      global: { plugins: [vuetify] },
    })
    const scroller = await prepareScroller(wrapper)
    scroller.scrollTo.mockClear()

    await wrapper.setProps({
      messages: [
        makeMessage(1, 'Starting'),
        makeMessage(2, 'More content', 'user'),
      ],
    })
    await nextTick()

    expect(scroller.scrollTo).toHaveBeenCalledWith({ top: 1000 })
  })
})
