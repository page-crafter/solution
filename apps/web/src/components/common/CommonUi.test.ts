import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { vuetify } from '../../plugins/vuetify'
import AdminPageShell from './AdminPageShell.vue'
import EmptyState from './EmptyState.vue'
import JobStatusChip from './JobStatusChip.vue'
import PageHeader from './PageHeader.vue'

describe('common UI components', () => {
  it('renders a page header with action slot content', () => {
    const wrapper = mount(PageHeader, {
      props: {
        title: 'Pages',
        description: 'Browse synced pages.',
      },
      slots: {
        actions: '<button>Refresh</button>',
      },
      global: { plugins: [vuetify] },
    })

    expect(wrapper.text()).toContain('Pages')
    expect(wrapper.text()).toContain('Browse synced pages.')
    expect(wrapper.text()).toContain('Refresh')
  })

  it('renders the admin page shell with actions and fill layout', () => {
    const wrapper = mount(AdminPageShell, {
      props: {
        title: 'Pages',
        description: 'Browse synced pages.',
        fill: true,
      },
      slots: {
        actions: '<button>Sync</button>',
        default: '<section>Admin content</section>',
      },
      global: { plugins: [vuetify] },
    })

    expect(wrapper.classes()).toContain('admin-page-shell--fill')
    expect(wrapper.find('.admin-page-shell__content--fill').exists()).toBe(true)
    expect(wrapper.text()).toContain('Pages')
    expect(wrapper.text()).toContain('Browse synced pages.')
    expect(wrapper.text()).toContain('Sync')
    expect(wrapper.text()).toContain('Admin content')
  })

  it('renders a reusable empty state', () => {
    const wrapper = mount(EmptyState, {
      props: {
        icon: 'mdi-file-search-outline',
        title: 'No results',
        message: 'Try another filter.',
      },
      global: { plugins: [vuetify] },
    })

    expect(wrapper.text()).toContain('No results')
    expect(wrapper.text()).toContain('Try another filter.')
  })

  it('maps job status into a chip label', () => {
    const wrapper = mount(JobStatusChip, {
      props: { status: 'failed' },
      global: { plugins: [vuetify] },
    })

    expect(wrapper.text()).toContain('failed')
  })
})
