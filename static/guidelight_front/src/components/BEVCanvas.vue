<template>
  <div class="bev-canvas-container" ref="container">
    <!-- 显示真实的BEV图像 -->
    <div v-if="bevImageData" class="bev-image-display">
      <img 
        :src="bevImageData" 
        :width="width" 
        :height="height"
        @mousemove="handleMouseMove"
        @click="handleClick"
        alt="BEV Environment View"
      />
    </div>
    
    <!-- 如果没有数据，显示Canvas -->
    <canvas 
      v-else
      ref="canvas" 
      :width="width" 
      :height="height"
      @mousemove="handleMouseMove"
      @click="handleClick"
    ></canvas>
    
    <!-- 数据覆盖层 -->
    <div class="bev-overlay">
      <div class="detected-objects" v-if="detectedObjects.length > 0">
        <h4>检测对象</h4>
        <div 
          v-for="obj in detectedObjects" 
          :key="obj.id"
          class="object-item"
          :style="{ color: `rgb(${obj.color?.join(',') || '255,255,255'})` }"
        >
          <span class="object-name">{{ obj.name }}</span>
          <span class="object-distance">{{ obj.distance.toFixed(1) }}mm</span>
          <span class="object-confidence">{{ (obj.confidence * 100).toFixed(1) }}%</span>
        </div>
      </div>
      
      <div class="performance-info" v-if="performanceData">
        <h4>性能统计</h4>
        <div class="perf-item">
          <span>处理时间: {{ (performanceData.processing_time * 1000).toFixed(1) }}ms</span>
        </div>
        <div class="perf-item">
          <span>帧数: {{ performanceData.frame_count }}</span>
        </div>
        <div class="perf-item">
          <span>追踪对象: {{ performanceData.tracked_objects || 0 }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
// @ts-ignore
import { environmentApi } from '../api'

// Props
interface Props {
  mode?: '2D' | '3D'
  width?: number
  height?: number
  autoUpdate?: boolean
  updateInterval?: number
}

const props = withDefaults(defineProps<Props>(), {
  mode: '2D',
  width: 830,
  height: 830,
  autoUpdate: true,
  updateInterval: 100  // 100ms更新间隔
})

// Emits
const emit = defineEmits<{
  'position-change': [position: { x: number; y: number; distance: number; angle: number }]
  'objects-detected': [objects: any[]]
  'collision-risk': [risk: number]
}>()

// Refs
const container = ref<HTMLDivElement>()
const canvas = ref<HTMLCanvasElement>()

// 环境感知数据
const bevImageData = ref<string>('')
const detectedObjects = ref<any[]>([])
const performanceData = ref<any>(null)
const collisionProbability = ref<number>(0)

// 更新相关
let updateTimer: number | null = null
let ctx: CanvasRenderingContext2D | null = null

// 鼠标位置
const mouseX = ref(0)
const mouseY = ref(0)

// 初始化Canvas（备用）
const initCanvas = () => {
  if (!canvas.value) return
  
  ctx = canvas.value.getContext('2d')
  if (!ctx) return
  
  // 设置默认样式
  ctx.strokeStyle = '#409EFF'
  ctx.fillStyle = '#409EFF'
  ctx.lineWidth = 2
}

// 绘制备用Canvas内容
const drawFallbackCanvas = () => {
  if (!ctx || !canvas.value) return
  
  const centerX = props.width / 2
  const centerY = props.height / 2
  
  // 清空画布
  ctx.clearRect(0, 0, props.width, props.height)
  
  // 绘制背景
  ctx.fillStyle = '#1a1a1a'
  ctx.fillRect(0, 0, props.width, props.height)
  
  // 绘制网格
  ctx.strokeStyle = 'rgba(64, 158, 255, 0.2)'
  ctx.lineWidth = 1
  
  const gridSize = 50
  for (let x = 0; x <= props.width; x += gridSize) {
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, props.height)
    ctx.stroke()
  }
  
  for (let y = 0; y <= props.height; y += gridSize) {
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(props.width, y)
    ctx.stroke()
  }
  
  // 绘制中心点
  ctx.fillStyle = '#00ff00'
  ctx.beginPath()
  ctx.arc(centerX, centerY, 5, 0, 2 * Math.PI)
  ctx.fill()
  
  // 绘制距离圆圈
  ctx.strokeStyle = '#409EFF'
  ctx.lineWidth = 2
  const distances = [50, 100, 150, 200] // 对应不同距离
  
  distances.forEach(radius => {
    ctx!.beginPath()
    ctx!.arc(centerX, centerY, radius, 0, 2 * Math.PI)
    ctx!.stroke()
  })
  
  // 显示无数据提示
  ctx.fillStyle = '#ffffff'
  ctx.font = '16px Arial'
  ctx.textAlign = 'center'
  ctx.fillText('等待环境感知数据...', centerX, centerY + 250)
}

// 获取环境感知数据
const fetchEnvironmentData = async () => {
  try {
    const response = await environmentApi.getLatestResult()
    
    if (response.success && response.result) {
      const result = response.result
      
      // 更新BEV图像
      if (result.bev_image_base64) {
        bevImageData.value = `data:image/jpeg;base64,${result.bev_image_base64}`
      }
      
      // 更新检测对象
      if (result.detected_objects) {
        detectedObjects.value = result.detected_objects
        emit('objects-detected', result.detected_objects)
      }
      
      // 更新碰撞概率
      if (typeof result.collision_probability === 'number') {
        collisionProbability.value = result.collision_probability
        emit('collision-risk', result.collision_probability)
      }
      
      // 更新性能数据
      performanceData.value = {
        processing_time: result.processing_time || 0,
        frame_count: result.frame_count || 0,
        tracked_objects: result.detected_objects?.length || 0
      }
    }
  } catch (error: any) {
    // 检查是否是404错误（暂无处理结果）
    if (error.response?.status === 404 || error.message?.includes('暂无处理结果')) {
      // 404错误是正常的，表示还没有处理结果，不需要记录为错误
      // 如果没有BEV图像数据，显示备用Canvas
      if (!bevImageData.value) {
        drawFallbackCanvas()
      }
      return
    }
    
    // 其他错误才记录为警告
    console.warn('获取环境感知数据失败:', error)
    
    // 如果获取数据失败，显示备用Canvas
    if (!bevImageData.value) {
      drawFallbackCanvas()
    }
  }
}

// 启动自动更新
const startAutoUpdate = () => {
  if (props.autoUpdate && !updateTimer) {
    updateTimer = setInterval(fetchEnvironmentData, props.updateInterval)
  }
}

// 停止自动更新
const stopAutoUpdate = () => {
  if (updateTimer) {
    clearInterval(updateTimer)
    updateTimer = null
  }
}

// 处理鼠标移动
const handleMouseMove = (event: MouseEvent) => {
  const rect = container.value?.getBoundingClientRect()
  if (!rect) return
  
  mouseX.value = event.clientX - rect.left
  mouseY.value = event.clientY - rect.top
  
  // 计算相对于中心的坐标
  const centerX = props.width / 2
  const centerY = props.height / 2
  const scale = 100 // 每100像素代表1米
  
  const x = (mouseX.value - centerX) / scale
  const y = -(mouseY.value - centerY) / scale
  
  // 计算距离和角度
  const distance = Math.sqrt(x * x + y * y)
  const angle = Math.atan2(y, x) * 180 / Math.PI
  
  emit('position-change', { x, y, distance, angle })
}

// 处理点击事件
const handleClick = (event: MouseEvent) => {
  // 可以在这里添加点击处理逻辑
  console.log('BEV clicked at:', mouseX.value, mouseY.value)
}

// 手动触发数据更新
const updateData = async () => {
  await fetchEnvironmentData()
}

// 启动环境感知处理
const startProcessing = async () => {
  try {
    await environmentApi.start()
    startAutoUpdate()
  } catch (error) {
    console.error('启动环境感知失败:', error)
  }
}

// 停止环境感知处理
const stopProcessing = async () => {
  try {
    await environmentApi.stop()
    stopAutoUpdate()
  } catch (error) {
    console.error('停止环境感知失败:', error)
  }
}

// 监听mode变化
watch(() => props.mode, () => {
  if (!bevImageData.value) {
    drawFallbackCanvas()
  }
})

// 监听autoUpdate变化
watch(() => props.autoUpdate, (newVal) => {
  if (newVal) {
    startAutoUpdate()
  } else {
    stopAutoUpdate()
  }
})

// 组件挂载
onMounted(() => {
  initCanvas()
  drawFallbackCanvas()
  
  if (props.autoUpdate) {
    startAutoUpdate()
  }
  
  // 初始数据获取
  fetchEnvironmentData()
})

// 组件卸载
onBeforeUnmount(() => {
  stopAutoUpdate()
})

// 暴露方法给父组件
defineExpose({
  updateData,
  startProcessing,
  stopProcessing,
  fetchEnvironmentData
})
</script>

<style scoped>
.bev-canvas-container {
  position: relative;
  display: inline-block;
}

.bev-image-display {
  position: relative;
}

.bev-image-display img {
  display: block;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.bev-overlay {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(0, 0, 0, 0.8);
  border-radius: 8px;
  padding: 10px;
  min-width: 200px;
  max-height: 80%;
  overflow-y: auto;
  backdrop-filter: blur(5px);
}

.detected-objects h4,
.performance-info h4 {
  margin: 0 0 10px 0;
  color: #409EFF;
  font-size: 14px;
  font-weight: 600;
}

.object-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  font-size: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.object-item:last-child {
  border-bottom: none;
}

.object-name {
  font-weight: 600;
  flex: 1;
}

.object-distance {
  margin: 0 8px;
  color: #67C23A;
}

.object-confidence {
  color: #E6A23C;
}

.performance-info {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
}

.perf-item {
  padding: 2px 0;
  font-size: 12px;
  color: #b0bec5;
}

canvas {
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}
</style> 