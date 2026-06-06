import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StepProgress from './StepProgress.vue'

describe('StepProgress', () => {
  const steps = ['World', 'Characters', 'Plot', 'Scenes']

  it('renders one label per step', () => {
    const wrapper = mount(StepProgress, { props: { steps, current: 1 } })
    const labels = wrapper.findAll('span.whitespace-nowrap')
    expect(labels).toHaveLength(steps.length)
    expect(labels.map((l) => l.text())).toEqual(steps)
  })

  it('marks the current step with the active pulse class', () => {
    const wrapper = mount(StepProgress, { props: { steps, current: 2 } })
    const circles = wrapper.findAll('.rounded-full')
    expect(circles[1].classes()).toContain('animate-pulse')
    expect(circles[1].classes()).toContain('bg-indigo-500')
  })

  it('marks completed steps with a check mark and green background', () => {
    const wrapper = mount(StepProgress, { props: { steps, current: 3 } })
    const circles = wrapper.findAll('.rounded-full')
    expect(circles[0].classes()).toContain('bg-green-600')
    expect(circles[0].text()).toBe('✓')
    expect(circles[1].classes()).toContain('bg-green-600')
  })

  it('marks upcoming steps as muted and shows their index number', () => {
    const wrapper = mount(StepProgress, { props: { steps, current: 1 } })
    const circles = wrapper.findAll('.rounded-full')
    expect(circles[3].classes()).toContain('bg-gray-800')
    expect(circles[3].text()).toBe('4')
  })

  it('renders connector lines between steps (one fewer than steps)', () => {
    const wrapper = mount(StepProgress, { props: { steps, current: 1 } })
    const connectors = wrapper.findAll('.h-px')
    expect(connectors).toHaveLength(steps.length - 1)
  })
})
