import { vi } from 'vitest'

// Mock vue-router
const mockRouter = {
  push: vi.fn(),
  replace: vi.fn(),
  back: vi.fn(),
  currentRoute: { value: { path: '/', params: {} } },
}
vi.mock('vue-router', async () => {
  const actual = await vi.importActual('vue-router')
  return {
    ...actual,
    useRouter: () => mockRouter,
    useRoute: () => ({ params: { id: '1', spaceId: '1', docId: '1' }, path: '/spaces/1' }),
  }
})

// Mock auth store
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    isLoggedIn: true,
    user: { id: 1, email: 'test@test.com', nickname: 'TestUser' },
    token: 'mock-token',
    login: vi.fn().mockResolvedValue(undefined),
    register: vi.fn().mockResolvedValue(undefined),
    logout: vi.fn(),
    fetchMe: vi.fn(),
  }),
}))

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
  ElMessageBox: {
    confirm: vi.fn().mockResolvedValue('confirm'),
    alert: vi.fn().mockResolvedValue(undefined),
  },
  ElNotification: {
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}))

// Mock Element Plus icons - use importOriginal to keep actual exports
vi.mock('@element-plus/icons-vue', async (importOriginal) => {
  const actual = await importOriginal<Record<string, any>>()
  return { ...actual }
})

// Mock ResizeObserver
global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
}