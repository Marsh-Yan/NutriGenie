import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { pinia } from '@/stores/pinia'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomePage.vue'),
    },
    {
      path: '/demo',
      name: 'demo-plan',
      component: () => import('@/views/DemoPlanPage.vue'),
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('@/views/ProfilePage.vue'),
      meta: { requiresAuth: true },
    },
    { path: '/auth', name: 'auth', component: () => import('@/views/AuthPage.vue') },
    {
      path: '/plan/new',
      name: 'plan-new',
      component: () => import('@/views/PlanNewPage.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/plan/:id',
      name: 'plan-result',
      component: () => import('@/views/PlanResultPage.vue'),
      meta: { requiresAuth: true },
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
  if (to.name === 'auth' && auth.isLoggedIn) return { name: 'home' }
})

router.afterEach((to) => {
  document.title = typeof to.meta.title === 'string'
    ? `${to.meta.title} · NutriGenie`
    : 'NutriGenie · AI 饮食规划'
})

export default router
