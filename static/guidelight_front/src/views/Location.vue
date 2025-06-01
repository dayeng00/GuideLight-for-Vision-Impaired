// 声明高德地图类型
declare global {
  interface Window {
    AMap: any;
  }
}

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount, computed } from 'vue'
import { ElMessage } from 'element-plus'
// @ts-ignore
import { locationApi } from '../api'
// 导入配置文件
import { MAP_CONFIG } from '../config'

// 位置数据
const currentLocation = ref<any>(null)
const locationHistory = ref<any[]>([])
const isLoading = ref(false)
const isStreaming = ref(false)
let locationStream: EventSource | null = null
const mapApiLoaded = ref(false)

// 地图相关
const mapLoaded = ref(false)
let map: any = null
let marker: any = null
let polyline: any = null
let locationUpdateTimer: any = null

// 模拟器控制
const simulatorControls = reactive({
  speed: 5,
  destination: {
    lat: 0,
    lng: 0
  },
  isCustomLocation: false,
  customLocation: {
    lat: 31.774134,
    lng: 117.208162
  }
})

// 加载当前位置
const loadCurrentLocation = async () => {
  if (isLoading.value) return
  
  isLoading.value = true
  
  try {
    const response = await locationApi.getCurrentLocation()
    if (response.data.code === 200) {
      currentLocation.value = response.data.data
      
      // 更新地图上的位置标记
      if (mapLoaded.value) {
        updateMarkerPosition(currentLocation.value)
      }
      
      console.log('位置已更新', currentLocation.value)
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
    isLoading.value = false
  }
}

// 加载位置历史记录
const loadLocationHistory = async () => {
  try {
    const response = await locationApi.getLocationHistory(20) // 获取最近20条记录
    if (response.data.code === 200) {
      locationHistory.value = response.data.data
      
      // 更新地图上的路线
      if (mapLoaded.value) {
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
}

// 更新地图上的路线
const updatePolyline = (locations) => {
  if (!map || !locations || locations.length === 0) return
  
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
}

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
  
  mapApiLoaded.value = true
  
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
    
    // 添加地图点击事件监听
    map.on('click', handleMapClick)
  } catch (error) {
    console.error('初始化地图时出错:', error)
    ElMessage.error('初始化地图时出错，请刷新页面重试')
  }
}

// 设置移动速度
const setSpeed = async () => {
  try {
    const response = await locationApi.setSpeed(simulatorControls.speed)
    if (response.data.success) {
      ElMessage.success(`速度已设置为 ${simulatorControls.speed} m/s`)
    } else {
      ElMessage.error(response.data.message || '设置速度失败')
    }
  } catch (error: any) {
    console.error('设置速度失败:', error)
    ElMessage.error('设置速度失败: ' + (error.response?.data?.message || error.message))
  }
}

// 设置目的地
const setDestination = async () => {
  // 从地图上获取当前中心点作为目的地
  if (map) {
    const center = map.getCenter()
    simulatorControls.destination.lng = center.getLng()
    simulatorControls.destination.lat = center.getLat()
  }
  
  try {
    const response = await locationApi.setDestination(
      simulatorControls.destination.lat,
      simulatorControls.destination.lng
    )
    
    if (response.data.success) {
      ElMessage.success('目的地已设置')
    } else {
      ElMessage.error(response.data.message || '设置目的地失败')
    }
  } catch (error: any) {
    console.error('设置目的地失败:', error)
    ElMessage.error('设置目的地失败: ' + (error.response?.data?.message || error.message))
  }
}

// 设置自定义位置
const setCustomLocation = async () => {
  if (!simulatorControls.isCustomLocation) {
    simulatorControls.isCustomLocation = true
    return
  }
  
  try {
    const response = await locationApi.setCurrentLocation(
      simulatorControls.customLocation.lat,
      simulatorControls.customLocation.lng
    )
    
    if (response.data.success) {
      ElMessage.success('当前位置已更新')
      // 重新加载当前位置
      loadCurrentLocation()
    } else {
      ElMessage.error(response.data.message || '设置自定义位置失败')
    }
  } catch (error: any) {
    console.error('设置自定义位置失败:', error)
    ElMessage.error('设置自定义位置失败: ' + (error.response?.data?.message || error.message))
  }
  
  // 关闭自定义位置模式
  simulatorControls.isCustomLocation = false
}

// 手动添加位置记录
const addLocationRecord = async () => {
  if (!currentLocation.value) return
  
  try {
    const response = await locationApi.addLocation(
      currentLocation.value.lat,
      currentLocation.value.lng
    )
    
    if (response.data.code === 200) {
      ElMessage.success('位置记录已添加')
      // 重新加载历史记录
      loadLocationHistory()
    } else {
      ElMessage.error(response.data.message || '添加位置记录失败')
    }
  } catch (error: any) {
    console.error('添加位置记录失败:', error)
    ElMessage.error('添加位置记录失败: ' + (error.response?.data?.message || error.message))
  }
}

// 处理地图点击事件
const handleMapClick = (e) => {
  if (simulatorControls.isCustomLocation) {
    // 更新自定义位置坐标
    simulatorControls.customLocation.lng = e.lnglat.getLng()
    simulatorControls.customLocation.lat = e.lnglat.getLat()
    
    // 在地图上标记位置
    updateMarkerPosition(simulatorControls.customLocation)
  }
}

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return '未知时间'
  
  const date = new Date(timestamp)
  return date.toLocaleString()
}

// 删除位置记录
const deleteLocationRecord = async (locationId) => {
  try {
    const response = await locationApi.deleteLocation(locationId)
    
    if (response.data.code === 200) {
      ElMessage.success('位置记录已删除')
      // 重新加载历史记录
      loadLocationHistory()
    } else {
      ElMessage.error(response.data.message || '删除位置记录失败')
    }
  } catch (error: any) {
    console.error('删除位置记录失败:', error)
    ElMessage.error('删除位置记录失败: ' + (error.response?.data?.message || error.message))
  }
}

// 创建一条默认位置记录
const createDefaultLocationRecord = async () => {
  try {
    // 使用新的默认坐标
    const response = await locationApi.addLocation(31.774134, 117.208162)
    
    if (response.data.code === 200) {
      ElMessage.success('已创建默认位置记录')
      // 重新加载位置数据
      await loadCurrentLocation()
      await loadLocationHistory()
    } else {
      ElMessage.error(response.data.message || '创建默认位置记录失败')
    }
  } catch (error: any) {
    console.error('创建默认位置记录失败:', error)
    ElMessage.error('创建默认位置记录失败: ' + (error.response?.data?.message || error.message))
  }
}

// 初始化定时器，定期更新位置
const initLocationUpdater = () => {
  // 每5秒更新一次位置
  locationUpdateTimer = setInterval(async () => {
    // 先加载当前位置
    await loadCurrentLocation()
    
    // 每次位置更新后，自动添加一条位置记录
    if (currentLocation.value) {
      try {
        // 添加当前位置到历史记录
        const response = await locationApi.addLocation(
          currentLocation.value.lat,
          currentLocation.value.lng
        )
        
        if (response.data.code === 200) {
          console.log('自动添加位置记录成功')
          // 刷新历史轨迹
          loadLocationHistory()
        } else {
          console.error('自动添加位置记录失败:', response.data.message)
        }
      } catch (error: any) {
        console.error('自动添加位置记录失败:', error)
      }
    }
  }, 5000)
}

// 获取最近的位置记录
const recentLocations = computed(() => {
  return locationHistory.value.slice(0, 5)
})

// 组件挂载
onMounted(() => {
  // 检查并加载高德地图API
  checkAndLoadMapAPI()
  
  // 初始化位置更新定时器
  initLocationUpdater()
})

// 组件卸载前清理资源
onBeforeUnmount(() => {
  // 清除定时器
  if (locationUpdateTimer) {
    clearInterval(locationUpdateTimer)
  }
  
  // 销毁地图实例
  if (map) {
    map.destroy()
  }
})
</script>

<template>
  <div class="location-container">
    <el-row :gutter="20">
      <!-- 位置信息卡片 -->
      <el-col :span="24">
        <el-card class="location-info-card">
          <template #header>
            <div class="card-header">
              <h3>位置信息</h3>
              <div class="action-buttons">
                <el-button 
                  type="primary" 
                  size="small" 
                  @click="loadCurrentLocation" 
                  :loading="isLoading"
                  icon="Refresh"
                >
                  刷新位置
                </el-button>
                <el-button 
                  type="success" 
                  size="small" 
                  @click="addLocationRecord" 
                  icon="Plus"
                >
                  添加位置记录
                </el-button>
                <el-button 
                  type="warning" 
                  size="small" 
                  @click="createDefaultLocationRecord" 
                  icon="Plus"
                >
                  创建默认位置
                </el-button>
              </div>
            </div>
          </template>
          
          <el-row :gutter="20">
            <el-col :md="8" :sm="24">
              <div class="info-item">
                <div class="info-label">当前位置:</div>
                <div class="info-value" v-if="currentLocation">
                  {{ currentLocation.lat.toFixed(6) }}, {{ currentLocation.lng.toFixed(6) }}
                </div>
                <div class="info-value" v-else>未知</div>
              </div>
            </el-col>
            
            <el-col :md="8" :sm="24">
              <div class="info-item">
                <div class="info-label">更新时间:</div>
                <div class="info-value" v-if="currentLocation && currentLocation.timestamp">
                  {{ formatTime(currentLocation.timestamp * 1000) }}
                </div>
                <div class="info-value" v-else>未知</div>
              </div>
            </el-col>
            
            <el-col :md="8" :sm="24">
              <div class="info-item">
                <div class="info-label">历史点数:</div>
                <div class="info-value">{{ locationHistory.length || 0 }}</div>
              </div>
            </el-col>
          </el-row>
          
          <!-- 地图加载状态提示 -->
          <el-alert
            v-if="!mapApiLoaded"
            title="高德地图API加载中，请稍候..."
            type="info"
            :closable="false"
            show-icon
            class="map-status-alert"
          />
          <el-alert
            v-else-if="!mapLoaded"
            title="地图正在初始化，请稍候..."
            type="info"
            :closable="false"
            show-icon
            class="map-status-alert"
          />
        </el-card>
      </el-col>
      
      <!-- 地图和控制面板 -->
      <el-col :span="24">
        <el-row :gutter="20">
          <!-- 地图 -->
          <el-col :lg="16" :md="24">
            <el-card class="map-card">
              <template #header>
                <div class="card-header">
                  <h3>位置地图</h3>
                  <el-tag v-if="mapLoaded" type="success">地图已加载</el-tag>
                  <el-tag type="warning" v-else>地图加载中</el-tag>
                </div>
              </template>
              
              <div class="map-container">
                <div id="location-map" class="location-map" @click="handleMapClick"></div>
                
                <div v-if="!mapLoaded" class="map-loading">
                  <el-icon class="is-loading"><Loading /></el-icon>
                  <p>地图加载中...</p>
                </div>
              </div>
            </el-card>
          </el-col>
          
          <!-- 控制面板 -->
          <el-col :lg="8" :md="24">
            <el-card class="control-card">
              <template #header>
                <div class="card-header">
                  <h3>模拟器控制</h3>
                </div>
              </template>
              
              <el-form label-position="top">
                <!-- 移动速度 -->
                <el-form-item label="移动速度 (m/s)">
                  <div class="speed-control">
                    <el-slider
                      v-model="simulatorControls.speed"
                      :min="1"
                      :max="20"
                      :step="1"
                      show-input
                    ></el-slider>
                    <el-button type="primary" @click="setSpeed">设置速度</el-button>
                  </div>
                </el-form-item>
                
                <!-- 目的地设置 -->
                <el-form-item label="目的地设置">
                  <p class="destination-tip">提示：将地图移动到目标位置，然后点击"设置目的地"</p>
                  <el-button type="primary" @click="setDestination" class="full-width-button">
                    设置地图中心为目的地
                  </el-button>
                </el-form-item>
                
                <!-- 自定义位置 -->
                <el-form-item label="自定义位置">
                  <el-button 
                    :type="simulatorControls.isCustomLocation ? 'success' : 'primary'"
                    class="full-width-button"
                    @click="setCustomLocation"
                  >
                    {{ simulatorControls.isCustomLocation ? '确认设置位置' : '在地图上选择位置' }}
                  </el-button>
                  
                  <div v-if="simulatorControls.isCustomLocation" class="custom-location-controls">
                    <el-input-number
                      v-model="simulatorControls.customLocation.lat"
                      :precision="6"
                      :step="0.000001"
                      placeholder="纬度"
                      class="coordinate-input"
                    ></el-input-number>
                    
                    <el-input-number
                      v-model="simulatorControls.customLocation.lng"
                      :precision="6"
                      :step="0.000001"
                      placeholder="经度"
                      class="coordinate-input"
                    ></el-input-number>
                  </div>
                </el-form-item>
              </el-form>
            </el-card>
            
            <!-- 历史记录 -->
            <el-card class="history-card">
              <template #header>
                <div class="card-header">
                  <h3>位置历史</h3>
                  <el-button size="small" type="primary" @click="loadLocationHistory" icon="Refresh">
                    刷新历史
                  </el-button>
                </div>
              </template>
              
              <el-table
                :data="recentLocations"
                style="width: 100%"
                :max-height="250"
                :stripe="true"
                :border="true"
              >
                <el-table-column prop="id" label="ID" width="60" />
                <el-table-column prop="time" label="时间" min-width="160">
                  <template #default="scope">
                    {{ formatTime(new Date(scope.row.time)) }}
                  </template>
                </el-table-column>
                <el-table-column prop="lat" label="纬度" width="100">
                  <template #default="scope">
                    {{ scope.row.lat.toFixed(6) }}
                  </template>
                </el-table-column>
                <el-table-column prop="lng" label="经度" width="100">
                  <template #default="scope">
                    {{ scope.row.lng.toFixed(6) }}
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="70" fixed="right">
                  <template #default="scope">
                    <el-button 
                      type="danger" 
                      size="small" 
                      icon="Delete" 
                      circle
                      @click="deleteLocationRecord(scope.row.id)"
                    />
                  </template>
                </el-table-column>
              </el-table>
              
              <div v-if="locationHistory.length === 0" class="no-data">
                <el-empty description="暂无历史数据" :image-size="60"></el-empty>
              </div>
              
              <div v-if="locationHistory.length > 5" class="view-more">
                <el-button type="text" @click="loadLocationHistory">
                  查看更多记录 (共{{ locationHistory.length }}条)
                </el-button>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.location-container {
  padding: 10px 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.action-buttons {
  display: flex;
  gap: 10px;
}

.location-info-card {
  margin-bottom: 20px;
}

.info-item {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.info-label {
  font-weight: 600;
  margin-right: 8px;
  min-width: 80px;
}

.map-status-alert {
  margin-top: 15px;
}

.map-card {
  margin-bottom: 20px;
}

.map-container {
  position: relative;
  height: 500px;
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

.control-card {
  margin-bottom: 20px;
}

.speed-control {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.destination-tip {
  margin: 0 0 10px;
  font-size: 12px;
  color: #909399;
}

.full-width-button {
  width: 100%;
}

.custom-location-controls {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

.coordinate-input {
  width: 100%;
}

.history-card {
  margin-bottom: 20px;
}

.no-data {
  padding: 20px 0;
  text-align: center;
}

.view-more {
  margin-top: 10px;
  text-align: center;
}
</style> 