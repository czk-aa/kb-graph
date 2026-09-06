<template>
  <div class="auth-page">
    <!-- 左侧品牌区 -->
    <div class="auth-brand">
      <div class="brand-content">
        <div class="brand-logo">
          <div class="logo-icon">
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
              <rect width="40" height="40" rx="10" fill="white" fill-opacity="0.2"/>
              <path d="M12 28V14L20 10L28 14V28L20 32L12 28Z" stroke="white" stroke-width="2" fill="none"/>
              <circle cx="20" cy="21" r="4" fill="white" fill-opacity="0.6"/>
              <line x1="20" y1="17" x2="20" y2="11" stroke="white" stroke-width="1.5" opacity="0.4"/>
              <line x1="20" y1="25" x2="20" y2="31" stroke="white" stroke-width="1.5" opacity="0.4"/>
            </svg>
          </div>
        </div>
        <h1 class="brand-title">KB-Graph</h1>
        <p class="brand-subtitle">AI 驱动的企业知识图谱平台</p>
        <div class="brand-features">
          <div class="feature-item">
            <span class="feature-dot" />
            <span>知识图谱可视化</span>
          </div>
          <div class="feature-item">
            <span class="feature-dot" />
            <span>GraphRAG 混合检索</span>
          </div>
          <div class="feature-item">
            <span class="feature-dot" />
            <span>团队协作 + AI 双驱动</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧表单区 -->
    <div class="auth-form-section">
      <div class="auth-card glass-strong">
        <h2 class="form-title">欢迎回来</h2>
        <p class="form-subtitle">登录你的知识库账号</p>

        <el-form :model="form" label-position="top" @submit.prevent>
          <el-form-item label="邮箱">
            <el-input
              v-model="form.email"
              type="email"
              placeholder="you@company.com"
              size="large"
              :prefix-icon="Message"
            />
          </el-form-item>
          <el-form-item label="密码">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="输入密码"
              size="large"
              show-password
              :prefix-icon="Lock"
            />
          </el-form-item>
          <el-button
            type="primary"
            size="large"
            class="submit-btn"
            :loading="loading"
            @click="submit"
          >
            {{ loading ? '登录中…' : '登录' }}
          </el-button>
        </el-form>

        <div class="switch-text">
          没有账号？
          <router-link to="/register" class="switch-link">立即注册</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Message, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const form = reactive({ email: '', password: '' })

async function submit() {
  if (!form.email || !form.password) {
    ElMessage.warning('请填写邮箱和密码')
    return
  }
  loading.value = true
  try {
    await auth.login(form.email, form.password)
    router.push('/')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { message?: string } } }
    ElMessage.error(err.response?.data?.message ?? '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.auth-brand {
  flex: 1;
  background: linear-gradient(135deg, #1e3a8a 0%, #1d4ed8 40%, #2563eb 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}
.auth-brand::before {
  content: '';
  position: absolute;
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(255,255,255,0.08), transparent 70%);
  border-radius: 60% 40% 30% 70% / 60% 30% 70% 40%;
  animation: blob-float 8s ease-in-out infinite alternate;
  top: -10%;
  right: -10%;
}
.auth-brand::after {
  content: '';
  position: absolute;
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(59,130,246,0.3), transparent 70%);
  border-radius: 40% 60% 70% 30% / 40% 50% 60% 50%;
  animation: blob-float 6s ease-in-out infinite alternate-reverse;
  bottom: -5%;
  left: -5%;
}

@keyframes blob-float {
  0% { transform: translate(0, 0) rotate(0deg) scale(1); }
  33% { transform: translate(30px, -50px) rotate(120deg) scale(1.1); }
  66% { transform: translate(-20px, 20px) rotate(240deg) scale(0.9); }
  100% { transform: translate(10px, -30px) rotate(360deg) scale(1); }
}

.brand-content {
  position: relative;
  z-index: 1;
  text-align: center;
  color: white;
  padding: var(--space-10);
}
.brand-logo { margin-bottom: var(--space-6); }
.logo-icon { display: inline-block; }
.brand-title {
  font-size: var(--font-size-4xl);
  font-weight: 800;
  margin-bottom: var(--space-2);
  letter-spacing: -0.02em;
}
.brand-subtitle {
  font-size: var(--font-size-lg);
  opacity: 0.75;
  margin-bottom: var(--space-10);
}
.brand-features {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  text-align: left;
  padding: 0 var(--space-8);
}
.feature-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--font-size-sm);
  opacity: 0.85;
}
.feature-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255,255,255,0.6);
  flex-shrink: 0;
}

.auth-form-section {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  background: var(--color-gray-50);
}

.auth-card {
  width: 420px;
  border-radius: var(--radius-2xl);
  padding: var(--space-10);
  box-shadow: var(--shadow-2xl);
  animation: card-enter 0.6s var(--transition-spring);
}
@keyframes card-enter {
  from { opacity: 0; transform: translateY(30px) scale(0.95); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.form-title {
  font-size: var(--font-size-3xl);
  font-weight: 700;
  margin: 0 0 var(--space-1);
  color: var(--color-gray-900);
}
.form-subtitle {
  color: var(--color-gray-500);
  margin: 0 0 var(--space-8);
  font-size: var(--font-size-sm);
}

.submit-btn {
  width: 100%;
  margin-top: var(--space-2);
  height: 44px;
  font-size: var(--font-size-base);
  font-weight: 600;
}

.switch-text {
  margin-top: var(--space-6);
  text-align: center;
  font-size: var(--font-size-sm);
  color: var(--color-gray-500);
}
.switch-link {
  color: var(--color-primary-500);
  font-weight: 600;
}
.switch-link:hover {
  color: var(--color-primary-600);
}

@media (max-width: 768px) {
  .auth-brand { display: none; }
  .auth-card { width: 90%; padding: var(--space-6); }
}
</style>