<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { systemApi } from '../api'

const router = useRouter()

// 系统状态
const systemStatus = ref({
  status: '正在连接...',
  modules: {
    video_modules: false,
    database: false
  },
  cameras: {
    d_estimator: false,
    f_detector: false,
    f_tracker: false,
    g_recognition: false,
    g_recognizer: false,
    m_detector: false,
    p_video: false,
    s_RGB: false
  }
})

// 显示摄像头友好名称
const cameraNames = {
  d_estimator: '视差估计',
  f_detector: '特征点检测器',
  f_tracker: '特征点追踪器',
  g_recognition: '手势特征点识别',
  g_recognizer: '手势识别',
  m_detector: 'MobileNetSSD目标检测',
  p_video: '人像追踪',
  s_RGB: '空间对象追踪'
}

// 定时刷新ID
let refreshTimer: number | null = null

// 获取系统状态
const fetchSystemStatus = async () => {
  try {
    const response = await systemApi.getHealth()
    systemStatus.value = response.data
    if (systemStatus.value.status === 'online') {
      ElMessage.success('系统连接成功')
    }
  } catch (error) {
    console.error('获取系统状态失败:', error)
    ElMessage.error('系统连接失败')
    systemStatus.value.status = '离线'
  }
}

// 导航到视频监控页面
const goToVideoMonitor = () => {
  router.push('/video-monitor')
}

// 导航到位置追踪页面
const goToLocationTrack = () => {
  router.push('/location')
}

// 获取摄像头名称
const getCameraName = (key: string) => {
  return cameraNames[key as keyof typeof cameraNames] || key
}

// 获取摄像头状态类型
const getCameraStatusType = (status: boolean) => {
  return status ? 'success' : 'info'
}

// 页面加载时获取系统状态
onMounted(() => {
  fetchSystemStatus()
  // 每30秒刷新一次系统状态
  refreshTimer = window.setInterval(fetchSystemStatus, 30000)
})

// 页面卸载时清除定时器
onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<template>
  <div class="dashboard-container">
    <el-row :gutter="20">
      <!-- 系统状态卡片 -->
      <el-col :span="24">
        <el-card shadow="hover" class="status-card">
          <template #header>
            <div class="card-header">
              <h2>系统状态</h2>
              <el-button type="primary" @click="fetchSystemStatus" size="small">
                刷新状态
              </el-button>
            </div>
          </template>

          <div class="status-overview">
            <div class="status-item">
              <span class="label">系统状态:</span>
              <el-tag :type="systemStatus.status === 'online' ? 'success' : 'danger'">
                {{ systemStatus.status === 'online' ? '在线' : '离线' }}
              </el-tag>
            </div>
          </div>

          <el-divider />

          <h3>模块状态</h3>
          <el-row :gutter="20">
            <el-col :md="12" :sm="24">
              <div class="status-item">
                <span class="label">视频模块:</span>
                <el-tag :type="systemStatus.modules.video_modules ? 'success' : 'danger'">
                  {{ systemStatus.modules.video_modules ? '可用' : '不可用' }}
                </el-tag>
              </div>
            </el-col>
            <el-col :md="12" :sm="24">
              <div class="status-item">
                <span class="label">数据库:</span>
                <el-tag :type="systemStatus.modules.database ? 'success' : 'danger'">
                  {{ systemStatus.modules.database ? '已连接' : '未连接' }}
                </el-tag>
              </div>
            </el-col>
          </el-row>

          <el-divider />

          <h3>摄像头状态</h3>
          <el-row :gutter="20">
            <el-col :xl="6" :lg="8" :md="12" :sm="24" v-for="(value, key) in systemStatus.cameras" :key="key">
              <div class="status-item">
                <span class="label">{{ getCameraName(key) }}:</span>
                <el-tag :type="getCameraStatusType(value)">
                  {{ value ? '运行中' : '未启动' }}
                </el-tag>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="feature-row">
      <el-col :lg="8" :md="12" :sm="24">
        <el-card shadow="hover" class="feature-card">
          <div class="feature-content">
            <el-icon class="feature-icon"><VideoCamera /></el-icon>
            <h3>视频监控</h3>
            <p>监控盲人用户的实时视频流，查看周围环境和物体识别结果</p>
            <el-button type="primary" @click="goToVideoMonitor">进入监控</el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :lg="8" :md="12" :sm="24">
        <el-card shadow="hover" class="feature-card">
          <div class="feature-content">
            <el-icon class="feature-icon"><Location /></el-icon>
            <h3>位置追踪</h3>
            <p>实时追踪盲人用户的位置信息，查看历史轨迹和地图导航</p>
            <el-button type="primary" @click="goToLocationTrack">查看位置</el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :lg="8" :md="12" :sm="24">
        <el-card shadow="hover" class="feature-card">
          <div class="feature-content">
            <el-icon class="feature-icon"><Bell /></el-icon>
            <h3>紧急提醒</h3>
            <p>接收紧急情况通知，快速响应可能的危险情况</p>
            <el-button type="primary" disabled>敬请期待</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.dashboard-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  margin: 0;
  font-size: 1.5rem;
}

.status-card {
  margin-bottom: 20px;
}

.status-overview {
  margin-bottom: 20px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding: 5px 0;
}

.status-item .label {
  font-weight: 500;
}

.feature-row {
  margin-top: 20px;
}

.feature-card {
  height: 100%;
  margin-bottom: 20px;
}

.feature-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 10px;
}

.feature-icon {
  font-size: 48px;
  margin-bottom: 15px;
  color: var(--el-color-primary);
}

.feature-content h3 {
  margin-top: 0;
  margin-bottom: 10px;
}

.feature-content p {
  margin-bottom: 20px;
  color: #606266;
  flex-grow: 1;
}
</style> 
 