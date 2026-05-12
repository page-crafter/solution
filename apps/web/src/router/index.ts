import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import ChatHomeView from '../views/ChatHomeView.vue'
import ChatView from '../views/ChatView.vue'
import DashboardView from '../views/DashboardView.vue'
import LoginView from '../views/LoginView.vue'
import PagesView from '../views/PagesView.vue'
import PageEditorView from '../views/PageEditorView.vue'
import RunsView from '../views/RunsView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView, meta: { layout: 'empty' } },
    { path: '/', component: PageEditorView, meta: { layout: 'editor', requiresAuth: true } },
    { path: '/dashboard', component: DashboardView, meta: { layout: 'website', requiresAuth: true, requiresAdmin: true } },
    { path: '/pages', component: PagesView, meta: { layout: 'website', requiresAuth: true, requiresAdmin: true } },
    { path: '/editor', component: PageEditorView, meta: { layout: 'editor', requiresAuth: true, requiresAdmin: true } },
    { path: '/chat', component: ChatView, meta: { layout: 'website', requiresAuth: true, requiresAdmin: true } },
    { path: '/runs', component: RunsView, meta: { layout: 'website', requiresAuth: true, requiresAdmin: true } },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  await auth.initialize()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return '/login'
  }
  if (to.path === '/login' && auth.isAuthenticated) {
    return auth.isAdmin ? '/editor' : '/'
  }
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return '/'
  }
  return true
})
