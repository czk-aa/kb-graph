<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">KB-Graph</div>
      <el-menu :default-active="route.path" router class="menu">
        <el-menu-item index="/spaces">知识空间</el-menu-item>
        <el-menu-item index="/chat" disabled>AI 问答（建设中）</el-menu-item>
        <el-menu-item index="/graph" disabled>知识图谱（建设中）</el-menu-item>
      </el-menu>
      <div class="user-box">
        <span class="nickname">{{ auth.user?.nickname ?? '...' }}</span>
        <el-button link type="danger" @click="logout">退出</el-button>
      </div>
    </el-aside>
    <el-main class="main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout {
  height: 100%;
}
.aside {
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--el-border-color-light);
}
.logo {
  font-size: 18px;
  font-weight: 700;
  padding: 20px 24px;
  color: var(--el-color-primary);
}
.menu {
  border-right: none;
  flex: 1;
}
.user-box {
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid var(--el-border-color-light);
}
.main {
  background: var(--el-fill-color-lighter);
  padding: 0;
}
</style>
