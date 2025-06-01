<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const goHome = () => {
  router.push('/')
}
</script>

<template>
  <div class="not-found-container">
    <div class="not-found-content">
      <h1 class="error-code">404</h1>
      <h2 class="error-title">页面不存在</h2>
      <p class="error-description">抱歉，您访问的页面不存在或已被移除。</p>
      <el-button type="primary" @click="goHome">返回首页</el-button>
    </div>
  </div>
</template>

<style scoped>
.not-found-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 80vh;
  text-align: center;
}

.not-found-content {
  max-width: 500px;
  padding: 40px;
}

.error-code {
  font-size: 120px;
  margin: 0;
  color: var(--el-color-primary);
  line-height: 1;
}

.error-title {
  font-size: 32px;
  margin: 20px 0;
}

.error-description {
  font-size: 16px;
  color: #606266;
  margin-bottom: 30px;
}
</style> 