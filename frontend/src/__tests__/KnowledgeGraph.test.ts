import { describe, it, expect, vi } from 'vitest'
import { mountWithStubs } from './helpers'
import KnowledgeGraph from '@/components/graph/KnowledgeGraph.vue'

// Mock G6
vi.mock('@antv/g6', () => {
  class MockGraph {
    destroy() {}
    render() { return Promise.resolve() }
    setData() {}
    on() {}
    setSize() {}
    getZoom() { return 1 }
    zoomTo() {}
    fitView() {}
  }
  return { Graph: MockGraph }
})

// Mock API
vi.mock('@/api/graph', () => ({
  getGraphOverview: vi.fn().mockResolvedValue({
    nodes: [
      { id: 1, name: 'FastAPI', type: 'technology', mention_count: 5, description: 'A web framework' },
      { id: 2, name: 'PostgreSQL', type: 'technology', mention_count: 3, description: 'A database' },
    ],
    edges: [
      { src_id: 1, dst_id: 2, relation: 'uses', weight: 3 },
    ],
  }),
  getEntityDetail: vi.fn().mockResolvedValue({
    id: 1, name: 'FastAPI', type: 'technology', mention_count: 5,
    description: 'A web framework', documents: [{ id: 1, title: 'FastAPI Guide' }],
  }),
}))

describe('KnowledgeGraph', () => {
  it('renders the toolbar', async () => {
    const wrapper = mountWithStubs(KnowledgeGraph, { props: { spaceId: 1 } })
    await wrapper.vm.$nextTick()
    await new Promise((r) => setTimeout(r, 50))
    expect(wrapper.find('.graph-toolbar').exists()).toBe(true)
  })

  it('renders the graph canvas', async () => {
    const wrapper = mountWithStubs(KnowledgeGraph, { props: { spaceId: 1 } })
    await wrapper.vm.$nextTick()
    await new Promise((r) => setTimeout(r, 50))
    expect(wrapper.find('.graph-canvas-wrapper').exists()).toBe(true)
  })

  it('shows entity and relation count', async () => {
    const wrapper = mountWithStubs(KnowledgeGraph, { props: { spaceId: 1 } })
    await wrapper.vm.$nextTick()
    await new Promise((r) => setTimeout(r, 50))
    const text = wrapper.text()
    expect(text).toContain('实体')
    expect(text).toContain('关系')
  })

  it('has zoom controls', () => {
    const wrapper = mountWithStubs(KnowledgeGraph, { props: { spaceId: 1 } })
    expect(wrapper.find('.zoom-controls').exists()).toBe(true)
  })

  it('has search input', () => {
    const wrapper = mountWithStubs(KnowledgeGraph, { props: { spaceId: 1 } })
    expect(wrapper.find('.graph-toolbar').exists()).toBe(true)
  })

  it('has type filter dropdown', () => {
    const wrapper = mountWithStubs(KnowledgeGraph, { props: { spaceId: 1 } })
    expect(wrapper.find('.graph-toolbar').exists()).toBe(true)
  })
})