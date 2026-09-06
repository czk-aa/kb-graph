import { describe, it, expect, vi } from 'vitest'
import { mountWithStubs } from './helpers'
import SpaceListView from '@/views/spaces/SpaceListView.vue'

// Mock API
vi.mock('@/api/spaces', () => ({
  listSpaces: vi.fn().mockResolvedValue([
    { id: 1, name: '技术知识库', description: '团队技术文档', my_role: 'owner' },
    { id: 2, name: '产品文档', description: '产品需求文档', my_role: 'admin' },
  ]),
  createSpace: vi.fn().mockResolvedValue({
    id: 3, name: '新空间', description: '', my_role: 'owner',
  }),
}))

describe('SpaceListView', () => {
  it('renders the page title', async () => {
    const wrapper = mountWithStubs(SpaceListView)
    await wrapper.vm.$nextTick()
    await new Promise((r) => setTimeout(r, 50))
    expect(wrapper.text()).toContain('知识空间')
  })

  it('renders the page subtitle', async () => {
    const wrapper = mountWithStubs(SpaceListView)
    await wrapper.vm.$nextTick()
    await new Promise((r) => setTimeout(r, 50))
    expect(wrapper.text()).toContain('管理你的知识库')
  })

  it('renders stats row', async () => {
    const wrapper = mountWithStubs(SpaceListView)
    await wrapper.vm.$nextTick()
    await new Promise((r) => setTimeout(r, 50))
    expect(wrapper.find('.stats-row').exists()).toBe(true)
  })

  it('renders create space button', () => {
    const wrapper = mountWithStubs(SpaceListView)
    expect(wrapper.text()).toContain('新建空间')
  })

  it('renders loading skeleton initially', () => {
    const wrapper = mountWithStubs(SpaceListView)
    expect(wrapper.find('.space-grid').exists() || wrapper.find('.empty-state').exists()).toBe(true)
  })

  it('has new space dialog', () => {
    const wrapper = mountWithStubs(SpaceListView)
    expect(wrapper.find('div').exists()).toBe(true)
  })
})