<template>
    <div id="app">
      <el-container style="height:100%;padding: 1%;">
        <!-- 侧边栏 -->
        <el-aside width="100%" class="sidebar">
          <el-menu
            default-active="1"
            class="el-menu-vertical-demo"
            @select="handleSelect"
          >
            <el-menu-item index="scan">实时检测</el-menu-item>
            <el-menu-item index="record">登录记录</el-menu-item>
            <el-menu-item index="demonstrate">说明文档</el-menu-item>
            <el-menu-item index="login">重新登录</el-menu-item>
          </el-menu>
        </el-aside>
      </el-container>
    </div>
  </template>
  
  <script setup>
  import { ElContainer, ElAside, ElMain, ElMenu, ElMenuItem } from 'element-plus'
  import { defineEmits } from 'vue';
  const emit = defineEmits(['login','scan','record','demonstrate'])
  const handleSelect = (index) => {
    console.log('选中的菜单项：', index)
    if( index === 'login'){
      emit('login','login')
    }else if(index === 'scan'){
      emit('scan','scan')
    }else if(index === 'record'){
      emit('record','record')
    }else if(index === 'demonstrate'){
      emit('demonstrate','demonstrate')
    }

  }
  </script>
  
  <style scoped>
  #app {
    font-family: Avenir, Helvetica, Arial, sans-serif;
  }
  
  .el-menu-vertical-demo {
    border-right: none;
  }
  
  .el-menu-item {
    background-color: #e4edef19;
  }

  .sidebar {
    background-color: #e4edef19;
    width: 100%;
    padding-top: 0%;
    border: 1px solid #e4edef19;
  border-radius: 15px; /* 这个值越大，圆角就越明显 */
  box-shadow: 0 8px 8px rgba(21, 21, 21, 0.1); /* 添加阴影效果，增强柔和感 */
  }
  
  .content {
    padding: 0%;
    text-align: center;
  }
  </style>
  