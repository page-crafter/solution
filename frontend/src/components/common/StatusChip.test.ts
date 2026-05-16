import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { vuetify } from '../../plugins/vuetify'
import StatusChip from './StatusChip.vue'

describe('StatusChip', () => {
  it('renders the draft state label', () => {
    const wrapper = mount(StatusChip, {
      props: { state: 'Preview ready' },
      global: { plugins: [vuetify] },
    })

    expect(wrapper.text()).toContain('Preview ready')
  })
})

