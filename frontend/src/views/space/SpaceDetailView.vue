<template>
  <div class="space-page">
    <!-- 空间头部横幅 -->
    <div class="space-banner">
      <div class="banner-content">
        <div class="banner-left">
          <el-button text class="back-btn" @click="$router.back()">
            <el-icon :size="18"><ArrowLeft /></el-icon>
          </el-button>
          <div>
            <h1>{{ spaceName }}</h1>
            <p class="banner-desc">知识图谱 · AI 问答 · 团队协作</p>
          </div>
        </div>
        <div class="banner-actions">
          <el-button @click="showUpload = true">
            <el-icon class="mr-2"><Upload /></el-icon>
            上传文件
          </el-button>
          <el-button type="primary" @click="createDoc">
            <el-icon class="mr-2"><Plus /></el-icon>
            新建文档
          </el-button>
        </div>
      </div>
    </div>

    <!-- Tab 切换 -->
    <div class="tabs-wrapper">
      <div class="tab-item" :class="{ active: activeTab === 'docs' }" @click="switchTab('docs')">
        <el-icon :size="16"><Document /></el-icon>
        <span>文档</span>
      </div>
      <div class="tab-item" :class="{ active: activeTab === 'graph' }" @click="switchTab('graph')">
        <el-icon :size="16"><Share /></el-icon>
        <span>图谱</span>
      </div>
      <div class="tab-item" :class="{ active: activeTab === 'chat' }" @click="switchTab('chat')">
        <el-icon :size="16"><ChatDotRound /></el-icon>
        <span>AI问答</span>
      </div>
      <div class="tab-item" :class="{ active: activeTab === 'members' }" @click="switchTab('members')">
        <el-icon :size="16"><User /></el-icon>
        <span>成员</span>
      </div>
    </div>

    <!-- Tab 内容 -->
    <div class="tab-content">
      <!-- 文档 Tab -->
      <div v-show="activeTab === 'docs'">
        <div v-if="loading" class="doc-grid">
          <div v-for="i in 6" :key="i" class="skeleton-card">
            <div class="skeleton" style="height: 16px; width: 60%; margin-bottom: 12px;" />
            <div class="skeleton" style="height: 12px; width: 80%; margin-bottom: 8px;" />
            <div class="skeleton" style="height: 12px; width: 40%;" />
          </div>
        </div>

        <div v-else-if="documents.length === 0" class="empty-state">
          <el-icon :size="64" color="var(--color-gray-300)"><Document /></el-icon>
          <h3>还没有文档</h3>
          <p>点击上方按钮创建或上传文档</p>
        </div>

        <div v-else class="doc-grid">
          <div
            v-for="doc in documents"
            :key="doc.id"
            class="doc-card"
            :class="'status-' + doc.status"
            @click="openDoc(doc.id)"
          >
            <div class="doc-card-header">
              <h3>{{ doc.title }}</h3>
              <el-tag :type="statusTag(doc.status)" size="small" effect="light" round>
                {{ statusLabel(doc.status) }}
              </el-tag>
            </div>
            <div class="doc-card-tags" v-if="doc.tags?.length">
              <el-tag
                v-for="t in doc.tags.slice(0, 3)"
                :key="t"
                size="small"
                type="info"
                effect="plain"
              >{{ t }}</el-tag>
            </div>
            <div class="doc-card-footer">
              <span class="doc-meta-item">
                <el-icon :size="12"><Clock /></el-icon>
                {{ fmt(doc.updated_at) }}
              </span>
              <el-button
                text
                type="danger"
                size="small"
                @click.stop="delDoc(doc.id)"
              >
                <el-icon :size="14"><Delete /></el-icon>
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 图谱 Tab -->
      <div v-if="activeTab === 'graph' || renderedTabs.has('graph')">
        <KnowledgeGraph :space-id="spaceId" />
      </div>

      <!-- AI 问答 Tab -->
      <div v-if="activeTab === 'chat' || renderedTabs.has('chat')">
        <ChatView :space-id="spaceId" />
      </div>

      <!-- 成员 Tab -->
      <div v-if="activeTab === 'members' || renderedTabs.has('members')">
        <SpaceMembers :space-id="spaceId" />
      </div>
    </div>

    <!-- 上传弹窗 -->
    <el-dialog v-model="showUpload" title="上传文件" width="500px">
      <el-upload
        ref="uploadRef"
        drag
        multiple
        :auto-upload="false"
        :on-change="onFileChange"
        :limit="10"
        accept=".md,.txt,.pdf,.docx,.html,.htm"
      >
        <el-icon class="el-icon--upload" :size="48"><UploadFilled /></el-icon>
        <div class="el-upload__text">拖拽文件到此处或<em>点击上传</em></div>
        <template #tip>
          <div class="el-upload__tip">支持 md / txt / pdf / docx / html</div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="showUpload = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="doUpload">开始上传</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Upload, Plus, Document, Share, ChatDotRound, User, Clock, Delete, UploadFilled } from '@element-plus/icons-vue'
import { listDocuments, createDocument, deleteDocument, uploadFiles, type Document as DocType } from '@/api/documents'
import { listSpaces } from '@/api/spaces'
import KnowledgeGraph from '@/components/graph/KnowledgeGraph.vue'
import ChatView from '@/views/space/ChatView.vue'
import SpaceMembers from '@/views/space/SpaceMembers.vue'

const route = useRoute()
const router = useRouter()
const spaceId = computed(() => Number(route.params.id))
const spaceName = ref('')
const documents = ref<DocType[]>([])
const loading = ref(true)
const activeTab = ref('docs')
const renderedTabs = reactive(new Set<string>(['docs']))
const showUpload = ref(false)

function switchTab(tab: string) {
  activeTab.value = tab
  renderedTabs.add(tab)
}
const uploading = ref(false)
const uploadFiles_ = ref<File[]>([])

onMounted(async () => {
  try {
    const spaces = await listSpaces()
    const s = spaces.find((s) => s.id === spaceId.value)
    spaceName.value = s?.name || '知识空间'
  } catch { /* ignore */ }
  await loadDocs()
})

async function loadDocs() {
  loading.value = true
  try {
    documents.value = await listDocuments(spaceId.value)
  } finally {
    loading.value = false
  }
}

async function createDoc() {
  try {
    const doc = await createDocument(spaceId.value, '未命名文档')
    router.push(`/spaces/${spaceId.value}/documents/${doc.id}`)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '创建失败')
  }
}

function openDoc(id: number) {
  router.push(`/spaces/${spaceId.value}/documents/${id}`)
}

async function delDoc(id: number) {
  try {
    await ElMessageBox.confirm('确定删除该文档？', '确认', { type: 'warning' })
    await deleteDocument(id)
    documents.value = documents.value.filter((d) => d.id !== id)
    ElMessage.success('已删除')
  } catch { /* cancelled */ }
}

function onFileChange(_file: any, fileList: any[]) {
  uploadFiles_.value = fileList.map((f: any) => f.raw).filter(Boolean)
}

async function doUpload() {
  if (uploadFiles_.value.length === 0) {
    ElMessage.warning('请选择文件')
    return
  }
  uploading.value = true
  try {
    await uploadFiles(spaceId.value, uploadFiles_.value)
    showUpload.value = false
    ElMessage.success('上传成功，正在解析…')
    await loadDocs()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

function statusTag(s: string) {
  return s === 'ready' ? 'success' : s === 'processing' ? 'warning' : s === 'failed' ? 'danger' : 'info'
}
function statusLabel(s: string) {
  return { ready: '就绪', processing: '处理中', failed: '失败', uploaded: '已上传' }[s] || s
}
function fmt(d: string) {
  return new Date(d).toLocaleString('zh-CN')
}
</script>

<style scoped>
.space-page { max-width: 1200px; margin: 0 auto; }
.mr-2 { margin-right: var(--space-2); }

/* Banner */
.space-banner {
  background: linear-gradient(135deg, var(--color-primary-600), var(--color-primary-800));
  border-radius: var(--radius-xl);
  margin-bottom: var(--space-6);
  position: relative;
  overflow: hidden;
}
.space-banner::before {
  content: '';
  position: absolute;
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(255,255,255,0.1), transparent);
  border-radius: 50%;
  top: -50%;
  right: -5%;
}
.banner-content {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-6) var(--space-8);
}
.banner-left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.back-btn {
  color: rgba(255,255,255,0.7);
  padding: 0;
}
.back-btn:hover {
  color: white;
}
.banner-left h1 {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: white;
  margin: 0 0 var(--space-1);
}
.banner-desc {
  color: rgba(255,255,255,0.75);
  margin: 0;
  font-size: var(--font-size-sm);
}
.banner-actions {
  display: flex;
  gap: var(--space-3);
}

/* Tabs */
.tabs-wrapper {
  display: flex;
  gap: var(--space-1);
  margin-bottom: var(--space-5);
  padding: var(--space-1);
  background: white;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-gray-200);
}
.tab-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-gray-500);
  cursor: pointer;
  transition: all var(--transition-fast);
  height: 38px;
}
.tab-item:hover {
  color: var(--color-gray-700);
  background: var(--color-gray-50);
}
.tab-item.active {
  color: var(--color-primary-600);
  background: var(--color-primary-50);
  font-weight: 600;
}

/* Document grid */
.doc-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--space-4);
}
.doc-card {
  background: white;
  border: 1px solid var(--color-gray-200);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  transition: all var(--transition-base);
  cursor: pointer;
  position: relative;
  overflow: hidden;
}
.doc-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
}
.doc-card.status-ready::before { background: var(--color-success); }
.doc-card.status-processing::before { background: var(--color-warning); }
.doc-card.status-failed::before { background: var(--color-danger); }
.doc-card.status-uploaded::before { background: var(--color-gray-400); }
.doc-card:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
  border-color: var(--color-primary-200);
}
.doc-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-3);
}
.doc-card-header h3 {
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--color-gray-900);
  margin: 0;
}
.doc-card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  margin-bottom: var(--space-3);
}
.doc-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: var(--font-size-xs);
  color: var(--color-gray-400);
}
.doc-meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.skeleton-card {
  background: white;
  border: 1px solid var(--color-gray-200);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
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
  margin: 0;
  font-size: var(--font-size-sm);
}
</style>