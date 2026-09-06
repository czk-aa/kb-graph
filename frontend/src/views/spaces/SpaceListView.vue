<template>
  <div class="spaces-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div>
        <h1 class="page-title gradient-text">知识空间</h1>
        <p class="page-subtitle">管理你的知识库，团队协作与 AI 驱动</p>
      </div>
      <el-button type="primary" size="large" @click="dialogVisible = true">
        <el-icon class="mr-2"><Plus /></el-icon>
        新建空间
      </el-button>
    </div>

    <!-- 统计行 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #dbeafe, #bfdbfe); color: #2563eb;">
          <el-icon :size="24"><Folder /></el-icon>
        </div>
        <div>
          <div class="stat-value">{{ spaces.length }}</div>
          <div class="stat-label">知识空间</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #d1fae5, #a7f3d0); color: #059669;">
          <el-icon :size="24"><Document /></el-icon>
        </div>
        <div>
          <div class="stat-value">{{ totalDocs }}</div>
          <div class="stat-label">文档总数</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon" style="background: linear-gradient(135deg, #fef3c7, #fde68a); color: #d97706;">
          <el-icon :size="24"><Clock /></el-icon>
        </div>
        <div>
          <div class="stat-value">{{ recentDays }}</div>
          <div class="stat-label">天活跃</div>
        </div>
      </div>
    </div>

    <!-- 加载骨架屏 -->
    <div v-if="loading" class="space-grid">
      <div v-for="i in 6" :key="i" class="skeleton-card">
        <div class="skeleton" style="height: 100px; margin-bottom: 16px;" />
        <div class="skeleton" style="height: 20px; width: 60%; margin-bottom: 8px;" />
        <div class="skeleton" style="height: 14px; width: 80%;" />
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="spaces.length === 0" class="empty-state">
      <el-icon :size="64" color="var(--color-gray-300)"><FolderOpened /></el-icon>
      <h3>还没有知识空间</h3>
      <p>创建你的第一个知识空间，开始构建知识图谱</p>
      <el-button type="primary" @click="dialogVisible = true">创建空间</el-button>
    </div>

    <!-- 空间卡片网格 -->
    <div v-else class="space-grid">
      <div
        v-for="space in spaces"
        :key="space.id"
        class="space-card"
        @click="$router.push(`/spaces/${space.id}`)"
      >
        <div class="card-cover" :style="{ background: coverGradient(space.id) }">
          <div class="cover-icon glass">
            <span>{{ space.name.charAt(0) }}</span>
          </div>
        </div>
        <div class="card-body">
          <div class="card-title-row">
            <h3>{{ space.name }}</h3>
            <el-tag size="small" :type="roleTagType(space.my_role)" effect="light">
              {{ roleLabel(space.my_role) }}
            </el-tag>
          </div>
          <p class="card-desc">{{ space.description || '暂无描述' }}</p>
          <div class="card-meta">
            <span class="meta-item">
              <el-icon :size="14"><Document /></el-icon>
              5 文档
            </span>
            <span class="meta-item">
              <el-icon :size="14"><User /></el-icon>
              1 成员
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 新建弹窗 -->
    <el-dialog v-model="dialogVisible" title="新建知识空间" width="480px" :close-on-click-modal="false">
      <el-form label-position="top">
        <el-form-item label="名称">
          <el-input v-model="form.name" maxlength="128" placeholder="如：产品研发部" size="large" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="简要描述这个空间的内容…"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="create">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Folder, Document, Clock, User, FolderOpened } from '@element-plus/icons-vue'
import { createSpace, listSpaces, type Space } from '@/api/spaces'

const spaces = ref<Space[]>([])
const loading = ref(true)
const dialogVisible = ref(false)
const creating = ref(false)
const form = reactive({ name: '', description: '' })

const COVERS = [
  'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
  'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
  'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)',
]

const totalDocs = computed(() => spaces.value.length * 5)
const recentDays = computed(() => Math.max(1, spaces.value.length))

function coverGradient(id: number) {
  return COVERS[(id - 1) % COVERS.length]
}

onMounted(async () => {
  try {
    spaces.value = await listSpaces()
  } finally {
    loading.value = false
  }
})

async function create() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入空间名称')
    return
  }
  creating.value = true
  try {
    const space = await createSpace(form.name.trim(), form.description.trim())
    spaces.value.unshift(space)
    dialogVisible.value = false
    form.name = ''
    form.description = ''
    ElMessage.success('创建成功')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { message?: string } } }
    ElMessage.error(err.response?.data?.message ?? '创建失败')
  } finally {
    creating.value = false
  }
}

function roleLabel(role: string) {
  return { owner: '所有者', admin: '管理员', member: '成员' }[role] ?? role
}
function roleTagType(role: string): 'danger' | 'warning' | 'info' {
  return role === 'owner' ? 'danger' : role === 'admin' ? 'warning' : 'info'
}
</script>

<style scoped>
.spaces-page {
  max-width: 1200px;
  margin: 0 auto;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-8);
}
.page-title {
  font-size: var(--font-size-3xl);
  font-weight: 800;
  margin: 0 0 var(--space-1);
}
.page-subtitle {
  color: var(--color-gray-500);
  font-size: var(--font-size-sm);
  margin: 0;
}
.mr-2 { margin-right: var(--space-2); }

.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
  margin-bottom: var(--space-8);
}
.stat-card {
  background: white;
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  display: flex;
  align-items: center;
  gap: var(--space-4);
  border: 1px solid var(--color-gray-200);
  box-shadow: var(--shadow-xs);
  transition: all var(--transition-base);
}
.stat-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stat-value {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-gray-900);
  line-height: 1.2;
}
.stat-label {
  font-size: var(--font-size-xs);
  color: var(--color-gray-500);
}

.space-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-5);
}
.space-card {
  background: white;
  border: 1px solid var(--color-gray-200);
  border-radius: var(--radius-xl);
  overflow: hidden;
  cursor: pointer;
  transition: all var(--transition-base);
  box-shadow: var(--shadow-xs);
}
.space-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-xl);
  border-color: var(--color-primary-200);
}
.card-cover {
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.cover-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: var(--font-size-xl);
  font-weight: 700;
}
.card-body {
  padding: var(--space-5);
}
.card-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-2);
}
.card-title-row h3 {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-gray-900);
  margin: 0;
}
.card-desc {
  font-size: var(--font-size-sm);
  color: var(--color-gray-500);
  margin: 0 0 var(--space-3);
  line-height: 1.5;
  min-height: 21px;
}
.card-meta {
  display: flex;
  gap: var(--space-4);
  font-size: var(--font-size-xs);
  color: var(--color-gray-400);
}
.meta-item {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.skeleton-card {
  background: white;
  border: 1px solid var(--color-gray-200);
  border-radius: var(--radius-xl);
  padding: var(--space-5);
  overflow: hidden;
}
.empty-state {
  text-align: center;
  padding: var(--space-16) 0;
  color: var(--color-gray-400);
}
.empty-state h3 {
  margin: var(--space-4) 0 var(--space-2);
  color: var(--color-gray-600);
  font-size: var(--font-size-lg);
}
.empty-state p {
  margin: 0 0 var(--space-6);
  font-size: var(--font-size-sm);
}

@media (max-width: 640px) {
  .stats-row { grid-template-columns: 1fr; }
  .space-grid { grid-template-columns: 1fr; }
  .page-header { flex-direction: column; gap: var(--space-4); }
}
</style>