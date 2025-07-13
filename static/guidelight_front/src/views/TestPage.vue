<template>
  <div class="test-page">
    <div class="test-header">
      <h1>GuideLight 功能测试页面</h1>
      <p>测试用户行为识别和碰撞概率显示功能</p>
    </div>
    
    <div class="test-content">
      <!-- 碰撞概率测试 -->
      <div class="test-section">
        <h2>碰撞概率显示测试</h2>
        <div class="collision-notice">
          <el-alert
            title="实时概率模拟"
            type="success"
            description="碰撞概率会基于时间平滑变化，适合静止状态的低风险范围（5-25%）"
            show-icon
            :closable="false"
          />
        </div>
        <div class="collision-test">
          <div class="collision-display">
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
          <div class="test-controls">
            <el-button @click="testCollisionData">获取碰撞数据</el-button>
            <el-button @click="mockHighRisk">模拟高风险</el-button>
            <el-button @click="mockLowRisk">模拟低风险</el-button>
            <div class="control-note">
              <p>🔄 自动更新：概率值会基于正弦波平滑变化</p>
            </div>
          </div>
          <div class="test-results">
            <h3>API响应数据：</h3>
            <pre>{{ JSON.stringify(lastCollisionData, null, 2) }}</pre>
          </div>
        </div>
      </div>
      
      <!-- 用户行为识别测试 -->
      <div class="test-section">
        <h2>用户行为识别测试</h2>
        <div class="behavior-notice">
          <el-alert
            title="静止状态模拟"
            type="info"
            description="当前模拟数据固定为静止状态，置信度会实时波动以展示数据更新效果"
            show-icon
            :closable="false"
          />
        </div>
        <div class="behavior-test">
          <div class="behavior-display">
            <UserBehaviorPanel />
          </div>
          <div class="test-controls">
            <el-button @click="testBehaviorData">获取行为数据</el-button>
            <el-button @click="mockWalking" disabled>模拟步行 (已禁用)</el-button>
            <el-button @click="mockDriving" disabled>模拟驾车 (已禁用)</el-button>
            <div class="control-note">
              <p>💡 提示：当前API固定返回静止状态，置信度会自动变化</p>
            </div>
          </div>
          <div class="test-results">
            <h3>API响应数据：</h3>
            <pre>{{ JSON.stringify(lastBehaviorData, null, 2) }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import UserBehaviorPanel from '../components/UserBehaviorPanel.vue'

// 响应式数据
const collisionProbability = ref(0)
const lastCollisionData = ref<any>(null)
const lastBehaviorData = ref<any>(null)

// 计算属性
const collisionLevel = computed(() => {
  if (collisionProbability.value > 80) return 'critical'
  if (collisionProbability.value > 60) return 'high'
  if (collisionProbability.value > 30) return 'medium'
  return 'low'
})

// 方法
const testCollisionData = async () => {
  try {
    const response = await fetch('http://localhost:5000/api/collision/risk')
    if (response.ok) {
      const data = await response.json()
      lastCollisionData.value = data
      
      if (data.success !== false) {
        const probabilityValue = data.max_probability || 0
        collisionProbability.value = Math.min(Math.max(probabilityValue, 0), 100)
        
        ElMessage.success(`碰撞概率: ${collisionProbability.value.toFixed(1)}%`)
      } else {
        ElMessage.warning('API返回错误状态')
      }
    } else {
      ElMessage.error('API调用失败')
    }
  } catch (error) {
    ElMessage.error('请求失败: ' + error)
    console.error('获取碰撞数据失败:', error)
  }
}

const mockHighRisk = () => {
  collisionProbability.value = 85
  lastCollisionData.value = {
    success: true,
    max_probability: 85,
    risk: {
      level: 'high',
      probability: 85,
      warning_message: '高风险：检测到潜在碰撞威胁',
      nearest_object: {
        type: '行人',
        distance: 3.2,
        confidence: 0.92
      }
    },
    is_mock: true
  }
  ElMessage.warning('模拟高风险状态')
}

const mockLowRisk = () => {
  collisionProbability.value = 12
  lastCollisionData.value = {
    success: true,
    max_probability: 12,
    risk: {
      level: 'low',
      probability: 12,
      warning_message: '低风险：环境安全',
      nearest_object: null
    },
    is_mock: true
  }
  ElMessage.success('模拟低风险状态')
}

const testBehaviorData = async () => {
  try {
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
      lastBehaviorData.value = data
      
      if (data.success && data.prediction) {
        ElMessage.success(`识别行为: ${data.prediction.predicted_class}`)
      }
    } else {
      ElMessage.error('API调用失败')
    }
  } catch (error) {
    ElMessage.error('请求失败: ' + error)
    console.error('获取行为数据失败:', error)
  }
}

const mockWalking = () => {
  lastBehaviorData.value = {
    success: true,
    prediction: {
      predicted_class: 'walking',
      confidence: 0.89,
      timestamp: Date.now()
    },
    is_mock: true
  }
  ElMessage.success('模拟步行状态')
}

const mockDriving = () => {
  lastBehaviorData.value = {
    success: true,
    prediction: {
      predicted_class: 'driving',
      confidence: 0.94,
      timestamp: Date.now()
    },
    is_mock: true
  }
  ElMessage.success('模拟驾车状态')
}

// 生命周期
onMounted(() => {
  // 自动获取一次数据
  testCollisionData()
  testBehaviorData()
})
</script>

<style scoped>
.test-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #0c1426 0%, #1a2332 50%, #2c3e50 100%);
  color: #ffffff;
  padding: 20px;
}

.test-header {
  text-align: center;
  margin-bottom: 40px;
  padding: 30px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.test-header h1 {
  margin: 0 0 10px 0;
  font-size: 2.5rem;
  background: linear-gradient(45deg, #409EFF, #67C23A);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.test-header p {
  margin: 0;
  font-size: 1.2rem;
  color: #b0bec5;
}

.test-content {
  display: grid;
  grid-template-columns: 1fr;
  gap: 30px;
  max-width: 1200px;
  margin: 0 auto;
}

.test-section {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  padding: 30px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.test-section h2 {
  margin: 0 0 20px 0;
  font-size: 1.5rem;
  color: #409EFF;
  border-bottom: 2px solid rgba(64, 158, 255, 0.3);
  padding-bottom: 10px;
}

.collision-test,
.behavior-test {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  align-items: start;
}

.collision-display {
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.behavior-display {
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  height: 500px;
}

.collision-warning {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 20px;
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
  font-size: 2rem;
}

.warning-content {
  display: flex;
  flex-direction: column;
  gap: 5px;
  flex: 1;
}

.warning-title {
  font-size: 1rem;
  color: #b0bec5;
}

.warning-value {
  font-size: 1.8rem;
  font-weight: bold;
}

.warning-meter {
  width: 120px;
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
}

.meter-fill {
  height: 100%;
  background: linear-gradient(90deg, #67C23A 0%, #E6A23C 50%, #F56C6C 100%);
  transition: width 0.5s ease;
  border-radius: 4px;
}

.test-controls {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.test-results {
  grid-column: 1 / -1;
  margin-top: 20px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.test-results h3 {
  margin: 0 0 15px 0;
  color: #409EFF;
}

.test-results pre {
  background: rgba(0, 0, 0, 0.5);
  border-radius: 8px;
  padding: 15px;
  overflow-x: auto;
  font-size: 0.9rem;
  color: #b0bec5;
  border: 1px solid rgba(255, 255, 255, 0.1);
  max-height: 300px;
  overflow-y: auto;
}

/* 提示信息样式 */
.collision-notice,
.behavior-notice {
  margin-bottom: 20px;
}

.control-note {
  margin-top: 15px;
  padding: 10px;
  background: rgba(64, 158, 255, 0.1);
  border-radius: 8px;
  border: 1px solid rgba(64, 158, 255, 0.2);
}

.control-note p {
  margin: 0;
  font-size: 0.9rem;
  color: #409EFF;
  text-align: center;
}

@media (max-width: 768px) {
  .collision-test,
  .behavior-test {
    grid-template-columns: 1fr;
  }
  
  .test-results {
    grid-column: 1;
  }
}
</style> 