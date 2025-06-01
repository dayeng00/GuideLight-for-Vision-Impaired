import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw, RouteLocationNormalized, NavigationGuardNext } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/introduction'
  },
  {
    path: '/introduction',
    name: 'Introduction',
    component: () => import('../views/Introduction.vue'),
    meta: {
      title: '欢迎',
      requiresAuth: false
    }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: {
      title: '登录',
      requiresAuth: false
    }
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: Dashboard,
    meta: {
      title: '仪表盘'
    }
  },
  {
    path: '/video-monitor',
    name: 'VideoMonitor',
    component: () => import('../views/VideoMonitor.vue'),
    meta: {
      title: '视频监控'
    }
  },
  {
    path: '/location',
    name: 'Location',
    component: () => import('../views/Location.vue'),
    meta: {
      title: '位置追踪'
    }
  },
  {
    path: '/integrated-monitoring',
    name: 'IntegratedMonitoring',
    component: () => import('../views/IntegratedMonitoring.vue'),
    meta: {
      title: '综合监控',
      requiresAuth: true
    }
  },
  {
    path: '/system-settings',
    name: 'SystemSettings',
    component: () => import('../views/SystemSettings.vue'),
    meta: {
      title: '系统设置'
    }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/SystemSettings.vue'),
    meta: {
      title: '系统设置'
    }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('../views/NotFound.vue'),
    meta: {
      title: '页面不存在'
    }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由前置守卫，用于检查登录状态
router.beforeEach((to: RouteLocationNormalized, from: RouteLocationNormalized, next: NavigationGuardNext) => {
  // 设置页面标题
  document.title = `${to.meta.title || '首页'} - 视障人士辅助系统`
  
  // 检查路由是否需要身份验证
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)
  
  // 获取用户登录状态
  const userString = localStorage.getItem('user')
  const isLoggedIn = userString ? JSON.parse(userString).isLoggedIn : false
  
  if (requiresAuth && !isLoggedIn) {
    // 需要身份验证但用户未登录，重定向到登录页面
    next({ name: 'Login' })
  } else if (to.path === '/login' && isLoggedIn) {
    // 用户已登录且尝试访问登录页面，重定向到控制面板
    next({ name: 'Dashboard' })
  } else {
    // 其他情况，允许访问
    next()
  }
})

export default router 