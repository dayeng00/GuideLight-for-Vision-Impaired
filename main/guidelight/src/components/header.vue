<template>
    <el-header class="main-header">
      <div class="header-content">
        <!-- 左侧 Logo 和标题 -->
        <div class="header-left">
          
          <span class="project-name">障碍检测系统</span>
        </div>
  
        <!-- 中间导航菜单 -->
        <el-menu 
          class="nav-menu"
          mode="horizontal"
          :default-active="activeMenu"
          @select="handleMenuSelect"
        >
          <el-menu-item index="home">首页</el-menu-item>
          <el-menu-item index="about">关于我们</el-menu-item>
        </el-menu>
  
        <!-- 右侧用户信息 -->
        <div class="header-right">
          <el-dropdown>
            <div class="user-info">
              <el-avatar 
                src="https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png"
                class="user-avatar"
              />
              <span class="user-name">张三</span>
              <el-icon class="el-icon--right">
                <arrow-down />
              </el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu
              @select="handleMenuSelect">
                <el-dropdown-item>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </el-header>
  </template>
  
  <script setup>
  import { ref } from 'vue'
  import { ElHeader, ElMenu, ElMenuItem, ElDropdown, ElDropdownMenu, ElDropdownItem, ElAvatar, ElIcon } from 'element-plus'
  import { defineEmits } from 'vue';
  const activeMenu = ref('1')
  
  const emit = defineEmits(['home', 'about'])

  const handleMenuSelect = (index) => {
    console.log('选中菜单:', index)
    if(index === 'home') {
      // 跳转到首页
      console.log('跳转到首页')
      emit('home','home')
    } else if(index === 'about') {
      // 跳转到关于我们页面
      console.log('跳转到关于我们页面')
      emit('about','about')
    }
  }
  </script>
  
  <style scoped>
  .main-header {
    height: 60px;
    background-color: #ffffff;
    border-bottom: 1px solid #e6e6e6;
    display: flex;
    align-items: center;
    padding: 0 20px;
  }
  
  .header-content {
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .header-left {
    display: flex;
    align-items: center;
    min-width: 200px;
  }
  
  .logo {
    width: 36px;
    height: 36px;
    margin-right: 12px;
  }
  
  .project-name {
    font-size: 18px;
    font-weight: 600;
    color: #303133;
  }
  
  .nav-menu {
    flex: 1;
    border-bottom: none;
    margin: 0 20px;
  }
  
  .header-right {
    min-width: 160px;
    display: flex;
    justify-content: flex-end;
  }
  
  .user-info {
    display: flex;
    align-items: center;
    cursor: pointer;
    padding: 5px 10px;
    transition: background-color 0.3s;
  }
  
  .user-info:hover {
    background-color: #f5f7fa;
    border-radius: 4px;
  }
  
  .user-avatar {
    margin-right: 8px;
  }
  
  .user-name {
    font-size: 14px;
    color: #606266;
  }
  </style>