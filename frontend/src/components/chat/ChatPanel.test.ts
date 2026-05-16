import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { createChatSession, fetchChatMessages, streamChatQuestion } from '../../api/chat'
import { vuetify } from '../../plugins/vuetify'
import type { ChatMessage } from '../../types/api'
import ChatComposer from './ChatComposer.vue'
import ChatPanel from './ChatPanel.vue'

const chatStatsCardStub = {
  emits: ['toggle'],
  props: ['collapsed', 'compact', 'stats'],
  template: `
    <section>
      <button data-testid="chat-stats-toggle" @click="$emit('toggle')">{{ collapsed }}</button>
      <span data-testid="chat-stats-compact">{{ compact }}</span>
      <pre data-testid="chat-stats-props">{{ JSON.stringify(stats) }}</pre>
    </section>
  `,
}

const chatSettingsCardStub = {
  emits: ['resetAll', 'resetSetting', 'toggle', 'updateSetting'],
  props: ['collapsed', 'compact', 'disabled', 'settings'],
  template: `
    <section>
      <button data-testid="chat-settings-toggle" @click="$emit('toggle')">{{ collapsed }}</button>
      <span data-testid="chat-settings-compact">{{ compact }}</span>
      <span>Advanced</span>
      <span>Query parameters</span>
    </section>
  `,
}

vi.mock('../../api/chat', () => ({
  createChatSession: vi.fn(),
  fetchChatMessages: vi.fn(),
  streamChatQuestion: vi.fn(),
}))

function makeMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: 1,
    session_id: 'session-1',
    role: 'assistant',
    content: 'Existing answer',
    citations_json: '[]',
    ...overrides,
  }
}

function readRenderedStats(wrapper: ReturnType<typeof mount>): Record<string, unknown> {
  return JSON.parse(wrapper.get('[data-testid="chat-stats-props"]').text()) as Record<
    string,
    unknown
  >
}

describe('ChatPanel', () => {
  beforeEach(() => {
    vi.stubGlobal('ResizeObserver', class ResizeObserver {
      observe(): void {}
      unobserve(): void {}
      disconnect(): void {}
    })

    vi.mocked(createChatSession)
      .mockResolvedValueOnce({ id: 'session-1', title: 'Documentation chat' })
      .mockResolvedValueOnce({ id: 'session-2', title: 'Documentation chat' })
    vi.mocked(fetchChatMessages).mockResolvedValue([makeMessage()])
    vi.mocked(streamChatQuestion).mockResolvedValue()
  })

  afterEach(() => {
    vi.clearAllMocks()
    vi.unstubAllGlobals()
  })

  it('clears the chat by creating a fresh session while preserving the draft', async () => {
    const wrapper = mount(ChatPanel, {
      global: {
        plugins: [vuetify],
        stubs: {
          ChatMessages: {
            props: ['messages'],
            template: '<div data-testid="message-count">{{ messages.length }}</div>',
          },
          ChatSettingsCard: chatSettingsCardStub,
          ChatStatsCard: chatStatsCardStub,
        },
      },
    })
    await flushPromises()

    wrapper.findComponent(ChatComposer).vm.$emit('update:modelValue', 'Keep this draft')
    await nextTick()
    expect(wrapper.get('[data-testid="message-count"]').text()).toBe('1')

    await wrapper.get('[data-testid="clear-chat-button"]').trigger('click')
    await flushPromises()

    expect(createChatSession).toHaveBeenCalledTimes(2)
    expect(wrapper.get('[data-testid="message-count"]').text()).toBe('0')
    expect(wrapper.findComponent(ChatComposer).props('modelValue')).toBe('Keep this draft')
    expect(readRenderedStats(wrapper).messageCount).toBe(0)
  })

  it('renders neutral advanced settings without exposing the backend name', async () => {
    const wrapper = mount(ChatPanel, {
      global: {
        plugins: [vuetify],
        stubs: {
          ChatMessages: true,
          ChatSettingsCard: chatSettingsCardStub,
          ChatStatsCard: chatStatsCardStub,
        },
      },
    })
    await flushPromises()

    expect(wrapper.get('[data-testid="chat-stats-toggle"]').text()).toBe('false')
    expect(wrapper.text()).toContain('Advanced')
    expect(wrapper.text()).toContain('Query parameters')
    expect(wrapper.text()).not.toContain('LightRAG')
  })

  it('collapses the conversation stats card from the sidebar', async () => {
    const wrapper = mount(ChatPanel, {
      global: {
        plugins: [vuetify],
        stubs: {
          ChatMessages: true,
          ChatSettingsCard: chatSettingsCardStub,
          ChatStatsCard: chatStatsCardStub,
        },
      },
    })
    await flushPromises()

    await wrapper.get('[data-testid="chat-stats-toggle"]').trigger('click')

    expect(wrapper.get('[data-testid="chat-stats-toggle"]').text()).toBe('true')
  })

  it('only keeps one right sidebar panel open at a time', async () => {
    const wrapper = mount(ChatPanel, {
      global: {
        plugins: [vuetify],
        stubs: {
          ChatMessages: true,
          ChatSettingsCard: chatSettingsCardStub,
          ChatStatsCard: chatStatsCardStub,
        },
      },
    })
    await flushPromises()

    expect(wrapper.get('.chat-sidebar').classes()).not.toContain('chat-sidebar--collapsed')
    expect(wrapper.get('[data-testid="chat-stats-toggle"]').text()).toBe('false')
    expect(wrapper.get('[data-testid="chat-settings-toggle"]').text()).toBe('true')

    await wrapper.get('[data-testid="chat-settings-toggle"]').trigger('click')

    expect(wrapper.get('.chat-sidebar').classes()).not.toContain('chat-sidebar--collapsed')
    expect(wrapper.get('[data-testid="chat-stats-toggle"]').text()).toBe('true')
    expect(wrapper.get('[data-testid="chat-settings-toggle"]').text()).toBe('false')

    await wrapper.get('[data-testid="chat-stats-toggle"]').trigger('click')

    expect(wrapper.get('.chat-sidebar').classes()).not.toContain('chat-sidebar--collapsed')
    expect(wrapper.get('[data-testid="chat-stats-toggle"]').text()).toBe('false')
    expect(wrapper.get('[data-testid="chat-settings-toggle"]').text()).toBe('true')
  })

  it('shrinks the right sidebar when every sidebar panel is collapsed', async () => {
    const wrapper = mount(ChatPanel, {
      global: {
        plugins: [vuetify],
        stubs: {
          ChatMessages: true,
          ChatSettingsCard: chatSettingsCardStub,
          ChatStatsCard: chatStatsCardStub,
        },
      },
    })
    await flushPromises()

    expect(wrapper.get('.chat-sidebar').classes()).not.toContain('chat-sidebar--collapsed')

    await wrapper.get('[data-testid="chat-stats-toggle"]').trigger('click')

    expect(wrapper.get('.chat-sidebar').classes()).toContain('chat-sidebar--collapsed')
    expect(wrapper.get('[data-testid="chat-stats-compact"]').text()).toBe('true')
    expect(wrapper.get('[data-testid="chat-settings-compact"]').text()).toBe('true')
  })

  it('tracks cumulative conversation stats across multiple prompts', async () => {
    const firstAssistantMessage = makeMessage({
      id: 3,
      role: 'assistant',
      content: 'Hello docs',
      citations_json: JSON.stringify([{ confluenceId: '123' }]),
    })
    const secondAssistantMessage = makeMessage({
      id: 5,
      role: 'assistant',
      content: 'More details',
      citations_json: JSON.stringify([{ confluenceId: '123' }, { confluenceId: '456' }]),
    })
    const firstUserMessage = makeMessage({
      id: 2,
      role: 'user',
      content: 'What changed?',
    })
    const secondUserMessage = makeMessage({
      id: 4,
      role: 'user',
      content: 'And now?',
    })
    vi.mocked(fetchChatMessages)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([firstUserMessage, firstAssistantMessage])
      .mockResolvedValueOnce([
        firstUserMessage,
        firstAssistantMessage,
        secondUserMessage,
        secondAssistantMessage,
      ])
    vi.mocked(streamChatQuestion).mockImplementation(
      async (_sessionId, _message, _settings, handlers) => {
        const isFirstPrompt = _message === 'What changed?'
        const response = isFirstPrompt ? 'Hello docs' : 'More details'
        const assistantMessage = isFirstPrompt ? firstAssistantMessage : secondAssistantMessage
        handlers.onStats?.({
          phase: 'started',
          elapsedMs: 0,
          historyMessageCount: isFirstPrompt ? 0 : 2,
          historyChars: isFirstPrompt ? 0 : 32,
          responseChars: 0,
          chunkCount: 0,
          referenceCount: 0,
          streamEventCount: 0,
          tokenUsage: null,
        })
        handlers.onReferences?.(
          isFirstPrompt
            ? [{ confluenceId: '123' }]
            : [{ confluenceId: '123' }, { confluenceId: '456' }],
        )
        handlers.onDelta?.(response)
        handlers.onStats?.({
          phase: 'completed',
          elapsedMs: isFirstPrompt ? 18 : 25,
          historyMessageCount: isFirstPrompt ? 0 : 2,
          historyChars: isFirstPrompt ? 0 : 32,
          responseChars: response.length,
          chunkCount: isFirstPrompt ? 1 : 2,
          referenceCount: isFirstPrompt ? 1 : 2,
          streamEventCount: isFirstPrompt ? 2 : 3,
          tokenUsage: { totalTokens: isFirstPrompt ? 42 : 21 },
        })
        handlers.onAssistantMessage?.(assistantMessage)
      },
    )

    const wrapper = mount(ChatPanel, {
      global: {
        plugins: [vuetify],
        stubs: {
          ChatMessages: true,
          ChatSettingsCard: chatSettingsCardStub,
          ChatStatsCard: chatStatsCardStub,
        },
      },
    })
    await flushPromises()

    wrapper.findComponent(ChatComposer).vm.$emit('update:modelValue', 'What changed?')
    await nextTick()
    wrapper.findComponent(ChatComposer).vm.$emit('submit')
    await flushPromises()

    wrapper.findComponent(ChatComposer).vm.$emit('update:modelValue', 'And now?')
    await nextTick()
    wrapper.findComponent(ChatComposer).vm.$emit('submit')
    await flushPromises()

    const stats = readRenderedStats(wrapper)
    const current = stats.current as Record<string, unknown>
    const totals = stats.totals as Record<string, unknown>

    expect(stats.questionCount).toBe(2)
    expect(stats.answerCount).toBe(2)
    expect(stats.referenceCount).toBe(3)
    expect(totals.requestCount).toBe(2)
    expect(totals.chunkCount).toBe(3)
    expect(totals.historyMessageCount).toBe(2)
    expect(totals.historyChars).toBe(32)
    expect(totals.responseChars).toBe(22)
    expect(totals.streamEventCount).toBe(5)
    expect(totals.tokenUsage).toEqual({ totalTokens: 63 })
    expect(current.historyMessageCount).toBe(2)
    expect(current.historyChars).toBe(32)
    expect(current.chunkCount).toBe(2)
    expect(current.tokenUsage).toEqual({ totalTokens: 21 })
  })
})
