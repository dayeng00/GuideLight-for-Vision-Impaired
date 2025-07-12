<template>
  <div class="system-settings-container">
    <el-card class="settings-card">
      <template #header>
        <div class="card-header">
          <h3>系统设置</h3>
        </div>
      </template>
      
      <el-form label-position="top">
        <el-form-item label="系统主题">
          <el-radio-group v-model="settings.theme">
            <el-radio label="light">浅色主题</el-radio>
            <el-radio label="dark">深色主题</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="语言设置">
          <el-select v-model="settings.language" placeholder="请选择语言">
            <el-option label="中文" value="zh-CN" />
            <el-option label="English" value="en-US" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="通知设置">
          <el-switch v-model="settings.notifications" />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="saveSettings">保存设置</el-button>
          <el-button @click="resetSettings">重置设置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const settings = ref({
  theme: 'light',
  language: 'zh-CN',
  notifications: true
})

const saveSettings = () => {
  // 保存设置到localStorage
  localStorage.setItem('systemSettings', JSON.stringify(settings.value))
  ElMessage.success('设置已保存')
}

const resetSettings = () => {
  settings.value = {
    theme: 'light',
    language: 'zh-CN',
    notifications: true
  }
  ElMessage.info('设置已重置')
}
</script>

<style scoped>
.system-settings-container {
  padding: 20px;
}

.settings-card {
  max-width: 600px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}
</style> 