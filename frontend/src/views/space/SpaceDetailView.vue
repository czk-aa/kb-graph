<template>
  <div class="page">
    <div class="header">
      <div class="header-left">
        <el-button text @click="$router.back()">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <h3>{{ spaceName }}</h3>
      </div>
      <div class="header-actions">
        <el-button @click="showUpload = true">上传文件</el-button>
        <el-button type="primary" @click="createDoc">新建文档</el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="文档" name="docs">
        <el-table :data="documents" v-loading="loading" stripe>
          <el-table-column prop="title" label="标题" min-width="200">
            <template #default="{ row }">
              <el-link type="primary" @click="openDoc(row.id)">{{ row.title }}</el-link>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="source_type" label="来源" width="80" />
          <el-table-column prop="updated_at" label="更新时间" width="180">
            <template #default="{ row }">{{ fmt(row.updated_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button text type="danger" size="small" @click="delDoc(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!loading && documents.length === 0" description="还没有文档，点击上方按钮创建或上传" />
      </el-tab-pane>
      <el-tab-pane label="图谱" name="graph">
        <KnowledgeGraph :space-id="spaceId" />
      </el-tab-pane>
      <el-tab-pane label="AI问答" name="chat">
        <ChatView :space-id="spaceId" />
      </el-tab-pane>
      <el-tab-pane label="成员" name="members">
        <SpaceMembers :space-id="spaceId" />
      </el-tab-pane>
    </el-tabs>

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
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">拖拽文件到此处或<em>点击上传</em></div>
        <template #tip>
          <div class="el-upload__tip">支持 md / txt / pdf / docx / html，单文件不超过 20MB</div>
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
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, UploadFilled } from '@element-plus/icons-vue'
import { listDocuments, createDocument, deleteDocument, uploadFiles, type Document } from '@/api/documents'
import { listSpaces } from '@/api/spaces'
import KnowledgeGraph from '@/components/graph/KnowledgeGraph.vue'
import ChatView from '@/views/space/ChatView.vue'
import SpaceMembers from '@/views/space/SpaceMembers.vue'

const route = useRoute()
const router = useRouter()
const spaceId = computed(() => Number(route.params.id))
const spaceName = ref('')
const documents = ref<Document[]>([])
const loading = ref(true)
const activeTab = ref('docs')
const showUpload = ref(false)
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
.page { padding: 24px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.header-left { display: flex; align-items: center; gap: 8px; }
.header-left h3 { margin: 0; }
</style>