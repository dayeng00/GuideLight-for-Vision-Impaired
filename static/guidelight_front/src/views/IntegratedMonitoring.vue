// 声明高德地图类型
declare global {
  interface Window {
    AMap: any;
  }
}

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
// @ts-ignore
import { videoApi, locationApi, systemApi } from '../api'
// 导入配置文件
import { MAP_CONFIG } from '../config'

// =============== 位置追踪相关 ===============
const currentLocation = ref<any>(null)
const locationHistory = ref<any[]>([])
const isLocationLoading = ref(false)
const mapApiLoaded = ref(false) // 添加地图API加载状态

// 地图相关
const mapLoaded = ref(false)
let map: any = null
let marker: any = null
let polyline: any = null
let locationUpdateTimer: any = null

// 检查并加载高德地图API
const checkAndLoadMapAPI = () => {
  if (typeof window.AMap !== 'undefined') {
    mapApiLoaded.value = true
    initMap()
    return
  }
  
  // 如果API未加载，动态加载API
  const script = document.createElement('script')
  script.type = 'text/javascript'
  script.src = `https://webapi.amap.com/maps?v=${MAP_CONFIG.version}&key=${MAP_CONFIG.key}&plugin=${MAP_CONFIG.plugins}&securityJsCode=${MAP_CONFIG.securityJsCode}`
  script.async = true
  script.onload = () => {
    mapApiLoaded.value = true
    console.log('高德地图API加载成功')
    initMap()
  }
  script.onerror = () => {
    console.error('高德地图API加载失败')
    ElMessage.error('高德地图API加载失败，请检查网络连接')
  }
  
  document.head.appendChild(script)
}

// 初始化地图
const initMap = () => {
  // 确保高德地图API已加载
  if (typeof window.AMap === 'undefined') {
    console.error('高德地图API未加载')
    checkAndLoadMapAPI()
    return
  }
  
  try {
    // 创建地图实例
    map = new window.AMap.Map('location-map', {
      zoom: 15,
      resizeEnable: true,
      // 启用标准图层和路网图层
      layers: [
        new window.AMap.TileLayer(), // 标准图层
        new window.AMap.TileLayer.RoadNet() // 路网图层
      ],
      // 启用建筑物和POI
      features: ['bg', 'road', 'building', 'point'],
      viewMode: '3D', // 使用3D视图可以更好地显示建筑物
      // 设置默认中心点为新的位置坐标
      center: [117.208162, 31.774134]
    })
    
    // 地图加载完成事件
    map.on('complete', () => {
      mapLoaded.value = true
      
      // 加载位置数据
      loadCurrentLocation()
      loadLocationHistory()
    })
    
    // 添加地图控件
    map.plugin(['AMap.ToolBar', 'AMap.Scale', 'AMap.MapType'], () => {
      // 工具条控件
      const toolBar = new window.AMap.ToolBar({
        position: 'RB'
      })
      
      // 比例尺控件
      const scale = new window.AMap.Scale()
      
      // 地图类型切换控件
      const mapType = new window.AMap.MapType()
      
      map.addControl(toolBar)
      map.addControl(scale)
      map.addControl(mapType)
    })
  } catch (error) {
    console.error('初始化地图时出错:', error)
    ElMessage.error('初始化地图时出错，请刷新页面重试')
  }
}

// 加载当前位置
const loadCurrentLocation = async () => {
  isLocationLoading.value = true
  
  try {
    const response = await locationApi.getCurrentLocation()
    
    if (response.data.code === 200) {
      currentLocation.value = response.data.data
      
      // 更新地图上的位置标记
      if (mapLoaded.value && currentLocation.value) {
        updateMarkerPosition(currentLocation.value)
      }
    } else {
      console.error('获取当前位置失败:', response.data.message)
      ElMessage.error(response.data.message || '获取当前位置失败')
      
      // 如果没有成功获取位置，使用默认位置
      if (!currentLocation.value) {
        currentLocation.value = {
          lat: 31.774134,
          lng: 117.208162,
          timestamp: Date.now() / 1000
        }
      }
    }
  } catch (error: any) {
    console.error('获取当前位置失败:', error)
    ElMessage.error('获取当前位置失败: ' + (error.response?.data?.message || error.message))
    
    // 如果没有成功获取位置，使用默认位置
    if (!currentLocation.value) {
      currentLocation.value = {
        lat: 31.774134,
        lng: 117.208162,
        timestamp: Date.now() / 1000
      }
    }
  } finally {
    isLocationLoading.value = false
  }
}

// 加载位置历史记录
const loadLocationHistory = async () => {
  try {
    const response = await locationApi.getLocationHistory(20) // 获取最近20条记录
    
    if (response.data.code === 200) {
      locationHistory.value = response.data.data
      
      // 更新地图上的路线
      if (mapLoaded.value && locationHistory.value && locationHistory.value.length > 0) {
        updatePolyline(locationHistory.value)
      }
    } else {
      console.error('获取位置历史记录失败:', response.data.message)
      ElMessage.error(response.data.message || '获取位置历史记录失败')
    }
  } catch (error: any) {
    console.error('获取位置历史记录失败:', error)
    ElMessage.error('获取位置历史记录失败: ' + (error.response?.data?.message || error.message))
  }
}

// 更新地图上的位置标记
const updateMarkerPosition = (location) => {
  if (!map || !location) return
  
  try {
    const { lat, lng } = location
    const position = new window.AMap.LngLat(lng, lat)
    
    if (!marker) {
      // 创建新标记
      marker = new window.AMap.Marker({
        position,
        icon: 'https://webapi.amap.com/theme/v1.3/markers/n/mark_b.png',
        anchor: 'bottom-center'
      })
      map.add(marker)
    } else {
      // 更新现有标记
      marker.setPosition(position)
    }
    
    // 将地图中心移动到当前位置
    map.setCenter(position)
  } catch (error) {
    console.error('更新位置标记失败:', error)
  }
}

// 更新地图上的路线
const updatePolyline = (locations) => {
  if (!map || !locations || locations.length === 0) return
  
  try {
    // 创建路径点数组
    const path = locations.map(loc => [loc.lng, loc.lat])
    
    if (!polyline) {
      // 创建新路线
      polyline = new window.AMap.Polyline({
        path,
        strokeColor: '#3498db',
        strokeWeight: 6,
        strokeOpacity: 0.8
      })
      map.add(polyline)
    } else {
      // 更新现有路线
      polyline.setPath(path)
    }
    
    // 调整地图视图以包含整个路线
    if (path.length > 1) {
      map.setFitView([polyline])
    }
  } catch (error) {
    console.error('更新路线失败:', error)
  }
}

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return '未知时间'
  
  const date = new Date(timestamp * 1000)
  return date.toLocaleString()
}

// 获取最近的位置记录
const recentLocations = computed(() => {
  return locationHistory.value.slice(0, 5)
})

// 初始化定时器，定期更新位置
const initLocationUpdater = () => {
  // 每10秒更新一次位置
  loadCurrentLocation() // 立即执行一次
  
  locationUpdateTimer = setInterval(async () => {
    await loadCurrentLocation()
    
    // 每3次位置更新后，刷新一次历史轨迹
    if (Math.floor(Date.now() / 10000) % 3 === 0) {
      loadLocationHistory()
    }
  }, 10000)
}

// =============== 摄像头相关 ===============
// 摄像头类型
const cameraTypes = [
  { id: 'd_estimator', name: '视差估计', hasDual: false },
  { id: 'f_detector', name: '特征点检测', hasDual: true },
  { id: 'g_recognition', name: '手势识别', hasDual: false },
  { id: 'p_video', name: '人像追踪', hasDual: false }
]

const activeCameraType = ref('p_video')
const isCameraLoading = ref(false)
const isStoppingCamera = ref(false)
const cameraError = ref('')
const cameraRunning = ref(false)
const refreshKey = ref(Date.now())

// 防抖控制
let isShuttingDown = false
let lastRequestTime = 0
const MIN_REQUEST_INTERVAL = 1000

// 启动摄像头
const startCamera = async () => {
  if (isCameraLoading.value) return
  
  isCameraLoading.value = true
  cameraError.value = ''
  
  try {
    await videoApi.startCamera(activeCameraType.value)
    ElMessage.success('摄像头已启动')
    cameraRunning.value = true
    refreshKey.value = Date.now() // 刷新视频流
  } catch (error: any) {
    cameraError.value = error.response?.data?.message || error.message || '启动摄像头失败'
    ElMessage.error(cameraError.value)
  } finally {
    isCameraLoading.value = false
  }
}

// 停止摄像头
const stopCamera = async () => {
  window.stop() // 停止所有正在进行的请求
  
  const now = Date.now()
  if (isShuttingDown || isStoppingCamera.value || now - lastRequestTime < MIN_REQUEST_INTERVAL) {
    return
  }
  
  isShuttingDown = true
  isStoppingCamera.value = true
  lastRequestTime = now
  cameraError.value = ''
  
  try {
    await videoApi.stopCamera(activeCameraType.value)
    ElMessage.success('摄像头已停止')
    cameraRunning.value = false
  } catch (error: any) {
    if (error.code === 'ECONNABORTED') {
      cameraError.value = '停止摄像头超时，可能摄像头已停止但服务器响应缓慢'
      ElMessage.warning(cameraError.value)
      cameraRunning.value = false
    } else {
      cameraError.value = error.response?.data?.message || error.message || '停止摄像头失败'
      ElMessage.error(cameraError.value)
    }
  } finally {
    isStoppingCamera.value = false
    setTimeout(() => {
      isShuttingDown = false
    }, MIN_REQUEST_INTERVAL)
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

// =============== 系统状态相关 ===============
const systemStatus = ref({
  status: 'offline',
  modules: {
    video_modules: false,
    database: false
  },
  cameras: {}
})

// 加载系统状态
const loadSystemStatus = async () => {
  try {
    const { data } = await systemApi.getHealth()
    systemStatus.value = data
  } catch (error) {
    console.error('获取系统状态失败:', error)
  }
}

// =============== 组件生命周期 ===============
onMounted(() => {
  // 检查并加载高德地图API
  checkAndLoadMapAPI()
  
  // 初始化位置更新定时器
  initLocationUpdater()
  
  // 加载系统状态
  loadSystemStatus()
  
  // 定期刷新系统状态
  setInterval(loadSystemStatus, 30000)
})

onBeforeUnmount(() => {
  // 清除定时器
  if (locationUpdateTimer) {
    clearInterval(locationUpdateTimer)
  }
  
  // 停止摄像头
  if (cameraRunning.value) {
    stopCamera()
  }
  
  // 销毁地图实例
  if (map) {
    map.destroy()
  }
})
</script>

<template>
  <div class="integrated-monitoring">
    <el-row :gutter="20">
      <!-- 顶部系统状态卡片 -->
      <el-col :span="24">
        <el-card class="system-status-card">
          <template #header>
            <div class="card-header">
              <h3>系统状态</h3>
              <el-tag :type="systemStatus.status === 'online' ? 'success' : 'danger'">
                {{ systemStatus.status === 'online' ? '在线' : '离线' }}
              </el-tag>
            </div>
          </template>
          
          <el-row :gutter="20">
            <el-col :md="8">
              <div class="status-item">
                <span class="label">位置服务:</span>
                <el-tag :type="currentLocation ? 'success' : 'info'">
                  {{ currentLocation ? '活跃' : '等待中' }}
                </el-tag>
              </div>
            </el-col>
            
            <el-col :md="8">
              <div class="status-item">
                <span class="label">摄像头服务:</span>
                <el-tag :type="systemStatus.modules.video_modules ? 'success' : 'danger'">
                  {{ systemStatus.modules.video_modules ? '可用' : '不可用' }}
                </el-tag>
              </div>
            </el-col>
            
            <el-col :md="8">
              <div class="status-item">
                <span class="label">数据库:</span>
                <el-tag :type="systemStatus.modules.database ? 'success' : 'warning'">
                  {{ systemStatus.modules.database ? '已连接' : '使用备用' }}
                </el-tag>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
      
      <!-- 左侧地图 -->
      <el-col :md="12">
        <el-card class="map-card">
          <template #header>
            <div class="card-header">
              <h3>位置追踪</h3>
              <div>
                <el-button 
                  type="primary" 
                  size="small" 
                  @click="loadCurrentLocation" 
                  :loading="isLocationLoading"
                >
                  刷新位置
                </el-button>
              </div>
            </div>
          </template>
          
          <div class="map-container">
            <div id="location-map" class="location-map"></div>
            
            <div v-if="!mapApiLoaded" class="map-loading">
              <el-icon class="is-loading"><Loading /></el-icon>
              <p>地图API加载中...</p>
            </div>
            <div v-else-if="!mapLoaded" class="map-loading">
              <el-icon class="is-loading"><Loading /></el-icon>
              <p>地图初始化中...</p>
            </div>
          </div>
          
          <div class="location-info" v-if="currentLocation">
            <p>
              <strong>当前位置:</strong> 
              {{ currentLocation.lat?.toFixed(6) || '未知' }}, {{ currentLocation.lng?.toFixed(6) || '未知' }}
            </p>
            <p v-if="currentLocation.timestamp">
              <strong>更新时间:</strong> {{ formatTime(currentLocation.timestamp) }}
            </p>
            <p v-if="locationHistory.length > 0">
              <strong>历史点数:</strong> {{ locationHistory.length }}
            </p>
          </div>
          
          <!-- 历史位置记录 -->
          <div class="history-records" v-if="locationHistory.length > 0">
            <h4>最近位置记录</h4>
            <el-table :data="recentLocations" size="small" style="width: 100%" :max-height="150">
              <el-table-column prop="time" label="时间" width="180">
                <template #default="scope">
                  {{ new Date(scope.row.time).toLocaleString() }}
                </template>
              </el-table-column>
              <el-table-column label="位置">
                <template #default="scope">
                  {{ scope.row.lat.toFixed(6) }}, {{ scope.row.lng.toFixed(6) }}
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-col>
      
      <!-- 右侧摄像头 -->
      <el-col :md="12">
        <el-card class="camera-card">
          <template #header>
            <div class="card-header">
              <h3>{{ getCurrentCamera()?.name || '视频监控' }}</h3>
              <div>
                <el-button 
                  type="success" 
                  size="small" 
                  @click="startCamera" 
                  :loading="isCameraLoading" 
                  :disabled="cameraRunning"
                >
                  开启
                </el-button>
                <el-button 
                  type="danger" 
                  size="small" 
                  @click="stopCamera" 
                  :loading="isStoppingCamera" 
                  :disabled="!cameraRunning"
                >
                  关闭
                </el-button>
              </div>
            </div>
          </template>
          
          <div class="camera-types">
            <el-radio-group v-model="activeCameraType" @change="changeCamera" size="small">
              <el-radio-button 
                v-for="type in cameraTypes" 
                :key="type.id" 
                :label="type.id"
              >
                {{ type.name }}
              </el-radio-button>
            </el-radio-group>
          </div>
          
          <el-alert
            v-if="cameraError"
            :title="cameraError"
            type="error"
            show-icon
            class="mt-10 mb-10"
          />
          
          <div v-if="!cameraRunning" class="video-placeholder">
            <el-empty description="请先启动摄像头">
              <el-button type="primary" @click="startCamera" :disabled="isCameraLoading">
                启动摄像头
              </el-button>
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
                    @error="cameraError = '视频流加载失败，请检查摄像头是否正确连接'"
                  />
                </div>
                <div class="video-wrapper">
                  <h4>右视图</h4>
                  <img 
                    :src="getVideoUrl('right')" 
                    alt="右摄像头" 
                    class="video-stream"
                    @error="cameraError = '视频流加载失败，请检查摄像头是否正确连接'"
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
                  @error="cameraError = '视频流加载失败，请检查摄像头是否正确连接'"
                />
              </div>
            </template>
          </div>
        </el-card>
      </el-col>
      
      <!-- 底部控制面板 -->
      <el-col :span="24">
        <el-card class="control-panel">
          <template #header>
            <div class="card-header">
              <h3>系统控制</h3>
            </div>
          </template>
          
          <el-row :gutter="20">
            <el-col :md="8">
              <el-card shadow="hover" class="control-card">
                <template #header>
                  <h4>语音提示设置</h4>
                </template>
                <div class="control-item">
                  <span>语音提示</span>
                  <el-switch v-model="voiceEnabled" />
                </div>
                <div class="control-item">
                  <span>语音音量</span>
                  <el-slider v-model="voiceVolume" :min="0" :max="100" :disabled="!voiceEnabled" />
                </div>
                <div class="control-item">
                  <span>语音速度</span>
                  <el-slider v-model="voiceSpeed" :min="0.5" :max="2" :step="0.1" :disabled="!voiceEnabled" />
                </div>
              </el-card>
            </el-col>
            
            <el-col :md="8">
              <el-card shadow="hover" class="control-card">
                <template #header>
                  <h4>位置追踪设置</h4>
                </template>
                <div class="control-item">
                  <span>位置追踪</span>
                  <el-switch v-model="locationEnabled" />
                </div>
                <div class="control-item">
                  <span>追踪频率</span>
                  <el-select v-model="locationFrequency" :disabled="!locationEnabled">
                    <el-option label="高 (5秒)" value="5" />
                    <el-option label="中 (10秒)" value="10" />
                    <el-option label="低 (30秒)" value="30" />
                  </el-select>
                </div>
                <div class="control-item">
                  <span>位置共享</span>
                  <el-switch v-model="locationSharing" :disabled="!locationEnabled" />
                </div>
              </el-card>
            </el-col>
            
            <el-col :md="8">
              <el-card shadow="hover" class="control-card">
                <template #header>
                  <h4>紧急联系人</h4>
                </template>
                <div class="contact-list">
                  <div class="contact-item" v-for="(contact, index) in emergencyContacts" :key="index">
                    <span>{{ contact.name }}</span>
                    <span>{{ contact.phone }}</span>
                    <el-button type="danger" size="small" circle>
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                  <div class="add-contact">
                    <el-button type="primary" size="small">添加联系人</el-button>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script lang="ts">
// 引入需要的图标
import { Loading, Delete } from '@element-plus/icons-vue'

// 系统设置模拟数据
const voiceEnabled = ref(true)
const voiceVolume = ref(80)
const voiceSpeed = ref(1)
const locationEnabled = ref(true)
const locationFrequency = ref('10')
const locationSharing = ref(true)
const emergencyContacts = ref([
  { name: '张三', phone: '13812345678' },
  { name: '李四', phone: '13987654321' }
])
</script>

<style scoped>
.integrated-monitoring {
  padding-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
  font-size: 16px;
}

.system-status-card {
  margin-bottom: 20px;
}

.status-item {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.status-item .label {
  margin-right: 10px;
  font-weight: 600;
}

.map-card, .camera-card {
  margin-bottom: 20px;
  height: 600px; /* 增加高度以容纳历史记录表格 */
}

.map-container {
  height: 350px;
  position: relative;
}

.location-map {
  width: 100%;
  height: 100%;
}

.map-loading {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background-color: rgba(255, 255, 255, 0.8);
}

.location-info {
  margin-top: 10px;
  padding: 10px;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.location-info p {
  margin: 5px 0;
}

.history-records {
  margin-top: 15px;
}

.history-records h4 {
  margin: 10px 0;
  font-size: 14px;
}

.camera-types {
  margin-bottom: 15px;
}

.video-placeholder {
  height: 350px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-container {
  width: 100%;
  height: 350px;
}

.dual-video {
  display: flex;
  gap: 10px;
  height: 100%;
}

.video-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.video-wrapper h4 {
  margin: 0 0 5px 0;
  text-align: center;
}

.video-stream {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background-color: #000;
  border-radius: 4px;
}

.single-video {
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.single-video .video-stream {
  max-height: 100%;
  max-width: 100%;
}

.mt-10 {
  margin-top: 10px;
}

.mb-10 {
  margin-bottom: 10px;
}

.control-panel {
  margin-bottom: 20px;
}

.control-card {
  height: 100%;
}

.control-card h4 {
  margin: 0;
  font-size: 14px;
}

.control-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 15px;
}

.contact-list {
  max-height: 150px;
  overflow-y: auto;
}

.contact-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid #eee;
}

.add-contact {
  margin-top: 10px;
  text-align: center;
}
</style> 