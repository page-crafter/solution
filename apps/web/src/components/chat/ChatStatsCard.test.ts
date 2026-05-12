import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { vuetify } from '../../plugins/vuetify'
import type { ChatConversationStats } from '../../composables/useChatConversationStats'
import ChatStatsCard from './ChatStatsCard.vue'

function makeStats(): ChatConversationStats {
  return {
    status: 'completed',
    questionCount: 2,
    answerCount: 2,
    messageCount: 4,
    totalChars: 64,
    totalWords: 10,
    referenceCount: 3,
    errorCount: 0,
    measuredElapsedMs: 100,
    totals: {
      requestCount: 2,
      assistantChars: 24,
      assistantWords: 4,
      historyMessageCount: 2,
      historyChars: 32,
      responseChars: 22,
      chunkCount: 3,
      referenceCount: 3,
      streamEventCount: 5,
      clientElapsedMs: 100,
      serverElapsedMs: 43,
      tokenUsage: { totalTokens: 63 },
    },
    current: {
      status: 'completed',
      elapsedMs: 50,
      responseChars: 3789,
      responseWords: 2,
      chunkCount: 2,
      referenceCount: 2,
      historyMessageCount: 2,
      historyChars: 32,
      streamEventCount: 3,
      serverElapsedMs: 25,
      tokenUsage: { totalTokens: 21 },
    },
  }
}

describe('ChatStatsCard', () => {
  it('shows the title in the collapsed rail unless the sidebar is compact', async () => {
    const wrapper = mount(ChatStatsCard, {
      props: {
        collapsed: true,
        compact: false,
        stats: makeStats(),
      },
      global: { plugins: [vuetify] },
    })

    expect(wrapper.text()).toContain('Conversation')
    expect(wrapper.text()).toContain('Last prompt')

    await wrapper.setProps({ compact: true })

    expect(wrapper.text()).not.toContain('Conversation')
    expect(wrapper.text()).not.toContain('Last prompt')
  })

  it('shows last prompt stats by default and switches to cumulative stats', async () => {
    const wrapper = mount(ChatStatsCard, {
      props: {
        collapsed: false,
        stats: makeStats(),
      },
      global: { plugins: [vuetify] },
    })

    expect(wrapper.text()).toContain('Last prompt')
    expect(wrapper.text()).toContain('Live elapsed')
    expect(wrapper.text()).toContain('3.8K chars')
    expect(wrapper.text()).not.toContain('Streamed text')
    expect(wrapper.text()).not.toContain('Tokens')
    expect(wrapper.text()).not.toContain('Non fourni')

    expect(wrapper.findAll('.stats-mode__button').map((button) => button.text())).toEqual([
      'Last prompt',
      'Cumul',
    ])

    const cumulativeButton = wrapper
      .findAll('button')
      .find((button) => button.text().includes('Cumul'))

    await cumulativeButton?.trigger('click')

    expect(wrapper.text()).toContain('Cumulative stats')
    expect(wrapper.text()).toContain('Streamed text')
    expect(wrapper.text()).toContain('22 chars')
    expect(wrapper.text()).not.toContain('Live elapsed')
    expect(wrapper.text()).not.toContain('Tokens')
    expect(wrapper.text()).not.toContain('Non fourni')
  })
})
