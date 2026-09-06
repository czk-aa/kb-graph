<template>
  <el-popover
    placement="bottom-end"
    :width="320"
    trigger="click"
    @show="loadNotifications"
  >
    <template #reference>
	      <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99">
	        <el-button text class="bell-btn" :class="{ 'has-unread': unreadCount > 0 }">
	          <el-icon :size="20"><Bell /></el-icon>
	        </el-button>
	      </el-badge>
	    </template>

    <div class="notify-panel">
      <div class="notify-header">
        <span>通知</span>
        <el-button
          v-if="unreadCount > 0"
          text
          size="small"
          type="primary"
          @click="markAll"
        >
          全部已读
        </el-button>
      </div>

      <div v-if="notifications.length" class="notify-list">
        <div
          v-for="n in notifications"
          :key="n.id"
          class="notify-item"
          :class="{ unread: !n.is_read }"
          @click="handleClick(n)"
        >
          <div class="notify-dot" v-if="!n.is_read" />
          <div class="notify-body">
            <div class="notify-title">{{ n.title }}</div>
            <div class="notify-text">{{ n.body?.slice(0, 100) }}</div>
            <div class="notify-time">{{ fmt(n.created_at) }}</div>
          </div>
        </div>
      </div>

      <el-empty v-else description="暂无通知" :image-size="40" />
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Bell } from '@element-plus/icons-vue'
import { listNotifications, markAllRead, markRead, type Notification } from '@/api/notifications'

const router = useRouter()
const notifications = ref<Notification[]>([])
const unreadCount = ref(0)

onMounted(() => {
  loadNotifications()
})

async function loadNotifications() {
  try {
    notifications.value = await listNotifications(false, 20)
    unreadCount.value = notifications.value.filter((n) => !n.is_read).length
  } catch { /* ignore */ }
}

async function markAll() {
  try {
    await markAllRead()
    notifications.value.forEach((n) => (n.is_read = true))
    unreadCount.value = 0
  } catch { /* ignore */ }
}

async function handleClick(n: Notification) {
  if (!n.is_read) {
    try {
      await markRead(n.id)
      n.is_read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    } catch { /* ignore */ }
  }
  // 根据类型跳转
  if (n.space_id) {
    router.push(`/spaces/${n.space_id}`)
  }
}

function fmt(d: string) {
  return new Date(d).toLocaleString('zh-CN')
}
</script>

<style scoped>
.bell-btn.has-unread .el-icon {
  animation: bell-ring 2s ease-in-out infinite;
}
@keyframes bell-ring {
  0%, 100% { transform: rotate(0); }
  5%, 15% { transform: rotate(15deg); }
  10%, 20% { transform: rotate(-15deg); }
  25% { transform: rotate(0); }
}
.notify-panel { max-height: 400px; overflow-y: auto; }
.notify-header { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--el-border-color-lighter); margin-bottom: 8px; font-weight: 600; }
.notify-list { display: flex; flex-direction: column; }
.notify-item { display: flex; gap: 8px; padding: 8px; cursor: pointer; border-radius: 4px; }
.notify-item:hover { background: var(--el-fill-color-light); }
.notify-item.unread { background: var(--el-color-primary-light-9); }
.notify-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--el-color-primary); flex-shrink: 0; margin-top: 6px; }
.notify-body { flex: 1; min-width: 0; }
.notify-title { font-size: 13px; font-weight: 500; }
.notify-text { font-size: 12px; color: var(--el-text-color-secondary); margin-top: 2px; word-break: break-all; }
.notify-time { font-size: 11px; color: var(--el-text-color-placeholder); margin-top: 4px; }
</style>