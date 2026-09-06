<template>
  <div class="auth-page">
    <div class="auth-brand">
      <div class="brand-content">
        <div class="brand-logo">
          <div class="logo-icon">
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
              <rect width="40" height="40" rx="10" fill="white" fill-opacity="0.2"/>
              <path d="M12 28V14L20 10L28 14V28L20 32L12 28Z" stroke="white" stroke-width="2" fill="none"/>
              <circle cx="20" cy="21" r="4" fill="white" fill-opacity="0.6"/>
            </svg>
          </div>
        </div>
        <h1 class="brand-title">加入 KB-Graph</h1>
        <p class="brand-subtitle">开启 AI 驱动的知识管理之旅</p>
      </div>
    </div>

    <div class="auth-form-section">
      <div class="auth-card glass-strong">
        <h2 class="form-title">创建账号</h2>
        <p class="form-subtitle">注册后即可创建你的知识空间</p>

        <el-form :model="form" label-position="top" @submit.prevent>
          <el-form-item label="昵称">
            <el-input
              v-model="form.nickname"
              placeholder="你的名字"
              size="large"
              :prefix-icon="User"
            />
          </el-form-item>
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
              placeholder="至少 8 位"
              size="large"
              show-password
              :prefix-icon="Lock"
            />
            <div class="password-strength" v-if="form.password">
              <div class="strength-bar">
                <div class="strength-fill" :class="strengthClass" :style="{ width: strengthPercent + '%' }" />
              </div>
              <span class="strength-label">{{ strengthLabel }}</span>
            </div>
          </el-form-item>
          <el-button
            type="primary"
            size="large"
            class="submit-btn"
            :loading="loading"
            @click="submit"
          >
            {{ loading ? '注册中…' : '注册' }}
          </el-button>
        </el-form>

        <div class="switch-text">
          已有账号？
          <router-link to="/login" class="switch-link">立即登录</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Message, Lock, User } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const form = reactive({ email: '', password: '', nickname: '' })

const strengthPercent = computed(() => {
  const len = form.password.length
  if (len < 4) return 25
  if (len < 8) return 50
  if (len < 12) return 75
  return 100
})
const strengthClass = computed(() => {
  const p = strengthPercent.value
  if (p <= 25) return 'weak'
  if (p <= 50) return 'medium'
  if (p <= 75) return 'good'
  return 'strong'
})
const strengthLabel = computed(() => {
  const p = strengthPercent.value
  if (p <= 25) return '弱'
  if (p <= 50) return '一般'
  if (p <= 75) return '良好'
  return '强'
})

async function submit() {
  if (!form.email || !form.password || !form.nickname) {
    ElMessage.warning('请填写完整信息')
    return
  }
  if (form.password.length < 8) {
    ElMessage.warning('密码至少 8 位')
    return
  }
  loading.value = true
  try {
    await auth.register(form.email, form.password, form.nickname)
    router.push('/')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { message?: string } } }
    ElMessage.error(err.response?.data?.message ?? '注册失败')
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
.password-strength {
  margin-top: var(--space-2);
}
.strength-bar {
  height: 4px;
  background: var(--color-gray-200);
  border-radius: var(--radius-full);
  overflow: hidden;
  margin-bottom: var(--space-1);
}
.strength-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width var(--transition-base), background var(--transition-base);
}
.strength-fill.weak { background: var(--color-danger); }
.strength-fill.medium { background: var(--color-warning); }
.strength-fill.good { background: var(--color-primary-400); }
.strength-fill.strong { background: var(--color-success); }
.strength-label {
  font-size: var(--font-size-xs);
  color: var(--color-gray-500);
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