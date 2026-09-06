import { describe, it, expect } from 'vitest'
import { mountWithStubs } from './helpers'
import EmptyState from '@/components/common/EmptyState.vue'
import { Document } from '@element-plus/icons-vue'

describe('EmptyState', () => {
  it('renders title and description', () => {
    const wrapper = mountWithStubs(EmptyState, {
      props: { icon: Document, title: '暂无数据', description: '请先创建内容' },
    })
    expect(wrapper.text()).toContain('暂无数据')
    expect(wrapper.text()).toContain('请先创建内容')
  })

  it('renders action button when actionText is provided', () => {
    const wrapper = mountWithStubs(EmptyState, {
      props: { icon: Document, title: '空状态', actionText: '立即创建' },
    })
    expect(wrapper.text()).toContain('立即创建')
  })

  it('does not render action button when actionText is empty', () => {
    const wrapper = mountWithStubs(EmptyState, {
      props: { icon: Document, title: '空状态' },
    })
    expect(wrapper.text()).not.toContain('立即创建')
  })

  it('renders the empty-state container', () => {
    const wrapper = mountWithStubs(EmptyState, {
      props: { icon: Document, title: 'Test' },
    })
    expect(wrapper.find('.empty-state').exists()).toBe(true)
  })

  it('applies custom size prop', () => {
    const wrapper = mountWithStubs(EmptyState, {
      props: { icon: Document, title: 'Test', size: 80 },
    })
    expect(wrapper.find('.empty-state').exists()).toBe(true)
  })
})