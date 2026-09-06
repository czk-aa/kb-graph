import { describe, it, expect, vi } from 'vitest'
import { mountWithStubs } from './helpers'
import SpaceDetailView from '@/views/space/SpaceDetailView.vue'

// Mock API
vi.mock('@/api/spaces', () => ({
  listSpaces: vi.fn().mockResolvedValue([
    { id: 1, name: '技术知识库', description: '团队技术文档', my_role: 'owner' },
  ]),
}))
vi.mock('@/api/documents', () => ({
  listDocuments: vi.fn().mockResolvedValue([
    { id: 1, title: 'FastAPI 架构', status: 'ready', tags: ['FastAPI', 'Python'], updated_at: '2026-01-01' },
    { id: 2, title: 'PostgreSQL 指南', status: 'processing', tags: ['PostgreSQL'], updated_at: '2026-01-01' },
  ]),
  createDocument: vi.fn().mockResolvedValue({ id: 3, title: '新文档' }),
  deleteDocument: vi.fn(),
  uploadFiles: vi.fn(),
}))
vi.mock('@/components/graph/KnowledgeGraph.vue', () => ({
  default: { template: '<div class="graph-mock">Graph</div>', props: ['spaceId'] },
}))
vi.mock('@/views/space/ChatView.vue', () => ({
  default: { template: '<div class="chat-mock">Chat</div>', props: ['spaceId'] },
}))
vi.mock('@/views/space/SpaceMembers.vue', () => ({
  default: { template: '<div class="members-mock">Members</div>', props: ['spaceId'] },
}))

describe('SpaceDetailView', () => {
  it('renders the space banner', async () => {
    const wrapper = mountWithStubs(SpaceDetailView)
    await wrapper.vm.$nextTick()
    await new Promise((r) => setTimeout(r, 50))
    expect(wrapper.find('.space-banner').exists()).toBe(true)
  })

  it('renders tab navigation', () => {
    const wrapper = mountWithStubs(SpaceDetailView)
    const tabs = wrapper.find('.tabs-wrapper')
    expect(tabs.exists()).toBe(true)
  })

  it('shows four tabs', () => {
    const wrapper = mountWithStubs(SpaceDetailView)
    const tabItems = wrapper.findAll('.tab-item')
    expect(tabItems.length).toBe(4)
  })

  it('tab labels are correct', () => {
    const wrapper = mountWithStubs(SpaceDetailView)
    const text = wrapper.text()
    expect(text).toContain('文档')
    expect(text).toContain('图谱')
    expect(text).toContain('AI问答')
    expect(text).toContain('成员')
  })

  it('has upload button', () => {
    const wrapper = mountWithStubs(SpaceDetailView)
    expect(wrapper.text()).toContain('上传文件')
  })

  it('has create document button', () => {
    const wrapper = mountWithStubs(SpaceDetailView)
    expect(wrapper.text()).toContain('新建文档')
  })
})