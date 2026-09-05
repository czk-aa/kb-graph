<template>
  <div class="chat-container">
    <div class="chat-sidebar">
      <div class="sidebar-header">
        <span>对话历史</span>
        <el-button size="small" text @click="newSession">+ 新对话</el-button>
      </div>
      <div class="session-list">
        <div
          v-for="s in sessions"
          :key="s.id"
          class="session-item"
          :class="{ active: s.id === sessionId }"
          @click="selectSession(s.id)"
        >
          <span class="session-title">{{ s.title || '新对话' }}</span>
          <el-button
            text
            size="small"
            type="danger"
            @click.stop="delSession(s.id)"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
        <el-empty v-if="sessions.length === 0" description="暂无对话" :image-size="60" />
      </div>
    </div>

    <div class="chat-main">
      <div v-if="!sessionId" class="chat-placeholder">
        <el-empty description="新建或选择一个对话开始提问" />
      </div>
      <div v-else class="chat-body">
        <div class="messages" ref="msgContainer">
          <div
            v-for="(m, i) in messages"
            :key="i"
            class="message"
            :class="m.role"
          >
            <div class="msg-avatar">
              <el-avatar :size="32" :icon="m.role === 'user' ? UserFilled : undefined">
                {{ m.role === 'assistant' ? 'AI' : '' }}
              </el-avatar>
            </div>
            <div class="msg-content">
              <div class="msg-text" v-html="renderMd(m.content)" />
              <div v-if="m.citations?.length" class="citations">
                <div class="citation-title">参考来源：</div>
                <div
                  v-for="c in m.citations"
                  :key="c.chunk_id"
                  class="citation-item"
                  @click="openDoc(c.doc_id)"
                >
                  <span class="citation-index">[{{ c.chunk_id }}]</span>
                  <span class="citation-doc">{{ c.doc_title }}</span>
                  <span v-if="c.section_path" class="citation-section"> > {{ c.section_path }}</span>
                  <span class="citation-score">{{ (c.score * 100).toFixed(0) }}%</span>
                </div>
              </div>
            </div>
          </div>
          <div v-if="streaming" class="message assistant">
            <div class="msg-avatar">
              <el-avatar :size="32">AI</el-avatar>
            </div>
            <div class="msg-content">
              <div class="msg-text streaming">{{ streamText }}<span class="cursor">|</span></div>
            </div>
          </div>
        </div>

        <div class="chat-input">
          <el-input
            v-model="question"
            type="textarea"
            :rows="3"
            placeholder="输入你的问题…"
            :disabled="streaming"
            @keydown.enter.exact="send"
          />
          <el-button
            type="primary"
            :loading="streaming"
            :disabled="!question.trim()"
            @click="send"
            style="margin-top: 8px;"
          >
            {{ streaming ? '思考中…' : '发送' }}
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Delete, UserFilled } from '@element-plus/icons-vue'
import {
  createSession,
  listSessions,
  getMessages,
  deleteSession,
  askStream,
  type ChatSession,
  type ChatMessage,
} from '@/api/chat'

const props = defineProps<{ spaceId: number }>()
const router = useRouter()

const sessions = ref<ChatSession[]>([])
const sessionId = ref<number>(0)
const messages = ref<ChatMessage[]>([])
const question = ref('')
const streaming = ref(false)
const streamText = ref('')
const msgContainer = ref<HTMLElement>()

onMounted(async () => {
  sessions.value = await listSessions(props.spaceId)
})

async function newSession() {
  const s = await createSession(props.spaceId)
  sessions.value.unshift(s)
  sessionId.value = s.id
  messages.value = []
}

async function selectSession(id: number) {
  sessionId.value = id
  messages.value = await getMessages(id)
  scrollBottom()
}

async function delSession(id: number) {
  await deleteSession(id)
  sessions.value = sessions.value.filter((s) => s.id !== id)
  if (sessionId.value === id) {
    sessionId.value = 0
    messages.value = []
  }
}

async function send() {
  const q = question.value.trim()
  if (!q || streaming.value) return
  question.value = ''

  messages.value.push({ id: 0, role: 'user', content: q, citations: null, meta: null })
  streamText.value = ''
  streaming.value = true
  scrollBottom()

  try {
    for await (const event of askStream(sessionId.value, q)) {
      if (event.type === 'delta') {
        streamText.value += event.data.text
        scrollBottom()
      } else if (event.type === 'done') {
        messages.value.push({
          id: 0,
          role: 'assistant',
          content: streamText.value || event.data.answer || '',
          citations: event.data.citations,
          meta: event.data.meta,
        })
        streamText.value = ''
        streaming.value = false
        scrollBottom()
      }
    }
  } catch (e: any) {
    ElMessage.error(e.message || '请求失败')
    if (streamText.value) {
      messages.value.push({
        id: 0,
        role: 'assistant',
        content: streamText.value,
        citations: null,
        meta: null,
      })
      streamText.value = ''
    }
    streaming.value = false
  }
}

function scrollBottom() {
  nextTick(() => {
    const el = msgContainer.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function openDoc(docId: number) {
  router.push(`/spaces/${props.spaceId}/documents/${docId}`)
}

function renderMd(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
}
</script>

<style scoped>
.chat-container { display: flex; height: calc(100vh - 200px); border: 1px solid var(--el-border-color); border-radius: 8px; overflow: hidden; }
.chat-sidebar { width: 240px; border-right: 1px solid var(--el-border-color); display: flex; flex-direction: column; }
.sidebar-header { padding: 12px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--el-border-color-lighter); }
.session-list { flex: 1; overflow-y: auto; }
.session-item { padding: 10px 12px; display: flex; justify-content: space-between; align-items: center; cursor: pointer; border-bottom: 1px solid var(--el-border-color-lighter); }
.session-item:hover, .session-item.active { background: var(--el-fill-color-light); }
.session-title { font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.chat-main { flex: 1; display: flex; flex-direction: column; }
.chat-placeholder { flex: 1; display: flex; align-items: center; justify-content: center; }
.chat-body { flex: 1; display: flex; flex-direction: column; }
.messages { flex: 1; overflow-y: auto; padding: 16px; }
.message { display: flex; gap: 12px; margin-bottom: 20px; }
.message.user { flex-direction: row-reverse; }
.message.user .msg-text { background: var(--el-color-primary-light-9); }
.msg-avatar { flex-shrink: 0; }
.msg-content { max-width: 75%; }
.msg-text { padding: 10px 14px; border-radius: 8px; background: var(--el-fill-color); font-size: 14px; line-height: 1.6; word-break: break-word; }
.msg-text.streaming { min-height: 20px; }
.cursor { animation: blink 1s infinite; }
@keyframes blink { 50% { opacity: 0; } }

.citations { margin-top: 8px; padding: 8px; background: var(--el-fill-color-lighter); border-radius: 6px; font-size: 12px; }
.citation-title { font-weight: 600; margin-bottom: 4px; color: var(--el-text-color-secondary); }
.citation-item { display: flex; gap: 6px; padding: 2px 0; cursor: pointer; color: var(--el-color-primary); }
.citation-item:hover { text-decoration: underline; }
.citation-index { color: var(--el-text-color-secondary); }
.citation-score { margin-left: auto; color: var(--el-text-color-placeholder); }

.chat-input { padding: 12px 16px; border-top: 1px solid var(--el-border-color); }
</style>