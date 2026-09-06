import { describe, it, expect } from 'vitest'
import { mountWithStubs } from './helpers'
import RegisterView from '@/views/auth/RegisterView.vue'

describe('RegisterView', () => {
  it('renders the brand section', () => {
    const wrapper = mountWithStubs(RegisterView)
    expect(wrapper.text()).toContain('加入 KB-Graph')
    expect(wrapper.text()).toContain('AI 驱动的知识管理之旅')
  })

  it('renders form title', () => {
    const wrapper = mountWithStubs(RegisterView)
    expect(wrapper.text()).toContain('创建账号')
  })

  it('renders form fields', () => {
    const wrapper = mountWithStubs(RegisterView)
    expect(wrapper.find('form').exists()).toBe(true)
    expect(wrapper.text()).toContain('注册')
  })

  it('has register button', () => {
    const wrapper = mountWithStubs(RegisterView)
    expect(wrapper.text()).toContain('注册')
  })

  it('has login link', () => {
    const wrapper = mountWithStubs(RegisterView)
    expect(wrapper.text()).toContain('立即登录')
  })

  it('has auth-brand and auth-form-section', () => {
    const wrapper = mountWithStubs(RegisterView)
    expect(wrapper.find('.auth-brand').exists()).toBe(true)
    expect(wrapper.find('.auth-form-section').exists()).toBe(true)
  })

  it('has auth-card', () => {
    const wrapper = mountWithStubs(RegisterView)
    expect(wrapper.find('.auth-card').exists()).toBe(true)
  })
})