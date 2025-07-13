<template>
  <div class="user-behavior-panel">
    <div class="panel-header">
      <h3>用户行为识别</h3>
      <div class="panel-controls">
        <el-button 
          :type="isProcessing ? 'success' : 'primary'"
          size="small" 
          @click="toggleProcessing"
          :loading="isLoading"
        >
          <el-icon><VideoPlay v-if="!isProcessing" /><VideoPause v-else /></el-icon>
          {{ isProcessing ? '停止识别' : '开始识别' }}
        </el-button>
        <el-button size="small" @click="refreshData">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>
    
    <div class="behavior-content">
      <!-- 当前行为状态 -->
      <div class="current-behavior">
        <div class="behavior-icon" :class="currentBehavior.type">
          {{ getBehaviorIcon(currentBehavior.type) }}
        </div>
        <div class="behavior-info">
          <h4>{{ getBehaviorName(currentBehavior.type) }}</h4>
          <p>置信度: {{ (currentBehavior.confidence * 100).toFixed(1) }}%</p>
          <p>持续时间: {{ formatDuration(currentBehavior.duration) }}</p>
        </div>
        <div class="behavior-indicator">
          <div class="confidence-bar">
            <div 
              class="confidence-fill" 
              :style="{ width: (currentBehavior.confidence * 100) + '%' }"
              :class="getConfidenceLevel(currentBehavior.confidence)"
            ></div>
          </div>
        </div>
      </div>
      
      <!-- 行为历史 -->
      <div class="behavior-history">
        <h4>行为历史</h4>
        <div class="history-list">
          <div 
            v-for="(behavior, index) in behaviorHistory" 
            :key="index"
            class="history-item"
            :class="{ active: index === 0 }"
          >
            <div class="history-time">{{ formatTime(behavior.timestamp) }}</div>
            <div class="history-behavior">
              <span class="behavior-emoji">{{ getBehaviorIcon(behavior.type) }}</span>
              <span class="behavior-name">{{ getBehaviorName(behavior.type) }}</span>
            </div>
            <div class="history-confidence">{{ (behavior.confidence * 100).toFixed(0) }}%</div>
          </div>
        </div>
      </div>
      
      <!-- 行为统计 -->
      <div class="behavior-stats">
        <h4>行为统计</h4>
        <div class="stats-grid">
          <div 
            v-for="(stat, type) in behaviorStats" 
            :key="type"
            class="stat-item"
          >
            <div class="stat-icon">{{ getBehaviorIcon(type) }}</div>
            <div class="stat-info">
              <span class="stat-name">{{ getBehaviorName(type) }}</span>
              <span class="stat-count">{{ stat.count }}次</span>
              <span class="stat-duration">{{ formatDuration(stat.totalDuration) }}</span>
            </div>
            <div class="stat-percentage">
              {{ ((stat.totalDuration / totalDuration) * 100).toFixed(1) }}%
            </div>
          </div>
        </div>
      </div>
      
      <!-- 实时数据图表 -->
      <div class="behavior-chart">
        <h4>实时置信度</h4>
        <div ref="chartContainer" class="chart-container"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount, computed, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoPlay, VideoPause, Refresh } from '@element-plus/icons-vue'
import * as echarts from 'echarts'

// 接口定义
interface BehaviorData {
  type: string
  confidence: number
  timestamp: number
  duration: number
}

interface BehaviorStat {
  count: number
  totalDuration: number
}

// 响应式数据
const isProcessing = ref(false)
const isLoading = ref(false)
const chartContainer = ref<HTMLElement>()

const currentBehavior = reactive<BehaviorData>({
  type: 'stationary',
  confidence: 0.95,
  timestamp: Date.now(),
  duration: 0
})

const behaviorHistory = ref<BehaviorData[]>([])
const behaviorStats = reactive<Record<string, BehaviorStat>>({
  stationary: { count: 0, totalDuration: 0 },
  walking: { count: 0, totalDuration: 0 },
  running: { count: 0, totalDuration: 0 },
  cycling: { count: 0, totalDuration: 0 },
  driving: { count: 0, totalDuration: 0 },
  bus: { count: 0, totalDuration: 0 },
  train: { count: 0, totalDuration: 0 },
  subway: { count: 0, totalDuration: 0 }
})

// 计算属性
const totalDuration = computed(() => {
  return Object.values(behaviorStats).reduce((sum, stat) => sum + stat.totalDuration, 0)
})

// 定时器
let updateTimer: number | null = null
let chartUpdateTimer: number | null = null
let chart: echarts.ECharts | null = null

// 行为类型映射
const behaviorNames: Record<string, string> = {
  stationary: '静止',
  walking: '步行',
  running: '跑步',
  cycling: '骑行',
  driving: '驾车',
  bus: '公交',
  train: '火车',
  subway: '地铁'
}

const behaviorIcons: Record<string, string> = {
  stationary: '🧍',
  walking: '🚶',
  running: '🏃',
  cycling: '🚴',
  driving: '🚗',
  bus: '🚌',
  train: '🚆',
  subway: '🚇'
}

// 方法
const getBehaviorName = (type: string): string => {
  return behaviorNames[type] || '未知'
}

const getBehaviorIcon = (type: string): string => {
  return behaviorIcons[type] || '❓'
}

const getConfidenceLevel = (confidence: number): string => {
  if (confidence > 0.8) return 'high'
  if (confidence > 0.6) return 'medium'
  return 'low'
}

const formatTime = (timestamp: number): string => {
  return new Date(timestamp).toLocaleTimeString()
}

const formatDuration = (seconds: number): string => {
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}m ${remainingSeconds}s`
}

const toggleProcessing = async () => {
  isLoading.value = true
  
  try {
    if (isProcessing.value) {
      // 停止处理
      if (updateTimer) {
        clearInterval(updateTimer)
        updateTimer = null
      }
      isProcessing.value = false
      ElMessage.success('用户行为识别已停止')
    } else {
      // 开始处理
      isProcessing.value = true
      startRealTimeProcessing()
      ElMessage.success('用户行为识别已启动')
    }
  } catch (error) {
    ElMessage.error('操作失败: ' + error)
  } finally {
    isLoading.value = false
  }
}

const refreshData = async () => {
  try {
    await fetchBehaviorData()
    ElMessage.success('数据已刷新')
  } catch (error) {
    ElMessage.error('刷新失败: ' + error)
  }
}

const fetchBehaviorData = async () => {
  try {
    // 调用后端API获取用户行为识别结果
    const response = await fetch('http://localhost:5000/api/signal/mock_predict', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        timestamp: Date.now()
      })
    })
    
    if (response.ok) {
      const data = await response.json()
      
      if (data.success && data.prediction) {
        updateBehaviorData(data.prediction)
      }
    }
  } catch (error) {
    console.error('获取用户行为数据失败:', error)
    // 使用模拟数据
    generateMockData()
  }
}

const generateMockData = () => {
  // 固定为静止状态，但置信度会实时变化
  const baseConfidence = 0.92
  const timeVariation = Math.sin(Date.now() / 5000) * 0.03 // 基于时间的正弦波变化
  const randomNoise = (Math.random() - 0.5) * 0.02 // 小幅随机噪声
  const confidence = Math.max(0.85, Math.min(0.98, baseConfidence + timeVariation + randomNoise))
  
  updateBehaviorData({
    predicted_class: 'stationary',
    confidence: confidence,
    timestamp: Date.now()
  })
}

const updateBehaviorData = (prediction: any) => {
  const newBehavior: BehaviorData = {
    type: prediction.predicted_class || prediction.behavior_type || 'stationary',
    confidence: prediction.confidence || 0.8,
    timestamp: prediction.timestamp || Date.now(),
    duration: 1
  }
  
  // 如果行为类型发生变化，更新历史记录
  if (newBehavior.type !== currentBehavior.type) {
    // 添加到历史记录
    behaviorHistory.value.unshift({
      ...currentBehavior,
      duration: Math.floor((Date.now() - currentBehavior.timestamp) / 1000)
    })
    
    // 限制历史记录数量
    if (behaviorHistory.value.length > 10) {
      behaviorHistory.value = behaviorHistory.value.slice(0, 10)
    }
    
    // 更新统计数据
    const prevType = currentBehavior.type
    if (behaviorStats[prevType]) {
      behaviorStats[prevType].count++
      behaviorStats[prevType].totalDuration += Math.floor((Date.now() - currentBehavior.timestamp) / 1000)
    }
    
    // 更新当前行为
    Object.assign(currentBehavior, newBehavior)
  } else {
    // 更新置信度和持续时间
    currentBehavior.confidence = newBehavior.confidence
    currentBehavior.duration = Math.floor((Date.now() - currentBehavior.timestamp) / 1000)
  }
  
  // 更新图表
  updateChart()
}

const startRealTimeProcessing = () => {
  if (updateTimer) return
  
  // 立即获取一次数据
  fetchBehaviorData()
  
  // 定期更新数据
  updateTimer = setInterval(() => {
    fetchBehaviorData()
  }, 2000) // 每2秒更新一次
}

const initChart = () => {
  if (!chartContainer.value) return
  
  chart = echarts.init(chartContainer.value)
  
  const option = {
    grid: {
      top: 10,
      left: 10,
      right: 10,
      bottom: 20,
      containLabel: true
    },
    xAxis: {
      type: 'time',
      boundaryGap: false,
      axisLabel: {
        fontSize: 10,
        color: '#b0bec5'
      },
      axisLine: {
        lineStyle: {
          color: 'rgba(255, 255, 255, 0.1)'
        }
      }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 1,
      axisLabel: {
        formatter: '{value}',
        fontSize: 10,
        color: '#b0bec5'
      },
      axisLine: {
        lineStyle: {
          color: 'rgba(255, 255, 255, 0.1)'
        }
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(255, 255, 255, 0.05)'
        }
      }
    },
    series: [{
      name: '置信度',
      type: 'line',
      smooth: true,
      data: [],
      lineStyle: {
        color: '#409EFF',
        width: 2
      },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [{
            offset: 0,
            color: 'rgba(64, 158, 255, 0.3)'
          }, {
            offset: 1,
            color: 'rgba(64, 158, 255, 0.05)'
          }]
        }
      },
      symbol: 'circle',
      symbolSize: 4
    }]
  }
  
  chart.setOption(option)
}

const updateChart = () => {
  if (!chart) return
  
  const option = chart.getOption() as any
  const data = option.series[0].data || []
  
  // 添加新数据点
  data.push([new Date(), currentBehavior.confidence])
  
  // 只保留最近50个数据点
  if (data.length > 50) {
    data.shift()
  }
  
  chart.setOption({
    series: [{
      data: data
    }]
  })
}

// 生命周期
onMounted(() => {
  nextTick(() => {
    initChart()
  })
  
  // 开始模拟数据生成
  generateMockData()
})

onBeforeUnmount(() => {
  if (updateTimer) {
    clearInterval(updateTimer)
  }
  if (chart) {
    chart.dispose()
  }
})
</script>

<style scoped>
.user-behavior-panel {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 20px;
  color: #ffffff;
  height: 100%;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.panel-header h3 {
  margin: 0;
  font-size: 1.2rem;
  font-weight: 600;
  color: #ffffff;
}

.panel-controls {
  display: flex;
  gap: 10px;
}

.behavior-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: calc(100% - 80px);
}

/* 当前行为状态 */
.current-behavior {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 20px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.behavior-icon {
  font-size: 3rem;
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: rgba(64, 158, 255, 0.2);
  border: 2px solid rgba(64, 158, 255, 0.4);
}

.behavior-icon.stationary {
  background: rgba(103, 194, 58, 0.2);
  border-color: rgba(103, 194, 58, 0.4);
}

.behavior-icon.walking,
.behavior-icon.running {
  background: rgba(230, 162, 60, 0.2);
  border-color: rgba(230, 162, 60, 0.4);
}

.behavior-icon.cycling,
.behavior-icon.driving,
.behavior-icon.bus,
.behavior-icon.train,
.behavior-icon.subway {
  background: rgba(245, 108, 108, 0.2);
  border-color: rgba(245, 108, 108, 0.4);
}

.behavior-info {
  flex: 1;
}

.behavior-info h4 {
  margin: 0 0 8px 0;
  font-size: 1.4rem;
  font-weight: 600;
  color: #ffffff;
}

.behavior-info p {
  margin: 4px 0;
  font-size: 0.9rem;
  color: #b0bec5;
}

.behavior-indicator {
  width: 120px;
}

.confidence-bar {
  width: 100%;
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  transition: width 0.5s ease;
  border-radius: 4px;
}

.confidence-fill.high {
  background: linear-gradient(90deg, #67C23A, #409EFF);
}

.confidence-fill.medium {
  background: linear-gradient(90deg, #E6A23C, #67C23A);
}

.confidence-fill.low {
  background: linear-gradient(90deg, #F56C6C, #E6A23C);
}

/* 行为历史 */
.behavior-history {
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  padding: 15px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.behavior-history h4 {
  margin: 0 0 15px 0;
  font-size: 1rem;
  color: #409EFF;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  transition: all 0.3s ease;
}

.history-item.active {
  background: rgba(64, 158, 255, 0.1);
  border-color: rgba(64, 158, 255, 0.3);
}

.history-item:hover {
  background: rgba(255, 255, 255, 0.08);
}

.history-time {
  font-size: 0.8rem;
  color: #b0bec5;
  min-width: 80px;
}

.history-behavior {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.behavior-emoji {
  font-size: 1.2rem;
}

.behavior-name {
  font-size: 0.9rem;
  color: #ffffff;
}

.history-confidence {
  font-size: 0.8rem;
  color: #67C23A;
  font-weight: 600;
  min-width: 40px;
  text-align: right;
}

/* 行为统计 */
.behavior-stats {
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  padding: 15px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.behavior-stats h4 {
  margin: 0 0 15px 0;
  font-size: 1rem;
  color: #409EFF;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.stat-icon {
  font-size: 1.2rem;
  width: 30px;
  text-align: center;
}

.stat-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-name {
  font-size: 0.9rem;
  color: #ffffff;
  font-weight: 500;
}

.stat-count,
.stat-duration {
  font-size: 0.8rem;
  color: #b0bec5;
}

.stat-percentage {
  font-size: 0.8rem;
  color: #67C23A;
  font-weight: 600;
  min-width: 40px;
  text-align: right;
}

/* 实时数据图表 */
.behavior-chart {
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  padding: 15px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  flex: 1;
}

.behavior-chart h4 {
  margin: 0 0 15px 0;
  font-size: 1rem;
  color: #409EFF;
}

.chart-container {
  height: 150px;
  width: 100%;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 4px;
  height: 4px;
}

::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 2px;
}

::-webkit-scrollbar-thumb {
  background: rgba(64, 158, 255, 0.3);
  border-radius: 2px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(64, 158, 255, 0.5);
}
</style> 