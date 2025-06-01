import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
// import Layout from '../components/HelloWorld.vue'

const routes: Array<RouteRecordRaw> = [
  {
  //路由初始指向
    path: '/',
    name: 'HelloWorld',
    component:()=>import('../components/HelloWorld.vue'),
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
