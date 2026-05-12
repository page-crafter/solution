import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { vuetify } from '../../plugins/vuetify'
import type { ChatQuerySettings } from '../../types/api'
import ChatSettingsCard from './ChatSettingsCard.vue'

const settings: ChatQuerySettings = {
  mode: 'mix',
  user_prompt: '',
  top_k: 40,
  chunk_top_k: 20,
  max_entity_tokens: 6000,
  max_relation_tokens: 8000,
  max_total_tokens: 30000,
  enable_rerank: true,
  only_need_context: false,
  only_need_prompt: false,
}

describe('ChatSettingsCard', () => {
  it('shows the title in the collapsed rail unless the sidebar is compact', async () => {
    const wrapper = mount(ChatSettingsCard, {
      props: {
        collapsed: true,
        compact: false,
        settings,
      },
      global: { plugins: [vuetify] },
    })

    expect(wrapper.text()).toContain('Advanced')
    expect(wrapper.text()).toContain('Query parameters')

    await wrapper.setProps({ compact: true })

    expect(wrapper.text()).not.toContain('Advanced')
    expect(wrapper.text()).not.toContain('Query parameters')
  })
})
