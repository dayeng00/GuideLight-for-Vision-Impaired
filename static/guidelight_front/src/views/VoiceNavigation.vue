<template>
  <div class="voice-navigation-container">
    <el-card class="voice-nav-card">
      <template #header>
        <div class="card-header">
          <h3>语音导航</h3>
        </div>
      </template>
      
      <div class="voice-content">
        <div class="voice-status">
          <el-tag :type="recordingStatus.isRecording ? 'danger' : 'info'" size="large">
            {{ recordingStatus.isRecording ? '录制中...' : '等待录制' }}
          </el-tag>
          <div v-if="recordingStatus.isRecording" class="recording-time">
            {{ formatTime(recordingStatus.duration) }}
          </div>
        </div>
        
        <div class="voice-buttons">
          <el-button 
            type="primary" 
            :icon="recordingStatus.isRecording ? Plus : Microphone" 
            :disabled="isProcessing || !isAudioSupported"
            @click="handleRecordClick">
            {{ recordingStatus.isRecording ? '停止录制' : '开始录制' }}
          </el-button>
          
          <el-button 
            type="success" 
            icon="el-icon-location"
            :disabled="!recognizedText || isProcessing"
            @click="startNavigation">
            开始导航
          </el-button>
        </div>
        
        <div class="audio-visualizer" ref="visualizerRef"></div>
        
        <el-divider>识别结果</el-divider>
        
        <div class="recognition-result">
          <div v-if="isProcessing" class="processing">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>处理中...</span>
          </div>
          
          <div v-else-if="recognizedText" class="result-text">
            <p><strong>识别文本:</strong> {{ recognizedText }}</p>
            <p v-if="destination"><strong>导航目的地:</strong> {{ destination }}</p>
          </div>
          
          <div v-else class="no-result">
            <el-empty description="暂无识别结果" />
          </div>
        </div>
        
        <div v-if="errorMessage" class="error-message">
          <el-alert
            :title="errorMessage"
            type="error"
            show-icon
            :closable="false"
          />
        </div>
      </div>
    </el-card>
    
    <!-- 导航状态卡片 -->
    <el-card v-if="navigationActive" class="navigation-card">
      <template #header>
        <div class="card-header">
          <h3>导航状态</h3>
          <el-button type="danger" size="small" @click="stopNavigation">
            停止导航
          </el-button>
        </div>
      </template>
      
      <div class="navigation-content">
        <el-steps :active="navigationStep" finish-status="success" simple>
          <el-step title="开始" />
          <el-step title="进行中" />
          <el-step title="到达" />
        </el-steps>
        
        <div class="destination-info">
          <p><strong>目的地:</strong> {{ destination }}</p>
          <p><strong>预计时间:</strong> {{ estimatedTime || '计算中...' }}</p>
          <p><strong>距离:</strong> {{ distance || '计算中...' }}</p>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { Microphone, Plus, Loading } from '@element-plus/icons-vue'
import axios from 'axios'

// 音频处理
const audioProcessor = ref<any>(null)
const isAudioSupported = ref(true)
const isProcessing = ref(false)
const errorMessage = ref('')
const visualizerRef = ref<HTMLElement | null>(null)
const visualizerContext = ref<CanvasRenderingContext2D | null>(null)
const analyser = ref<AnalyserNode | null>(null)

// 识别结果
const recognizedText = ref('')
const destination = ref('')

// 导航信息
const navigationActive = ref(false)
const navigationStep = ref(1)
const estimatedTime = ref('')
const distance = ref('')

// 录制状态
const recordingStatus = reactive({
  isRecording: false,
  duration: 0
})

// 录制定时器
let recordingTimer: number | null = null

// 格式化时间
const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

// 初始化音频处理器
const initAudioProcessor = async () => {
  try {
    // 动态导入音频处理器
    const { AudioProcessor } = await import('../utils/audioProcessor')
    
    audioProcessor.value = new AudioProcessor({
      sampleRate: 16000,
      channels: 1
    })
    
    const initResult = await audioProcessor.value.initialize()
    isAudioSupported.value = initResult
    
    if (!initResult) {
      errorMessage.value = '您的浏览器不支持音频录制'
      ElMessage.warning('您的浏览器不支持音频录制')
    }
  } catch (error) {
    console.error('初始化音频处理器失败:', error)
    isAudioSupported.value = false
    errorMessage.value = '初始化音频处理器失败'
  }
}

// 初始化可视化器
const initVisualizer = () => {
  if (!visualizerRef.value) return
  
  const canvas = document.createElement('canvas')
  canvas.width = visualizerRef.value.clientWidth
  canvas.height = 100
  visualizerRef.value.appendChild(canvas)
  
  visualizerContext.value = canvas.getContext('2d')
  
  if (!visualizerContext.value) {
    console.error('无法获取Canvas上下文')
    return
  }
}

// 更新可视化器
const updateVisualizer = () => {
  if (!analyser.value || !visualizerContext.value) return
  
  const canvas = visualizerContext.value.canvas
  const width = canvas.width
  const height = canvas.height
  
  const bufferLength = analyser.value.frequencyBinCount
  const dataArray = new Uint8Array(bufferLength)
  analyser.value.getByteFrequencyData(dataArray)
  
  visualizerContext.value.clearRect(0, 0, width, height)
  visualizerContext.value.fillStyle = '#f0f0f0'
  visualizerContext.value.fillRect(0, 0, width, height)
  
  const barWidth = (width / bufferLength) * 2.5
  let x = 0
  
  for (let i = 0; i < bufferLength; i++) {
    const barHeight = (dataArray[i] / 255) * height
    
    visualizerContext.value.fillStyle = `rgb(${dataArray[i]}, 50, 100)`
    visualizerContext.value.fillRect(x, height - barHeight, barWidth, barHeight)
    
    x += barWidth + 1
  }
  
  if (recordingStatus.isRecording) {
    requestAnimationFrame(updateVisualizer)
  }
}

// 处理录制按钮点击
const handleRecordClick = async () => {
  if (!audioProcessor.value) {
    ElMessage.error('音频处理器未初始化')
    return
  }
  
  if (recordingStatus.isRecording) {
    await stopRecording()
  } else {
    await startRecording()
  }
}

// 开始录制
const startRecording = async () => {
  if (!audioProcessor.value) return
  
  try {
    const result = await audioProcessor.value.startRecording()
    
    if (result) {
      recordingStatus.isRecording = true
      recordingStatus.duration = 0
      
      // 创建分析器节点
      analyser.value = await audioProcessor.value.createVisualizer()
      
      // 开始定时器
      recordingTimer = window.setInterval(() => {
        recordingStatus.duration += 1
        
        // 限制录制时间（最多60秒）
        if (recordingStatus.duration >= 60) {
          stopRecording()
        }
      }, 1000)
      
      // 开始可视化
      updateVisualizer()
      
      // 清除之前的结果
      recognizedText.value = ''
      destination.value = ''
      errorMessage.value = ''
      
      ElMessage.success('开始录制')
    } else {
      ElMessage.error('无法开始录制')
    }
  } catch (error) {
    console.error('开始录制失败:', error)
    ElMessage.error('开始录制失败')
  }
}

// 停止录制
const stopRecording = async () => {
  if (!audioProcessor.value) return
  
  try {
    isProcessing.value = true
    
    // 停止定时器
    if (recordingTimer) {
      clearInterval(recordingTimer)
      recordingTimer = null
    }
    
    const recordingResult = await audioProcessor.value.stopRecording()
    recordingStatus.isRecording = false
    
    if (!recordingResult) {
      ElMessage.warning('没有录制到音频数据')
      isProcessing.value = false
      return
    }
    
    // 将音频数据发送到后端处理
    await processAudio(recordingResult)
    
  } catch (error) {
    console.error('停止录制失败:', error)
    ElMessage.error('停止录制失败')
    isProcessing.value = false
  }
}

// 处理音频数据
const processAudio = async (recordingResult: any) => {
  try {
    console.log('开始处理录制的音频数据...');
    
    if (!recordingResult) {
      console.error('录制结果为空');
      ElMessage.error('录制结果为空');
      isProcessing.value = false;
      return;
    }
    
    console.log(`录制数据: 时长 ${recordingResult.duration.toFixed(2)}秒, ` +
               `采样率 ${recordingResult.sampleRate}Hz, 声道数 ${recordingResult.channels}`);
    console.log(`音频数据大小: ${recordingResult.audioData.byteLength} 字节`);
    
    // 转换为WAV格式
    console.log('开始转换为WAV格式...');
    const wavBlob = await convertToWav(recordingResult);
    console.log(`WAV转换完成，大小: ${wavBlob.size} 字节, 类型: ${wavBlob.type}`);
    
    // 创建FormData
    const formData = new FormData();
    formData.append('audio_file', wavBlob, 'recording.wav');
    
    // 记录发送时间
    const startTime = Date.now();
    console.log('开始发送音频数据到服务器...');
    
    // 发送到后端
    try {
      const response = await axios.post('/api/navigation/voice_navigate', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        // 添加超时设置
        timeout: 30000,
        // 添加上传进度监听
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            console.log(`上传进度: ${percentCompleted}%`);
          }
        }
      });
      
      const endTime = Date.now();
      console.log(`服务器响应时间: ${endTime - startTime}ms`);
      
      const data = response.data;
      console.log('服务器响应:', data);
      
      if (data.success) {
        recognizedText.value = data.recognized_text || '未能识别语音';
        destination.value = data.destination || '';
        ElMessage.success(data.message || '处理成功');
        
        // 如果识别结果为空但服务器返回成功，显示提示
        if (!data.recognized_text) {
          ElMessage.warning('语音识别结果为空，请重试');
        }
      } else {
        errorMessage.value = data.message || '处理失败';
        ElMessage.error(data.message || '处理失败');
        console.error('服务器处理失败:', data.error || '未知错误');
      }
    } catch (error: any) {
      console.error('发送请求失败:', error);
      
      // 检查是否是网络错误
      if (error.message.includes('Network Error')) {
        ElMessage.error('网络错误，请检查网络连接');
        errorMessage.value = '网络错误，请检查网络连接';
      } else if (error.code === 'ECONNABORTED') {
        ElMessage.error('请求超时，服务器响应时间过长');
        errorMessage.value = '请求超时，服务器响应时间过长';
      } else {
        ElMessage.error(error.message || '处理音频失败');
        errorMessage.value = error.message || '处理音频失败';
      }
    }
  } catch (error: any) {
    console.error('处理音频失败:', error);
    errorMessage.value = error.message || '处理音频失败';
    ElMessage.error(error.message || '处理音频失败');
  } finally {
    isProcessing.value = false;
  }
}

// 将录制结果转换为WAV格式
const convertToWav = async (recordingResult: any): Promise<Blob> => {
  console.log('开始将录制结果转换为WAV格式...');
  
  try {
    // 将采样率转换为16000Hz的PCM数据
    console.log('开始转换为PCM格式...');
    const pcmData = await audioProcessor.value.convertToPCM(recordingResult);
    console.log(`PCM转换完成，数据大小: ${pcmData.byteLength} 字节`);
    
    // 检查PCM数据是否有效
    if (!pcmData || pcmData.byteLength === 0) {
      console.error('PCM数据无效或为空');
      throw new Error('PCM数据无效或为空');
    }
    
    // 创建WAV文件头
    console.log('创建WAV文件头...');
    const wavHeader = createWavHeader(pcmData.byteLength, 16000, 1, 16);
    console.log(`WAV文件头创建完成，大小: ${wavHeader.byteLength} 字节`);
    
    // 检查WAV文件头是否有效
    if (!wavHeader || wavHeader.byteLength === 0) {
      console.error('WAV文件头无效或为空');
      throw new Error('WAV文件头无效或为空');
    }
    
    // 合并头部和数据
    console.log('合并WAV文件头和PCM数据...');
    const wavFile = new Blob([wavHeader, pcmData], { type: 'audio/wav' });
    console.log(`WAV文件创建完成，总大小: ${wavFile.size} 字节`);
    
    // 验证WAV文件
    if (!wavFile || wavFile.size <= wavHeader.byteLength) {
      console.error('WAV文件无效或只包含头部');
      throw new Error('WAV文件无效或只包含头部');
    }
    
    // 可选：在开发环境中创建一个下载链接，方便调试
    if (process.env.NODE_ENV === 'development') {
      const url = URL.createObjectURL(wavFile);
      console.log('开发环境: 可以下载WAV文件进行调试:', url);
      // 不要忘记在适当的时候调用 URL.revokeObjectURL(url)
    }
    
    return wavFile;
  } catch (error) {
    console.error('WAV转换失败:', error);
    
    // 创建一个空的WAV文件作为后备方案
    console.log('创建空的WAV文件作为后备方案...');
    const sampleRate = 16000;
    const channels = 1;
    const bitsPerSample = 16;
    
    // 创建1秒的静音PCM数据
    const silentPcmLength = sampleRate * channels * (bitsPerSample / 8);
    const silentPcm = new ArrayBuffer(silentPcmLength);
    
    // 创建WAV头
    const wavHeader = createWavHeader(silentPcmLength, sampleRate, channels, bitsPerSample);
    
    // 合并为WAV文件
    const silentWav = new Blob([wavHeader, silentPcm], { type: 'audio/wav' });
    console.log(`已创建静音WAV文件，大小: ${silentWav.size} 字节`);
    
    return silentWav;
  }
}

// 创建WAV文件头
const createWavHeader = (
  pcmDataLength: number,
  sampleRate: number,
  numChannels: number,
  bitsPerSample: number
): ArrayBuffer => {
  const dataLength = pcmDataLength
  const buffer = new ArrayBuffer(44)
  const view = new DataView(buffer)
  
  // RIFF标识符
  writeString(view, 0, 'RIFF')
  // 文件长度
  view.setUint32(4, 36 + dataLength, true)
  // WAVE标识符
  writeString(view, 8, 'WAVE')
  // fmt子块标识符
  writeString(view, 12, 'fmt ')
  // 子块长度
  view.setUint32(16, 16, true)
  // 音频格式（PCM = 1）
  view.setUint16(20, 1, true)
  // 通道数
  view.setUint16(22, numChannels, true)
  // 采样率
  view.setUint32(24, sampleRate, true)
  // 字节率
  view.setUint32(28, sampleRate * numChannels * bitsPerSample / 8, true)
  // 块对齐
  view.setUint16(32, numChannels * bitsPerSample / 8, true)
  // 每个样本的位数
  view.setUint16(34, bitsPerSample, true)
  // data子块标识符
  writeString(view, 36, 'data')
  // 数据长度
  view.setUint32(40, dataLength, true)
  
  return buffer
}

// 写入字符串到DataView
const writeString = (view: DataView, offset: number, string: string) => {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i))
  }
}

// 开始导航
const startNavigation = async () => {
  if (!destination.value) {
    ElMessage.warning('请先指定导航目的地')
    return
  }
  
  try {
    // 调用导航API
    const response = await axios.post('/api/navigation/start', {
      destination: destination.value
    })
    
    const data = response.data
    
    if (data.success) {
      navigationActive.value = true
      navigationStep.value = 1
      estimatedTime.value = data.estimated_time || '15分钟'
      distance.value = data.distance || '1.2公里'
      
      ElMessage.success(data.message)
      
      // 模拟导航进度
      setTimeout(() => {
        navigationStep.value = 2
      }, 3000)
    } else {
      ElMessage.error(data.message || '导航启动失败')
    }
  } catch (error: any) {
    console.error('启动导航失败:', error)
    ElMessage.error(error.message || '启动导航失败')
  }
}

// 停止导航
const stopNavigation = async () => {
  try {
    const response = await axios.post('/api/navigation/stop')
    const data = response.data
    
    if (data.success) {
      navigationActive.value = false
      ElMessage.success(data.message)
    } else {
      ElMessage.error(data.message || '停止导航失败')
    }
  } catch (error: any) {
    console.error('停止导航失败:', error)
    ElMessage.error(error.message || '停止导航失败')
  }
}

// 组件挂载
onMounted(async () => {
  await initAudioProcessor()
  initVisualizer()
})

// 组件卸载
onBeforeUnmount(() => {
  // 清理资源
  if (recordingTimer) {
    clearInterval(recordingTimer)
  }
  
  if (audioProcessor.value) {
    audioProcessor.value.destroy()
  }
  
  // 停止导航
  if (navigationActive.value) {
    stopNavigation()
  }
})
</script>

<style scoped>
.voice-navigation-container {
  padding: 20px;
}

.voice-nav-card {
  margin-bottom: 20px;
}

.navigation-card {
  margin-top: 20px;
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

.voice-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.voice-status {
  display: flex;
  align-items: center;
  gap: 10px;
}

.recording-time {
  font-family: monospace;
  font-size: 18px;
}

.voice-buttons {
  display: flex;
  gap: 15px;
}

.audio-visualizer {
  width: 100%;
  height: 100px;
  background-color: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}

.recognition-result {
  min-height: 100px;
  padding: 10px;
  border-radius: 4px;
  background-color: #f9f9f9;
}

.processing {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  height: 100px;
}

.result-text {
  line-height: 1.6;
}

.result-text p {
  margin: 5px 0;
}

.error-message {
  margin-top: 10px;
}

.navigation-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.destination-info {
  padding: 10px;
  background-color: #f9f9f9;
  border-radius: 4px;
  line-height: 1.6;
}

.destination-info p {
  margin: 5px 0;
}
</style> 