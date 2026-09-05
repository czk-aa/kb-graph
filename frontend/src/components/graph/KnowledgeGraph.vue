<template>
  <div class="graph-wrapper">
    <div class="graph-toolbar">
      <el-input
        v-model="search"
        placeholder="搜索实体…"
        size="small"
        clearable
        style="width: 200px"
        @keyup.enter="doSearch"
      />
      <el-select v-model="typeFilter" size="small" clearable placeholder="类型筛选" style="width: 140px" @change="doSearch">
        <el-option label="技术" value="technology" />
        <el-option label="概念" value="concept" />
        <el-option label="人物" value="person" />
        <el-option label="组织" value="organization" />
        <el-option label="产品" value="product" />
        <el-option label="事件" value="event" />
        <el-option label="其他" value="other" />
      </el-select>
      <span class="graph-info">{{ nodes.length }} 实体, {{ edges.length }} 关系</span>
    </div>

    <div ref="container" class="graph-canvas" />

    <el-drawer v-model="drawerVisible" title="实体详情" size="360px">
      <template v-if="selectedEntity">
        <div class="entity-detail">
          <h3>{{ selectedEntity.name }}</h3>
          <el-tag size="small" :type="typeColor(selectedEntity.type)">{{ selectedEntity.type }}</el-tag>
          <p v-if="selectedEntity.description" class="desc">{{ selectedEntity.description }}</p>
          <div class="meta">提及次数: {{ selectedEntity.mention_count }}</div>
          <div v-if="selectedEntity.documents?.length" class="docs">
            <h4>关联文档</h4>
            <div
              v-for="doc in selectedEntity.documents"
              :key="doc.id"
              class="doc-link"
              @click="openDoc(doc.id)"
            >
              {{ doc.title }}
            </div>
          </div>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Graph } from '@antv/g6'
import { getGraphOverview, getEntityDetail, type GraphNode, type GraphEdge } from '@/api/graph'

const props = defineProps<{ spaceId: number }>()
const router = useRouter()

const container = ref<HTMLElement>()
const search = ref('')
const typeFilter = ref('')
const nodes = ref<GraphNode[]>([])
const edges = ref<GraphEdge[]>([])
const drawerVisible = ref(false)
const selectedEntity = ref<any>(null)

let graph: Graph | null = null

const TYPE_COLORS: Record<string, string> = {
  technology: '#3b82f6',
  concept: '#8b5cf6',
  person: '#ec4899',
  organization: '#f59e0b',
  product: '#10b981',
  event: '#ef4444',
  other: '#6b7280',
}

const TYPE_SIZES: Record<string, number> = {
  technology: 36,
  concept: 32,
  person: 30,
  organization: 34,
  product: 32,
  event: 28,
  other: 26,
}

async function loadData() {
  const data = await getGraphOverview(props.spaceId, {
    search: search.value || undefined,
    type_filter: typeFilter.value || undefined,
  })
  nodes.value = data.nodes
  edges.value = data.edges
  renderGraph()
}

function renderGraph() {
  if (!container.value) return

  if (graph) {
    graph.destroy()
    graph = null
  }

  const g6Nodes = nodes.value.map((n) => ({
    id: String(n.id),
    data: {
      label: n.name,
      type: n.type,
      mentionCount: n.mention_count,
      description: n.description,
      color: TYPE_COLORS[n.type] || TYPE_COLORS.other,
      size: Math.min(TYPE_SIZES[n.type] || 26 + Math.log2(n.mention_count + 1) * 4, 50),
    },
  }))

  const g6Edges = edges.value.map((e) => ({
    source: String(e.src_id),
    target: String(e.dst_id),
    data: {
      label: e.relation,
      weight: e.weight,
    },
  }))

  const width = container.value.clientWidth || 800
  const height = container.value.clientHeight || 500

  graph = new Graph({
    container: container.value,
    width,
    height,
    data: { nodes: g6Nodes, edges: g6Edges },
    layout: {
      type: 'force',
      preventOverlap: true,
      linkDistance: 150,
      nodeStrength: -200,
    },
    node: {
      style: (d: any) => ({
        fill: d.data?.color || '#3b82f6',
        size: d.data?.size || 32,
        labelText: d.data?.label || '',
        labelFill: '#333',
        labelFontSize: 12,
        labelPlacement: 'bottom',
        labelOffsetY: 6,
      }),
      state: {
        hover: {
          fill: '#f59e0b',
          size: (d: any) => (d.data?.size || 32) + 6,
        },
      },
    },
    edge: {
      style: (d: any) => ({
        stroke: '#c0c4cc',
        lineWidth: Math.min((d.data?.weight || 1) * 1.5, 4),
        labelText: d.data?.label || '',
        labelFontSize: 10,
        labelFill: '#909399',
        labelBackground: true,
      }),
      state: {
        hover: { stroke: '#3b82f6', lineWidth: 3 },
      },
    },
    behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element'],
    autoFit: 'view',
  })

  graph.on('node:click', async (evt: any) => {
    const nodeId = evt.target?.id
    if (!nodeId) return
    const entityId = Number(nodeId)
    try {
      const detail = await getEntityDetail(entityId)
      selectedEntity.value = detail
      drawerVisible.value = true
    } catch { /* ignore */ }
  })

  graph.render()
}

function doSearch() {
  loadData()
}

function openDoc(docId: number) {
  drawerVisible.value = false
  router.push(`/spaces/${props.spaceId}/documents/${docId}`)
}

function typeColor(t: string) {
  return t === 'technology' ? 'primary' : t === 'person' ? 'danger' : t === 'organization' ? 'warning' : 'info'
}

let resizeObserver: ResizeObserver | null = null

onMounted(async () => {
  await loadData()
  resizeObserver = new ResizeObserver(() => {
    if (graph && container.value) {
      const w = container.value.clientWidth
      const h = container.value.clientHeight
      graph.setSize(w, h)
    }
  })
  if (container.value) resizeObserver.observe(container.value)
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  graph?.destroy()
})

watch(() => props.spaceId, () => {
  loadData()
})
</script>

<style scoped>
.graph-wrapper { height: 100%; display: flex; flex-direction: column; }
.graph-toolbar { display: flex; gap: 12px; align-items: center; padding: 12px 0; }
.graph-info { font-size: 12px; color: var(--el-text-color-secondary); margin-left: auto; }
.graph-canvas { flex: 1; min-height: 500px; border: 1px solid var(--el-border-color); border-radius: 8px; background: #fafafa; }

.entity-detail h3 { margin: 0 0 8px; }
.entity-detail .desc { color: var(--el-text-color-secondary); margin: 12px 0; line-height: 1.6; }
.entity-detail .meta { font-size: 13px; color: var(--el-text-color-secondary); margin-bottom: 16px; }
.entity-detail .docs h4 { margin: 0 0 8px; }
.entity-detail .doc-link { padding: 6px 0; cursor: pointer; color: var(--el-color-primary); font-size: 14px; }
.entity-detail .doc-link:hover { text-decoration: underline; }
</style>