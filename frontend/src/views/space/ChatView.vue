<template>
  <div class="chat-container">
    <!-- 对话历史侧边栏 -->
    <div class="chat-sidebar custom-scrollbar">
      <div class="sidebar-header">
        <span class="sidebar-title">对话历史</span>
        <el-button size="small" type="primary" text @click="newSession" :loading="creating">
          <el-icon :size="14"><Plus /></el-icon>
          新对话
        </el-button>
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
            class="session-del"
            @click.stop="delSession(s.id)"
          >
            <el-icon :size="14"><Delete /></el-icon>
          </el-button>
        </div>
        <div v-if="sessions.length === 0" class="sidebar-empty">
          <span>暂无对话</span>
        </div>
      </div>
    </div>

    <!-- 聊天主区域 -->
    <div class="chat-main">
      <div v-if="!sessionId" class="chat-placeholder">
        <div class="placeholder-content">
          <div class="placeholder-icon">
            <el-icon :size="48" color="var(--color-primary-300)"><ChatDotRound /></el-icon>
          </div>
          <h3>AI 知识问答</h3>
          <p>基于知识图谱的智能检索增强生成</p>
          <el-button type="primary" @click="newSession" :loading="creating">开始新对话</el-button>
        </div>
      </div>

      <div v-else class="chat-body">
        <div class="messages custom-scrollbar" ref="msgContainer">
          <div
            v-for="(m, i) in messages"
            :key="i"
            class="message"
            :class="m.role"
          >
            <div class="msg-avatar">
              <div v-if="m.role === 'user'" class="avatar-circle user-avatar">
                <el-icon :size="16"><User /></el-icon>
              </div>
              <div v-else class="avatar-circle ai-avatar">
                <span class="ai-label">AI</span>
              </div>
            </div>
            <div class="msg-bubble">
              <div class="msg-text" v-html="renderMd(m.content)" />
              <div v-if="m.citations?.length" class="citations">
                <div class="citation-title">参考来源</div>
                <div
                  v-for="c in m.citations"
                  :key="c.chunk_id"
                  class="citation-item"
                  @click="openDoc(c.doc_id)"
                >
                  <span class="citation-doc">{{ c.doc_title }}</span>
                  <span v-if="c.section_path" class="citation-section">{{ c.section_path }}</span>
                  <span class="citation-score">{{ (c.score * 100).toFixed(0) }}%</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 流式生成中 -->
          <div v-if="streaming" class="message assistant">
            <div class="msg-avatar">
              <div class="avatar-circle ai-avatar">
                <span class="ai-label">AI</span>
              </div>
            </div>
            <div class="msg-bubble">
              <div class="msg-text" v-html="renderMd(streamText) || '&nbsp;'" />
              <div class="typing-indicator">
                <span /><span /><span />
              </div>
            </div>
          </div>
        </div>

        <!-- 输入区 -->
        <div class="chat-input-area">
          <div class="input-wrapper">
            <textarea
              v-model="question"
              class="chat-textarea"
              placeholder="输入你的问题…（Enter 发送，Shift+Enter 换行）"
              :disabled="streaming"
              rows="1"
              ref="inputRef"
              @keydown.enter.exact.prevent="send"
              @input="autoResize"
            />
            <el-button
              class="send-btn"
              :class="{ active: question.trim() && !streaming }"
              :disabled="!question.trim() || streaming"
              @click="send"
            >
              <el-icon :size="18"><component :is="streaming ? Loading : Promotion" /></el-icon>
            </el-button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Delete, Plus, ChatDotRound, User, Promotion, Loading } from '@element-plus/icons-vue'
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
const creating = ref(false)
const streamText = ref('')
const msgContainer = ref<HTMLElement>()
const inputRef = ref<HTMLTextAreaElement>()

onMounted(async () => {
  sessions.value = await listSessions(props.spaceId)
})

async function newSession() {
  if (creating.value) return
  creating.value = true
  try {
    // 清理已有空会话（防止积累未使用的会话）
    for (const s of sessions.value) {
      try {
        const msgs = await getMessages(s.id)
        if (msgs.length === 0) {
          await deleteSession(s.id)
          sessions.value = sessions.value.filter((x) => x.id !== s.id)
        }
      } catch { /* ignore */ }
    }
    
    const s = await createSession(props.spaceId)
    sessions.value.unshift(s)
    sessionId.value = s.id
    messages.value = []
    nextTick(() => inputRef.value?.focus())
  } finally {
    creating.value = false
  }
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
  autoResize()

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

function autoResize() {
  nextTick(() => {
    if (inputRef.value) {
      inputRef.value.style.height = 'auto'
      inputRef.value.style.height = Math.min(inputRef.value.scrollHeight, 120) + 'px'
    }
  })
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
    .replace(/`([^`]+)`/g, '<code>$1</code>')
}
</script>

<style scoped>
.chat-container {
  display: flex;
  height: calc(100vh - 320px);
  min-height: 500px;
  border-radius: var(--radius-xl);
  border: 1px solid var(--color-gray-200);
  overflow: hidden;
  background: white;
}

/* Sidebar */
.chat-sidebar {
  width: 240px;
  border-right: 1px solid var(--color-gray-100);
  display: flex;
  flex-direction: column;
  background: var(--color-gray-50);
}
.sidebar-header {
  padding: var(--space-3) var(--space-4);
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--color-gray-200);
}
.sidebar-title {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--color-gray-700);
}
.session-list { flex: 1; overflow-y: auto; }
.session-item {
  padding: var(--space-3) var(--space-4);
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  border-bottom: 1px solid var(--color-gray-100);
  transition: background var(--transition-fast);
}
.session-item:hover { background: var(--color-gray-100); }
.session-item.active { background: var(--color-primary-50); }
.session-title {
  font-size: var(--font-size-sm);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}
.session-del { opacity: 0; }
.session-item:hover .session-del { opacity: 1; }
.sidebar-empty {
  text-align: center;
  padding: var(--space-8);
  color: var(--color-gray-400);
  font-size: var(--font-size-sm);
}

/* Main */
.chat-main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.chat-placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.placeholder-content {
  text-align: center;
  color: var(--color-gray-500);
}
.placeholder-icon {
  margin-bottom: var(--space-4);
}
.placeholder-content h3 {
  font-size: var(--font-size-xl);
  font-weight: 600;
  color: var(--color-gray-700);
  margin: 0 0 var(--space-2);
}
.placeholder-content p {
  font-size: var(--font-size-sm);
  margin: 0 0 var(--space-6);
}

.chat-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* Messages */
.messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.message {
  display: flex;
  gap: var(--space-3);
  max-width: 85%;
  animation: msg-in 0.3s var(--transition-spring);
}
@keyframes msg-in {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
.message.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}
.message.assistant {
  align-self: flex-start;
}

.msg-avatar { flex-shrink: 0; margin-top: 2px; }
.avatar-circle {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
}
.user-avatar {
  background: var(--color-primary-500);
  color: white;
}
.ai-avatar {
  background: linear-gradient(135deg, #8b5cf6, #6366f1);
  color: white;
}
.ai-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.msg-bubble {
  max-width: 100%;
}
.msg-text {
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-lg);
  font-size: var(--font-size-sm);
  line-height: 1.7;
  word-break: break-word;
}
.message.user .msg-text {
  background: linear-gradient(135deg, var(--color-primary-500), var(--color-primary-600));
  color: white;
  border-bottom-right-radius: var(--radius-sm);
}
.message.assistant .msg-text {
  background: white;
  border: 1px solid var(--color-gray-200);
  color: var(--color-gray-800);
  border-bottom-left-radius: var(--radius-sm);
  box-shadow: var(--shadow-xs);
}
.msg-text :deep(code) {
  background: rgba(0,0,0,0.06);
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 0.9em;
}
.msg-text :deep(strong) { font-weight: 600; }

/* Typing indicator */
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: var(--space-2) var(--space-4);
}
.typing-indicator span {
  width: 6px;
  height: 6px;
  background: var(--color-gray-400);
  border-radius: 50%;
  animation: typing-bounce 1.4s infinite;
}
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typing-bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-6px); opacity: 1; }
}

/* Citations */
.citations {
  margin-top: var(--space-2);
  padding: var(--space-3);
  background: var(--color-gray-50);
  border-radius: var(--radius-md);
  font-size: var(--font-size-xs);
}
.citation-title {
  font-weight: 600;
  margin-bottom: var(--space-1);
  color: var(--color-gray-500);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.citation-item {
  display: flex;
  gap: var(--space-2);
  padding: 3px 0;
  cursor: pointer;
  color: var(--color-primary-600);
  transition: color var(--transition-fast);
}
.citation-item:hover { color: var(--color-primary-700); text-decoration: underline; }
.citation-doc { font-weight: 500; }
.citation-section { color: var(--color-gray-500); }
.citation-score { margin-left: auto; color: var(--color-gray-400); }

/* Input */
.chat-input-area {
  padding: var(--space-4) var(--space-6);
  border-top: 1px solid var(--color-gray-100);
  background: var(--color-gray-50);
}
.input-wrapper {
  display: flex;
  gap: var(--space-3);
  align-items: flex-end;
  background: white;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-gray-200);
  padding: var(--space-2);
  transition: border-color var(--transition-fast);
}
.input-wrapper:focus-within {
  border-color: var(--color-primary-400);
  box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
}
.chat-textarea {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  padding: var(--space-2) var(--space-3);
  font-size: var(--font-size-sm);
  line-height: 1.6;
  font-family: var(--font-family);
  color: var(--color-gray-800);
  min-height: 24px;
  max-height: 120px;
}
.chat-textarea::placeholder { color: var(--color-gray-400); }
.send-btn {
  width: 38px;
  height: 38px;
  border-radius: var(--radius-md);
  border: none;
  background: var(--color-gray-200);
  color: var(--color-gray-400);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--transition-fast);
  flex-shrink: 0;
  padding: 0;
}
.send-btn.active {
  background: var(--color-primary-500);
  color: white;
}
.send-btn.active:hover {
  background: var(--color-primary-600);
  box-shadow: var(--shadow-glow);
}

@media (max-width: 768px) {
  .chat-sidebar { display: none; }
}
</style>