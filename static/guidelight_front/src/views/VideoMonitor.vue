<script setup lang="ts">
import { ref, onMounted, onUnmounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
// @ts-ignore
import { videoApi } from '../api'

// 摄像头类型
const cameraTypes = [
  { id: 'd_estimator', name: '视差估计', hasDual: false },
  { id: 'f_detector', name: '特征点检测', hasDual: true },
  { id: 'f_tracker', name: '特征点追踪', hasDual: true },
  { id: 'g_recognition', name: '手势特征点识别', hasDual: false },
  { id: 'g_recognizer', name: '手势类别判断', hasDual: false },
  { id: 'm_detector', name: 'MobileNetSSD目标检测', hasDual: false },
  { id: 'p_video', name: '人像追踪', hasDual: false },
  { id: 's_RGB', name: '空间物体追踪', hasDual: false }
]

const activeCameraType = ref('f_detector')
const isLoading = ref(false)
const isStoppingCamera = ref(false) // 单独跟踪停止摄像头的状态
const errorMsg = ref('')
const cameraRunning = ref(false)

// 控制视频流刷新
const refreshKey = ref(Date.now())

// 添加防抖控制
let isShuttingDown = false
let lastRequestTime = 0
const MIN_REQUEST_INTERVAL = 1000 // 最小请求间隔，单位毫秒

// 启动摄像头
const startCamera = async () => {
  if (isLoading.value) return
  
  isLoading.value = true
  errorMsg.value = ''
  
  try {
    const { data } = await videoApi.startCamera(activeCameraType.value)
    ElMessage.success('摄像头已启动')
    cameraRunning.value = true
    refreshKey.value = Date.now() // 刷新视频流
  } catch (error: any) {
    errorMsg.value = error.response?.data?.message || error.message || '启动摄像头失败'
    ElMessage.error(errorMsg.value)
  } finally {
    isLoading.value = false
  }
}

// 停止摄像头
const stopCamera = async () => {

  window.stop() // 停止所有正在进行的请求和页面加载操作
  // 防抖处理，避免短时间内重复请求
  const now = Date.now()
  if (isShuttingDown || isStoppingCamera.value || now - lastRequestTime < MIN_REQUEST_INTERVAL) {
    console.log('防抖：忽略重复的停止摄像头请求')
    return
  }
  
  isShuttingDown = true
  isStoppingCamera.value = true
  lastRequestTime = now
  errorMsg.value = ''
  isLoading.value = true
  
  ElMessage({
    message: '正在停止摄像头，请稍候...',
    type: 'info',
    duration: 0
  })
  
  try {
    await videoApi.stopCamera(activeCameraType.value)
    ElMessage.success('摄像头已停止')
    cameraRunning.value = false
  } catch (error: any) {
    console.error('停止摄像头失败:', error)
    
    // 特殊处理超时错误
    if (error.code === 'ECONNABORTED') {
      errorMsg.value = '停止摄像头超时，可能摄像头已经停止但服务器响应缓慢'
      ElMessage({
        type: 'warning',
        message: errorMsg.value,
        duration: 5000
      })
      
      // 假设摄像头已停止，让UI显示正确状态
      cameraRunning.value = false
    } else {
      errorMsg.value = error.response?.data?.message || error.message || '停止摄像头失败'
      ElMessage.error(errorMsg.value)
    }
  } finally {
    // 关闭所有消息
    ElMessage.closeAll()
    isLoading.value = false
    isStoppingCamera.value = false
    setTimeout(() => {
      isShuttingDown = false
    }, MIN_REQUEST_INTERVAL)
  }
}

// 强制停止摄像头（用于当正常停止失败时）
const forceStopCamera = async () => {
  if (!errorMsg.value) return
  
  try {
    // 多次尝试停止摄像头
    await Promise.all([
      videoApi.stopCamera(activeCameraType.value),
      // 等待1秒后再次尝试
      new Promise(resolve => setTimeout(resolve, 1000))
        .then(() => videoApi.stopCamera(activeCameraType.value))
    ])
    
    ElMessage.success('摄像头已强制停止')
    cameraRunning.value = false
    errorMsg.value = ''
  } catch (error: any) {
    console.error('强制停止摄像头失败:', error)
    ElMessage.error('强制停止失败，请尝试刷新页面')
  }
}

// 切换摄像头类型
const changeCamera = (type: string) => {
  if (cameraRunning.value) {
    ElMessageBox.confirm(
      '切换摄像头类型将停止当前摄像头，是否继续？',
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    ).then(async () => {
      await stopCamera()
      activeCameraType.value = type
    }).catch(() => {
      // 取消切换
    })
  } else {
    activeCameraType.value = type
  }
}

// 获取视频流URL
const getVideoUrl = (side?: string) => {
  const url = videoApi.getVideoStreamUrl(activeCameraType.value, side)
  return `${url}?t=${refreshKey.value}`
}

// 获取当前摄像头信息
const getCurrentCamera = () => {
  return cameraTypes.find(item => item.id === activeCameraType.value)
}

// 视频加载错误处理
const handleVideoError = () => {
  if (cameraRunning.value) {
    errorMsg.value = '视频流加载失败，请检查摄像头是否正确连接'
  }
}

// 使用 beforeUnmount 而不是 unMounted 来确保在页面刷新前处理好关闭操作
onBeforeUnmount(async () => {
  if (cameraRunning.value && !isShuttingDown && !isStoppingCamera.value) {
    console.log('组件即将卸载，停止摄像头')
    try {
      await videoApi.stopCamera(activeCameraType.value)
    } catch (error) {
      console.error('卸载时停止摄像头失败:', error)
      // 组件卸载时不显示错误消息
    }
  }
})
</script>

<template>
  <div class="video-monitor-container">
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card class="control-card">
          <div class="control-header">
            <h3>视频监控控制台</h3>
            <div class="control-actions">
              <el-button 
                type="success" 
                @click="startCamera" 
                :loading="isLoading" 
                :disabled="cameraRunning"
              >
                启动摄像头
              </el-button>
              <el-button 
                type="danger" 
                @click="stopCamera" 
                :loading="isStoppingCamera" 
                :disabled="!cameraRunning"
              >
                停止摄像头
              </el-button>
              <el-button 
                v-if="errorMsg && errorMsg.includes('超时')" 
                type="warning" 
                @click="forceStopCamera"
              >
                强制停止
              </el-button>
            </div>
          </div>
          
          <el-alert
            v-if="errorMsg"
            :title="errorMsg"
            type="error"
            show-icon
            class="mb-20"
            :closable="true"
          />

          <div class="camera-types">
            <el-radio-group v-model="activeCameraType" @change="changeCamera">
              <el-radio-button 
                v-for="type in cameraTypes" 
                :key="type.id" 
                :label="type.id"
              >
                {{ type.name }}
              </el-radio-button>
            </el-radio-group>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" class="mt-20">
      <el-col :span="24">
        <el-card class="video-card">
          <template #header>
            <div class="video-header">
              <h3>{{ getCurrentCamera()?.name || '视频监控' }}</h3>
              <el-tag :type="cameraRunning ? 'success' : 'info'">
                {{ cameraRunning ? '已连接' : '未连接' }}
              </el-tag>
            </div>
          </template>
          
          <div v-if="!cameraRunning" class="video-placeholder">
            <el-empty description="请先启动摄像头">
              <el-button type="primary" @click="startCamera">启动摄像头</el-button>
            </el-empty>
          </div>
          
          <div v-else class="video-container">
            <!-- 双摄像头视图 -->
            <template v-if="getCurrentCamera()?.hasDual">
              <div class="dual-video">
                <div class="video-wrapper">
                  <h4>左视图</h4>
                  <img 
                    :src="getVideoUrl('left')" 
                    alt="左摄像头" 
                    class="video-stream"
                    @error="handleVideoError"
                  />
                </div>
                <div class="video-wrapper">
                  <h4>右视图</h4>
                  <img 
                    :src="getVideoUrl('right')" 
                    alt="右摄像头" 
                    class="video-stream"
                    @error="handleVideoError"
                  />
                </div>
              </div>
            </template>
            
            <!-- 单摄像头视图 -->
            <template v-else>
              <div class="single-video">
                <img 
                  :src="getVideoUrl()" 
                  alt="摄像头视频流" 
                  class="video-stream"
                  @error="handleVideoError"
                />
              </div>
            </template>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" class="mt-20">
      <el-col :span="24">
        <el-card>
          <template #header>
            <h3>摄像头说明</h3>
          </template>
          
          <el-descriptions :column="1" border>
            <el-descriptions-item v-if="activeCameraType === 'd_estimator'" label="视差估计">
              通过深度摄像头计算场景中物体的视差图，帮助盲人理解环境中物体的远近关系。
            </el-descriptions-item>
            
            <el-descriptions-item v-if="activeCameraType === 'f_detector'" label="特征点检测">
              检测环境中的关键特征点，为盲人提供周围环境的特征描述。
            </el-descriptions-item>
            
            <el-descriptions-item v-if="activeCameraType === 'f_tracker'" label="特征点追踪">
              追踪特征点的运动，帮助盲人了解环境中物体的动态变化。
            </el-descriptions-item>
            
            <el-descriptions-item v-if="activeCameraType === 'g_recognition'" label="手势特征点识别">
              识别手势的关键点，为手势交互提供基础。
            </el-descriptions-item>
            
            <el-descriptions-item v-if="activeCameraType === 'g_recognizer'" label="手势类别判断">
              判断用户做出的手势类型，支持盲人通过手势进行交互。
            </el-descriptions-item>
            
            <el-descriptions-item v-if="activeCameraType === 'm_detector'" label="MobileNetSSD目标检测">
              使用MobileNetSSD神经网络识别环境中的常见物体，为盲人提供物体识别功能。
            </el-descriptions-item>
            
            <el-descriptions-item v-if="activeCameraType === 'p_video'" label="人像追踪">
              检测并追踪视野中的人像，帮助盲人感知周围的人。
            </el-descriptions-item>
            
            <el-descriptions-item v-if="activeCameraType === 's_RGB'" label="空间物体追踪">
              在三维空间中追踪物体，提供更准确的物体位置信息。
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.video-monitor-container {
  padding-bottom: 20px;
}

.control-card, .video-card {
  margin-bottom: 20px;
}

.control-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.control-header h3 {
  margin: 0;
}

.camera-types {
  margin-top: 20px;
}

.mb-20 {
  margin-bottom: 20px;
}

.mt-20 {
  margin-top: 20px;
}

.video-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.video-header h3 {
  margin: 0;
}

.video-container {
  width: 100%;
}

.video-placeholder {
  height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dual-video {
  display: flex;
  gap: 20px;
}

.video-wrapper {
  flex: 1;
}

.video-wrapper h4 {
  margin-top: 0;
  margin-bottom: 10px;
  text-align: center;
}

.video-stream {
  width: 100%;
  height: auto;
  max-height: 400px;
  object-fit: contain;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background-color: #000;
}

.single-video .video-stream {
  display: block;
  margin: 0 auto;
  max-height: 500px;
}
</style> 