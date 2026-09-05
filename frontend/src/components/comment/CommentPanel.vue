<template>
  <div class="comments-panel">
    <h4>评论 ({{ comments.length }})</h4>

    <div class="comment-input">
      <el-input
        v-model="newComment"
        type="textarea"
        :rows="2"
        placeholder="写下你的评论…"
        @keydown.enter.ctrl="submitComment"
      />
      <el-button
        type="primary"
        size="small"
        :loading="submitting"
        :disabled="!newComment.trim()"
        @click="submitComment"
        style="margin-top: 8px"
      >
        发表
      </el-button>
    </div>

    <div v-if="comments.length" class="comment-list">
      <div v-for="c in comments" :key="c.id" class="comment-item">
        <div class="comment-avatar">
          <el-avatar :size="28">{{ c.user?.nickname?.charAt(0) || '?' }}</el-avatar>
        </div>
        <div class="comment-body">
          <div class="comment-header">
            <span class="comment-author">{{ c.user?.nickname || '未知' }}</span>
            <span class="comment-time">{{ fmt(c.created_at) }}</span>
            <el-button
              v-if="c.user_id === currentUserId"
              text
              size="small"
              type="danger"
              @click="delComment(c.id)"
            >
              删除
            </el-button>
          </div>
          <div class="comment-content">{{ c.content }}</div>
          <el-button text size="small" @click="replyTo = c.id; replyInput = ''">回复</el-button>

          <!-- 回复列表 -->
          <div v-if="c.replies?.length" class="replies">
            <div v-for="r in c.replies" :key="r.id" class="reply-item">
              <div class="comment-avatar">
                <el-avatar :size="22">{{ r.user?.nickname?.charAt(0) || '?' }}</el-avatar>
              </div>
              <div class="comment-body">
                <div class="comment-header">
                  <span class="comment-author">{{ r.user?.nickname || '未知' }}</span>
                  <span class="comment-time">{{ fmt(r.created_at) }}</span>
                  <el-button
                    v-if="r.user_id === currentUserId"
                    text
                    size="small"
                    type="danger"
                    @click="delComment(r.id)"
                  >
                    删除
                  </el-button>
                </div>
                <div class="comment-content">{{ r.content }}</div>
              </div>
            </div>
          </div>

          <!-- 回复输入框 -->
          <div v-if="replyTo === c.id" class="reply-input">
            <el-input
              v-model="replyInput"
              type="textarea"
              :rows="2"
              placeholder="写下回复…"
            />
            <div class="reply-actions">
              <el-button size="small" @click="replyTo = 0">取消</el-button>
              <el-button size="small" type="primary" :disabled="!replyInput.trim()" @click="submitReply(c.id)">回复</el-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <el-empty v-else description="暂无评论" :image-size="40" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listComments, createComment, deleteComment, type Comment } from '@/api/comments'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{ docId: number }>()
const auth = useAuthStore()

const comments = ref<Comment[]>([])
const newComment = ref('')
const submitting = ref(false)
const replyTo = ref(0)
const replyInput = ref('')

const currentUserId = auth.user?.id || 0

onMounted(async () => {
  await loadComments()
})

async function loadComments() {
  try {
    comments.value = await listComments(props.docId)
  } catch { /* ignore */ }
}

async function submitComment() {
  if (!newComment.value.trim()) return
  submitting.value = true
  try {
    await createComment(props.docId, newComment.value.trim())
    newComment.value = ''
    await loadComments()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '评论失败')
  } finally {
    submitting.value = false
  }
}

async function submitReply(parentId: number) {
  if (!replyInput.value.trim()) return
  try {
    await createComment(props.docId, replyInput.value.trim(), parentId)
    replyTo.value = 0
    replyInput.value = ''
    await loadComments()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '回复失败')
  }
}

async function delComment(id: number) {
  try {
    await deleteComment(id)
    ElMessage.success('已删除')
    await loadComments()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '删除失败')
  }
}

function fmt(d: string) {
  return new Date(d).toLocaleString('zh-CN')
}
</script>

<style scoped>
.comments-panel { margin-top: 24px; border-top: 1px solid var(--el-border-color-lighter); padding-top: 16px; }
.comments-panel h4 { margin: 0 0 12px; font-size: 15px; }
.comment-input { margin-bottom: 16px; }
.comment-list { display: flex; flex-direction: column; gap: 12px; }
.comment-item { display: flex; gap: 10px; }
.comment-avatar { flex-shrink: 0; }
.comment-body { flex: 1; }
.comment-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.comment-author { font-weight: 600; font-size: 13px; }
.comment-time { font-size: 11px; color: var(--el-text-color-placeholder); }
.comment-content { font-size: 14px; line-height: 1.6; white-space: pre-wrap; }
.replies { margin-top: 8px; padding-left: 16px; border-left: 2px solid var(--el-border-color-lighter); }
.reply-item { display: flex; gap: 8px; margin-bottom: 8px; }
.reply-input { margin-top: 8px; }
.reply-actions { display: flex; gap: 8px; margin-top: 6px; justify-content: flex-end; }
</style>