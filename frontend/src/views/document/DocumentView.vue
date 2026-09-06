<template>
  <div class="document-page">
    <!-- 顶部编辑栏 -->
    <div class="doc-topbar">
      <el-button text class="back-btn" @click="$router.push(`/spaces/${spaceId}`)">
        <el-icon :size="18"><ArrowLeft /></el-icon>
      </el-button>
      <input
        v-model="title"
        class="doc-title-input"
        placeholder="文档标题"
        @blur="saveTitle"
      />
      <div class="topbar-right">
        <span class="save-status" :class="saveStatus">
          <el-icon :size="14"><component :is="saveStatusIcon" /></el-icon>
          {{ saveStatusText }}
        </span>
        <el-button @click="showVersions = true">版本历史</el-button>
        <el-button type="primary" :loading="saving" @click="saveContent">保存</el-button>
      </div>
    </div>

    <!-- 双栏布局 -->
    <div class="doc-body">
      <!-- 左侧编辑器 -->
      <div class="editor-area">
        <div class="editor-toolbar">
          <span class="toolbar-label">Markdown 编辑器</span>
        </div>
        <textarea
          v-model="content"
          class="text-editor"
          placeholder="在此编写文档内容…支持 Markdown 语法"
          spellcheck="false"
        />
      </div>

      <!-- 右侧面板 -->
      <div class="side-panel custom-scrollbar">
        <!-- AI 摘要 -->
        <div class="panel-card" :class="{ 'has-summary': summary }">
          <div class="panel-header">
            <el-icon :size="16" color="var(--color-primary-500)"><MagicStick /></el-icon>
            <span>AI 摘要</span>
          </div>
          <div v-if="summary" class="panel-body">
            <p class="summary-text">{{ summary }}</p>
            <div v-if="tags?.length" class="tags-row">
              <el-tag v-for="t in tags" :key="t" size="small" effect="light" round>{{ t }}</el-tag>
            </div>
          </div>
          <div v-else class="panel-empty">保存后自动生成</div>
        </div>

        <!-- 关联文档 -->
        <div class="panel-card">
          <div class="panel-header">
            <el-icon :size="16" color="var(--color-purple-500)"><Connection /></el-icon>
            <span>关联文档</span>
          </div>
          <div v-if="related.length" class="panel-body">
            <div
              v-for="r in related"
              :key="r.id"
              class="related-item"
              @click="$router.push(`/spaces/${spaceId}/documents/${r.id}`)"
            >
              <div class="related-title">{{ r.title }}</div>
              <div v-if="r.summary" class="related-summary">{{ r.summary.slice(0, 60) }}…</div>
            </div>
          </div>
          <div v-else class="panel-empty">暂无关联文档</div>
        </div>

        <!-- 评论 -->
        <div class="panel-card">
          <div class="panel-header">
            <el-icon :size="16" color="var(--color-warning)"><ChatLineSquare /></el-icon>
            <span>评论</span>
          </div>
          <div class="panel-body">
            <CommentPanel :doc-id="docId" />
          </div>
        </div>
      </div>
    </div>

    <!-- 版本历史弹窗 -->
    <el-dialog v-model="showVersions" title="版本历史" width="640px">
      <el-timeline v-if="versions.length > 0">
        <el-timeline-item
          v-for="v in versions"
          :key="v.version_no"
          :timestamp="fmt(v.created_at)"
          placement="top"
          :type="v.version_no === versions[0].version_no ? 'primary' : 'info'"
        >
          <div class="version-item">
            <div class="version-header">
              <el-tag size="small" :type="v.version_no === versions[0].version_no ? 'primary' : 'info'" effect="light">
                v{{ v.version_no }}
              </el-tag>
              <el-button
                v-if="v.version_no !== versions[0].version_no"
                text
                size="small"
                type="primary"
                @click="restore(v.version_no)"
              >
                恢复到此版本
              </el-button>
            </div>
            <p class="version-preview">{{ v.content_md?.slice(0, 150) || '(空内容)' }}</p>
          </div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else description="暂无版本" />
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
import { ArrowLeft, MagicStick, Connection, ChatLineSquare, CircleCheck, Loading, Clock } from '@element-plus/icons-vue'
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
import CommentPanel from '@/components/comment/CommentPanel.vue'

const route = useRoute()
const spaceId = computed(() => Number(route.params.spaceId))
const docId = computed(() => Number(route.params.docId))

const title = ref('')
const content = ref('')
const summary = ref('')
const tags = ref<string[]>([])
const saving = ref(false)
const saveStatus = ref<'saved' | 'saving' | 'idle'>('idle')
const showVersions = ref(false)
const versions = ref<DocumentVersion[]>([])
const versionLoading = ref(false)
const related = ref<Document[]>([])

const saveStatusIcon = computed(() => {
  if (saveStatus.value === 'saved') return CircleCheck
  if (saveStatus.value === 'saving') return Loading
  return Clock
})
const saveStatusText = computed(() => {
  if (saveStatus.value === 'saved') return '已保存'
  if (saveStatus.value === 'saving') return '保存中…'
  return ''
})

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
  saveStatus.value = 'saving'
  try {
    await saveContent(docId.value, content.value)
    saveStatus.value = 'saved'
    setTimeout(() => {
      saveStatus.value = 'idle'
      loadDoc()
      loadRelated()
    }, 2000)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '保存失败')
    saveStatus.value = 'idle'
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
.document-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 64px - var(--space-6) * 2);
}

/* Topbar */
.doc-topbar {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-5);
  background: white;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-gray-200);
  margin-bottom: var(--space-4);
  flex-shrink: 0;
}
.back-btn { padding: 0; }
.doc-title-input {
  flex: 1;
  font-size: var(--font-size-xl);
  font-weight: 600;
  border: none;
  outline: none;
  background: transparent;
  color: var(--color-gray-900);
  min-width: 0;
}
.doc-title-input::placeholder { color: var(--color-gray-400); }
.topbar-right {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.save-status {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--font-size-xs);
  color: var(--color-gray-400);
}
.save-status.saved { color: var(--color-success); }
.save-status.saving { color: var(--color-warning); }

/* Body */
.doc-body {
  flex: 1;
  display: flex;
  gap: var(--space-5);
  min-height: 0;
}

/* Editor */
.editor-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-gray-200);
  overflow: hidden;
}
.editor-toolbar {
  padding: var(--space-2) var(--space-4);
  border-bottom: 1px solid var(--color-gray-100);
  background: var(--color-gray-50);
}
.toolbar-label {
  font-size: var(--font-size-xs);
  color: var(--color-gray-500);
  font-weight: 500;
}
.text-editor {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  padding: var(--space-5);
  font-size: var(--font-size-base);
  line-height: 1.8;
  color: var(--color-gray-800);
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  background: white;
}
.text-editor::placeholder { color: var(--color-gray-400); }

/* Side panel */
.side-panel {
  width: 320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  overflow-y: auto;
}
.panel-card {
  background: white;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-gray-200);
  padding: var(--space-4);
}
.panel-card.has-summary {
  border-color: var(--color-primary-200);
  background: linear-gradient(135deg, var(--color-primary-50), #f0f5ff);
}
.panel-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-gray-700);
  margin-bottom: var(--space-3);
}
.panel-body {}
.panel-empty {
  font-size: var(--font-size-xs);
  color: var(--color-gray-400);
  text-align: center;
  padding: var(--space-4) 0;
}
.summary-text {
  font-size: var(--font-size-sm);
  line-height: 1.6;
  color: var(--color-gray-700);
  margin: 0 0 var(--space-3);
}
.tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}
.related-item {
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--transition-fast);
  margin-bottom: var(--space-1);
}
.related-item:hover {
  background: var(--color-gray-50);
}
.related-title {
  font-size: var(--font-size-sm);
  font-weight: 500;
  color: var(--color-primary-600);
}
.related-summary {
  font-size: var(--font-size-xs);
  color: var(--color-gray-500);
  margin-top: 2px;
}

/* Version dialog */
.version-item {
  padding-bottom: var(--space-2);
}
.version-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}
.version-preview {
  font-size: var(--font-size-sm);
  color: var(--color-gray-500);
  margin: 0;
  line-height: 1.5;
}

@media (max-width: 1024px) {
  .side-panel { display: none; }
}
</style>