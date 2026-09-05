import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/auth/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/auth/RegisterView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      children: [
        { path: '', redirect: '/spaces' },
        {
          path: 'spaces',
          name: 'spaces',
          component: () => import('@/views/spaces/SpaceListView.vue'),
        },
        {
          path: 'spaces/:id',
          name: 'spaceDetail',
          component: () => import('@/views/space/SpaceDetailView.vue'),
        },
        {
          path: 'spaces/:spaceId/documents/:docId',
          name: 'document',
          component: () => import('@/views/document/DocumentView.vue'),
        },
      ],
    },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.isLoggedIn) {
    return { name: 'login' }
  }
  if (to.meta.public && auth.isLoggedIn && (to.name === 'login' || to.name === 'register')) {
    return { path: '/' }
  }
})

export default router