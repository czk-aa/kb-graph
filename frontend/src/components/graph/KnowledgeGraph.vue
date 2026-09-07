<template>
  <div class="graph-wrapper">
    <!-- 工具栏 -->
    <div class="graph-toolbar">
      <el-input
        v-model="search"
        placeholder="搜索星系…"
        size="small"
        clearable
        style="width: 160px"
        :prefix-icon="SearchIcon"
        @keyup.enter="doSearch"
        @clear="doSearch"
      />
      <el-select v-model="typeFilter" size="small" clearable placeholder="星体类型" style="width: 130px" @change="doSearch">
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
            opacity: typeFilter && typeFilter !== item.type ? 0.35 : 1,
          }"
          :title="item.label"
        />
      </div>

      <span class="graph-info">{{ filteredNodes.length }} 星体, {{ filteredEdges.length }} 星轨</span>

      <!-- 旋转控制 -->
      <el-button
        size="small"
        text
        @click="toggleRotation"
        :type="isRotating ? 'primary' : 'info'"
      >
        <el-icon :size="14"><component :is="isRotating ? VideoPause : VideoPlay" /></el-icon>
        {{ isRotating ? '暂停旋转' : '旋转星系' }}
      </el-button>

      <el-button size="small" text type="warning" @click="handleCleanup" :loading="cleaning">
        <el-icon :size="14"><Delete /></el-icon>
        清理孤立
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
      <!-- 星空背景画布 -->
      <canvas ref="starCanvasRef" class="starfield-canvas" />
      <div v-if="loading" class="graph-loading">
        <el-icon :size="32" class="loading-icon"><Loading /></el-icon>
        <span>生成星系…</span>
      </div>
      <div v-else-if="nodes.length === 0" class="graph-empty">
        <el-icon :size="64" color="var(--color-gray-300)"><Share /></el-icon>
        <h3>星系尚未形成</h3>
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
    <el-drawer v-model="drawerVisible" title="星体详情" size="380px">
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
import { Search as SearchIcon, Minus, Plus, FullScreen, Loading, Share, Document, Delete, VideoPause, VideoPlay } from '@element-plus/icons-vue'
import { cleanupOrphanEntities, getGraphOverview, getSubgraph, getEntityDetail, type GraphNode, type GraphEdge } from '@/api/graph'

const props = defineProps<{ spaceId: number }>()
const router = useRouter()

const container = ref<HTMLElement>()
const tooltip = ref<HTMLElement>()
const starCanvasRef = ref<HTMLCanvasElement>()
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
const isRotating = ref(true)

let graph: Graph | null = null
let resizeObserver: ResizeObserver | null = null
let rotateRaf: number | null = null
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
  technology: '技术星',
  concept: '概念星',
  person: '人物星',
  organization: '组织星',
  product: '产品星',
  event: '事件星',
  other: '其他星',
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

// 星空背景画布
interface Star {
  x: number; y: number; r: number; alpha: number; speed: number; phase: number
  color: string; blink: boolean
}
interface Nebula { x: number; y: number; r: number; color: string; alpha: number }
interface ShootingStar {
  x: number; y: number; dx: number; dy: number; life: number; maxLife: number; alpha: number
}

let stars: Star[] = []
let nebulae: Nebula[] = []
let shootingStars: ShootingStar[] = []
let starAnimId: number | null = null
let starTimer = 0

function createStarfield() {
  const canvas = starCanvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const W = (canvas.width = canvas.clientWidth)
  const H = (canvas.height = canvas.clientHeight)

  // 生成 600 颗恒星
  stars = []
  for (let i = 0; i < 600; i++) {
    const r = Math.random()
    stars.push({
      x: Math.random() * W,
      y: Math.random() * H,
      r: r < 0.7 ? Math.random() * 1.2 + 0.3    // 70% 小星
           : r < 0.9 ? Math.random() * 1.5 + 1.2  // 20% 中星
           : Math.random() * 2 + 2.5,              // 10% 亮星
      alpha: Math.random() * 0.6 + 0.2,
      speed: Math.random() * 0.02 + 0.005,
      phase: Math.random() * Math.PI * 2,
      color: Math.random() < 0.15 ? '#ffe4c4'      // 暖色星
           : Math.random() < 0.15 ? '#b8d4ff'      // 冷色星
           : '#ffffff',
      blink: Math.random() > 0.5,
    })
  }

  // 星云
  nebulae = [
    { x: W * 0.2, y: H * 0.3, r: 120, color: '#3b82f6', alpha: 0.04 },
    { x: W * 0.7, y: H * 0.6, r: 100, color: '#8b5cf6', alpha: 0.035 },
    { x: W * 0.5, y: H * 0.2, r: 80, color: '#ec4899', alpha: 0.03 },
    { x: W * 0.8, y: H * 0.8, r: 90, color: '#10b981', alpha: 0.025 },
  ]

  startStarAnimation()
}

function drawStarfield(time: number) {
  const canvas = starCanvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  const W = canvas.width; const H = canvas.height

  ctx.clearRect(0, 0, W, H)

  // 绘制星云
  for (const n of nebulae) {
    const grad = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.r)
    grad.addColorStop(0, n.color + Math.round(n.alpha * 255).toString(16).padStart(2, '0'))
    grad.addColorStop(1, 'transparent')
    ctx.fillStyle = grad
    ctx.fillRect(0, 0, W, H)
  }

  // 绘制恒星（带闪烁）
  for (const s of stars) {
    const flicker = s.blink ? Math.sin(time * s.speed + s.phase) * 0.3 + 0.7 : 1
    const a = s.alpha * flicker
    ctx.beginPath()
    ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2)
    ctx.fillStyle = s.color
    ctx.globalAlpha = a
    ctx.fill()

    // 亮星加十字光芒
    if (s.r > 2.5) {
      ctx.globalAlpha = a * 0.3
      ctx.strokeStyle = s.color
      ctx.lineWidth = 0.5
      for (let ang = 0; ang < 4; ang++) {
        const rad = (ang / 4) * Math.PI
        ctx.beginPath()
        ctx.moveTo(s.x - Math.cos(rad) * s.r * 3, s.y - Math.sin(rad) * s.r * 3)
        ctx.lineTo(s.x + Math.cos(rad) * s.r * 3, s.y + Math.sin(rad) * s.r * 3)
        ctx.stroke()
      }
    }
  }
  ctx.globalAlpha = 1

  // 流星
  for (let i = shootingStars.length - 1; i >= 0; i--) {
    const ss = shootingStars[i]
    ss.x += ss.dx; ss.y += ss.dy; ss.life++
    ss.alpha = 1 - ss.life / ss.maxLife
    if (ss.life >= ss.maxLife || ss.alpha <= 0) {
      shootingStars.splice(i, 1)
      continue
    }
    ctx.beginPath()
    ctx.moveTo(ss.x, ss.y)
    ctx.lineTo(ss.x - ss.dx * 4, ss.y - ss.dy * 4)
    ctx.strokeStyle = `rgba(255,255,255,${ss.alpha * 0.8})`
    ctx.lineWidth = 1.5
    ctx.stroke()
    // 流星头部光晕
    ctx.beginPath()
    ctx.arc(ss.x, ss.y, 2, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(255,255,255,${ss.alpha})`
    ctx.fill()
  }
}

function startStarAnimation() {
  if (starAnimId) return
  let lastTime = 0
  function frame(time: number) {
    const dt = lastTime ? time - lastTime : 0
    lastTime = time
    starTimer += dt
    // 每 6-10 秒生成一颗流星
    if (starTimer > 6000 + Math.random() * 4000) {
      starTimer = 0
      const angle = Math.PI * 0.25 + Math.random() * Math.PI * 0.15
      const speed = 4 + Math.random() * 3
      const canvas = starCanvasRef.value
      if (canvas) {
        shootingStars.push({
          x: Math.random() * canvas.width * 0.8 + canvas.width * 0.1,
          y: 0,
          dx: Math.cos(angle) * speed,
          dy: Math.sin(angle) * speed,
          life: 0,
          maxLife: 40 + Math.random() * 30,
          alpha: 1,
        })
      }
    }
    drawStarfield(time)
    starAnimId = requestAnimationFrame(frame)
  }
  starAnimId = requestAnimationFrame(frame)
}

function stopStarAnimation() {
  if (starAnimId) {
    cancelAnimationFrame(starAnimId)
    starAnimId = null
  }
}

// 螺旋星系布局
function computeGalaxyPositions() {
  const items = filteredNodes.value
  if (items.length === 0) return []

  // 按提及次数排序（最重要的在中心）
  const sorted = [...items].sort((a, b) => b.mention_count - a.mention_count)
  const goldenAngle = Math.PI * (3 - Math.sqrt(5))
  const spacing = Math.min(120, Math.max(60, 600 / Math.sqrt(sorted.length)))

  const positions: Record<string, { x: number; y: number }> = {}
  for (let i = 0; i < sorted.length; i++) {
    const angle = i * goldenAngle
    // 按类型分组偏移（不同旋臂）
    const typeOffset = TYPE_COLORS[sorted[i].type] ? 0 : 0.3
    const radius = Math.sqrt(i + 1) * spacing
    const a = angle + typeOffset
    positions[String(sorted[i].id)] = {
      x: radius * Math.cos(a),
      y: radius * Math.sin(a),
    }
  }
  return positions
}

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
  const positions = computeGalaxyPositions()

  const g6Nodes = filteredNodes.value.map((n) => {
    const pos = positions[String(n.id)] || { x: 0, y: 0 }
    const size = 20 + Math.log2(n.mention_count + 1) * 8
    const color = TYPE_COLORS[n.type] || TYPE_COLORS.other
    return {
      id: String(n.id),
      x: pos.x,
      y: pos.y,
      data: {
        label: n.name,
        type: n.type,
        mentionCount: n.mention_count,
        description: n.description,
        color,
        size,
      },
    }
  })

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
    layout: { type: 'preset' },
    node: {
      style: (d: any) => ({
        fill: d.data?.color || '#3b82f6',
        size: d.data?.size || 28,
        // 辐射渐变模拟星体
        fillRadial: {
          offset: 0,
          stops: [
            { offset: 0, color: '#ffffff' },
            { offset: 0.3, color: d.data?.color || '#3b82f6' },
            { offset: 1, color: 'transparent' },
          ],
        },
        labelText: d.data?.label || '',
        labelFill: '#e2e8f0',
        labelFontSize: 11,
        labelFontWeight: 600,
        labelPlacement: 'bottom',
        labelOffsetY: d.data?.size / 2 + 6,
        labelMaxLines: 1,
        labelWordWrap: false,
        // 外发光（日冕效果）
        shadowBlur: d.data?.size * 0.8,
        shadowColor: (d.data?.color || '#3b82f6') + '60',
        // 双重发光：内层
        stroke: (d.data?.color || '#3b82f6') + '40',
        lineWidth: 3,
        // 透明度随机微调（模拟闪烁）
        opacity: 0.9,
      }),
      state: {
        selected: {
          shadowBlur: 40,
          shadowColor: (d: any) => (d.data?.color || '#3b82f6') + 'cc',
          stroke: '#ffffff',
          lineWidth: 3,
          opacity: 1,
        },
        hover: {
          shadowBlur: 30,
          shadowColor: (d: any) => (d.data?.color || '#3b82f6') + 'aa',
          lineWidth: 2.5,
          opacity: 1,
        },
      },
    },
    edge: {
      style: (d: any) => ({
        stroke: (d.data?.weight || 1) > 2 ? '#94a3b8' : '#475569',
        lineWidth: Math.min((d.data?.weight || 1) * 0.8, 3),
        labelText: d.data?.label || '',
        labelFontSize: 9,
        labelFill: '#94a3b8',
        labelBackground: true,
        labelBackgroundFill: '#0f172a',
        labelBackgroundOpacity: 0.7,
        labelBackgroundCornerRadius: 3,
        labelPadding: [1, 4],
        endArrow: true,
        endArrowSize: 8,
        opacity: 0.35,
        // 曲线效果（星轨）
        curveOffset: 20,
        curvePosition: 0.5,
      }),
      state: {
        hover: { stroke: '#f59e0b', lineWidth: 2.5, opacity: 0.8 },
      },
    },
    behaviors: [
      'drag-canvas',
      'zoom-canvas',
      {
        type: 'drag-element',
        enable: (evt: any) => evt.target?.type === 'node',
      },
      {
        type: 'hover-activate',
        degree: 1,
      },
    ],
    plugins: [
      {
        type: 'minimap',
        size: [160, 110],
        backgroundColor: '#0f172a',
        border: '1px solid #334155',
        filter: (d: any) => d.id !== undefined,
      },
    ],
    autoFit: false,
    animation: false,
  })

  // 居中
  graph.fitView()

  // 事件绑定
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
          ElMessage.info(`星系扩展 ${newNodes.length} 颗星体, ${newEdges.length} 条星轨`)
        } else {
          ElMessage.info('该星体已完整呈现')
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

  graph.on('node:pointerleave', () => { tooltipVisible.value = false })
  graph.on('canvas:click', () => { tooltipVisible.value = false })

  // 拖拽时暂停旋转
  graph.on('dragstart', () => { isRotating.value = false; stopRotation() })
  graph.on('dragend', () => { isRotating.value = true; startRotation() })

  graph.render()
  startRotation()
}

// 旋转动画
function startRotation() {
  if (!graph || rotateRaf) return
  const step = () => {
    if (!graph || !isRotating.value) {
      rotateRaf = null
      return
    }
    graph.rotateBy(0.003)
    rotateRaf = requestAnimationFrame(step)
  }
  rotateRaf = requestAnimationFrame(step)
}

function stopRotation() {
  if (rotateRaf) {
    cancelAnimationFrame(rotateRaf)
    rotateRaf = null
  }
}

function toggleRotation() {
  isRotating.value = !isRotating.value
  if (isRotating.value) {
    startRotation()
  } else {
    stopRotation()
  }
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
  graph?.fitCenter?.()
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
  createStarfield()
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
        // 画布大小变化时重建星空
        createStarfield()
      }, 200)
    })
    resizeObserver.observe(container.value)
  }
})

onUnmounted(() => {
  stopRotation()
  stopStarAnimation()
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

/* 工具栏 */
.graph-toolbar {
  display: flex;
  gap: var(--space-3);
  align-items: center;
  padding: var(--space-2) var(--space-4);
  background: rgba(15, 23, 42, 0.9);
  border-radius: var(--radius-lg);
  border: 1px solid #334155;
  margin-bottom: var(--space-3);
  flex-shrink: 0;
  backdrop-filter: blur(8px);
}
.graph-toolbar :deep(.el-input__wrapper),
.graph-toolbar :deep(.el-select__wrapper) {
  background: rgba(30, 41, 59, 0.8);
  border: 1px solid #475569;
  box-shadow: none;
}
.graph-toolbar :deep(.el-input__inner),
.graph-toolbar :deep(.el-select__placeholder) {
  color: #e2e8f0;
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
  border: 2px solid rgba(255,255,255,0.6);
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 0 6px currentColor;
}
.legend-dot:hover {
  transform: scale(1.3);
}

.graph-info {
  font-size: var(--font-size-xs);
  color: #94a3b8;
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
  color: #94a3b8;
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
  background: radial-gradient(ellipse at 50% 50%, #0f172a 0%, #020617 100%);
}
.graph-canvas {
  width: 100%;
  height: 100%;
}
.graph-canvas.hidden { display: none; }

/* 星空背景画布 */
.starfield-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}

.graph-loading,
.graph-empty {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  color: #94a3b8;
  font-size: var(--font-size-sm);
  z-index: 1;
  background: radial-gradient(ellipse at 50% 50%, #0f172a 0%, #020617 100%);
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
  background: rgba(15, 23, 42, 0.95);
  color: #e2e8f0;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
  pointer-events: none;
  white-space: nowrap;
  max-width: 240px;
  border: 1px solid #334155;
  box-shadow: 0 4px 20px rgba(0,0,0,0.5);
  line-height: 1.5;
  backdrop-filter: blur(4px);
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
  box-shadow: 0 0 16px currentColor;
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