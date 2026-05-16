import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createChatSession, fetchChatMessages, streamChatQuestion } from '../../api/chat'
import { resetEasterEggsForTest } from '../../composables/useEasterEggs'
import ChatWidget from './ChatWidget.vue'

vi.mock('../../api/chat', () => ({
  createChatSession: vi.fn(),
  fetchChatMessages: vi.fn(),
  streamChatQuestion: vi.fn(),
}))

describe('ChatWidget easter eggs', () => {
  afterEach(() => {
    resetEasterEggsForTest()
    vi.clearAllMocks()
  })

  it('answers /vault locally without streaming to the API', async () => {
    vi.mocked(createChatSession).mockResolvedValue({ id: 'session-1', title: 'Widget' })
    vi.mocked(fetchChatMessages).mockResolvedValue([])

    const wrapper = mount(ChatWidget, {
      global: {
        stubs: {
          AppSpinner: true,
          ChatMessages: {
            props: ['messages'],
            template: `
              <div data-testid="messages">
                <article v-for="message in messages" :key="message.id">
                  {{ message.content }}
                </article>
              </div>
            `,
          },
          ChatComposer: {
            emits: ['submit', 'update:modelValue'],
            template: `
              <button
                data-testid="vault-command"
                @click="$emit('update:modelValue', '/vault'); $emit('submit')"
              >
                Vault
              </button>
            `,
          },
          VBtn: {
            emits: ['click'],
            template: '<button v-bind="$attrs" @click="$emit(\'click\')"><slot /></button>',
          },
          VIcon: true,
        },
      },
    })
    await flushPromises()

    await wrapper.find('.chat-widget__fab').trigger('click')
    await wrapper.find('[data-testid="vault-command"]').trigger('click')

    expect(wrapper.find('[data-testid="messages"]').text()).toContain('/vault')
    expect(wrapper.find('[data-testid="messages"]').text()).toContain('Vault access granted')
    expect(streamChatQuestion).not.toHaveBeenCalled()
  })
})
