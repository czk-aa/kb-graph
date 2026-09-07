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

      <el-button size="small" :type="mode3d ? 'primary' : 'default'" @click="toggle3D">
        <el-icon :size="14"><component :is="mode3d ? View : Monitor" /></el-icon>
        {{ mode3d ? '3D' : '2D' }}
      </el-button>

      <el-button size="small" text type="warning" @click="handleCleanup" :loading="cleaning">
        <el-icon :size="14"><Delete /></el-icon>
        清理孤立实体
      </el-button>

      <div class="zoom-controls" v-if="!mode3d">
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
        <span>{{ mode3d ? '加载 3D 场景…' : '加载图谱数据…' }}</span>
      </div>
      <div v-else-if="nodes.length === 0" class="graph-empty">
        <el-icon :size="64" color="var(--color-gray-300)"><Share /></el-icon>
        <h3>暂无图谱数据</h3>
        <p>创建文档后，AI 将自动抽取实体和关系构建知识图谱</p>
      </div>
      <!-- 2D G6 容器 -->
      <div ref="container" class="graph-canvas" :class="{ hidden: loading || nodes.length === 0 || mode3d }" />
      <!-- 3D Three.js 容器 -->
      <div ref="threeContainer" class="graph-canvas three-canvas" :class="{ hidden: loading || nodes.length === 0 || !mode3d }" />
    </div>

    <div ref="tooltip" class="graph-tooltip" v-show="tooltipVisible && !mode3d" :style="tooltipStyle">
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
import { Search as SearchIcon, Minus, Plus, FullScreen, Loading, Share, Document, Delete, View, Monitor } from '@element-plus/icons-vue'
import { cleanupOrphanEntities, getGraphOverview, getEntityDetail, type GraphNode, type GraphEdge } from '@/api/graph'

const props = defineProps<{ spaceId: number }>()
const router = useRouter()

const container = ref<HTMLElement>()
const threeContainer = ref<HTMLElement>()
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
const cleaning = ref(false)
const mode3d = ref(false)

let graph: Graph | null = null
let resizeObserver: ResizeObserver | null = null
let threeScene: any = null
let threeAnimId: number | null = null

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
    if (mode3d.value) {
      initThreeScene()
    } else {
      renderGraph()
    }
  } finally {
    loading.value = false
  }
}

function renderGraph() {
  if (!container.value) return
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

  const data = { nodes: g6Nodes, edges: g6Edges }

  if (graph) {
    graph.setData(data)
    graph.render()
    return
  }

  graph = new Graph({
    container: container.value,
    width,
    height,
    data,
    layout: {
      type: 'force',
      preventOverlap: true,
      linkDistance: 150,
      nodeStrength: -200,
      edgeStrength: 0.1,
      animation: false,
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
        hover: { fill: '#f59e0b', lineWidth: 2 },
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
        hover: { stroke: '#3b82f6', lineWidth: 2 },
      },
    },
    behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element'],
    autoFit: false,
    animation: false,
  })

  graph.render()
  graph.fitView()

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

  graph.on('node:pointerleave', () => { tooltipVisible.value = false })
  graph.on('canvas:click', () => { tooltipVisible.value = false })
}

// ---- 3D Scene ----
async function initThreeScene() {
  const el = threeContainer.value
  if (!el || filteredNodes.value.length === 0) return

  destroyThreeScene()

  const THREE = await import('three')
  const { Scene, PerspectiveCamera, WebGLRenderer, SphereGeometry, RingGeometry, MeshPhysicalMaterial, Mesh, CylinderGeometry, MeshBasicMaterial, AmbientLight, DirectionalLight, HemisphereLight, Color, Group, Vector3, Points, PointsMaterial, BufferGeometry, Float32BufferAttribute, AdditiveBlending } = THREE
  const { OrbitControls } = await import('three/examples/jsm/controls/OrbitControls.js')
  const { EffectComposer } = await import('three/examples/jsm/postprocessing/EffectComposer.js')
  const { RenderPass } = await import('three/examples/jsm/postprocessing/RenderPass.js')
  const { UnrealBloomPass } = await import('three/examples/jsm/postprocessing/UnrealBloomPass.js')

  const W = el.clientWidth
  const H = el.clientHeight

  const scene = new Scene()
  scene.background = new Color(0x0a0e1a)

  const camera = new PerspectiveCamera(50, W / H, 0.1, 5000)
  camera.position.set(0, 300, 700)

  const renderer = new WebGLRenderer({ antialias: true, alpha: false })
  renderer.setSize(W, H)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5))
  renderer.toneMapping = 2
  renderer.toneMappingExposure = 1.2
  el.appendChild(renderer.domElement)

  // Bloom 后期（0.5 分辨率提升性能）
  const composer = new EffectComposer(renderer)
  composer.addPass(new RenderPass(scene, camera))
  const bloom = new UnrealBloomPass(new Vector2(W, H), 0.6, 0.3, 0.1)
  bloom.resolution.setScalar(0.5)
  composer.addPass(bloom)

  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.08
  controls.minDistance = 200
  controls.maxDistance = 3000
  controls.autoRotate = false
  controls.rotateSpeed = 0.8

  // 光源
  scene.add(new AmbientLight(0x404060, 0.8))
  scene.add(new DirectionalLight(0xffffff, 1.5))
  scene.add(new HemisphereLight(0x8888ff, 0x444422, 1.0))

  // 节点球体 + 光环
  const nodeGroup = new Group()
  const nodeMeshes: any[] = []
  const nodePositions: { id: string; x: number; y: number; z: number }[] = []
  const nodeData: { id: string; color: string; size: number }[] = []

  const items = filteredNodes.value
  const sorted = [...items].sort((a, b) => b.mention_count - a.mention_count)
  const goldenAngle = Math.PI * (3 - Math.sqrt(5))
  const spacing = Math.min(280, Math.max(150, 1400 / Math.sqrt(sorted.length)))

  // 共享几何体减少 GPU 开销
  const geoCache = new Map<number, typeof SphereGeometry>()

  for (let i = 0; i < sorted.length; i++) {
    const n = sorted[i]
    const angle = i * goldenAngle
    const radius = Math.sqrt(i + 1) * spacing
    const x = radius * Math.cos(angle)
    const y = radius * Math.sin(angle)
    const z = (Math.random() - 0.5) * (120 - i * 1.2)
    const size = 8 + Math.log2(n.mention_count + 1) * 4
    const color = TYPE_COLORS[n.type] || TYPE_COLORS.other

    // 共享几何体
    let geo = geoCache.get(Math.round(size))
    if (!geo) {
      geo = new SphereGeometry(size, 20, 20)
      geoCache.set(Math.round(size), geo)
    }

    const mat = new MeshPhysicalMaterial({
      color: color,
      emissive: color,
      emissiveIntensity: 0.35,
      metalness: 0.15,
      roughness: 0.25,
      clearcoat: 0.5,
      clearcoatRoughness: 0.2,
    })
    const mesh = new Mesh(geo, mat)
    mesh.position.set(x, y, z)
    mesh.userData = { nodeId: String(n.id), name: n.name, baseSize: size, phase: Math.random() * Math.PI * 2, color }
    nodeGroup.add(mesh)
    nodeMeshes.push(mesh)
    nodePositions.push({ id: String(n.id), x, y, z })
    nodeData.push({ id: String(n.id), color, size })

    // 外圈光环（扁平圆环）
    const ringGeo = new RingGeometry(size * 1.6, size * 2.2, 24)
    const ringMat = new MeshBasicMaterial({
      color: color,
      transparent: true,
      opacity: 0.15,
      side: 2,
      depthWrite: false,
    })
    const ring = new Mesh(ringGeo, ringMat)
    ring.position.set(x, y, z)
    ring.lookAt(camera.position)
    ring.userData = { isRing: true, phase: Math.random() * Math.PI * 2 }
    nodeGroup.add(ring)
    nodeMeshes.push(ring) // 添加到点击检测
  }
  scene.add(nodeGroup)

  // 边（发光圆柱体）+ 粒子流
  const edgeParticles: { src: typeof Vector3; dst: typeof Vector3; t: number; speed: number }[] = []

  for (const e of filteredEdges.value) {
    const src = nodePositions.find((p) => p.id === String(e.src_id))
    const dst = nodePositions.find((p) => p.id === String(e.dst_id))
    if (!src || !dst) continue
    const dx = dst.x - src.x
    const dy = dst.y - src.y
    const dz = dst.z - src.z
    const length = Math.sqrt(dx * dx + dy * dy + dz * dz)
    if (length < 1) continue
    const weight = e.weight || 1
    const radius = Math.min(0.3 + weight * 0.15, 1.2)
    const opacity = Math.min(0.4 + weight * 0.1, 0.85)

    // 主连线
    const geo = new CylinderGeometry(radius, radius, length, 6)
    const mat = new MeshBasicMaterial({ color: 0x60a5fa, transparent: true, opacity })
    const mesh = new Mesh(geo, mat)
    mesh.position.set((src.x + dst.x) / 2, (src.y + dst.y) / 2, (src.z + dst.z) / 2)
    mesh.quaternion.setFromUnitVectors(new Vector3(0, 1, 0), new Vector3(dx, dy, dz).normalize())
    scene.add(mesh)

    // 外层光晕
    if (weight > 1) {
      const glowGeo = new CylinderGeometry(radius * 3, radius * 3, length, 6)
      const glowMat = new MeshBasicMaterial({ color: 0x60a5fa, transparent: true, opacity: opacity * 0.15 })
      const glowMesh = new Mesh(glowGeo, glowMat)
      glowMesh.position.copy(mesh.position)
      glowMesh.quaternion.copy(mesh.quaternion)
      scene.add(glowMesh)
    }

    // 粒子流
    const particleCount = Math.max(3, Math.floor(weight * 4))
    for (let p = 0; p < particleCount; p++) {
      edgeParticles.push({
        src: new Vector3(src.x, src.y, src.z),
        dst: new Vector3(dst.x, dst.y, dst.z),
        t: p / particleCount,
        speed: (0.3 + Math.random() * 0.4) * (weight > 1 ? 1.5 : 1),
      })
    }
  }

  // 粒子流系统
  const particleCount = edgeParticles.length
  const particleGeo = new BufferGeometry()
  const particlePos = new Float32Array(particleCount * 3)
  for (let i = 0; i < particleCount; i++) {
    const p = edgeParticles[i]
    particlePos[i * 3] = p.src.x + (p.dst.x - p.src.x) * p.t
    particlePos[i * 3 + 1] = p.src.y + (p.dst.y - p.src.y) * p.t
    particlePos[i * 3 + 2] = p.src.z + (p.dst.z - p.src.z) * p.t
  }
  particleGeo.setAttribute('position', new Float32BufferAttribute(particlePos, 3))
  const particleMat = new PointsMaterial({
    color: 0x93c5fd,
    size: 2.5,
    transparent: true,
    opacity: 0.8,
    blending: AdditiveBlending,
    depthWrite: false,
  })
  const particleSystem = new Points(particleGeo, particleMat)
  scene.add(particleSystem)

  // 背景星空粒子
  const bgStarCount = 400
  const bgStarPos = new Float32Array(bgStarCount * 3)
  for (let i = 0; i < bgStarCount * 3; i++) {
    bgStarPos[i] = (Math.random() - 0.5) * 3000
  }
  const bgStarGeo = new BufferGeometry()
  bgStarGeo.setAttribute('position', new Float32BufferAttribute(bgStarPos, 3))
  const bgStarMat = new PointsMaterial({
    color: 0xffffff,
    size: 0.6,
    transparent: true,
    opacity: 0.4,
    blending: AdditiveBlending,
    depthWrite: false,
  })
  const bgStars = new Points(bgStarGeo, bgStarMat)
  scene.add(bgStars)

  // 中心光晕
  const centerGlowGeo = new RingGeometry(0, 80, 32)
  const centerGlowMat = new MeshBasicMaterial({
    color: 0x3b82f6,
    transparent: true,
    opacity: 0.04,
    side: 2,
    depthWrite: false,
  })
  const centerGlow = new Mesh(centerGlowGeo, centerGlowMat)
  centerGlow.position.set(0, 0, 0)
  centerGlow.lookAt(camera.position)
  scene.add(centerGlow)

  threeScene = { scene, camera, renderer, controls, composer, nodeGroup, nodeMeshes, centerGlow, particleSystem, particleMat, edgeParticles, el, bloom }

  // 点击射线检测
  const raycaster = new THREE.Raycaster()
  const mouse = { x: 0, y: 0 }
  renderer.domElement.addEventListener('click', async (evt: MouseEvent) => {
    const rect = renderer.domElement.getBoundingClientRect()
    mouse.x = ((evt.clientX - rect.left) / rect.width) * 2 - 1
    mouse.y = -((evt.clientY - rect.top) / rect.height) * 2 + 1
    const ray = new raycaster()
    ray.setFromCamera(mouse, camera)
    const intersects = ray.intersectObjects(nodeMeshes)
    if (intersects.length > 0) {
      const mesh = intersects[0].object
      const nodeId = mesh.userData.nodeId
      if (nodeId) {
        try {
          const detail = await getEntityDetail(Number(nodeId))
          selectedEntity.value = detail
          drawerVisible.value = true
        } catch { /* ignore */ }
      }
    }
  })

  let autoRotate = true
  controls.addEventListener('start', () => { autoRotate = false })
  controls.addEventListener('end', () => { autoRotate = true })

  // 动画循环
  function animate(time: number) {
    if (autoRotate && threeScene) {
      nodeGroup.rotation.y += 0.0015
    }

    // 节点脉冲 + 光环始终面向相机
    for (const mesh of nodeMeshes) {
      if (mesh.userData.isRing) {
        mesh.lookAt(camera.position)
        const phase = mesh.userData.phase || 0
        const s = 1 + Math.sin(time * 0.0015 + phase) * 0.1
        mesh.scale.setScalar(s)
        continue
      }
      const phase = mesh.userData.phase || 0
      const scale = 1 + Math.sin(time * 0.002 + phase) * 0.06
      mesh.scale.setScalar(scale)
      const mat = mesh.material as any
      if (mat.emissiveIntensity) {
        mat.emissiveIntensity = 0.25 + Math.sin(time * 0.003 + phase) * 0.15
      }
    }

    // 中心光晕面向相机
    centerGlow.lookAt(camera.position)
    centerGlow.scale.setScalar(1 + Math.sin(time * 0.001) * 0.05)

    // 粒子流动画
    if (threeScene) {
      const pos = particleSystem.geometry.attributes.position.array as Float32Array
      for (let i = 0; i < edgeParticles.length; i++) {
        const p = edgeParticles[i]
        p.t += 0.005 * p.speed
        if (p.t > 1) p.t -= 1
        pos[i * 3] = p.src.x + (p.dst.x - p.src.x) * p.t
        pos[i * 3 + 1] = p.src.y + (p.dst.y - p.src.y) * p.t
        pos[i * 3 + 2] = p.src.z + (p.dst.z - p.src.z) * p.t
      }
      particleSystem.geometry.attributes.position.needsUpdate = true
    }

    controls.update()
    composer.render()
    threeAnimId = requestAnimationFrame(animate)
  }
  threeAnimId = requestAnimationFrame(animate)
}

function destroyThreeScene() {
  if (threeAnimId) {
    cancelAnimationFrame(threeAnimId)
    threeAnimId = null
  }
  if (threeScene) {
    threeScene.renderer.domElement.remove()
    threeScene.renderer.dispose()
    threeScene = null
  }
}

function toggle3D() {
  mode3d.value = !mode3d.value
  if (mode3d.value) {
    // 切到 3D：隐藏 G6 tooltip，初始化 3D
    tooltipVisible.value = false
    nextTick(() => initThreeScene())
  } else {
    // 切回 2D：销毁 3D，重新渲染 2D
    destroyThreeScene()
    nextTick(() => renderGraph())
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
      // 3D 场景 resize
      if (threeScene && threeContainer.value) {
        const w = threeContainer.value.clientWidth
        const h = threeContainer.value.clientHeight
        if (w > 0 && h > 0) {
          threeScene.camera.aspect = w / h
          threeScene.camera.updateProjectionMatrix()
          threeScene.renderer.setSize(w, h)
        }
      }
    })
    resizeObserver.observe(container.value.parentElement!)
  }
})

onUnmounted(() => {
  destroyThreeScene()
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
.three-canvas {
  position: absolute;
  inset: 0;
  background: #0f172a;
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