<template>
  <div class="page">
    <div class="header">
      <div class="header-left">
        <el-button text @click="$router.push(`/spaces/${spaceId}`)">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <el-input
          v-model="title"
          class="title-input"
          placeholder="文档标题"
          @blur="saveTitle"
        />
      </div>
      <div class="header-actions">
        <el-button @click="saveContent" :loading="saving">保存</el-button>
        <el-button @click="showVersions = true">版本历史</el-button>
      </div>
    </div>

    <div class="body">
      <div class="editor-area">
        <el-input
          v-model="content"
          type="textarea"
          :rows="22"
          placeholder="在此编写文档内容…"
          class="editor"
        />
      </div>

      <div class="side-panel">
        <!-- AI 摘要与标签 -->
        <div v-if="summary || tags?.length" class="panel-section">
          <h4>AI 摘要</h4>
          <p class="summary-text">{{ summary }}</p>
          <div v-if="tags?.length" class="tags">
            <el-tag v-for="t in tags" :key="t" size="small" class="tag">{{ t }}</el-tag>
          </div>
        </div>

        <!-- 关联文档 -->
        <div class="panel-section">
          <h4>关联文档</h4>
          <div v-if="related.length" class="related-list">
            <div
              v-for="r in related"
              :key="r.id"
              class="related-item"
              @click="$router.push(`/spaces/${spaceId}/documents/${r.id}`)"
            >
              <span class="related-title">{{ r.title }}</span>
              <span v-if="r.summary" class="related-summary">{{ r.summary.slice(0, 60) }}…</span>
            </div>
          </div>
          <el-empty v-else description="暂无关联" :image-size="40" />
        </div>
      </div>
    </div>

    <!-- 版本历史弹窗 -->
    <el-dialog v-model="showVersions" title="版本历史" width="700px">
      <el-table :data="versions" v-loading="versionLoading" stripe>
        <el-table-column label="版本号" width="80">
          <template #default="{ row }">v{{ row.version_no }}</template>
        </el-table-column>
        <el-table-column label="内容预览" min-width="300">
          <template #default="{ row }">{{ row.content_md?.slice(0, 100) || '' }}</template>
        </el-table-column>
        <el-table-column label="时间" width="180">
          <template #default="{ row }">{{ fmt(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button text size="small" type="primary" @click="restore(row.version_no)">
              恢复
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!versionLoading && versions.length === 0" description="暂无版本" />
      <template #footer>
        <el-button @click="showVersions = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import {
  getDocument,
  saveContent,
  updateDocument,
  getVersions,
  restoreVersion,
  getRelatedDocuments,
  type Document,
  type DocumentVersion,
} from '@/api/documents'

const route = useRoute()
const spaceId = computed(() => Number(route.params.spaceId))
const docId = computed(() => Number(route.params.docId))

const title = ref('')
const content = ref('')
const summary = ref('')
const tags = ref<string[]>([])
const saving = ref(false)
const showVersions = ref(false)
const versions = ref<DocumentVersion[]>([])
const versionLoading = ref(false)
const related = ref<Document[]>([])

onMounted(async () => {
  await loadDoc()
  loadRelated()
})

async function loadDoc() {
  const doc = await getDocument(docId.value)
  title.value = doc.title
  content.value = doc.content_text || ''
  summary.value = doc.summary || ''
  tags.value = doc.tags || []
}

async function loadRelated() {
  try {
    related.value = await getRelatedDocuments(docId.value)
  } catch { /* ignore */ }
}

async function saveTitle() {
  if (!title.value.trim()) return
  try {
    await updateDocument(docId.value, title.value.trim())
  } catch { /* ignore */ }
}

async function saveContent() {
  saving.value = true
  try {
    await saveContent(docId.value, content.value)
    ElMessage.success('保存成功')
    // 保存后重新加载摘要和关联
    setTimeout(async () => {
      await loadDoc()
      loadRelated()
    }, 2000)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function loadVersions() {
  versionLoading.value = true
  try {
    versions.value = await getVersions(docId.value)
  } finally {
    versionLoading.value = false
  }
}

async function restore(versionNo: number) {
  try {
    const doc = await restoreVersion(docId.value, versionNo)
    content.value = doc.content_text || ''
    showVersions.value = false
    ElMessage.success(`已恢复到 v${versionNo}`)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '恢复失败')
  }
}

watch(showVersions, (v) => {
  if (v) loadVersions()
})

function fmt(d: string) {
  return new Date(d).toLocaleString('zh-CN')
}
</script>

<style scoped>
.page { padding: 24px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.header-left { display: flex; align-items: center; gap: 8px; flex: 1; }
.title-input { max-width: 400px; }
.header-actions { display: flex; gap: 8px; }

.body { display: flex; gap: 20px; }
.editor-area { flex: 1; }
.editor { font-family: 'Consolas', 'Monaco', monospace; font-size: 14px; line-height: 1.6; }

.side-panel { width: 260px; flex-shrink: 0; }
.panel-section { margin-bottom: 20px; padding: 12px; background: var(--el-fill-color); border-radius: 8px; }
.panel-section h4 { margin: 0 0 8px; font-size: 14px; color: var(--el-text-color-secondary); }
.summary-text { font-size: 13px; line-height: 1.6; color: var(--el-text-color-regular); }
.tags { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 4px; }
.tag { margin: 0; }

.related-list { display: flex; flex-direction: column; gap: 6px; }
.related-item { padding: 6px 8px; cursor: pointer; border-radius: 4px; }
.related-item:hover { background: var(--el-fill-color-light); }
.related-title { font-size: 13px; font-weight: 500; display: block; }
.related-summary { font-size: 11px; color: var(--el-text-color-secondary); display: block; margin-top: 2px; }
</style>