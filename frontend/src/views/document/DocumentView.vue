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

    <div class="editor-area">
      <el-input
        v-model="content"
        type="textarea"
        :rows="25"
        placeholder="在此编写文档内容…"
        class="editor"
      />
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
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import {
  getDocument,
  saveContent,
  updateDocument,
  getVersions,
  restoreVersion,
  type DocumentVersion,
} from '@/api/documents'

const route = useRoute()
const spaceId = computed(() => Number(route.params.spaceId))
const docId = computed(() => Number(route.params.docId))

const title = ref('')
const content = ref('')
const saving = ref(false)
const showVersions = ref(false)
const versions = ref<DocumentVersion[]>([])
const versionLoading = ref(false)

onMounted(async () => {
  const doc = await getDocument(docId.value)
  title.value = doc.title
  content.value = doc.content_text || ''
})

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

// 打开弹窗时自动加载版本
const showVersionsRef = ref(showVersions)
import { watch } from 'vue'
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
.editor-area { margin-top: 16px; }
.editor { font-family: 'Consolas', 'Monaco', monospace; font-size: 14px; line-height: 1.6; }
</style>