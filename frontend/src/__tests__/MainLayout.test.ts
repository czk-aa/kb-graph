import { describe, it, expect, vi } from 'vitest'
import { mountWithStubs } from './helpers'
import MainLayout from '@/layouts/MainLayout.vue'

vi.mock('@/components/notification/NotificationBell.vue', () => ({
  default: { template: '<div class="bell-mock">Bell</div>' },
}))

describe('MainLayout', () => {
  it('renders the sidebar', () => {
    const wrapper = mountWithStubs(MainLayout)
    expect(wrapper.find('.sidebar').exists()).toBe(true)
  })

  it('renders the logo', () => {
    const wrapper = mountWithStubs(MainLayout)
    expect(wrapper.text()).toContain('KB-Graph')
  })

  it('renders the topbar', () => {
    const wrapper = mountWithStubs(MainLayout)
    expect(wrapper.find('.topbar').exists()).toBe(true)
  })

  it('renders the main content area', () => {
    const wrapper = mountWithStubs(MainLayout)
    expect(wrapper.find('.main-content').exists()).toBe(true)
  })

  it('renders the sidebar navigation', () => {
    const wrapper = mountWithStubs(MainLayout)
    expect(wrapper.find('.sidebar-nav').exists()).toBe(true)
  })

  it('renders sidebar user section', () => {
    const wrapper = mountWithStubs(MainLayout)
    expect(wrapper.find('.sidebar-bottom').exists()).toBe(true)
  })

  it('shows user nickname', () => {
    const wrapper = mountWithStubs(MainLayout)
    expect(wrapper.text()).toContain('TestUser')
  })
})