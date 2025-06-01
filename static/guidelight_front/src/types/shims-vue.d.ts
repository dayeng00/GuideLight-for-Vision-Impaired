declare module 'vue-router' {
  import type { DefineComponent } from 'vue'
  export type RouteRecordRaw = any
  export type RouteLocationNormalized = any
  export type NavigationGuardNext = any
  export const createRouter: any
  export const createWebHistory: any
  export const useRouter: any
  export const useRoute: any
  const _default: DefineComponent
  export default _default
}

declare module 'element-plus' {
  import type { Component } from 'vue'
  const ElComponent: Component
  export default ElComponent
  export const ElMessage: any
  export const ElMessageBox: any
  export const ElNotification: any
}

declare module 'element-plus/dist/locale/zh-cn.mjs'
declare module '@element-plus/icons-vue'

// 高德地图类型声明
interface Window {
  AMap: any
} 