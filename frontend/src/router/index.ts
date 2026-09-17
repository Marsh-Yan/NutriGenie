import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { pinia } from '@/stores/pinia'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) return { el: to.hash, top: 92, behavior: 'smooth' }
    if (to.path === from.path) return false
    return { top: 0, behavior: 'auto' }
  },
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomePage.vue'),
      meta: { title: '首页' },
    },
    {
      path: '/demo',
      name: 'demo-plan',
      component: () => import('@/views/DemoPlanPage.vue'),
      meta: { title: '方案示例' },
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('@/views/DashboardPage.vue'),
      meta: { requiresAuth: true, title: '今日计划' },
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('@/views/ProfilePage.vue'),
      meta: { requiresAuth: true, title: '健康画像' },
    },
    { path: '/auth', name: 'auth', component: () => import('@/views/AuthPage.vue'), meta: { title: '登录或注册' } },
    {
      path: '/plan/new',
      name: 'plan-new',
      component: () => import('@/views/PlanNewPage.vue'),
      meta: { requiresAuth: true, title: '创建规划' },
    },
    {
      path: '/plan/:id',
      name: 'plan-result',
      component: () => import('@/views/PlanResultPage.vue'),
      meta: { requiresAuth: true, title: '方案结果' },
    },
    {
      path: '/plans',
      name: 'plan-history',
      component: () => import('@/views/PlanHistoryPage.vue'),
      meta: { requiresAuth: true, title: '我的方案' },
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('@/views/AdminPage.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    {
      path: '/admin/ingredients',
      name: 'admin-ingredients',
      component: () => import('@/views/AdminIngredientsPage.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
    },
    { path: '/admin/recipes', name: 'admin-recipes', component: () => import('@/views/AdminRecipesPage.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
    { path: '/admin/knowledge', name: 'admin-knowledge', component: () => import('@/views/AdminKnowledgePage.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundPage.vue'),
      meta: { title: '页面未找到' },
    },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore(pinia)
  if (!auth.restored) await auth.restore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { name: 'auth', query: { redirect: to.fullPath } }
  }
  if (to.meta.requiresAdmin && !auth.isAdmin) return { name: 'home' }
  if (to.name === 'auth' && auth.isLoggedIn) return { name: 'dashboard' }
})

router.afterEach((to) => {
  document.title = typeof to.meta.title === 'string'
    ? `${to.meta.title} · NutriGenie`
    : 'NutriGenie · AI 饮食规划'
})

export default router
