<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { 
  Guide, 
  VideoCamera, 
  Location, 
  Monitor, 
  Headset, 
  Opportunity, 
  ArrowRight 
} from '@element-plus/icons-vue'

const router = useRouter()
const activeSection = ref(0)
const animationActive = ref(false)

// 功能特点列表
const features = [
  {
    title: '视频监控',
    description: '实时视频监控系统，支持多种视觉算法，提供人像追踪、特征点检测、手势识别等功能',
    icon: VideoCamera,
    color: '#409EFF'
  },
  {
    title: '位置追踪',
    description: '实时追踪视障人士位置，提供精确的定位服务，支持历史轨迹回放和紧急定位',
    icon: Location,
    color: '#67C23A'
  },
  {
    title: '综合监控',
    description: '将视频和位置数据整合在一起，提供全面的监控视图，让您随时了解视障人士的安全状况',
    icon: Monitor,
    color: '#E6A23C'
  },
  {
    title: '语音反馈',
    description: '智能语音提示系统，帮助视障人士识别周围环境，避开障碍物，提高出行安全',
    icon: Headset,
    color: '#F56C6C'
  },
  {
    title: '智能辅助',
    description: '基于AI的智能辅助功能，包括物体识别、场景理解和危险预警等多种服务',
    icon: Opportunity,
    color: '#909399'
  }
]

// 动画控制
let animationTimer: any = null

const startAnimation = () => {
  animationActive.value = true
  clearInterval(animationTimer)
  animationTimer = setInterval(() => {
    activeSection.value = (activeSection.value + 1) % features.length
  }, 5000)
}

const stopAnimation = () => {
  clearInterval(animationTimer)
  animationActive.value = false
}

const setActiveSection = (index: number) => {
  activeSection.value = index
  stopAnimation()
}

// 导航到主页
const navigateToDashboard = () => {
  router.push('/dashboard')
}

onMounted(() => {
  startAnimation()
})

onUnmounted(() => {
  stopAnimation()
})
</script>

<template>
  <div class="introduction-container">
    <!-- 背景元素 -->
    <div class="background-elements">
      <div class="floating-circle circle-1"></div>
      <div class="floating-circle circle-2"></div>
      <div class="floating-circle circle-3"></div>
      <div class="floating-circle circle-4"></div>
    </div>
    
    <!-- 主内容区 -->
    <div class="content-container">
      <!-- 标题部分 -->
      <div class="title-section">
        <div class="logo-container">
          <el-icon class="logo-icon"><Guide /></el-icon>
        </div>
        <h1 class="main-title">盲人安全实时检测系统</h1>
        <p class="subtitle">为视障人士提供安全、便捷的出行保障</p>
      </div>
      
      <!-- 主要特点展示 -->
      <div class="features-section">
        <div class="features-nav">
          <div 
            v-for="(feature, index) in features" 
            :key="index"
            class="feature-nav-item"
            :class="{ 'active': activeSection === index }"
            @click="setActiveSection(index)"
          >
            <el-icon :style="{ color: feature.color }">
              <component :is="feature.icon" />
            </el-icon>
            <span>{{ feature.title }}</span>
          </div>
        </div>
        
        <div class="feature-display">
          <transition name="fade" mode="out-in">
            <div 
              :key="activeSection"
              class="feature-card"
              :style="{ borderColor: features[activeSection].color }"
            >
              <div class="feature-icon" :style="{ backgroundColor: features[activeSection].color }">
                <el-icon>
                  <component :is="features[activeSection].icon" />
                </el-icon>
              </div>
              <div class="feature-content">
                <h3>{{ features[activeSection].title }}</h3>
                <p>{{ features[activeSection].description }}</p>
              </div>
            </div>
          </transition>
        </div>
      </div>
      
      <!-- 简介部分 -->
      <div class="description-section">
        <div class="description-card">
          <h2>关于本系统</h2>
          <p>
            盲人安全实时检测系统是一套专为视障人士及其家人设计的安全辅助系统。
            通过先进的计算机视觉技术和定位服务，为视障人士提供实时环境感知和安全保障。
            同时，家人可以通过监控界面实时了解视障人士的位置和周围环境，确保他们的安全。
          </p>
          <p>
            系统采用最新的人工智能技术，包括物体检测、场景理解、特征点追踪等多种算法，
            能够有效识别潜在危险，并通过语音提示帮助视障人士避开障碍物，安全到达目的地。
          </p>
        </div>
      </div>
      
      <!-- 进入系统按钮 -->
      <div class="action-section">
        <el-button 
          type="primary" 
          size="large" 
          round 
          @click="navigateToDashboard" 
          class="enter-button"
        >
          进入系统
          <el-icon class="el-icon--right"><ArrowRight /></el-icon>
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.introduction-container {
  min-height: 100vh;
  width: 100%;
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8f0 100%);
  color: #333;
  display: flex;
  justify-content: center;
  align-items: center;
}

/* 背景动画元素 */
.background-elements {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 0;
  overflow: hidden;
}

.floating-circle {
  position: absolute;
  border-radius: 50%;
  opacity: 0.15;
}

.circle-1 {
  width: 300px;
  height: 300px;
  background: linear-gradient(45deg, #409EFF, #67C23A);
  top: -100px;
  left: -50px;
  animation: float-1 15s infinite linear;
}

.circle-2 {
  width: 200px;
  height: 200px;
  background: linear-gradient(135deg, #E6A23C, #F56C6C);
  bottom: -50px;
  right: 100px;
  animation: float-2 20s infinite linear;
}

.circle-3 {
  width: 150px;
  height: 150px;
  background: linear-gradient(225deg, #67C23A, #409EFF);
  top: 70%;
  left: 10%;
  animation: float-3 18s infinite linear;
}

.circle-4 {
  width: 120px;
  height: 120px;
  background: linear-gradient(315deg, #F56C6C, #409EFF);
  top: 20%;
  right: 10%;
  animation: float-4 25s infinite linear;
}

@keyframes float-1 {
  0% { transform: translate(0, 0) rotate(0deg); }
  50% { transform: translate(30px, 50px) rotate(180deg); }
  100% { transform: translate(0, 0) rotate(360deg); }
}

@keyframes float-2 {
  0% { transform: translate(0, 0) rotate(0deg); }
  50% { transform: translate(-40px, -30px) rotate(180deg); }
  100% { transform: translate(0, 0) rotate(360deg); }
}

@keyframes float-3 {
  0% { transform: translate(0, 0) rotate(0deg); }
  50% { transform: translate(20px, -40px) rotate(180deg); }
  100% { transform: translate(0, 0) rotate(360deg); }
}

@keyframes float-4 {
  0% { transform: translate(0, 0) rotate(0deg); }
  50% { transform: translate(-30px, 30px) rotate(180deg); }
  100% { transform: translate(0, 0) rotate(360deg); }
}

/* 主内容区样式 */
.content-container {
  position: relative;
  z-index: 1;
  width: 90%;
  max-width: 1200px;
  padding: 40px 0;
  display: flex;
  flex-direction: column;
  gap: 40px;
}

/* 标题部分 */
.title-section {
  text-align: center;
  margin-bottom: 20px;
}

.logo-container {
  margin: 0 auto 20px;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, #409EFF, #67C23A);
  display: flex;
  justify-content: center;
  align-items: center;
  box-shadow: 0 10px 30px rgba(64, 158, 255, 0.2);
}

.logo-icon {
  font-size: 40px;
  color: white;
}

.main-title {
  font-size: 36px;
  font-weight: 600;
  margin: 0;
  color: #333;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.subtitle {
  font-size: 18px;
  color: #666;
  margin: 10px 0 0;
}

/* 特点展示部分 */
.features-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.features-nav {
  display: flex;
  justify-content: center;
  gap: 10px;
  flex-wrap: wrap;
}

.feature-nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 15px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.feature-nav-item:hover {
  background-color: rgba(255, 255, 255, 0.7);
  transform: translateY(-2px);
}

.feature-nav-item.active {
  background-color: white;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transform: translateY(-3px);
}

.feature-nav-item el-icon {
  font-size: 24px;
  margin-bottom: 5px;
}

.feature-nav-item span {
  font-size: 14px;
  font-weight: 500;
}

.feature-display {
  padding: 20px 0;
  min-height: 250px;
}

.feature-card {
  display: flex;
  background-color: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.08);
  border-left: 5px solid;
  transition: all 0.3s ease;
}

.feature-icon {
  padding: 30px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.feature-icon el-icon {
  font-size: 40px;
  color: white;
}

.feature-content {
  padding: 30px;
  flex: 1;
}

.feature-content h3 {
  margin: 0 0 15px;
  font-size: 24px;
  font-weight: 600;
}

.feature-content p {
  margin: 0;
  font-size: 16px;
  line-height: 1.6;
  color: #666;
}

/* 简介部分 */
.description-section {
  margin: 20px 0;
}

.description-card {
  background-color: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.08);
}

.description-card h2 {
  margin: 0 0 20px;
  font-size: 24px;
  font-weight: 600;
  color: #333;
}

.description-card p {
  margin: 0 0 15px;
  font-size: 16px;
  line-height: 1.7;
  color: #666;
}

/* 操作部分 */
.action-section {
  text-align: center;
  margin: 20px 0;
}

.enter-button {
  padding: 12px 40px;
  font-size: 18px;
  transition: all 0.3s ease;
}

.enter-button:hover {
  transform: translateY(-3px);
  box-shadow: 0 10px 20px rgba(64, 158, 255, 0.3);
}

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s ease, transform 0.5s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

/* 响应式调整 */
@media (max-width: 768px) {
  .content-container {
    padding: 20px;
  }
  
  .main-title {
    font-size: 28px;
  }
  
  .subtitle {
    font-size: 16px;
  }
  
  .feature-card {
    flex-direction: column;
  }
  
  .feature-icon {
    padding: 20px;
  }
  
  .feature-content {
    padding: 20px;
  }
  
  .feature-content h3 {
    font-size: 20px;
  }
}
</style> 