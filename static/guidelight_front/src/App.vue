<script setup lang="ts">
import { ref, computed } from 'vue'
// @ts-ignore
import { useRouter, useRoute } from 'vue-router'
import { 
  Location, 
  VideoCamera, 
  Monitor, 
  Menu as IconMenu,
  HomeFilled,
  SwitchButton,
  Guide
} from '@element-plus/icons-vue'

const isCollapse = ref(false)
const router = useRouter()
const route = useRoute()

// 计算当前是否在登录页面或介绍页面
const isFullPage = computed(() => {
  return route.path === '/login' || route.path === '/introduction'
})

const handleSelect = (key: string) => {
  router.push(key)
}

const toggleSidebar = () => {
  isCollapse.value = !isCollapse.value
}

// 退出登录
const logout = () => {
  localStorage.removeItem('user')
  router.push('/login')
}
</script>

<template>
  <!-- 全屏页面直接渲染路由内容，不显示导航 -->
  <router-view v-if="isFullPage" />
  
  <!-- 非全屏页面显示布局 -->
  <div v-else class="app-container">
    <el-container class="layout-container">
      <!-- 侧边栏 -->
      <el-aside :width="isCollapse ? '64px' : '200px'" class="aside">
        <div class="logo-container">
          <h1 class="logo-text" v-if="!isCollapse">盲人助手</h1>
          <h1 class="logo-text" v-else>盲</h1>
        </div>
        <el-menu
          default-active="dashboard"
          class="el-menu-vertical"
          :collapse="isCollapse"
          @select="handleSelect"
          router
        >
          <el-menu-item index="/dashboard">
            <el-icon><HomeFilled /></el-icon>
            <template #title>控制面板</template>
          </el-menu-item>
          <el-menu-item index="/video-monitor">
            <el-icon><VideoCamera /></el-icon>
            <template #title>视频监控</template>
          </el-menu-item>
          <el-menu-item index="/location">
            <el-icon><Location /></el-icon>
            <template #title>位置追踪</template>
          </el-menu-item>
          <el-menu-item index="/integrated-monitoring">
            <el-icon><Monitor /></el-icon>
            <template #title>综合监控</template>
          </el-menu-item>
          <el-menu-item index="/introduction">
            <el-icon><Guide /></el-icon>
            <template #title>系统介绍</template>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <!-- 主内容区 -->
      <el-container>
        <el-header class="header">
          <div class="header-left">
            <el-icon class="toggle-button" @click="toggleSidebar">
              <IconMenu />
            </el-icon>
            <h2 class="title">盲人安全实时检测系统 - 家人视角</h2>
          </div>
          <div class="header-right">
            <el-dropdown>
              <el-button type="primary" text>
                用户中心 <el-icon><SwitchButton /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="logout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-header>
        <el-main class="main-content">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<style scoped>
.app-container {
  height: 100vh;
  width: 100vw;
}

.layout-container {
  height: 100%;
}

.aside {
  background-color: #304156;
  transition: width 0.3s;
  overflow: hidden;
}

.logo-container {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 0;
}

.logo-text {
  color: #fff;
  font-size: 20px;
  margin: 0;
  white-space: nowrap;
}

.el-menu-vertical {
  border-right: none;
}

.header {
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
}

.toggle-button {
  font-size: 20px;
  margin-right: 15px;
  cursor: pointer;
}

.title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.main-content {
  background-color: #f5f7fa;
  padding: 20px;
  overflow-y: auto;
}
</style>
