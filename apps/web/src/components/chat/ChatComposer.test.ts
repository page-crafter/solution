import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { vuetify } from '../../plugins/vuetify'
import ChatComposer from './ChatComposer.vue'

describe('ChatComposer', () => {
  beforeEach(() => {
    vi.stubGlobal('ResizeObserver', class ResizeObserver {
      observe(): void {}
      unobserve(): void {}
      disconnect(): void {}
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('emits submit when the current draft is not empty', async () => {
    const wrapper = mount(ChatComposer, {
      props: { modelValue: 'What changed?' },
      global: { plugins: [vuetify] },
    })

    await wrapper.get('form').trigger('submit')

    expect(wrapper.emitted('submit')).toHaveLength(1)
  })

  it('emits clearChat without clearing the draft locally', async () => {
    const wrapper = mount(ChatComposer, {
      props: { modelValue: 'Draft message' },
      global: { plugins: [vuetify] },
    })

    await wrapper.get('[data-testid="clear-chat-button"]').trigger('click')

    expect(wrapper.emitted('clearChat')).toHaveLength(1)
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  })

  it('keeps clear chat clickable when submit/input are disabled', async () => {
    const wrapper = mount(ChatComposer, {
      props: { disabled: true, modelValue: 'Draft message' },
      global: { plugins: [vuetify] },
    })

    await wrapper.get('[data-testid="clear-chat-button"]').trigger('click')

    expect(wrapper.emitted('clearChat')).toHaveLength(1)
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
    expect(wrapper.emitted('submit')).toBeUndefined()
  })

  it('disables clear chat when the parent has no chat to clear', () => {
    const wrapper = mount(ChatComposer, {
      props: { clearDisabled: true, modelValue: 'Draft message' },
      global: { plugins: [vuetify] },
    })

    expect(wrapper.get('[data-testid="clear-chat-button"]').attributes('disabled')).toBeDefined()
  })
})
