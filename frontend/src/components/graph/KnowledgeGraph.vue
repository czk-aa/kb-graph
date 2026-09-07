<template>
  <div class="graph-wrapper">
    <!-- 工具栏 -->
    <div class="graph-toolbar">
      <el-input
        v-model="search"
        placeholder="搜索实体…"
        size="small"
        clearable
        style="width: 180px"
        :prefix-icon="SearchIcon"
        @keyup.enter="doSearch"
        @clear="doSearch"
      />
      <el-select v-model="typeFilter" size="small" clearable placeholder="类型筛选" style="width: 130px" @change="doSearch">
        <el-option label="技术" value="technology" />
        <el-option label="概念" value="concept" />
        <el-option label="人物" value="person" />
        <el-option label="组织" value="organization" />
        <el-option label="产品" value="product" />
        <el-option label="事件" value="event" />
        <el-option label="其他" value="other" />
      </el-select>

      <div class="toolbar-spacer" />

      <!-- 图例 -->
      <div class="graph-legend">
        <span
          v-for="item in legendItems"
          :key="item.type"
          class="legend-dot"
          :style="{
            background: item.color,
            opacity: typeFilter && typeFilter !== item.type ? 0.4 : 1,
          }"
          :title="item.label"
        />
      </div>

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

    <!-- 图谱容器 -->
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

    <!-- 工具提示 -->
    <div ref="tooltip" class="graph-tooltip" v-show="tooltipVisible" :style="tooltipStyle">
      <div class="tooltip-name">{{ tooltipData.name }}</div>
      <div class="tooltip-type">{{ tooltipData.type }}</div>
      <div class="tooltip-meta" v-if="tooltipData.mentionCount">
        提及 {{ tooltipData.mentionCount }} 次
        <template v-if="tooltipData.docCount"> · {{ tooltipData.docCount }} 篇文档</template>
      </div>
      <div class="tooltip-desc" v-if="tooltipData.description">{{ tooltipData.description }}</div>
    </div>

    <!-- 实体详情抽屉 -->
    <el-drawer v-model="drawerVisible" title="实体详情" size="380px">
      <template v-if="selectedEntity">
        <div class="entity-detail">
          <div class="entity-header">
            <div class="entity-avatar" :style="{ background: typeColor(selectedEntity.type) }">
              {{ selectedEntity.name.charAt(0) }}
            </div>
            <div class="entity-info">
              <h3>{{ selectedEntity.name }}</h3>
              <el-tag size="small" :type="typeTagColor(selectedEntity.type)" effect="light">
                {{ typeLabel(selectedEntity.type) }}
              </el-tag>
            </div>
          </div>
          <p v-if="selectedEntity.description" class="desc">{{ selectedEntity.description }}</p>
          <div class="meta-row">
            <div class="meta-item">
              <span class="meta-label">提及次数</span>
              <span class="meta-value">{{ selectedEntity.mention_count }}</span>
            </div>
          </div>
          <div v-if="selectedEntity.aliases?.length" class="aliases-section">
            <h4>别名</h4>
            <div class="alias-tags">
              <el-tag v-for="a in selectedEntity.aliases" :key="a" size="small" effect="plain">{{ a }}</el-tag>
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
import { cleanupOrphanEntities, getGraphOverview, getSubgraph, getEntityDetail, type GraphNode, type GraphEdge } from '@/api/graph'

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
const tooltipData = ref<{ name: string; type: string; mentionCount?: number; docCount?: number; description?: string }>({ name: '', type: '' })
const tooltipStyle = ref({ left: '0px', top: '0px' })
const cleaning = ref(false)

let graph: Graph | null = null
let resizeObserver: ResizeObserver | null = null
const resizeDebounce = ref<ReturnType<typeof setTimeout> | null>(null)

const TYPE_COLORS: Record<string, string> = {
  technology: '#3b82f6',
  concept: '#8b5cf6',
  person: '#ec4899',
  organization: '#f59e0b',
  product: '#10b981',
  event: '#ef4444',
  other: '#6b7280',
}

const TYPE_LABELS: Record<string, string> = {
  technology: '技术',
  concept: '概念',
  person: '人物',
  organization: '组织',
  product: '产品',
  event: '事件',
  other: '其他',
}

const legendItems = computed(() =>
  Object.entries(TYPE_COLORS).map(([type, color]) => ({
    type,
    color,
    label: TYPE_LABELS[type] || type,
  })),
)

function typeColor(t: string) {
  return TYPE_COLORS[t] || TYPE_COLORS.other
}

function typeLabel(t: string) {
  return TYPE_LABELS[t] || t
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

function buildG6Data() {
  const g6Nodes = filteredNodes.value.map((n) => ({
    id: String(n.id),
    data: {
      label: n.name,
      type: n.type,
      mentionCount: n.mention_count,
      description: n.description,
      color: TYPE_COLORS[n.type] || TYPE_COLORS.other,
      // 节点大小：基础 28 + 提及次数的对数缩放 + 类型加成
      size: 28 + Math.log2(n.mention_count + 1) * 6,
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

  return { nodes: g6Nodes, edges: g6Edges }
}

function renderGraph() {
  if (!container.value) return
  const width = container.value.clientWidth || 800
  const height = container.value.clientHeight || 500
  if (width === 0 || height === 0) return

  const g6Data = buildG6Data()

  if (graph) {
    // 更新已有图实例（性能优化：不销毁重建）
    graph.setData(g6Data)
    graph.render()
    return
  }

  // 首次创建
  graph = new Graph({
    container: container.value,
    width,
    height,
    data: g6Data,
    layout: {
      type: 'force',
      preventOverlap: true,
      linkDistance: 200,
      nodeStrength: -300,
      edgeStrength: 0.15,
      animation: false,
    },
    node: {
      style: (d: any) => ({
        fill: d.data?.color || '#3b82f6',
        size: d.data?.size || 32,
        labelText: d.data?.label || '',
        labelFill: '#ffffff',
        labelFontSize: 11,
        labelFontWeight: 600,
        labelPlacement: 'bottom',
        labelOffsetY: 8,
        labelMaxLines: 1,
        labelWordWrap: false,
        // 外发光
        shadowBlur: 12,
        shadowColor: (d.data?.color || '#3b82f6') + '80',
        // 描边
        stroke: '#ffffff',
        lineWidth: 1.5,
      }),
      state: {
        selected: {
          shadowBlur: 24,
          shadowColor: '#f59e0b',
          stroke: '#f59e0b',
          lineWidth: 3,
        },
        hover: {
          shadowBlur: 20,
          shadowColor: (d: any) => (d.data?.color || '#3b82f6') + 'cc',
          lineWidth: 2.5,
        },
      },
    },
    edge: {
      style: (d: any) => ({
        stroke: (d.data?.weight || 1) > 2 ? '#94a3b8' : '#cbd5e1',
        lineWidth: Math.min((d.data?.weight || 1) * 1.2, 4),
        lineDash: (d.data?.weight || 1) <= 1 ? [4, 4] : undefined,
        labelText: d.data?.label || '',
        labelFontSize: 10,
        labelFill: '#64748b',
        labelBackground: true,
        labelBackgroundFill: '#1e293b',
        labelBackgroundOpacity: 0.85,
        labelBackgroundCornerRadius: 4,
        labelPadding: [2, 6],
        endArrow: true,
        endArrowSize: 10,
        opacity: 0.7,
      }),
      state: {
        hover: { stroke: '#f59e0b', lineWidth: 2.5, opacity: 1 },
      },
    },
    behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element', {
      type: 'hover-activate',
      degree: 1,
      // 仅高亮目标节点和边，降低性能开销
    }],
    plugins: [
      {
        type: 'minimap',
        size: [180, 120],
        backgroundColor: '#0f172a',
        border: '1px solid #334155',
        filter: (d: any) => d.id !== undefined,
      },
    ],
    autoFit: false,
    animation: false,
  })

  // 布局完成后渐显
  graph.on('afterlayout', () => {
    if (container.value) {
      container.value.style.opacity = '1'
    }
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

  graph.on('node:dblclick', async (evt: any) => {
    const nodeId = evt.target?.id
    if (!nodeId) return
    try {
      loading.value = true
      const subgraph = await getSubgraph(props.spaceId, Number(nodeId), 2)
      if (subgraph.nodes.length > 0) {
        // 合并子图数据到当前图谱
        const existingIds = new Set(nodes.value.map((n) => n.id))
        const newNodes = subgraph.nodes.filter((n) => !existingIds.has(n.id))
        const existingEdgeKeys = new Set(edges.value.map((e) => `${e.src_id}-${e.dst_id}-${e.relation}`))
        const newEdges = subgraph.edges.filter((e) => !existingEdgeKeys.has(`${e.src_id}-${e.dst_id}-${e.relation}`))

        if (newNodes.length > 0 || newEdges.length > 0) {
          nodes.value = [...nodes.value, ...newNodes]
          edges.value = [...edges.value, ...newEdges]
          await nextTick()
          if (graph) {
            graph.setData(buildG6Data())
            graph.render()
          }
          ElMessage.info(`已扩展 ${newNodes.length} 个实体, ${newEdges.length} 条关系`)
        } else {
          ElMessage.info('该实体已展示完整子图')
        }
      }
    } catch { /* ignore */ }
    finally {
      loading.value = false
    }
  })

  graph.on('node:pointerenter', (evt: any) => {
    const nodeId = evt.target?.id
    if (!nodeId || !tooltip.value) return
    const nodeData = g6Data.nodes.find((n) => n.id === nodeId)
    if (!nodeData) return
    const rawNode = filteredNodes.value.find((n) => String(n.id) === nodeId)
    tooltipData.value = {
      name: nodeData.data.label,
      type: typeLabel(nodeData.data.type),
      mentionCount: nodeData.data.mentionCount,
      docCount: rawNode?.doc_count || 0,
      description: nodeData.data.description || '',
    }
    tooltipVisible.value = true
    const rect = container.value!.getBoundingClientRect()
    tooltipStyle.value = {
      left: `${evt.client.x - rect.left + 14}px`,
      top: `${evt.client.y - rect.top - 14}px`,
    }
  })

  graph.on('node:pointerleave', () => {
    tooltipVisible.value = false
  })

  graph.on('canvas:click', () => {
    tooltipVisible.value = false
  })

  graph.on('wheelzoom', updateZoom)
  graph.on('zoom', updateZoom)

  // 设置初始透明度为 0，布局完成后渐显
  if (container.value) {
    container.value.style.opacity = '0'
    container.value.style.transition = 'opacity 0.6s ease'
  }
  graph.render()
}

function updateZoom() {
  if (graph) {
    zoomPercent.value = Math.round((graph.getZoom?.() || 1) * 100)
  }
}

function zoomIn() {
  if (!graph) return
  const z = graph.getZoom?.() || 1
  graph.zoomTo?.(z * 1.4)
  updateZoom()
}
function zoomOut() {
  if (!graph) return
  const z = graph.getZoom?.() || 1
  graph.zoomTo?.(z / 1.4)
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

async function handleCleanup() {
  try {
    await ElMessageBox.confirm(
      '将删除不再被任何文档引用的孤立实体，此操作无法撤销。确定继续？',
      '确认清理',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' },
    )
    cleaning.value = true
    const { deleted } = await cleanupOrphanEntities(props.spaceId)
    if (deleted === 0) {
      ElMessage.success('没有需要清理的孤立实体')
    } else {
      ElMessage.success(`已成功删除 ${deleted} 个孤立实体`)
    }
    await loadData()
  } catch {
    // cancelled
  } finally {
    cleaning.value = false
  }
}

function typeTagColor(t: string) {
  const map: Record<string, 'primary' | 'danger' | 'warning' | 'info' | 'success'> = {
    technology: 'primary',
    concept: '' as any,
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
      if (resizeDebounce.value) clearTimeout(resizeDebounce.value)
      resizeDebounce.value = setTimeout(() => {
        if (graph && container.value) {
          const w = container.value.clientWidth
          const h = container.value.clientHeight
          if (w > 0 && h > 0) {
            graph.setSize?.(w, h)
          }
        }
      }, 200)
    })
    resizeObserver.observe(container.value)
  }
})

onUnmounted(() => {
  resizeDebounce.value && clearTimeout(resizeDebounce.value)
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

/* Toolbar */
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

.graph-legend {
  display: flex;
  gap: 6px;
  align-items: center;
  padding: 0 var(--space-2);
}
.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid rgba(255,255,255,0.8);
  cursor: pointer;
  transition: opacity 0.2s;
  box-shadow: 0 1px 3px rgba(0,0,0,0.15);
}
.legend-dot:hover {
  transform: scale(1.2);
}

.graph-info {
  font-size: var(--font-size-xs);
  color: var(--color-gray-500);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
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

/* Canvas */
.graph-canvas-wrapper {
  flex: 1;
  position: relative;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: radial-gradient(ellipse at center, #1e293b 0%, #0f172a 100%);
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
  background: radial-gradient(ellipse at center, #1e293b 0%, #0f172a 100%);
}
.loading-icon { animation: spin 1s linear infinite; }
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Tooltip */
.graph-tooltip {
  position: absolute;
  z-index: 100;
  background: #1e293b;
  color: #e2e8f0;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  pointer-events: none;
  white-space: nowrap;
  max-width: 240px;
  border: 1px solid #334155;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  line-height: 1.5;
}
.tooltip-name {
  font-weight: 600;
  font-size: 13px;
  color: white;
}
.tooltip-type {
  opacity: 0.7;
  font-size: 11px;
}
.tooltip-meta {
  margin-top: 4px;
  font-size: 11px;
  color: #94a3b8;
}
.tooltip-desc {
  margin-top: 4px;
  font-size: 11px;
  color: #94a3b8;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Entity Detail */
.entity-detail {}
.entity-header {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}
.entity-avatar {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 20px;
  font-weight: 700;
  flex-shrink: 0;
}
.entity-info h3 {
  margin: 0 0 var(--space-1);
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
.aliases-section {
  margin-bottom: var(--space-4);
}
.aliases-section h4,
.docs-section h4 {
  margin: 0 0 var(--space-2);
  font-size: var(--font-size-sm);
  color: var(--color-gray-600);
}
.alias-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}
.docs-section {}
.doc-link {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) 0;
  cursor: pointer;
  color: var(--color-primary-600);
  font-size: var(--font-size-sm);
  transition: color var(--transition-fast);
  border-bottom: 1px solid var(--color-gray-100);
}
.doc-link:hover {
  color: var(--color-primary-700);
  text-decoration: underline;
}
</style>