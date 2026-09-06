import { describe, it, expect } from 'vitest'
import { mountWithStubs } from './helpers'
import LoginView from '@/views/auth/LoginView.vue'

describe('LoginView', () => {
  it('renders the brand section with KB-Graph title', () => {
    const wrapper = mountWithStubs(LoginView)
    expect(wrapper.text()).toContain('KB-Graph')
    expect(wrapper.text()).toContain('AI 驱动的企业知识图谱平台')
  })

  it('renders the form title', () => {
    const wrapper = mountWithStubs(LoginView)
    expect(wrapper.text()).toContain('欢迎回来')
  })

  it('renders brand features', () => {
    const wrapper = mountWithStubs(LoginView)
    expect(wrapper.text()).toContain('知识图谱可视化')
    expect(wrapper.text()).toContain('GraphRAG 混合检索')
    expect(wrapper.text()).toContain('团队协作')
  })

  it('has login button', () => {
    const wrapper = mountWithStubs(LoginView)
    expect(wrapper.text()).toContain('登录')
  })

  it('has register link', () => {
    const wrapper = mountWithStubs(LoginView)
    expect(wrapper.text()).toContain('立即注册')
  })

  it('has auth-brand and auth-form-section layout', () => {
    const wrapper = mountWithStubs(LoginView)
    expect(wrapper.find('.auth-brand').exists()).toBe(true)
    expect(wrapper.find('.auth-form-section').exists()).toBe(true)
  })

  it('has brand-content with features', () => {
    const wrapper = mountWithStubs(LoginView)
    expect(wrapper.find('.brand-content').exists()).toBe(true)
    expect(wrapper.find('.brand-features').exists()).toBe(true)
  })
})