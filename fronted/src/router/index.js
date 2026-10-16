import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '@/utils/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'Layout',
      component: () => import('@/layouts/layouts.vue'),
      redirect: '/home',
      meta: { requiresAuth: true },
      children: [
        {
          path: 'home',
          name: 'Home',
          component: () => import('@/views/home.vue')
        },
        {
          path: 'lab',
          name: 'Lab',
          component: () => import('@/views/lab.vue')
        },
        {
          path: 'equ',
          name: 'Equ',
          component: () => import('@/views/equ.vue')
        },
        {
          path: 'user',
          name: 'User',
          component: () => import('@/views/user.vue')
        },
        {
          path: 'reservation',
          name: 'Reservation',
          component: () => import('@/views/reservation.vue')
        },
        {
          path: 'chat',
          name: 'Chat',
          component: () => import('@/views/chat.vue')
        },
        {
          path: 'announcement',
          name: 'Announcement',
          component: () => import('@/views/announcement.vue')
        },
        {
          path: 'repair',
          name: 'Repair',
          component: () => import('@/views/repair.vue')
        }
      ]
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/login.vue')
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('@/views/register.vue')
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/home'
    }
  ]
})

// 路由守卫负责页面级鉴权；接口级安全仍由后端 JWT 校验保证。
router.beforeEach((to) => {
  const token = getToken()
  if (to.meta.requiresAuth && !token) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if ((to.path === '/login' || to.path === '/register') && token) {
    return '/home'
  }
})

export default router
