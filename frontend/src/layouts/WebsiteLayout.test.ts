import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { resetEasterEggsForTest } from '../composables/useEasterEggs'
import WebsiteLayout from './WebsiteLayout.vue'

vi.mock('vue-router', () => ({
  useRoute: () => ({ path: '/dashboard' }),
}))

vi.mock('../stores/auth', () => ({
  useAuthStore: () => ({
    displayName: 'Docs Admin',
    isAdmin: true,
    isChat: false,
    logout: vi.fn(),
  }),
}))

describe('WebsiteLayout easter eggs', () => {
  afterEach(() => {
    resetEasterEggsForTest()
  })

  it('animates the sidebar after five logo activations', async () => {
    const wrapper = mount(WebsiteLayout, {
      global: {
        stubs: {
          ParticleBackground: true,
          RouterLink: true,
          VAppBar: { template: '<header><slot /></header>' },
          VAvatar: { template: '<span class="v-avatar"><slot /></span>' },
          VBtn: { template: '<button><slot /></button>' },
          VIcon: true,
          VList: { template: '<nav v-bind="$attrs"><slot /></nav>' },
          VListItem: { props: ['title'], template: '<div class="v-list-item">{{ title }}</div>' },
          VMain: { template: '<main><slot /></main>' },
          VNavigationDrawer: {
            template: '<aside><slot name="prepend" /><slot /><slot name="append" /></aside>',
          },
          VSpacer: true,
          VToolbarTitle: { template: '<h1><slot /></h1>' },
        },
      },
    })

    for (let i = 0; i < 5; i += 1) {
      await wrapper.find('.brand-trigger').trigger('click')
    }
    await nextTick()

    expect(wrapper.find('.drawer-list--shuffle').exists()).toBe(true)
  })
})
