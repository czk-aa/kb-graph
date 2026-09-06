import { describe, it, expect, vi } from 'vitest'
import { mountWithStubs } from './helpers'
import DocumentView from '@/views/document/DocumentView.vue'

// Mock API
vi.mock('@/api/documents', () => ({
  getDocument: vi.fn().mockResolvedValue({
    id: 1, title: '测试文档', content_text: '## Hello World',
    summary: '这是一个测试文档', tags: ['test', 'demo'],
    status: 'ready',
  }),
  saveContent: vi.fn().mockResolvedValue({}),
  updateDocument: vi.fn().mockResolvedValue({}),
  getVersions: vi.fn().mockResolvedValue([
    { version_no: 3, content_md: 'v3 content', created_at: '2026-01-03' },
    { version_no: 2, content_md: 'v2 content', created_at: '2026-01-02' },
    { version_no: 1, content_md: 'v1 content', created_at: '2026-01-01' },
  ]),
  restoreVersion: vi.fn().mockResolvedValue({ content_text: 'restored' }),
  getRelatedDocuments: vi.fn().mockResolvedValue([
    { id: 2, title: '关联文档', summary: '关联内容' },
  ]),
}))
vi.mock('@/components/comment/CommentPanel.vue', () => ({
  default: { template: '<div class="comment-mock">Comments</div>', props: ['docId'] },
}))

describe('DocumentView', () => {
  it('renders the topbar with save button', async () => {
    const wrapper = mountWithStubs(DocumentView)
    await wrapper.vm.$nextTick()
    await new Promise((r) => setTimeout(r, 50))
    expect(wrapper.find('.doc-topbar').exists()).toBe(true)
    expect(wrapper.text()).toContain('保存')
  })

  it('renders the version history button', async () => {
    const wrapper = mountWithStubs(DocumentView)
    await wrapper.vm.$nextTick()
    await new Promise((r) => setTimeout(r, 50))
    expect(wrapper.text()).toContain('版本历史')
  })

  it('renders the editor area', async () => {
    const wrapper = mountWithStubs(DocumentView)
    await wrapper.vm.$nextTick()
    await new Promise((r) => setTimeout(r, 50))
    expect(wrapper.find('.editor-area').exists()).toBe(true)
  })

  it('renders the side panel with AI summary section', async () => {
    const wrapper = mountWithStubs(DocumentView)
    await wrapper.vm.$nextTick()
    await new Promise((r) => setTimeout(r, 50))
    expect(wrapper.find('.side-panel').exists()).toBe(true)
    expect(wrapper.text()).toContain('AI 摘要')
  })

  it('renders the related documents section', async () => {
    const wrapper = mountWithStubs(DocumentView)
    await wrapper.vm.$nextTick()
    await new Promise((r) => setTimeout(r, 50))
    expect(wrapper.text()).toContain('关联文档')
  })

  it('renders the comments section', async () => {
    const wrapper = mountWithStubs(DocumentView)
    await wrapper.vm.$nextTick()
    await new Promise((r) => setTimeout(r, 50))
    expect(wrapper.text()).toContain('评论')
  })

  it('has two-column layout', async () => {
    const wrapper = mountWithStubs(DocumentView)
    await wrapper.vm.$nextTick()
    await new Promise((r) => setTimeout(r, 50))
    expect(wrapper.find('.doc-body').exists()).toBe(true)
  })
})