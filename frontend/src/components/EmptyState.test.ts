import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import EmptyState from './EmptyState.vue'

describe('EmptyState', () => {
  it('renders the title', () => {
    const wrapper = mount(EmptyState, { props: { title: 'No projects' } })
    expect(wrapper.find('h3').text()).toBe('No projects')
  })

  it('renders the icon and description when provided', () => {
    const wrapper = mount(EmptyState, {
      props: { title: 'Empty', icon: '📦', description: 'Nothing here' },
    })
    expect(wrapper.text()).toContain('📦')
    expect(wrapper.find('p').text()).toBe('Nothing here')
  })

  it('omits the description paragraph when not provided', () => {
    const wrapper = mount(EmptyState, { props: { title: 'Empty' } })
    expect(wrapper.find('p').exists()).toBe(false)
  })

  it('renders no action button without an actionLabel', () => {
    const wrapper = mount(EmptyState, { props: { title: 'Empty' } })
    expect(wrapper.find('button').exists()).toBe(false)
  })

  it('renders the action button and emits "action" on click', async () => {
    const wrapper = mount(EmptyState, {
      props: { title: 'Empty', actionLabel: 'Create' },
    })
    const button = wrapper.find('button')
    expect(button.exists()).toBe(true)
    expect(button.text()).toBe('Create')

    await button.trigger('click')
    expect(wrapper.emitted('action')).toHaveLength(1)
  })
})
