<template>
  <div class="main-layout" :class="{ collapsed: isCollapsed }">
    <!-- 深色侧边栏 -->
    <aside class="sidebar" :class="{ collapsed: isCollapsed }">
      <div class="sidebar-logo" @click="router.push('/spaces')">
        <div class="logo-icon">KB</div>
        <span class="logo-text">KB-Graph</span>
      </div>

      <nav class="sidebar-nav">
        <el-menu
          :default-active="route.path"
          router
          :collapse="isCollapsed"
          background-color="transparent"
          text-color="var(--sidebar-text)"
          active-text-color="var(--sidebar-text-active)"
        >
          <el-menu-item index="/spaces">
            <el-icon><Folder /></el-icon>
            <template #title>知识空间</template>
          </el-menu-item>
        </el-menu>
      </nav>

      <div class="sidebar-bottom">
        <div class="sidebar-user">
          <el-avatar :size="32">{{ auth.user?.nickname?.charAt(0) || '?' }}</el-avatar>
          <div class="user-info" v-show="!isCollapsed">
            <div class="user-name">{{ auth.user?.nickname || '...' }}</div>
            <div class="user-role">成员</div>
          </div>
        </div>
        <el-button
          class="collapse-btn"
          text
          @click="toggleCollapse"
        >
          <el-icon :size="18">
            <Fold v-if="!isCollapsed" />
            <Expand v-else />
          </el-icon>
        </el-button>
      </div>
    </aside>

    <!-- 主内容区 -->
    <div class="main-area">
      <header class="topbar">
        <div class="topbar-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/spaces' }">知识空间</el-breadcrumb-item>
            <el-breadcrumb-item v-if="route.params.id">详情</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="topbar-right">
          <NotificationBell />
          <el-button
            text
            class="logout-btn"
            @click="logout"
          >
            <el-icon :size="18"><SwitchButton /></el-icon>
          </el-button>
        </div>
      </header>

      <main class="main-content">
        <router-view />
      </main>
    </div>

    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Folder, Fold, Expand, SwitchButton } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import NotificationBell from '@/components/notification/NotificationBell.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const isCollapsed = ref(localStorage.getItem('sidebar-collapsed') === 'true')

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
  localStorage.setItem('sidebar-collapsed', String(isCollapsed.value))
}

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.main-layout {
  display: flex;
  min-height: 100vh;
  background: var(--color-gray-50);
}

/* Sidebar */
.sidebar {
  width: var(--sidebar-width);
  background: var(--sidebar-bg);
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: var(--z-sidebar);
  display: flex;
  flex-direction: column;
  transition: width var(--transition-base);
  overflow: hidden;
}
.sidebar.collapsed {
  width: var(--sidebar-collapsed-width);
}

.sidebar-logo {
  padding: var(--space-4) var(--space-4);
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 64px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  cursor: pointer;
}
.logo-icon {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, var(--color-primary-400), var(--color-primary-600));
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 800;
  font-size: var(--font-size-sm);
  flex-shrink: 0;
}
.logo-text {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: white;
  white-space: nowrap;
  overflow: hidden;
}

.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-3) 0;
}
.sidebar-nav :deep(.el-menu-item) {
  margin: 2px var(--space-2);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  height: 44px;
  line-height: 44px;
}
.sidebar-nav :deep(.el-menu-item:hover) {
  background: var(--sidebar-item-hover) !important;
}
.sidebar-nav :deep(.el-menu-item.is-active) {
  background: var(--sidebar-item-active) !important;
  color: var(--color-primary-400) !important;
  font-weight: 600;
}

.sidebar-bottom {
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding: var(--space-3) var(--space-4);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.sidebar-user {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
.user-info {
  overflow: hidden;
}
.user-name {
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: var(--sidebar-text);
  white-space: nowrap;
}
.user-role {
  font-size: var(--font-size-xs);
  color: var(--color-gray-500);
}
.collapse-btn {
  color: var(--sidebar-text);
  flex-shrink: 0;
}
.collapse-btn:hover {
  color: var(--sidebar-text-active);
}

/* Main area */
.main-area {
  flex: 1;
  margin-left: var(--sidebar-width);
  transition: margin-left var(--transition-base);
  min-width: 0;
}
.main-layout.collapsed .main-area {
  margin-left: var(--sidebar-collapsed-width);
}

/* Topbar */
.topbar {
  position: sticky;
  top: 0;
  height: 64px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--color-gray-200);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-6);
  z-index: var(--z-topbar);
}
.topbar-left {
  display: flex;
  align-items: center;
}
.topbar-right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.logout-btn {
  color: var(--color-gray-500);
}
.logout-btn:hover {
  color: var(--color-danger);
}

/* Main content */
.main-content {
  padding: var(--space-6);
  min-height: calc(100vh - 64px);
}

@media (max-width: 768px) {
  .sidebar {
    width: var(--sidebar-collapsed-width);
  }
  .main-area {
    margin-left: var(--sidebar-collapsed-width);
  }
}
</style>