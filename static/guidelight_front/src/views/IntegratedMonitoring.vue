<template>
  <div class="integrated-monitoring">
    <!-- 顶部状态栏 -->
    <div class="top-status-bar">
      <div class="status-section">
        <div class="system-logo">
          <div class="logo-icon">🎯</div>
          <div class="logo-text">
            <h2>GuideLight 智能监控系统</h2>
            <p>基于视觉环境感知的视障人士出行导航系统 V2.0</p>
          </div>
        </div>
      </div>
      
      <div class="status-section">
        <div class="collision-warning" :class="collisionLevel">
          <div class="warning-icon">⚠️</div>
          <div class="warning-content">
            <span class="warning-title">碰撞概率</span>
            <span class="warning-value">{{ collisionProbability.toFixed(1) }}%</span>
          </div>
          <div class="warning-meter">
            <div class="meter-fill" :style="{ width: collisionProbability + '%' }"></div>
          </div>
        </div>
      </div>
      
      <div class="status-section">
        <div class="system-status">
          <div class="status-item">
            <span class="status-label">系统状态:</span>
            <span class="status-value" :class="systemStatus.type">{{ systemStatus.text }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">连接设备:</span>
            <span class="status-value">{{ connectedDevices }}台</span>
          </div>
          <div class="status-item">
            <span class="status-label">运行时间:</span>
            <span class="status-value">{{ formatDuration(runtime) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 主要内容区域 -->
    <div class="main-dashboard">
      <!-- 左侧视觉处理面板 -->
      <div class="left-panel">
        <!-- 视觉算法控制 -->
        <div class="vision-control-panel">
          <div class="panel-header">
            <h3>视觉算法控制中心</h3>
            <div class="algorithm-selector">
              <el-select v-model="selectedAlgorithm" @change="switchAlgorithm">
                <el-option 
                  v-for="algo in algorithms" 
                  :key="algo.id"
                  :label="algo.name"
                  :value="algo.id"
                />
              </el-select>
            </div>
          </div>
          
          <div class="algorithm-grid">
            <div 
              v-for="algo in algorithmModules" 
              :key="algo.id"
              class="algorithm-card"
              :class="{ active: algo.status === 'active' }"
              @click="toggleAlgorithm(algo.id)"
            >
              <div class="card-header">
                <div class="algorithm-icon" :style="{ backgroundColor: algo.color }">
                  {{ algo.icon }}
                </div>
                <div class="algorithm-info">
                  <h4>{{ algo.name }}</h4>
                  <p>{{ algo.description }}</p>
                </div>
              </div>
              <div class="card-status">
                <el-tag :type="algo.status === 'active' ? 'success' : 'info'" size="small">
                  {{ algo.status === 'active' ? '运行中' : '未激活' }}
                </el-tag>
                <div class="performance-indicator">
                  <span>{{ algo.performance }}ms</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 系统状态面板 -->
        <div class="system-status-panel">
          <div class="panel-header">
            <h3>系统状态监控</h3>
          </div>
          
          <div class="status-grid">
            <div class="status-card">
              <div class="status-icon">🔧</div>
              <div class="status-info">
                <h4>算法状态</h4>
                <p>{{ activeAlgorithmsCount }}/{{ totalAlgorithmsCount }} 个算法运行中</p>
              </div>
            </div>
            
            <div class="status-card">
              <div class="status-icon">📊</div>
              <div class="status-info">
                <h4>性能监控</h4>
                <p>平均延迟: {{ averageLatency }}ms</p>
              </div>
            </div>
            
            <div class="status-card">
              <div class="status-icon">💾</div>
              <div class="status-info">
                <h4>资源使用</h4>
                <p>内存: {{ memoryUsage }}% | CPU: {{ cpuUsage }}%</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 中央BEV和地图区域 -->
      <div class="center-panel">
        <!-- BEV鸟瞰图 -->
        <div class="bev-section">
          <div class="panel-header">
            <h3>鸟瞰图 (BEV) - 环境感知</h3>
            <div class="bev-controls">
              <el-button-group>
                <el-button 
                  :type="bevMode === '2D' ? 'primary' : ''"
                  @click="setBEVMode('2D')"
                  size="small"
                >
                  2D视图
                </el-button>
                <el-button 
                  :type="bevMode === '3D' ? 'primary' : ''"
                  @click="setBEVMode('3D')"
                  size="small"
                >
                  3D视图
                </el-button>
              </el-button-group>
              <el-button size="small" @click="resetBEVView">重置</el-button>
              <el-button size="small" @click="exportBEVData">导出</el-button>
            </div>
          </div>
          
          <div class="bev-container">
            <BEVCanvas 
              ref="bevCanvas" 
              :mode="bevMode"
              @position-change="onBEVPositionChange"
              @objects-detected="onObjectsDetected"
              @collision-risk="onCollisionRisk"
            />
            
            <!-- BEV数据覆盖层 -->
            <div class="bev-overlay-panel">
              <div class="coordinate-display">
                <h4>坐标信息</h4>
                <div class="coord-item">
                  <span>X: {{ mousePosition.x.toFixed(2) }}m</span>
                </div>
                <div class="coord-item">
                  <span>Y: {{ mousePosition.y.toFixed(2) }}m</span>
                </div>
                <div class="coord-item">
                  <span>距离: {{ mousePosition.distance.toFixed(2) }}m</span>
                </div>
                <div class="coord-item">
                  <span>角度: {{ mousePosition.angle.toFixed(1) }}°</span>
                </div>
              </div>
              
              <div class="risk-assessment">
                <h4>风险评估</h4>
                <div class="risk-item">
                  <span class="risk-label">碰撞风险:</span>
                  <span class="risk-value" :class="collisionLevel">{{ collisionLevel.toUpperCase() }}</span>
                </div>
                <div class="risk-item">
                  <span class="risk-label">预测时间:</span>
                  <span class="risk-value">{{ predictedTime.toFixed(1) }}s</span>
                </div>
                <div class="risk-item">
                  <span class="risk-label">最近物体:</span>
                  <span class="risk-value">{{ nearestObject.name }}</span>
                </div>
                <div class="risk-item">
                  <span class="risk-label">距离:</span>
                  <span class="risk-value">{{ nearestObject.distance.toFixed(1) }}m</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 高德地图智能导航系统 -->
        <div class="navigation-container enhanced-navigation">
          <div class="panel-header nav-header">
            <div class="nav-title">
              <div class="nav-icon">🗺️</div>
              <h3>高德地图智能导航系统</h3>
            </div>
            <div class="nav-controls">
              <el-button type="primary" size="small" @click="getCurrentLocation">
                <el-icon><Location /></el-icon>
                定位
              </el-button>
              <el-button type="success" size="small" @click="startNavigation" :disabled="!destination.address">
                <el-icon><Guide /></el-icon>
                导航
              </el-button>
              <el-button type="warning" size="small" @click="stopNavigation">
                <el-icon><CircleClose /></el-icon>
                停止
              </el-button>
            </div>
          </div>
          
          <div class="navigation-content enhanced-content">
            <!-- 智能搜索栏 -->
            <div class="smart-search-section">
              <div class="search-header">
                <el-icon class="search-icon"><Search /></el-icon>
                <span>智能目的地搜索</span>
              </div>
              <div class="search-input-container">
                <el-input
                  v-model="searchKeyword"
                  placeholder="输入目的地名称、地址或关键词..."
                  @input="onSearchInput"
                  @keyup.enter="searchDestination"
                  class="smart-search-input"
                  clearable
                >
                  <template #prepend>
                    <el-icon><Search /></el-icon>
                  </template>
                  <template #append>
                    <el-button type="primary" @click="searchDestination">搜索</el-button>
                  </template>
                </el-input>
              </div>
              
              <!-- 搜索结果 -->
              <div v-if="searchResults.length > 0" class="search-results enhanced-results">
                <div class="results-header">
                  <span>搜索结果 ({{ searchResults.length }})</span>
                </div>
                <div 
                  v-for="result in searchResults" 
                  :key="result.id"
                  class="search-result-item enhanced-item"
                  @click="selectDestination(result)"
                >
                  <div class="result-icon">📍</div>
                  <div class="result-content">
                    <div class="result-name">{{ result.name }}</div>
                    <div class="result-address">{{ result.address }}</div>
                  </div>
                  <div class="result-action">
                    <el-icon><ArrowRight /></el-icon>
                  </div>
                </div>
              </div>
              
              <div v-if="isSearching" class="searching-indicator enhanced-loading">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span>智能搜索中...</span>
              </div>
            </div>
            
            <!-- 高德地图显示 -->
            <div class="map-section">
              <div class="map-header">
                <span>高德地图</span>
                <div class="map-tools">
                  <el-button-group size="small">
                    <el-button @click="zoomIn">
                      <el-icon><ZoomIn /></el-icon>
                    </el-button>
                    <el-button @click="zoomOut">
                      <el-icon><ZoomOut /></el-icon>
                    </el-button>
                    <el-button @click="resetMapView">
                      <el-icon><Refresh /></el-icon>
                    </el-button>
                  </el-button-group>
                </div>
              </div>
              <div id="map-container" class="map-display enhanced-map"></div>
            </div>
            
            <!-- 导航信息面板 -->
            <div v-if="destination.address" class="navigation-info enhanced-info">
              <div class="info-header">
                <el-icon><Guide /></el-icon>
                <span>导航信息</span>
              </div>
              
              <div class="route-info enhanced-route">
                <div class="info-card">
                  <div class="info-icon">🎯</div>
                  <div class="info-content">
                    <span class="label">目的地</span>
                    <span class="value">{{ destination.address }}</span>
                  </div>
                </div>
                
                <div class="info-card">
                  <div class="info-icon">📏</div>
                  <div class="info-content">
                    <span class="label">距离</span>
                    <span class="value">{{ routeInfo.distance }}</span>
                  </div>
                </div>
                
                <div class="info-card">
                  <div class="info-icon">⏱️</div>
                  <div class="info-content">
                    <span class="label">预计时间</span>
                    <span class="value">{{ routeInfo.duration }}</span>
                  </div>
                </div>
                
                <div class="info-card full-width">
                  <div class="info-icon">🛣️</div>
                  <div class="info-content">
                    <span class="label">推荐路线</span>
                    <span class="value">{{ routeInfo.route }}</span>
                  </div>
                </div>
              </div>
              
              <!-- 模拟控制 -->
              <div class="simulation-controls enhanced-controls">
                <div class="controls-header">
                  <span>位置模拟器</span>
                </div>
                <div class="controls-buttons">
                  <el-button-group>
                    <el-button 
                      :type="simulationStatus === 'running' ? 'success' : 'primary'"
                      @click="startSimulation"
                      :disabled="simulationStatus === 'running'"
                      size="small"
                    >
                      <el-icon><VideoPlay /></el-icon>
                      开始模拟
                    </el-button>
                    <el-button 
                      @click="pauseSimulation"
                      :disabled="simulationStatus !== 'running'"
                      size="small"
                    >
                      <el-icon><VideoPause /></el-icon>
                      暂停
                    </el-button>
                    <el-button 
                      @click="stopSimulation"
                      :disabled="simulationStatus === 'stopped'"
                      size="small"
                    >
                      <el-icon><Close /></el-icon>
                      停止
                    </el-button>
                  </el-button-group>
                </div>
                
                <div class="simulation-status enhanced-status">
                  <el-tag :type="simulationStatus === 'running' ? 'success' : 'info'" size="small">
                    {{ simulationStatus === 'running' ? '模拟进行中' : '模拟已停止' }}
                  </el-tag>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧控制面板 -->
      <div class="right-panel">
        <!-- 系统控制 -->
        <div class="control-panel">
          <div class="panel-header">
            <h3>系统控制</h3>
          </div>
          
          <div class="control-buttons">
            <el-button 
              type="primary" 
              @click="startAllStreams"
              :loading="isStarting"
              :disabled="allStreamsActive"
              size="large"
            >
              {{ isStarting ? '启动中...' : '启动所有流' }}
            </el-button>
            
            <el-button 
              type="danger" 
              @click="stopAllStreams"
              :loading="isStopping"
              :disabled="!anyStreamActive"
              size="large"
            >
              {{ isStopping ? '停止中...' : '停止所有流' }}
            </el-button>
          </div>
        </div>

        <!-- 语音控制 -->
        <div class="voice-control-panel">
          <div class="panel-header">
            <h3>语音控制</h3>
          </div>
          
          <div class="voice-controls">
            <div class="voice-status">
              <span>状态: </span>
              <el-tag :type="voiceStatus === 'listening' ? 'success' : voiceStatus === 'processing' ? 'warning' : 'info'" size="small">
                {{ voiceStatus === 'listening' ? '正在聆听' : voiceStatus === 'processing' ? '处理中' : '待机中' }}
              </el-tag>
            </div>
            
            <div class="voice-buttons">
              <el-button 
                :type="voiceStatus === 'listening' ? 'success' : 'primary'"
                @click="toggleVoiceRecognition"
                :disabled="!speechRecognitionClient || voiceStatus === 'processing'"
                size="large"
                :loading="voiceStatus === 'processing'"
              >
                <el-icon v-if="voiceStatus === 'listening'" class="voice-icon-listening">
                  <Microphone />
                </el-icon>
                <el-icon v-else-if="voiceStatus === 'idle'" class="voice-icon">
                  <Microphone />
                </el-icon>
                {{ voiceStatus === 'listening' ? '停止聆听' : voiceStatus === 'processing' ? '处理中...' : '开始语音识别' }}
              </el-button>
            </div>
            
            <div class="voice-tips">
              <p>💡 提示：您可以说 "导航到某某地方" 或 "去某某地方" 来设置导航目的地</p>
            </div>
            
            <div v-if="lastVoiceCommand" class="voice-result">
              <div class="result-header">
                <h4>识别结果</h4>
                <span class="result-time">{{ formatTime(lastVoiceCommand.timestamp) }}</span>
              </div>
              <div class="result-content">
                <div class="result-item">
                  <el-icon><ChatDotRound /></el-icon>
                  <span class="result-label">识别文本:</span>
                  <span class="result-value">{{ lastVoiceCommand.text }}</span>
                </div>
                <div v-if="lastVoiceCommand.command" class="result-item">
                  <el-icon><Operation /></el-icon>
                  <span class="result-label">命令类型:</span>
                  <el-tag size="small">{{ lastVoiceCommand.command.type }}</el-tag>
                </div>
                <div v-if="lastVoiceCommand.command && lastVoiceCommand.command.destination" class="result-item">
                  <el-icon><Location /></el-icon>
                  <span class="result-label">目的地:</span>
                  <span class="result-value">{{ lastVoiceCommand.command.destination }}</span>
                </div>
                <div v-if="lastVoiceCommand.result" class="result-item">
                  <el-icon><CircleCheck /></el-icon>
                  <span class="result-label">执行结果:</span>
                  <span class="result-value">{{ lastVoiceCommand.result.message }}</span>
                </div>
              </div>
            </div>
            
            <div v-if="voiceStatus === 'listening'" class="voice-animation">
              <div class="voice-wave">
                <span></span>
                <span></span>
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        </div>

        <!-- 用户行为识别面板 -->
        <div class="user-behavior-analysis-panel">
          <UserBehaviorPanel />
        </div>

        <!-- 碰撞概率分析 -->
        <div class="collision-analysis-panel">
          <div class="panel-header">
            <h3>碰撞概率分析</h3>
            <el-button size="small" @click="refreshCollisionData">刷新</el-button>
          </div>
          
          <div class="collision-content">
            <div class="probability-chart" ref="probabilityChart"></div>
            
            <div class="collision-details">
              <div class="detail-item">
                <span class="label">当前概率:</span>
                <span class="value" :class="collisionLevel">{{ collisionProbability.toFixed(1) }}%</span>
              </div>
              <div class="detail-item">
                <span class="label">预警时间:</span>
                <span class="value">{{ predictedTime.toFixed(1) }}s</span>
              </div>
              <div class="detail-item">
                <span class="label">最近物体:</span>
                <span class="value">{{ nearestObject.name }}</span>
              </div>
              <div class="detail-item">
                <span class="label">距离:</span>
                <span class="value">{{ nearestObject.distance.toFixed(1) }}m</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部控制栏 -->
    <div class="bottom-control-bar">
      <!-- 性能指标 -->
      <div class="performance-indicators">
        <div class="performance-header">
          <h4>性能监控</h4>
          <div class="performance-actions">
            <el-button size="small" @click="resetPerformanceStats">重置</el-button>
          </div>
        </div>
        
        <div class="indicators-grid">
          <div class="indicator-card">
            <div class="indicator-icon">📊</div>
            <div class="indicator-content">
              <span class="indicator-label">FPS</span>
              <span class="indicator-value">{{ currentFPS }}</span>
            </div>
            <div class="indicator-progress">
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: (currentFPS / 60) * 100 + '%' }"></div>
              </div>
            </div>
          </div>
          
          <div class="indicator-card">
            <div class="indicator-icon">⏱️</div>
            <div class="indicator-content">
              <span class="indicator-label">延迟</span>
              <span class="indicator-value">{{ currentLatency }}ms</span>
            </div>
            <div class="indicator-progress">
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: Math.max(0, 100 - (currentLatency / 100) * 100) + '%' }"></div>
              </div>
            </div>
          </div>
          
          <div class="indicator-card">
            <div class="indicator-icon">💾</div>
            <div class="indicator-content">
              <span class="indicator-label">内存</span>
              <span class="indicator-value">{{ memoryUsage }}MB</span>
            </div>
            <div class="indicator-progress">
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: (memoryUsage / 1024) * 100 + '%' }"></div>
              </div>
            </div>
          </div>
          
          <div class="indicator-card">
            <div class="indicator-icon">🔥</div>
            <div class="indicator-content">
              <span class="indicator-label">CPU</span>
              <span class="indicator-value">{{ cpuUsage }}%</span>
            </div>
            <div class="indicator-progress">
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: cpuUsage + '%' }"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 系统日志 -->
      <div class="system-logs-panel">
        <div class="panel-header">
          <h4>系统日志</h4>
          <div class="log-actions">
            <el-button size="small" @click="clearTerminal">清除</el-button>
            <el-button size="small" @click="exportLogs">导出</el-button>
          </div>
        </div>
        
        <div class="logs-container" ref="terminalOutput">
          <div 
            v-for="log in terminalLogs" 
            :key="log.timestamp"
            class="log-item"
            :class="log.type"
          >
            <span class="log-timestamp">{{ formatTime(log.timestamp) }}</span>
            <span class="log-message">{{ log.message }}</span>
          </div>
          
          <div v-if="terminalLogs.length === 0" class="no-logs">
            <el-icon><Monitor /></el-icon>
            <span>暂无日志记录</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// 声明高德地图类型
declare global {
  interface Window {
    AMap: any;
  }
}
import { ref, reactive, onMounted, onBeforeUnmount, computed, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  VideoCamera, 
  Monitor, 
  Location, 
  Search, 
  Loading, 
  Delete,
  Microphone,
  ChatDotRound,
  Operation,
  CircleCheck,
  Guide,
  CircleClose,
  ArrowRight,
  ZoomIn,
  ZoomOut,
  Refresh,
  VideoPlay,
  VideoPause,
  Close
} from '@element-plus/icons-vue'
// @ts-ignore
import { videoApi, yoloApi, speechApi, navigationApi, integratedApi, environmentApi } from '../api'
import * as echarts from 'echarts'
import BEVCanvas from '../components/BEVCanvas.vue'
import UserBehaviorPanel from '../components/UserBehaviorPanel.vue'
// 在文件顶部添加导入
import { SpeechRecognitionClient } from '../utils/audioProcessor'
import { streamMonitor } from '../utils/streamMonitor'

// 接口定义
interface VideoStream {
  status: 'active' | 'inactive'
}

interface NearestObject {
  name: string
  distance: number
}



interface TerminalLog {
  timestamp: number
  message: string
  type: string
}

interface Algorithm {
  id: string
  name: string
}

interface MousePosition {
  x: number
  y: number
  distance: number
  angle: number
}

// 响应式数据
const collisionProbability = ref(0) // 修改初始值为0，避免永远显示危险预警
const bevMode = ref<'2D' | '3D'>('2D')
const mousePosition = reactive<MousePosition>({
  x: 0,
  y: 0,
  distance: 0,
  angle: 0
})

const videoStreams = reactive<Record<string, VideoStream>>({
  objectDetection: { status: 'inactive' },
  semanticSegmentation: { status: 'inactive' },
  depth: { status: 'inactive' }
})



const terminalLogs = ref<TerminalLog[]>([
  {
    timestamp: Date.now(),
    message: '系统初始化完成',
    type: 'info'
  },
  {
    timestamp: Date.now() - 1000,
    message: '等待用户启动监控流...',
    type: 'warning'
  },
  {
    timestamp: Date.now() - 2000,
    message: '视觉算法模块已加载',
    type: 'success'
  }
])

// 环境感知相关数据
const environmentData = ref<any>(null)
const environmentStatus = ref<any>(null)
const isEnvironmentProcessing = ref(false)

const algorithms = ref<Algorithm[]>([
  { id: 'yolov8', name: 'YOLOv8目标检测' },
  { id: 'mobilenet', name: 'MobileNet-SSD' },
  { id: 'feature_tracking', name: '特征点追踪' },
  { id: 'depth_estimation', name: '深度估计' }
])

const selectedAlgorithm = ref('yolov8')
const isStarting = ref(false)
const isStopping = ref(false)
const predictedTime = ref(3.2)
const nearestObject = reactive<NearestObject>({
  name: '行人',
  distance: 8.5
})

// 新增响应式数据
const systemStatus = reactive({
  type: 'success',
  text: '系统正常运行'
})

const connectedDevices = ref(8)
const runtime = ref(0)

const algorithmModules = ref([
  {
    id: 'object_detection',
    name: '目标检测',
    description: 'YOLOv8实时目标检测',
    icon: '🎯',
    color: '#409EFF',
    status: 'inactive',
    performance: 35
  },
  {
    id: 'semantic_segmentation', 
    name: '语义分割',
    description: '场景语义理解',
    icon: '🧩',
    color: '#67C23A',
    status: 'inactive',
    performance: 45
  },
  {
    id: 'depth_estimation',
    name: '深度估计',
    description: '立体视觉深度计算',
    icon: '📏',
    color: '#E6A23C',
    status: 'inactive',
    performance: 28
  },
  {
    id: 'feature_tracking',
    name: '特征追踪',
    description: '运动目标轨迹追踪',
    icon: '📍',
    color: '#F56C6C',
    status: 'inactive',
    performance: 22
  },
  {
    id: 'gesture_recognition',
    name: '手势识别',
    description: '手势交互识别',
    icon: '👋',
    color: '#909399',
    status: 'inactive',
    performance: 18
  },
  {
    id: 'spatial_tracking',
    name: '空间追踪',
    description: '3D空间物体追踪',
    icon: '🌐',
    color: '#722ED1',
    status: 'inactive',
    performance: 52
  }
])

// 系统状态监控数据
const activeAlgorithmsCount = computed(() => {
  return algorithmModules.value.filter(algo => algo.status === 'active').length
})

const totalAlgorithmsCount = computed(() => {
  return algorithmModules.value.length
})

const averageLatency = computed(() => {
  const activeAlgos = algorithmModules.value.filter(algo => algo.status === 'active')
  if (activeAlgos.length === 0) return 0
  const totalLatency = activeAlgos.reduce((sum, algo) => sum + algo.performance, 0)
  return Math.round(totalLatency / activeAlgos.length)
})

// 性能指标
const currentFPS = ref(30)
const currentLatency = ref(45)
const memoryUsage = ref(42)
const cpuUsage = ref(35)

// 添加声明的变量
const bevCanvas = ref<any>(null)
const terminalOutput = ref<any>(null)
const probabilityChart = ref<any>(null)

// 语音识别相关
const speechRecognitionClient = ref<SpeechRecognitionClient | null>(null)
const voiceStatus = ref<'idle' | 'listening' | 'processing'>('idle')
const lastVoiceCommand = ref<any>(null)



// 导航相关
const currentLocation = reactive({
  lng: 117.283042,
  lat: 31.844786,
  address: '合肥工业大学'
})

const destination = reactive({
  lng: 0,
  lat: 0,
  address: ''
})

const routeInfo = reactive({
  distance: '0km',
  duration: '0min',
  route: '暂无路线'
})

const searchKeyword = ref('')
const searchResults = ref<any[]>([])
const isSearching = ref(false)
const simulationStatus = ref<'stopped' | 'running' | 'paused'>('stopped')

// 计算属性
const collisionLevel = computed(() => {
  if (collisionProbability.value > 80) return 'critical'
  if (collisionProbability.value > 60) return 'high'
  if (collisionProbability.value > 30) return 'medium'
  return 'low'
})

const allStreamsActive = computed(() => {
  return Object.values(videoStreams).every(stream => stream.status === 'active')
})

const anyStreamActive = computed(() => {
  return Object.values(videoStreams).some(stream => stream.status === 'active')
})

// 数据处理相关
let dataProcessingInterval: number | null = null
let locationUpdateInterval: number | null = null

// 方法
const getVideoStreamUrl = (type: string, side?: string) => {
  let url: string
  
  if (side) {
    // 对于带有side参数的流，使用特定的URL格式
    url = `http://localhost:5000/${type}/video_feed_${side}`
  } else {
    // 对于不带side参数的流，使用标准格式
    url = `http://localhost:5000/${type}/video_feed`
  }
  
  // 直接返回完整URL，不使用streamMonitor
  return url
}

const handleVideoError = (event: Event) => {
  const img = event.target as HTMLImageElement
  const streamId = img.dataset.streamId
  
  if (streamId) {
    const stats = streamMonitor.getStreamStats(streamId)
    if (stats && stats.errorCount > 3) {
      ElMessage.error(`视频流 ${streamId} 连接失败，请检查摄像头状态`)
    } else {
      ElMessage.warning('视频流连接失败，正在重试...')
    }
  } else {
    ElMessage.warning('视频流连接失败，请检查摄像头状态')
  }
}

const handleVideoLoad = (event: Event) => {
  const img = event.target as HTMLImageElement
  const streamId = img.dataset.streamId
  
  if (streamId) {
    // 注册流监控
    streamMonitor.registerStream({
      id: streamId,
      url: img.src.split('?')[0], // 获取基础URL
      retryCount: 5,
      retryDelay: 1000,
      timeout: 10000,
      quality: 'medium'
    })
    
    // 开始监控图像元素
    streamMonitor.monitorImageElement(img, streamId)
  }
}

const startAllStreams = async () => {
  isStarting.value = true
  try {
    // 启动所有算法模块
    for (const algo of algorithmModules.value) {
      try {
        // 模拟启动算法
        await new Promise(resolve => setTimeout(resolve, 200))
        algo.status = 'active'
        addTerminalLog(`${algo.name}算法已启动`, 'success')
      } catch (error) {
        addTerminalLog(`${algo.name}算法启动失败: ${error}`, 'error')
      }
    }
    
    // 启动系统核心服务
    videoStreams.objectDetection.status = 'active'
    videoStreams.semanticSegmentation.status = 'active'
    videoStreams.depth.status = 'active'
    
    ElMessage.success('所有算法模块已启动')
    
    // 启动实时数据处理
    if (!dataProcessingInterval) {
      startRealTimeProcessing()
    }
  } catch (error: any) {
    ElMessage.error('启动算法模块失败: ' + error.message)
    addTerminalLog('启动算法模块失败: ' + error.message, 'error')
  } finally {
    isStarting.value = false
  }
}

const stopAllStreams = async () => {
  isStopping.value = true
  try {
    // 停止所有算法模块
    for (const algo of algorithmModules.value) {
      try {
        // 模拟停止算法
        await new Promise(resolve => setTimeout(resolve, 100))
        algo.status = 'inactive'
        addTerminalLog(`${algo.name}算法已停止`, 'warning')
      } catch (error) {
        addTerminalLog(`${algo.name}算法停止失败: ${error}`, 'error')
      }
    }
    
    // 停止系统核心服务
    videoStreams.objectDetection.status = 'inactive'
    videoStreams.semanticSegmentation.status = 'inactive'
    videoStreams.depth.status = 'inactive'
    
    ElMessage.success('所有算法模块已停止')
    addTerminalLog('所有算法模块已停止', 'warning')
    
    // 停止实时数据处理
    stopRealTimeProcessing()
  } catch (error: any) {
    ElMessage.error('停止算法模块失败: ' + error.message)
    addTerminalLog('停止算法模块失败: ' + error.message, 'error')
  } finally {
    isStopping.value = false
  }
}

const toggleBEVMode = () => {
  bevMode.value = bevMode.value === '2D' ? '3D' : '2D'
  if (bevCanvas.value) {
    bevCanvas.value.refresh()
  }
  addTerminalLog(`切换到${bevMode.value}模式`, 'info')
}

const resetBEVView = () => {
  if (bevCanvas.value) {
    bevCanvas.value.refresh()
  }
  addTerminalLog('BEV视图已重置', 'info')
}



const switchAlgorithm = () => {
  const algo = algorithms.value.find(a => a.id === selectedAlgorithm.value)
  addTerminalLog(`切换到${algo?.name}算法`, 'info')
}

const addTerminalLog = (message: string, type: string = 'info') => {
  terminalLogs.value.unshift({
    timestamp: Date.now(),
    message,
    type
  })
  
  // 限制日志数量
  if (terminalLogs.value.length > 100) {
    terminalLogs.value = terminalLogs.value.slice(0, 100)
  }
  
  // 自动滚动到顶部
  nextTick(() => {
    if (terminalOutput.value) {
      terminalOutput.value.scrollTop = 0
    }
  })
}

const clearTerminal = () => {
  terminalLogs.value = []
  addTerminalLog('终端已清除', 'info')
}

const resetPerformanceStats = () => {
  currentFPS.value = 30
  currentLatency.value = 25
  memoryUsage.value = 256
  cpuUsage.value = 35
  addTerminalLog('性能统计已重置', 'info')
}

const exportLogs = () => {
  const logs = terminalLogs.value.map(log => 
    `${formatTime(log.timestamp)} [${log.type.toUpperCase()}] ${log.message}`
  ).join('\n')
  
  const blob = new Blob([logs], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `system_logs_${new Date().toISOString().slice(0, 10)}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

const formatTime = (timestamp: number) => {
  return new Date(timestamp).toLocaleTimeString()
}

const refreshCollisionData = async () => {
  try {
    const response = await fetch('http://localhost:5000/api/collision/risk')
    if (response.ok) {
      const data = await response.json()
      
              // 修复碰撞概率显示问题 - 确保数据格式正确
        if (data.success !== false) {
          // 更新碰撞概率 - 优先使用risk.probability，如果没有则使用max_probability
          let probabilityValue = 0
          if (data.risk && data.risk.probability !== undefined && data.risk.probability !== null) {
            probabilityValue = data.risk.probability
          } else if (data.max_probability !== undefined && data.max_probability !== null) {
            probabilityValue = data.max_probability
          }
          
          collisionProbability.value = Math.min(Math.max(probabilityValue, 0), 100)
        
        // 更新预测时间和最近物体信息
        if (data.risk) {
          // 处理time_to_collision，如果是null或undefined则设为0
          predictedTime.value = (data.risk.time_to_collision !== null && data.risk.time_to_collision !== undefined) ? data.risk.time_to_collision : 0
          
          if (data.risk.nearest_object) {
            nearestObject.name = data.risk.nearest_object.type || '未知'
            nearestObject.distance = data.risk.nearest_object.distance || 0
          } else {
            // 如果没有nearest_object，但有detected_objects，使用最近的一个
            if (data.detected_objects && data.detected_objects.length > 0) {
              const nearest = data.detected_objects.reduce((prev, current) => 
                prev.distance < current.distance ? prev : current
              )
              nearestObject.name = nearest.type || '未知'
              nearestObject.distance = nearest.distance || 0
            } else {
              nearestObject.name = '无检测对象'
              nearestObject.distance = 0
            }
          }
          
                      // 记录碰撞风险等级
            const riskLevel = data.risk.level
            const logType = riskLevel === 'critical' ? 'error' : riskLevel === 'high' ? 'error' : riskLevel === 'medium' ? 'warning' : 'info'
            addTerminalLog(`碰撞风险: ${riskLevel} - ${data.risk.warning_message}`, logType)
          }
          
          // 记录检测到的对象信息
          if (data.detected_objects && data.detected_objects.length > 0) {
            addTerminalLog(`检测到 ${data.detected_objects.length} 个对象`, 'info')
            data.detected_objects.forEach(obj => {
              addTerminalLog(`- ${obj.type}: 距离${obj.distance.toFixed(2)}m, 置信度${(obj.confidence * 100).toFixed(1)}%`, 'info')
            })
          }
          
          addTerminalLog(`碰撞概率数据已更新: ${collisionProbability.value.toFixed(1)}% (风险等级: ${data.risk?.level || '未知'})`, 'success')
          
          // 调试信息
          console.log('碰撞概率数据更新:', {
            risk_probability: data.risk?.probability,
            max_probability: data.max_probability,
            final_probability: collisionProbability.value,
            nearest_object: nearestObject.name,
            distance: nearestObject.distance
          })
      } else {
        // 如果API返回success: false，使用默认值
        collisionProbability.value = 0
        predictedTime.value = 0
        nearestObject.name = '服务不可用'
        nearestObject.distance = 0
        addTerminalLog('碰撞检测服务返回错误状态', 'warning')
      }
    } else {
      // API调用失败，显示0值
      console.warn('碰撞数据API调用失败，状态码:', response.status)
      collisionProbability.value = 0
      predictedTime.value = 0
      nearestObject.name = '无数据'
      nearestObject.distance = 0
      
      addTerminalLog(`碰撞检测API调用失败(状态码: ${response.status})，显示默认值`, 'warning')
    }
  } catch (error) {
    console.error('获取碰撞数据失败:', error)
    // 发生错误时显示0值
    collisionProbability.value = 0
    predictedTime.value = 0
    nearestObject.name = '连接失败'
    nearestObject.distance = 0
    
    addTerminalLog('碰撞检测连接失败，显示默认值: ' + String(error), 'error')
  }
}

const onBEVPositionChange = (position: MousePosition) => {
  mousePosition.x = position.x
  mousePosition.y = position.y
  mousePosition.distance = position.distance
  mousePosition.angle = position.angle
}

// 初始化概率图表
const initProbabilityChart = () => {
  if (!probabilityChart.value) return
  
  const chart = echarts.init(probabilityChart.value)
  
  const option = {
    title: {
      text: '碰撞概率趋势',
      textStyle: {
        fontSize: 14
      }
    },
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'time',
      boundaryGap: false
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: {
        formatter: '{value}%'
      }
    },
    series: [{
      name: '碰撞概率',
      type: 'line',
      smooth: true,
      data: [],
      lineStyle: {
        color: '#409EFF'
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
            color: 'rgba(64, 158, 255, 0.8)'
          }, {
            offset: 1,
            color: 'rgba(64, 158, 255, 0.1)'
          }]
        }
      }
    }]
  }
  
  chart.setOption(option)
  
  // 模拟数据更新
  const updateData = () => {
    const now = new Date()
    const chartOption = chart.getOption() as any
    const data = chartOption.series[0].data || []
    data.push([now, collisionProbability.value])
    
    // 只保留最近20个数据点
    if (data.length > 20) {
      data.shift()
    }
    
    chart.setOption({
      series: [{
        data: data
      }]
    })
  }
  
  setInterval(updateData, 1000)
}

// 语音识别
const initSpeechRecognition = async () => {
  try {
    speechRecognitionClient.value = new SpeechRecognitionClient()
    const success = await speechRecognitionClient.value.initialize()
    
    if (success) {
      addTerminalLog('语音识别初始化成功', 'success')
    } else {
      addTerminalLog('语音识别初始化失败', 'error')
    }
  } catch (error) {
    console.error('语音识别初始化失败:', error)
    addTerminalLog('语音识别初始化失败: ' + error, 'error')
  }
}

const toggleVoiceRecognition = async () => {
  if (!speechRecognitionClient.value) {
    ElMessage.error('语音识别未初始化')
    return
  }
  
  if (voiceStatus.value === 'listening') {
    // 停止识别
    voiceStatus.value = 'processing'
    addTerminalLog('停止语音识别，处理中...', 'info')
    
    try {
      const result = await speechRecognitionClient.value.stopRecognitionAndGetResult()
      
      if (result.success) {
        lastVoiceCommand.value = {
          timestamp: Date.now(),
          text: result.recognition_text,
          command: result.command,
          result: result.result
        }
        
        addTerminalLog(`语音识别成功: ${result.recognition_text}`, 'success')
        
        // 执行相应的命令
        if (result.command && result.command.type === 'navigation') {
          const destinationName = result.command.destination || extractDestinationFromText(result.recognition_text)
          if (destinationName) {
            ElMessage.success(`导航命令: ${destinationName}`)
            // 自动搜索并设置目的地
            searchKeyword.value = destinationName
            await searchDestination()
            // 如果只有一个搜索结果，自动选择
            if (searchResults.value.length === 1) {
              selectDestination(searchResults.value[0])
              startNavigation()
            }
          }
        }
      } else {
        addTerminalLog(`语音识别失败: ${result.error}`, 'error')
        ElMessage.error('语音识别失败: ' + result.error)
      }
    } catch (error) {
      addTerminalLog('语音识别处理失败: ' + error, 'error')
      ElMessage.error('语音识别处理失败')
    }
    
    voiceStatus.value = 'idle'
  } else {
    // 开始识别
    try {
      const success = await speechRecognitionClient.value.startRecognition()
      
      if (success) {
        voiceStatus.value = 'listening'
        addTerminalLog('开始语音识别，请说话...', 'info')
        ElMessage.success('开始语音识别，请说话...')
      } else {
        addTerminalLog('启动语音识别失败', 'error')
        ElMessage.error('启动语音识别失败')
      }
    } catch (error) {
      addTerminalLog('启动语音识别失败: ' + error, 'error')
      ElMessage.error('启动语音识别失败')
    }
  }
}



// 实时数据处理
const startRealTimeProcessing = () => {
  if (dataProcessingInterval) return
  
  // 立即执行一次数据刷新
  refreshCollisionData()
  
  dataProcessingInterval = setInterval(async () => {
    // 获取实时碰撞数据
    await refreshCollisionData()
    
    // 模拟系统状态数据（后续可以从实际API获取）
    currentFPS.value = Math.floor(Math.random() * 10) + 25
    currentLatency.value = Math.floor(Math.random() * 20) + 30
    memoryUsage.value = Math.floor(Math.random() * 100) + 200
    cpuUsage.value = Math.floor(Math.random() * 30) + 50
    
    // 更新运行时间
    runtime.value += 1
  }, 1000)
  
  addTerminalLog('实时数据处理已启动', 'info')
}

const stopRealTimeProcessing = () => {
  if (dataProcessingInterval) {
    clearInterval(dataProcessingInterval)
    dataProcessingInterval = null
    addTerminalLog('实时数据处理已停止', 'warning')
  }
}

// 格式化持续时间
const formatDuration = (seconds: number) => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  
  if (hours > 0) {
    return `${hours}h ${minutes}m ${secs}s`
  } else if (minutes > 0) {
    return `${minutes}m ${secs}s`
  } else {
    return `${secs}s`
  }
}

// 从语音文本中提取目的地
const extractDestinationFromText = (text: string): string => {
  // 定义导航关键词模式
  const patterns = [
    /导航到(.+)/,
    /导航至(.+)/,
    /去(.+)/,
    /前往(.+)/,
    /到(.+)去/,
    /我要去(.+)/,
    /带我去(.+)/
  ]
  
  for (const pattern of patterns) {
    const match = text.match(pattern)
    if (match && match[1]) {
      return match[1].trim()
    }
  }
  
  return ''
}

// 导航相关方法
const getCurrentLocation = async () => {
  try {
    addTerminalLog('正在获取当前位置...', 'info')
    
    // 调用后端API获取位置
    const response = await fetch('/location/current')
    const data = await response.json()
    
    if (data.code === 200) {
      currentLocation.lng = data.data.lng
      currentLocation.lat = data.data.lat
      currentLocation.address = data.data.name || '当前位置'
      
      addTerminalLog(`当前位置: ${currentLocation.address}`, 'success')
      ElMessage.success('位置获取成功')
      
      // 更新地图中心
      if (map) {
        map.setCenter([currentLocation.lng, currentLocation.lat])
      }
    } else {
      addTerminalLog('获取位置失败: ' + data.message, 'error')
      ElMessage.error('获取位置失败')
    }
  } catch (error) {
    addTerminalLog('获取位置失败: ' + error, 'error')
    ElMessage.error('获取位置失败')
  }
}

const startNavigation = () => {
  if (!destination.address) {
    ElMessage.warning('请先设置目的地')
    return
  }
  
  addTerminalLog(`开始导航到: ${destination.address}`, 'info')
  ElMessage.success('导航已开始')
  
  // 计算路线
  calculateRoute()
}

const stopNavigation = () => {
  addTerminalLog('导航已停止', 'warning')
  ElMessage.info('导航已停止')
  
  // 清除路线
  if (map && navigationPath) {
    map.remove(navigationPath)
    navigationPath = null
  }
}

const onSearchInput = () => {
  if (searchKeyword.value.length > 2) {
    searchDestination()
  } else {
    searchResults.value = []
  }
}

const searchDestination = async () => {
  if (!searchKeyword.value.trim()) return
  
  isSearching.value = true
  searchResults.value = []
  
  try {
    addTerminalLog(`搜索目的地: ${searchKeyword.value}`, 'info')
    
    // 使用高德地图API搜索
    if (window.AMap && window.AMap.PlaceSearch) {
      const placeSearch = new window.AMap.PlaceSearch({
        city: '合肥',
        pageSize: 10,
        pageIndex: 1
      })
      
      return new Promise<void>((resolve) => {
        placeSearch.search(searchKeyword.value, (status: string, result: any) => {
          if (status === 'complete' && result.info === 'OK') {
            searchResults.value = result.poiList.pois.map((poi: any, index: number) => ({
              id: index + 1,
              name: poi.name,
              address: poi.address,
              lng: poi.location.lng,
              lat: poi.location.lat
            }))
            addTerminalLog(`找到 ${searchResults.value.length} 个搜索结果`, 'success')
          } else {
            // 如果API搜索失败，使用模拟数据
            searchResults.value = [
              {
                id: 1,
                name: '合肥火车站',
                address: '安徽省合肥市瑶海区站前路',
                lng: 117.301692,
                lat: 31.878719
              },
              {
                id: 2,
                name: '合肥南站',
                address: '安徽省合肥市包河区徽州大道',
                lng: 117.219983,
                lat: 31.745087
              },
              {
                id: 3,
                name: '合肥市政府',
                address: '安徽省合肥市蜀山区东流路',
                lng: 117.243534,
                lat: 31.820592
              }
            ]
            addTerminalLog('使用模拟搜索结果', 'warning')
          }
          isSearching.value = false
          resolve()
        })
      })
    } else {
      // 如果没有加载地图API，使用模拟数据
      setTimeout(() => {
        searchResults.value = [
          {
            id: 1,
            name: '合肥火车站',
            address: '安徽省合肥市瑶海区站前路',
            lng: 117.301692,
            lat: 31.878719
          },
          {
            id: 2,
            name: '合肥南站',
            address: '安徽省合肥市包河区徽州大道',
            lng: 117.219983,
            lat: 31.745087
          },
          {
            id: 3,
            name: '合肥市政府',
            address: '安徽省合肥市蜀山区东流路',
            lng: 117.243534,
            lat: 31.820592
          }
        ]
        isSearching.value = false
        addTerminalLog(`找到 ${searchResults.value.length} 个搜索结果`, 'success')
      }, 1000)
    }
  } catch (error) {
    isSearching.value = false
    addTerminalLog('搜索失败: ' + error, 'error')
    ElMessage.error('搜索失败')
  }
}

const selectDestination = (result: any) => {
  destination.lng = result.lng
  destination.lat = result.lat
  destination.address = result.name
  
  searchKeyword.value = result.name
  searchResults.value = []
  
  addTerminalLog(`选择目的地: ${result.name}`, 'info')
  
  // 在地图上标记目的地
  if (map) {
    const marker = new window.AMap.Marker({
      position: [result.lng, result.lat],
      icon: 'https://webapi.amap.com/theme/v1.3/markers/n/mark_r.png',
      anchor: 'bottom-center',
      label: {
        content: result.name,
        direction: 'top'
      }
    })
    map.add(marker)
  }
}

const calculateRoute = () => {
  if (!map || !destination.lng || !destination.lat) return
  
  // 计算路线
  const driving = new window.AMap.Driving({
    policy: window.AMap.DrivingPolicy.LEAST_TIME
  })
  
  driving.search([currentLocation.lng, currentLocation.lat], [destination.lng, destination.lat], (status: string, result: any) => {
    if (status === 'complete') {
      const route = result.routes[0]
      routeInfo.distance = (route.distance / 1000).toFixed(1) + 'km'
      routeInfo.duration = Math.round(route.time / 60) + 'min'
      routeInfo.route = route.steps.map((step: any) => step.instruction).join(' -> ')
      
      // 绘制路线
      const path = []
      route.steps.forEach((step: any) => {
        step.path.forEach((point: any) => {
          path.push([point.lng, point.lat])
        })
      })
      
      if (navigationPath) {
        map.remove(navigationPath)
      }
      
      navigationPath = new window.AMap.Polyline({
        path: path,
        strokeColor: '#409EFF',
        strokeWeight: 6,
        strokeOpacity: 0.8
      })
      
      map.add(navigationPath)
      map.setFitView([navigationPath])
      
      addTerminalLog(`路线计算完成: ${routeInfo.distance}, ${routeInfo.duration}`, 'success')
    } else {
      addTerminalLog('路线计算失败', 'error')
    }
  })
}

// 位置模拟器
const startSimulation = () => {
  simulationStatus.value = 'running'
  addTerminalLog('开始位置模拟', 'info')
  
  // 开始定期更新位置
  locationUpdateInterval = setInterval(() => {
    // 模拟位置变化
    const deltaLng = (Math.random() - 0.5) * 0.001
    const deltaLat = (Math.random() - 0.5) * 0.001
    
    currentLocation.lng += deltaLng
    currentLocation.lat += deltaLat
    
    // 更新地图中心
    if (map) {
      map.setCenter([currentLocation.lng, currentLocation.lat])
    }
  }, 2000)
}

const pauseSimulation = () => {
  simulationStatus.value = 'paused'
  addTerminalLog('位置模拟已暂停', 'warning')
  
  if (locationUpdateInterval) {
    clearInterval(locationUpdateInterval)
    locationUpdateInterval = null
  }
}

const stopSimulation = () => {
  simulationStatus.value = 'stopped'
  addTerminalLog('位置模拟已停止', 'warning')
  
  if (locationUpdateInterval) {
    clearInterval(locationUpdateInterval)
    locationUpdateInterval = null
  }
}

// 新增方法
const toggleAlgorithm = async (algorithmId: string) => {
  const algo = algorithmModules.value.find(a => a.id === algorithmId)
  if (!algo) return
  
  if (algo.status === 'active') {
    // 停止算法
    try {
      await videoApi.stopCamera(getAlgorithmType(algorithmId))
      algo.status = 'inactive'
      addTerminalLog(`${algo.name}已停止`, 'warning')
    } catch (error: any) {
      ElMessage.error('停止算法失败: ' + error.message)
    }
  } else {
    // 启动算法
    try {
      await videoApi.startCamera(getAlgorithmType(algorithmId))
      algo.status = 'active'
      addTerminalLog(`${algo.name}已启动`, 'success')
    } catch (error: any) {
      ElMessage.error('启动算法失败: ' + error.message)
    }
  }
}

const getAlgorithmType = (algorithmId: string): string => {
  const typeMap: Record<string, string> = {
    'object_detection': 'm_detector',
    'semantic_segmentation': 'f_detector', 
    'depth_estimation': 'd_estimator',
    'feature_tracking': 'f_tracker',
    'gesture_recognition': 'g_recognition',
    'spatial_tracking': 's_RGB'
  }
  return typeMap[algorithmId] || 'm_detector'
}

const setBEVMode = (mode: '2D' | '3D') => {
  bevMode.value = mode
  addTerminalLog(`BEV视图切换到${mode}模式`, 'info')
}

const exportBEVData = () => {
  addTerminalLog('BEV数据导出功能开发中...', 'info')
  ElMessage.info('功能开发中...')
}

const refreshAllStreams = () => {
  // 刷新算法模块性能数据
  algorithmModules.value.forEach(algo => {
    if (algo.status === 'active') {
      // 模拟性能数据刷新
      algo.performance = Math.floor(Math.random() * 30) + 15
    }
  })
  addTerminalLog('所有算法模块已刷新', 'info')
}

const toggleFullscreen = () => {
  addTerminalLog('全屏模式功能开发中...', 'info')
  ElMessage.info('功能开发中...')
}

// 添加地图相关变量
let map: any = null
let navigationPath: any = null

// 初始化地图
const initMap = () => {
  // 确保高德地图API已加载
  if (typeof window.AMap === 'undefined') {
    console.error('高德地图API未加载')
    return
  }
  
  try {
    // 创建地图实例
    map = new window.AMap.Map('map-container', {
      zoom: 15,
      resizeEnable: true,
      center: [currentLocation.lng, currentLocation.lat],
      viewMode: '2D'
    })
    
    // 添加地图控件
    map.plugin(['AMap.ToolBar', 'AMap.Scale', 'AMap.Geolocation'], () => {
      const toolBar = new window.AMap.ToolBar()
      const scale = new window.AMap.Scale()
      const geolocation = new window.AMap.Geolocation({
        enableHighAccuracy: true,
        timeout: 10000,
        buttonPosition: 'RB',
        buttonOffset: new window.AMap.Pixel(10, 20),
        zoomToAccuracy: true
      })
      
      map.addControl(toolBar)
      map.addControl(scale)
      map.addControl(geolocation)
    })
    
    // 添加当前位置标记
    const marker = new window.AMap.Marker({
      position: [currentLocation.lng, currentLocation.lat],
      icon: 'https://webapi.amap.com/theme/v1.3/markers/n/mark_b.png',
      anchor: 'bottom-center',
      label: {
        content: '当前位置',
        direction: 'top'
      }
    })
    map.add(marker)
    
    // 添加地图点击事件 - 设置目的地
    map.on('click', handleMapClick)
    
    // 初始化搜索服务
    initSearchService()
    
    addTerminalLog('地图初始化成功', 'success')
  } catch (error) {
    console.error('初始化地图时出错:', error)
    ElMessage.error('地图初始化失败')
    addTerminalLog('地图初始化失败', 'error')
  }
}

// 处理地图点击事件
const handleMapClick = (e: any) => {
  const lngLat = e.lnglat
  
  // 设置为目的地
  setDestination({
    lng: lngLat.getLng(),
    lat: lngLat.getLat(),
    address: '正在获取地址...'
  })
  
  // 获取地址信息
  getAddressByLocation(lngLat.getLng(), lngLat.getLat())
}

// 根据经纬度获取地址
const getAddressByLocation = (lng: number, lat: number) => {
  if (typeof window.AMap === 'undefined') return
  
  const geocoder = new window.AMap.Geocoder()
  
  geocoder.getAddress([lng, lat], (status: string, result: any) => {
    if (status === 'complete' && result.info === 'OK') {
      const address = result.regeocode.formattedAddress
      destination.address = address
      addTerminalLog(`目的地地址: ${address}`, 'info')
    } else {
      destination.address = `位置(${lng.toFixed(6)}, ${lat.toFixed(6)})`
      addTerminalLog('无法获取目的地地址', 'warning')
    }
  })
}

// 设置目的地
const setDestination = (dest: any) => {
  destination.lng = dest.lng
  destination.lat = dest.lat
  destination.address = dest.address
  
  // 清除之前的标记
  if (map) {
    map.clearInfoWindow()
    
    // 移除之前的目的地标记
    const overlays = map.getAllOverlays('marker')
    overlays.forEach((overlay: any) => {
      if (overlay.getExtData() === 'destination') {
        map.remove(overlay)
      }
    })
    
    // 添加新的目的地标记
    const marker = new window.AMap.Marker({
      position: [dest.lng, dest.lat],
      icon: 'https://webapi.amap.com/theme/v1.3/markers/n/mark_r.png',
      anchor: 'bottom-center',
      extData: 'destination',
      label: {
        content: '目的地',
        direction: 'top'
      }
    })
    map.add(marker)
  }
}

// 初始化搜索服务
const initSearchService = () => {
  if (typeof window.AMap === 'undefined') return
  
  // 这里可以初始化高德地图的搜索服务
  addTerminalLog('搜索服务初始化成功', 'success')
}

// 生命周期钩子
onMounted(async () => {
  // 初始化组件
  initProbabilityChart()
  initSpeechRecognition()
  
  // 延迟初始化地图，确保DOM已渲染
  nextTick(() => {
    setTimeout(() => {
      initMap()
    }, 1000)
  })
  
  // 自动启动环境感知处理器
  try {
    addTerminalLog('正在启动环境感知处理器...', 'info')
    
    // 启动BEV组件中的环境感知处理
    if (bevCanvas.value) {
      await bevCanvas.value.startProcessing()
      addTerminalLog('环境感知处理器启动成功', 'success')
    } else {
      // 如果BEV组件还没准备好，延迟启动
      setTimeout(async () => {
        if (bevCanvas.value) {
          await bevCanvas.value.startProcessing()
          addTerminalLog('环境感知处理器启动成功', 'success')
        }
      }, 2000)
    }
  } catch (error: any) {
    addTerminalLog('环境感知处理器启动失败: ' + error.message, 'error')
    console.error('环境感知启动失败:', error)
  }
  
  // 开始运行时间计数
  setInterval(() => {
    runtime.value += 1
  }, 1000)
})

onBeforeUnmount(() => {
  // 清理资源
  if (dataProcessingInterval) {
    clearInterval(dataProcessingInterval)
    dataProcessingInterval = null
  }
  
  if (locationUpdateInterval) {
    clearInterval(locationUpdateInterval)
    locationUpdateInterval = null
  }
  
  if (speechRecognitionClient.value) {
    speechRecognitionClient.value.destroy()
  }
})
</script>

<style scoped>
.integrated-monitoring {
  min-height: 100vh;
  background: linear-gradient(135deg, #0c1426 0%, #1a2332 50%, #2c3e50 100%);
  color: #ffffff;
  font-family: 'Roboto', 'Arial', sans-serif;
  position: relative;
  overflow-x: hidden;
}

/* 顶部状态栏 */
.top-status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 30px;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(64, 158, 255, 0.2);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.status-section {
  display: flex;
  align-items: center;
  gap: 20px;
}

.system-logo {
  display: flex;
  align-items: center;
  gap: 15px;
}

.logo-icon {
  font-size: 2.5rem;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

.logo-text h2 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
  background: linear-gradient(45deg, #409EFF, #67C23A);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.logo-text p {
  margin: 5px 0 0;
  font-size: 0.9rem;
  color: #b0bec5;
}

.collision-warning {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px 25px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
}

.collision-warning.low {
  border-color: #67C23A;
  box-shadow: 0 0 20px rgba(103, 194, 58, 0.3);
}

.collision-warning.medium {
  border-color: #E6A23C;
  box-shadow: 0 0 20px rgba(230, 162, 60, 0.3);
}

.collision-warning.high {
  border-color: #F56C6C;
  box-shadow: 0 0 20px rgba(245, 108, 108, 0.3);
}

.collision-warning.critical {
  border-color: #F56C6C;
  box-shadow: 0 0 30px rgba(245, 108, 108, 0.5);
  animation: warning-pulse 1s infinite;
}

@keyframes warning-pulse {
  0%, 100% { box-shadow: 0 0 30px rgba(245, 108, 108, 0.5); }
  50% { box-shadow: 0 0 40px rgba(245, 108, 108, 0.8); }
}

.warning-icon {
  font-size: 1.5rem;
}

.warning-content {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.warning-title {
  font-size: 0.9rem;
  color: #b0bec5;
}

.warning-value {
  font-size: 1.4rem;
  font-weight: bold;
}

.warning-meter {
  width: 120px;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
}

.meter-fill {
  height: 100%;
  background: linear-gradient(90deg, #67C23A 0%, #E6A23C 50%, #F56C6C 100%);
  transition: width 0.5s ease;
  border-radius: 3px;
}

.system-status {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.9rem;
}

.status-label {
  color: #b0bec5;
  min-width: 80px;
}

.status-value {
  font-weight: 600;
}

.status-value.success {
  color: #67C23A;
}

.status-value.error {
  color: #F56C6C;
}

/* 主要内容区域 */
.main-dashboard {
  display: grid;
  grid-template-columns: 1fr 2fr 1fr;
  gap: 25px;
  padding: 25px 30px;
  min-height: calc(100vh - 200px);
}

/* 面板通用样式 */
.vision-control-panel,
.system-status-panel,
.bev-section,
.navigation-container,
.voice-interaction-panel,
.risk-assessment-panel,
.system-terminal-panel,
.user-behavior-analysis-panel,
.collision-analysis-panel {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  transition: all 0.3s ease;
}

.vision-control-panel:hover,
.system-status-panel:hover,
.bev-section:hover,
.navigation-container:hover,
.voice-interaction-panel:hover,
.risk-assessment-panel:hover,
.system-terminal-panel:hover {
  border-color: rgba(64, 158, 255, 0.4);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
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

/* 左侧面板 */
.left-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.algorithm-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.algorithm-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 15px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.algorithm-card:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(64, 158, 255, 0.4);
  transform: translateY(-2px);
}

.algorithm-card.active {
  background: rgba(64, 158, 255, 0.1);
  border-color: #409EFF;
  box-shadow: 0 0 20px rgba(64, 158, 255, 0.3);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.algorithm-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  color: white;
}

.algorithm-info h4 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
}

.algorithm-info p {
  margin: 5px 0 0;
  font-size: 0.8rem;
  color: #b0bec5;
}

.card-status {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.performance-indicator {
  font-size: 0.8rem;
  color: #b0bec5;
}

/* 视频流网格 */
.video-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 15px;
}

.video-stream-card {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.video-stream-card.active {
  border-color: #67C23A;
  box-shadow: 0 0 15px rgba(103, 194, 58, 0.3);
}

.stream-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 15px;
  background: rgba(0, 0, 0, 0.2);
}

.stream-header h4 {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 600;
}

.stream-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.8rem;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #909399;
}

.status-dot.active {
  background: #67C23A;
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0.3; }
}

.stream-content {
  position: relative;
  height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-feed {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.stream-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: #b0bec5;
}

.placeholder-icon {
  font-size: 2rem;
}

.stream-footer {
  padding: 8px 15px;
  background: rgba(0, 0, 0, 0.2);
  font-size: 0.8rem;
  color: #b0bec5;
}

.stream-info {
  display: flex;
  justify-content: space-between;
}

/* 中央面板 */
.center-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.bev-container {
  position: relative;
  height: 500px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 12px;
  overflow: hidden;
}

.bev-overlay-panel {
  position: absolute;
  top: 15px;
  right: 15px;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(10px);
  border-radius: 8px;
  padding: 15px;
  min-width: 200px;
}

.coordinate-display h4,
.detected-objects h4 {
  margin: 0 0 10px;
  font-size: 0.9rem;
  color: #409EFF;
}

.coord-item {
  margin-bottom: 5px;
  font-size: 0.8rem;
  color: #b0bec5;
}

.object-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px;
  margin-bottom: 8px;
  border-left: 3px solid;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
}

.object-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.object-name {
  font-size: 0.8rem;
  font-weight: 600;
}

.object-distance {
  font-size: 0.7rem;
  color: #b0bec5;
}

.object-risk {
  font-size: 0.7rem;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.object-risk.low {
  background: #67C23A;
  color: white;
}

.object-risk.medium {
  background: #E6A23C;
  color: white;
}

.object-risk.high {
  background: #F56C6C;
  color: white;
}

.object-risk.critical {
  background: #F56C6C;
  color: white;
  animation: critical-blink 0.5s infinite;
}

@keyframes critical-blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0.5; }
}

/* 导航部分优化样式 */
.navigation-container {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  transition: all 0.3s ease;
}

.navigation-container:hover {
  border-color: rgba(64, 158, 255, 0.4);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
}

.navigation-content {
  display: flex;
  flex-direction: column;
  gap: 15px;
  height: 100%;
}

.nav-controls {
  display: flex;
  gap: 10px;
}

.destination-search {
  position: relative;
  margin-bottom: 15px;
}

.destination-search .el-input {
  font-size: 0.95rem;
}

.destination-search .el-input__inner {
  background: rgba(0, 0, 0, 0.2);
  border-color: rgba(255, 255, 255, 0.2);
  color: #ffffff;
}

.destination-search .el-input__inner:focus {
  border-color: #409EFF;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

.search-input-wrapper {
  position: relative;
}

.search-input {
  width: 100%;
}

.voice-nav-button {
  border-radius: 6px 0 0 6px;
  border-right: none;
  background: linear-gradient(45deg, #409EFF, #67C23A);
  color: white;
  font-weight: 600;
  transition: all 0.3s ease;
}

.voice-nav-button:hover {
  background: linear-gradient(45deg, #67C23A, #409EFF);
  transform: scale(1.05);
}

.search-results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: rgba(0, 0, 0, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  max-height: 300px;
  overflow-y: auto;
  z-index: 1000;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(10px);
}

.search-results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  font-weight: 600;
  color: #409EFF;
}

.search-results-list {
  padding: 5px 0;
}

.search-result-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 15px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.search-result-item:hover {
  background: rgba(64, 158, 255, 0.1);
  transform: translateX(5px);
}

.result-icon {
  font-size: 1.2rem;
  color: #409EFF;
}

.result-content {
  flex: 1;
}

.result-name {
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 2px;
}

.result-address {
  font-size: 0.8rem;
  color: #b0bec5;
}

.result-distance {
  font-size: 0.8rem;
  color: #67C23A;
  font-weight: 600;
}

.searching-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 15px;
  color: #b0bec5;
  justify-content: center;
}

.map-display {
  height: 450px;
  min-height: 450px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 12px;
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: inset 0 2px 10px rgba(0, 0, 0, 0.3);
}

#map-container {
  width: 100%;
  height: 100%;
  border-radius: 12px;
}

.map-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
}

.placeholder-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.placeholder-icon {
  font-size: 4rem;
  opacity: 0.6;
}

.placeholder-hint {
  font-size: 0.8rem;
  color: #909399;
  margin-top: 5px;
}

.nav-status-indicator {
  position: absolute;
  top: 15px;
  right: 15px;
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(0, 0, 0, 0.7);
  padding: 8px 12px;
  border-radius: 20px;
  color: #67C23A;
  font-weight: 600;
  font-size: 0.8rem;
  backdrop-filter: blur(5px);
}

.nav-status-indicator .status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #67C23A;
  animation: pulse 2s infinite;
}

.navigation-info {
  flex: 1;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.nav-info-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.nav-info-header h4 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
}

.nav-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
  color: #909399;
}

.nav-status.active {
  color: #67C23A;
}

.nav-status .status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #909399;
}

.nav-status.active .status-dot {
  background: #67C23A;
  animation: pulse 2s infinite;
}

.route-info {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
}

.info-item:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(64, 158, 255, 0.3);
}

.item-icon {
  font-size: 1.2rem;
  width: 24px;
  text-align: center;
}

.item-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item .label {
  font-size: 0.8rem;
  color: #b0bec5;
  font-weight: 500;
}

.info-item .value {
  font-size: 0.9rem;
  font-weight: 600;
  color: #ffffff;
}

.destination-item {
  background: rgba(64, 158, 255, 0.1);
  border-color: rgba(64, 158, 255, 0.3);
}

.clear-btn {
  margin-left: auto;
  padding: 4px 8px;
  font-size: 0.7rem;
}

.speed-control {
  display: flex;
  align-items: center;
  gap: 10px;
}

.speed-value {
  font-size: 0.8rem;
  color: #67C23A;
  font-weight: 600;
  min-width: 40px;
}

.navigation-progress {
  margin-top: 20px;
  padding: 15px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.progress-label {
  font-size: 0.9rem;
  color: #b0bec5;
  margin-bottom: 8px;
  font-weight: 500;
}

.progress-text {
  text-align: center;
  margin-top: 8px;
  font-size: 0.8rem;
  color: #67C23A;
  font-weight: 600;
}

/* 右侧面板 */
.right-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 语音交互 */
.voice-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
  margin-bottom: 15px;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #909399;
}

.voice-status.active .status-indicator {
  background: #67C23A;
  animation: pulse 1s infinite;
}

.voice-buttons {
  margin-bottom: 15px;
}

.voice-buttons .el-button {
  width: 100%;
  height: 60px;
  font-size: 1rem;
  font-weight: 600;
  transition: all 0.3s ease;
}

.voice-icon, .voice-icon-listening {
  font-size: 1.2rem;
  margin-right: 8px;
}

.voice-icon-listening {
  animation: pulse 1s infinite;
}

.voice-tips {
  background: rgba(64, 158, 255, 0.1);
  border: 1px solid rgba(64, 158, 255, 0.3);
  border-radius: 8px;
  padding: 10px 15px;
  margin-bottom: 15px;
}

.voice-tips p {
  margin: 0;
  font-size: 0.85rem;
  color: #409EFF;
}

.voice-result {
  margin-top: 15px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  padding: 15px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.result-header h4 {
  margin: 0;
  font-size: 1rem;
  color: #409EFF;
}

.result-time {
  font-size: 0.8rem;
  color: #b0bec5;
}

.result-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
}

.result-item .el-icon {
  font-size: 1rem;
  color: #409EFF;
}

.result-label {
  font-size: 0.85rem;
  color: #b0bec5;
  min-width: 80px;
}

.result-value {
  font-size: 0.9rem;
  color: #ffffff;
  flex: 1;
}

.voice-animation {
  display: flex;
  justify-content: center;
  padding: 20px 0;
}

.voice-wave {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 40px;
}

.voice-wave span {
  display: inline-block;
  width: 4px;
  height: 100%;
  background: linear-gradient(to top, #409EFF, #67C23A);
  border-radius: 2px;
  animation: wave 1.2s linear infinite;
}

.voice-wave span:nth-child(2) {
  animation-delay: -1.1s;
}

.voice-wave span:nth-child(3) {
  animation-delay: -1.0s;
}

.voice-wave span:nth-child(4) {
  animation-delay: -0.9s;
}

.voice-wave span:nth-child(5) {
  animation-delay: -0.8s;
}

@keyframes wave {
  0%, 40%, 100% {
    transform: scaleY(0.4);
  }
  20% {
    transform: scaleY(1);
  }
}



/* 用户行为识别面板 */
.user-behavior-analysis-panel {
  background: linear-gradient(135deg, rgba(230, 162, 60, 0.1) 0%, rgba(64, 158, 255, 0.1) 100%);
  border: 2px solid rgba(230, 162, 60, 0.3);
  box-shadow: 0 12px 48px rgba(230, 162, 60, 0.2);
}

/* 风险评估 */
.risk-content {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.risk-chart {
  height: 120px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
}

.risk-details {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.risk-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8rem;
}

.risk-label {
  color: #b0bec5;
}

.risk-value {
  font-weight: 600;
}

.risk-value.low {
  color: #67C23A;
}

.risk-value.medium {
  color: #E6A23C;
}

.risk-value.high {
  color: #F56C6C;
}

.risk-value.critical {
  color: #F56C6C;
  animation: critical-blink 0.5s infinite;
}

.risk-value.suggestion {
  color: #409EFF;
  font-style: italic;
}

.risk-history h4 {
  margin: 0 0 10px;
  font-size: 0.9rem;
  color: #409EFF;
}

.trend-chart {
  height: 80px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 6px;
}

/* 系统终端 */
.terminal-container {
  height: 200px;
  background: rgba(0, 0, 0, 0.5);
  border-radius: 8px;
  padding: 12px;
  overflow-y: auto;
  font-family: 'Courier New', monospace;
}

/* 系统日志面板样式 */
.system-logs-panel {
  flex: 2;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 16px;
  padding: 30px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  backdrop-filter: blur(10px);
  display: flex;
  flex-direction: column;
  min-height: 420px;
}

.system-logs-panel .panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 15px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.system-logs-panel .panel-header h4 {
  margin: 0;
  color: #409EFF;
  font-size: 1.1rem;
  font-weight: 600;
}

.log-actions {
  display: flex;
  gap: 8px;
}

.log-actions .el-button {
  border-radius: 6px;
  font-size: 0.85rem;
  padding: 6px 12px;
}

.logs-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  font-family: 'Courier New', 'Monaco', monospace;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 320px;
}

.log-item {
  display: flex;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 0.85rem;
  line-height: 1.5;
  transition: all 0.2s ease;
  border-left: 3px solid transparent;
}

.log-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.log-item.info {
  color: #409EFF;
  border-left-color: #409EFF;
}

.log-item.success {
  color: #67C23A;
  border-left-color: #67C23A;
}

.log-item.warning {
  color: #E6A23C;
  border-left-color: #E6A23C;
}

.log-item.error {
  color: #F56C6C;
  border-left-color: #F56C6C;
}

.log-timestamp {
  color: #b0bec5;
  min-width: 80px;
  font-size: 0.75rem;
  font-weight: 500;
}

.log-message {
  flex: 1;
  word-break: break-word;
}

.no-logs {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #b0bec5;
  font-size: 0.9rem;
  gap: 10px;
}

.no-logs .el-icon {
  font-size: 2rem;
  opacity: 0.5;
}

/* 底部控制栏 */
.bottom-control-bar {
  display: flex;
  gap: 30px;
  padding: 30px 35px;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(10px);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  height: 500px;
  min-height: 500px;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.group-title {
  font-size: 0.8rem;
  color: #b0bec5;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.control-buttons {
  display: flex;
  gap: 10px;
}

.performance-indicators {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 16px;
  padding: 30px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  backdrop-filter: blur(10px);
  min-height: 420px;
}

.performance-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.performance-header h4 {
  margin: 0;
  color: #409EFF;
  font-size: 1.1rem;
  font-weight: 600;
}

.performance-actions {
  display: flex;
  gap: 8px;
}

.performance-actions .el-button {
  border-radius: 6px;
  font-size: 0.85rem;
  padding: 6px 12px;
}

.indicators-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  flex: 1;
}

.indicator-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 25px 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
  min-height: 160px;
  justify-content: center;
}

.indicator-card:hover {
  background: rgba(64, 158, 255, 0.1);
  border-color: rgba(64, 158, 255, 0.3);
  transform: translateY(-2px);
}

.indicator-icon {
  font-size: 2.2rem;
  margin-bottom: 8px;
}

.indicator-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}

.indicator-label {
  font-size: 0.85rem;
  color: #b0bec5;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.indicator-value {
  font-size: 1.4rem;
  color: #ffffff;
  font-weight: 700;
}

.indicator-progress {
  width: 100%;
}

.progress-bar {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #67C23A 0%, #E6A23C 70%, #F56C6C 100%);
  transition: width 0.5s ease;
  border-radius: 3px;
}

.indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
}

.progress-bar {
  width: 80px;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #67C23A 0%, #E6A23C 70%, #F56C6C 100%);
  transition: width 0.5s ease;
  border-radius: 3px;
}

.quick-actions {
  display: flex;
  gap: 8px;
}

/* 响应式设计 */
@media (max-width: 1400px) {
  .main-dashboard {
    grid-template-columns: 1fr 1.5fr 1fr;
  }
}

@media (max-width: 1200px) {
  .main-dashboard {
    grid-template-columns: 1fr;
    gap: 20px;
  }
  
  .bottom-control-bar {
    flex-direction: column;
    gap: 25px;
    height: auto;
    min-height: 600px;
    padding: 25px 20px;
  }
  
  .indicators-grid {
    grid-template-columns: repeat(4, 1fr);
    gap: 15px;
  }
}

@media (max-width: 768px) {
  .top-status-bar {
    flex-direction: column;
    gap: 15px;
    padding: 15px 20px;
  }
  
  .navigation-container {
    flex-direction: column;
    height: auto;
  }
  
  .video-grid {
    grid-template-columns: 1fr;
  }
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb {
  background: rgba(64, 158, 255, 0.5);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(64, 158, 255, 0.7);
}

/* 加载动画 */
.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
  z-index: 10;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(64, 158, 255, 0.3);
  border-top: 3px solid #409EFF;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 特殊效果 */
.glow-effect {
  box-shadow: 0 0 20px rgba(64, 158, 255, 0.4);
}

.success-glow {
  box-shadow: 0 0 20px rgba(103, 194, 58, 0.4);
}

.warning-glow {
  box-shadow: 0 0 20px rgba(230, 162, 60, 0.4);
}

.error-glow {
  box-shadow: 0 0 20px rgba(245, 108, 108, 0.4);
}

/* 高德地图智能导航系统增强样式 */
.enhanced-navigation {
  position: relative;
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.1) 0%, rgba(103, 194, 58, 0.1) 100%);
  border: 2px solid rgba(64, 158, 255, 0.3);
  box-shadow: 0 12px 48px rgba(64, 158, 255, 0.2);
}

.nav-header {
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.15) 0%, rgba(103, 194, 58, 0.15) 100%);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 25px;
  border: 1px solid rgba(64, 158, 255, 0.2);
}

.nav-title {
  display: flex;
  align-items: center;
  gap: 15px;
}

.nav-icon {
  font-size: 2rem;
  animation: rotate 4s linear infinite;
}

@keyframes rotate {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.nav-title h3 {
  background: linear-gradient(45deg, #409EFF, #67C23A, #E6A23C);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-size: 1.4rem;
  font-weight: 700;
  margin: 0;
}

.nav-controls {
  display: flex;
  gap: 12px;
}

.nav-controls .el-button {
  border-radius: 8px;
  font-weight: 600;
  transition: all 0.3s ease;
}

.nav-controls .el-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(64, 158, 255, 0.3);
}

.enhanced-content {
  display: flex;
  flex-direction: column;
  gap: 25px;
}

/* 智能搜索栏样式 */
.smart-search-section {
  background: rgba(255, 255, 255, 0.03);
  border-radius: 16px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.search-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
  color: #409EFF;
  font-weight: 600;
}

.search-icon {
  font-size: 1.2rem;
}

.search-input-container {
  position: relative;
}

.smart-search-input {
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.smart-search-input .el-input__wrapper {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(64, 158, 255, 0.3);
  border-radius: 12px;
  transition: all 0.3s ease;
}

.smart-search-input .el-input__wrapper:hover {
  border-color: rgba(64, 158, 255, 0.5);
  box-shadow: 0 0 20px rgba(64, 158, 255, 0.2);
}

.smart-search-input .el-input__wrapper.is-focus {
  border-color: #409EFF;
  box-shadow: 0 0 25px rgba(64, 158, 255, 0.3);
}

/* 搜索结果样式 */
.enhanced-results {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(64, 158, 255, 0.2);
  border-radius: 12px;
  margin-top: 15px;
  overflow: hidden;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}

.results-header {
  padding: 12px 20px;
  background: rgba(64, 158, 255, 0.1);
  border-bottom: 1px solid rgba(64, 158, 255, 0.2);
  font-weight: 600;
  color: #409EFF;
}

.enhanced-item {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  cursor: pointer;
  transition: all 0.3s ease;
}

.enhanced-item:hover {
  background: rgba(64, 158, 255, 0.1);
  transform: translateX(5px);
}

.enhanced-item:last-child {
  border-bottom: none;
}

.result-icon {
  font-size: 1.2rem;
  color: #409EFF;
}

.result-content {
  flex: 1;
}

.result-name {
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 5px;
}

.result-address {
  font-size: 0.9rem;
  color: #b0bec5;
}

.result-action {
  color: #409EFF;
  font-size: 1.1rem;
  transition: transform 0.3s ease;
}

.enhanced-item:hover .result-action {
  transform: translateX(5px);
}

.enhanced-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 20px;
  background: rgba(64, 158, 255, 0.05);
  border-radius: 12px;
  margin-top: 15px;
  color: #409EFF;
  font-weight: 600;
}

/* 地图区域样式 */
.map-section {
  background: rgba(255, 255, 255, 0.03);
  border-radius: 16px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  min-height: 500px;
}

.map-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  color: #409EFF;
  font-weight: 600;
}

.map-tools .el-button-group .el-button {
  border-radius: 6px;
  padding: 6px 10px;
}

.enhanced-map {
  height: 450px;
  min-height: 450px;
  border-radius: 12px;
  overflow: hidden;
  border: 2px solid rgba(64, 158, 255, 0.2);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}

/* 导航信息面板样式 */
.enhanced-info {
  background: rgba(255, 255, 255, 0.03);
  border-radius: 16px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.info-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  color: #409EFF;
  font-weight: 600;
  font-size: 1.1rem;
}

.enhanced-route {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
  margin-bottom: 25px;
}

.info-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 15px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
}

.info-card:hover {
  background: rgba(64, 158, 255, 0.1);
  border-color: rgba(64, 158, 255, 0.3);
  transform: translateY(-2px);
}

.info-card.full-width {
  grid-column: 1 / -1;
}

.info-icon {
  font-size: 1.5rem;
  min-width: 30px;
  text-align: center;
}

.info-content {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.info-content .label {
  font-size: 0.9rem;
  color: #b0bec5;
  font-weight: 500;
}

.info-content .value {
  font-size: 1.1rem;
  color: #ffffff;
  font-weight: 600;
}

/* 模拟控制样式 */
.enhanced-controls {
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.controls-header {
  margin-bottom: 15px;
  color: #409EFF;
  font-weight: 600;
}

.controls-buttons {
  margin-bottom: 15px;
}

.controls-buttons .el-button {
  border-radius: 8px;
  font-weight: 600;
}

.enhanced-status {
  display: flex;
  justify-content: center;
}

/* 系统状态面板样式 */
.system-status-panel {
  background: linear-gradient(135deg, rgba(103, 194, 58, 0.1) 0%, rgba(64, 158, 255, 0.1) 100%);
  border: 2px solid rgba(103, 194, 58, 0.3);
}

.status-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 15px;
}

.status-card {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 20px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
}

.status-card:hover {
  background: rgba(103, 194, 58, 0.1);
  border-color: rgba(103, 194, 58, 0.3);
  transform: translateY(-2px);
}

.status-icon {
  font-size: 2rem;
  min-width: 40px;
  text-align: center;
}

.status-info h4 {
  margin: 0 0 8px 0;
  color: #ffffff;
  font-weight: 600;
}

.status-info p {
  margin: 0;
  color: #b0bec5;
  font-size: 0.9rem;
}

.search-results {
  background-color: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  z-index: 100;
}

.search-result-item {
  padding: 8px 12px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
}

.search-result-item:hover {
  background-color: #f5f7fa;
}

.result-name {
  font-weight: bold;
  font-size: 14px;
}

.result-address {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.searching-indicator {
  padding: 10px;
  text-align: center;
  color: #909399;
}

.map-display {
  height: 450px;
  min-height: 450px;
  border-radius: 4px;
  overflow: hidden;
}

.navigation-info {
  margin-top: 10px;
  padding: 10px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.route-info .info-item {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.route-info .label {
  width: 80px;
  color: #606266;
  font-weight: bold;
}

.route-info .value {
  flex: 1;
  color: #303133;
}

.simulation-controls {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed #dcdfe6;
}

.simulation-status {
  margin-top: 10px;
  text-align: right;
}

.performance-indicators {
  display: flex;
  gap: 20px;
}

.indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
}

.progress-bar {
  width: 80px;
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #67C23A 0%, #E6A23C 70%, #F56C6C 100%);
  transition: width 0.5s ease;
  border-radius: 3px;
}

.performance-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.performance-actions {
  display: flex;
  gap: 10px;
}

.indicator-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
}

.indicator-icon {
  font-size: 1.5rem;
  color: #409EFF;
}

.indicator-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
}

.indicator-label {
  font-size: 0.8rem;
  color: #b0bec5;
  font-weight: 500;
}

.indicator-value {
  font-size: 1rem;
  color: #ffffff;
  font-weight: 600;
}

.indicator-progress {
  width: 100%;
}
</style> 