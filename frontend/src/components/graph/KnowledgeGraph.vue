<template>
  <div class="graph-wrapper">
    <div class="graph-toolbar">
      <el-input
        v-model="search"
        placeholder="搜索实体…"
        size="small"
        clearable
        style="width: 200px"
        :prefix-icon="SearchIcon"
        @keyup.enter="doSearch"
        @clear="doSearch"
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

      <div class="toolbar-spacer" />

      <span class="graph-info">{{ filteredNodes.length }} 实体, {{ filteredEdges.length }} 关系</span>

      <el-button size="small" text type="warning" @click="handleCleanup" :loading="cleaning">
        <el-icon :size="14"><Delete /></el-icon>
        清理孤立实体
      </el-button>

      <div class="zoom-controls">
        <el-button circle size="small" @click="zoomOut" :disabled="!graph">
          <el-icon :size="14"><Minus /></el-icon>
        </el-button>
        <span class="zoom-level">{{ zoomPercent }}%</span>
        <el-button circle size="small" @click="zoomIn" :disabled="!graph">
          <el-icon :size="14"><Plus /></el-icon>
        </el-button>
        <el-button circle size="small" @click="fitView" :disabled="!graph">
          <el-icon :size="14"><FullScreen /></el-icon>
        </el-button>
      </div>
    </div>

    <div class="graph-canvas-wrapper">
      <div v-if="loading" class="graph-loading">
        <el-icon :size="32" class="loading-icon"><Loading /></el-icon>
        <span>加载图谱数据…</span>
      </div>
      <div v-else-if="nodes.length === 0" class="graph-empty">
        <el-icon :size="64" color="var(--color-gray-300)"><Share /></el-icon>
        <h3>暂无图谱数据</h3>
        <p>创建文档后，AI 将自动抽取实体和关系构建知识图谱</p>
      </div>
      <div ref="container" class="graph-canvas" :class="{ hidden: loading || nodes.length === 0 }" />
    </div>

    <div ref="tooltip" class="graph-tooltip" v-show="tooltipVisible" :style="tooltipStyle">
      <div class="tooltip-name">{{ tooltipData.name }}</div>
      <div class="tooltip-type">{{ tooltipData.type }}</div>
    </div>

    <el-drawer v-model="drawerVisible" title="实体详情" size="380px">
      <template v-if="selectedEntity">
        <div class="entity-detail">
          <div class="entity-header">
            <h3>{{ selectedEntity.name }}</h3>
            <el-tag size="small" :type="typeTagColor(selectedEntity.type)" effect="light">
              {{ selectedEntity.type }}
            </el-tag>
          </div>
          <p v-if="selectedEntity.description" class="desc">{{ selectedEntity.description }}</p>
          <div class="meta-row">
            <div class="meta-item">
              <span class="meta-label">提及次数</span>
              <span class="meta-value">{{ selectedEntity.mention_count }}</span>
            </div>
          </div>
          <div v-if="selectedEntity.documents?.length" class="docs-section">
            <h4>关联文档</h4>
            <div
              v-for="doc in selectedEntity.documents"
              :key="doc.id"
              class="doc-link"
              @click="openDoc(doc.id)"
            >
              <el-icon :size="14"><Document /></el-icon>
              <span>{{ doc.title }}</span>
            </div>
          </div>
        </div>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { Graph } from '@antv/g6'
import { Search as SearchIcon, Minus, Plus, FullScreen, Loading, Share, Document, Delete } from '@element-plus/icons-vue'
import { cleanupOrphanEntities, getGraphOverview, getEntityDetail, type GraphNode, type GraphEdge } from '@/api/graph'

const props = defineProps<{ spaceId: number }>()
const router = useRouter()

const container = ref<HTMLElement>()
const tooltip = ref<HTMLElement>()
const search = ref('')
const typeFilter = ref('')
const nodes = ref<GraphNode[]>([])
const edges = ref<GraphEdge[]>([])
const loading = ref(true)
const drawerVisible = ref(false)
const selectedEntity = ref<any>(null)
const zoomPercent = ref(100)
const tooltipVisible = ref(false)
const tooltipData = ref<{ name: string; type: string }>({ name: '', type: '' })
const tooltipStyle = ref({ left: '0px', top: '0px' })

let graph: Graph | null = null
let resizeObserver: ResizeObserver | null = null

const TYPE_COLORS: Record<string, string> = {
  technology: '#3b82f6',
  concept: '#8b5cf6',
  person: '#ec4899',
  organization: '#f59e0b',
  product: '#10b981',
  event: '#ef4444',
  other: '#6b7280',
}

const filteredNodes = computed(() => {
  if (!typeFilter.value) return nodes.value
  return nodes.value.filter((n) => n.type === typeFilter.value)
})
const filteredEdges = computed(() => {
  if (!typeFilter.value) return edges.value
  const nodeIds = new Set(filteredNodes.value.map((n) => String(n.id)))
  return edges.value.filter((e) => nodeIds.has(String(e.src_id)) && nodeIds.has(String(e.dst_id)))
})

async function loadData() {
  loading.value = true
  try {
    const data = await getGraphOverview(props.spaceId, {
      search: search.value || undefined,
      type_filter: typeFilter.value || undefined,
    })
    nodes.value = data.nodes
    edges.value = data.edges
    await nextTick()
    renderGraph()
  } finally {
    loading.value = false
  }
}

function renderGraph() {
  if (!container.value) return

  if (graph) {
    graph.destroy()
    graph = null
  }

  const width = container.value.clientWidth || 800
  const height = container.value.clientHeight || 500

  if (width === 0 || height === 0) return

  const g6Nodes = filteredNodes.value.map((n) => ({
    id: String(n.id),
    data: {
      label: n.name,
      type: n.type,
      mentionCount: n.mention_count,
      description: n.description,
      color: TYPE_COLORS[n.type] || TYPE_COLORS.other,
      size: Math.min((TYPE_COLORS[n.type] ? 32 : 26) + Math.log2(n.mention_count + 1) * 4, 50),
    },
  }))

  const g6Edges = filteredEdges.value.map((e, idx) => ({
    id: `edge-${e.src_id}-${e.dst_id}-${idx}`,
    source: String(e.src_id),
    target: String(e.dst_id),
    data: {
      label: e.relation,
      weight: e.weight,
    },
  }))

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
      edgeStrength: 0.1,
    },
    node: {
      style: (d: any) => ({
        fill: d.data?.color || '#3b82f6',
        size: d.data?.size || 32,
        labelText: d.data?.label || '',
        labelFill: '#1f2937',
        labelFontSize: 12,
        labelPlacement: 'bottom',
        labelOffsetY: 6,
        labelFontWeight: 500,
      }),
      state: {
        hover: {
          fill: '#f59e0b',
          lineWidth: 3,
          shadowBlur: 10,
          shadowColor: 'rgba(59,130,246,0.4)',
        },
      },
    },
    edge: {
      style: (d: any) => ({
        stroke: '#d1d5db',
        lineWidth: Math.min((d.data?.weight || 1) * 1.5, 4),
        labelText: d.data?.label || '',
        labelFontSize: 10,
        labelFill: '#6b7280',
        labelBackground: true,
        labelBackgroundFill: '#fff',
        labelBackgroundOpacity: 0.8,
        endArrow: true,
      }),
      state: {
        hover: { stroke: '#3b82f6', lineWidth: 3 },
      },
    },
    behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element', 'hover-activate'],
    autoFit: 'view',
    animation: true,
  })

  graph.on('node:click', async (evt: any) => {
    const nodeId = evt.target?.id
    if (!nodeId) return
    try {
      const detail = await getEntityDetail(Number(nodeId))
      selectedEntity.value = detail
      drawerVisible.value = true
    } catch { /* ignore */ }
  })

  graph.on('node:pointerenter', (evt: any) => {
    const nodeId = evt.target?.id
    if (!nodeId || !tooltip.value) return
    const nodeData = g6Nodes.find((n) => n.id === nodeId)
    if (!nodeData) return
    tooltipData.value = { name: nodeData.data.label, type: nodeData.data.type }
    tooltipVisible.value = true
    const rect = container.value!.getBoundingClientRect()
    tooltipStyle.value = {
      left: `${evt.client.x - rect.left + 12}px`,
      top: `${evt.client.y - rect.top - 12}px`,
    }
  })

  graph.on('node:pointerleave', () => {
    tooltipVisible.value = false
  })

  graph.on('canvas:click', () => {
    tooltipVisible.value = false
  })

  graph.render().then(() => {
    updateZoom()
  })
}

function updateZoom() {
  if (graph) {
    zoomPercent.value = Math.round((graph.getZoom?.() || 1) * 100)
  }
}

function zoomIn() {
  if (!graph) return
  const z = graph.getZoom?.() || 1
  graph.zoomTo?.(z * 1.3)
  updateZoom()
}
function zoomOut() {
  if (!graph) return
  const z = graph.getZoom?.() || 1
  graph.zoomTo?.(z / 1.3)
  updateZoom()
}
function fitView() {
  graph?.fitView?.()
  setTimeout(updateZoom, 400)
}

function doSearch() {
  loadData()
}

function openDoc(docId: number) {
  drawerVisible.value = false
  router.push(`/spaces/${props.spaceId}/documents/${docId}`)
}

const cleaning = ref(false)

async function handleCleanup() {
  try {
    await ElMessageBox.confirm(
      '将删除不再被任何文档引用的孤立实体，此操作无法撤销。确定继续？',
      '确认清理',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    cleaning.value = true
    const { deleted } = await cleanupOrphanEntities(props.spaceId)
    if (deleted === 0) {
      ElMessage.success('没有需要清理的孤立实体')
    } else {
      ElMessage.success(`已成功删除 ${deleted} 个孤立实体`)
    }
    await loadData()
    cleaning.value = false
  } catch {
    cleaning.value = false
  }
}

function typeTagColor(t: string) {
  const map: Record<string, 'primary' | 'danger' | 'warning' | 'info' | 'success'> = {
    technology: 'primary',
    concept: '',
    person: 'danger',
    organization: 'warning',
    product: 'success',
    event: 'danger',
  }
  return map[t] || 'info'
}

onMounted(async () => {
  await loadData()
  if (container.value) {
    resizeObserver = new ResizeObserver(() => {
      if (graph && container.value) {
        const w = container.value.clientWidth
        const h = container.value.clientHeight
        if (w > 0 && h > 0) {
          graph.setSize?.(w, h)
        }
      }
    })
    resizeObserver.observe(container.value)
  }
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
.graph-wrapper {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 320px);
  min-height: 500px;
}

.graph-toolbar {
  display: flex;
  gap: var(--space-3);
  align-items: center;
  padding: var(--space-2) var(--space-4);
  background: white;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-gray-200);
  margin-bottom: var(--space-3);
  flex-shrink: 0;
}
.toolbar-spacer { flex: 1; }
.graph-info {
  font-size: var(--font-size-xs);
  color: var(--color-gray-500);
  white-space: nowrap;
}
.zoom-controls {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}
.zoom-level {
  font-size: var(--font-size-xs);
  color: var(--color-gray-500);
  min-width: 36px;
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.graph-canvas-wrapper {
  flex: 1;
  position: relative;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-gray-200);
  overflow: hidden;
  background: #fafafa;
}
.graph-canvas {
  width: 100%;
  height: 100%;
}
.graph-canvas.hidden { display: none; }

.graph-loading,
.graph-empty {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  color: var(--color-gray-400);
  font-size: var(--font-size-sm);
}
.loading-icon { animation: spin 1s linear infinite; }
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.graph-tooltip {
  position: absolute;
  z-index: var(--z-tooltip);
  background: var(--color-gray-900);
  color: white;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  pointer-events: none;
  white-space: nowrap;
}
.tooltip-name { font-weight: 600; }
.tooltip-type { opacity: 0.7; font-size: 11px; }

.entity-detail {}
.entity-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}
.entity-header h3 {
  margin: 0;
  font-size: var(--font-size-lg);
}
.desc {
  color: var(--color-gray-600);
  margin: 0 0 var(--space-4);
  line-height: 1.6;
  font-size: var(--font-size-sm);
}
.meta-row {
  margin-bottom: var(--space-4);
}
.meta-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.meta-label {
  font-size: var(--font-size-xs);
  color: var(--color-gray-500);
}
.meta-value {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-gray-800);
}
.docs-section h4 {
  margin: 0 0 var(--space-3);
  font-size: var(--font-size-sm);
  color: var(--color-gray-600);
}
.doc-link {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) 0;
  cursor: pointer;
  color: var(--color-primary-600);
  font-size: var(--font-size-sm);
  transition: color var(--transition-fast);
}
.doc-link:hover {
  color: var(--color-primary-700);
  text-decoration: underline;
}
</style>