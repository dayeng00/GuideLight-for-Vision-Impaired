import axios from 'axios'

// 修复API基础URL - 指向正确的后端端口
const API_BASE_URL = 'http://localhost:5000'

// 创建axios实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证token等
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    console.error('API请求失败:', error)
    return Promise.reject(error)
  }
)

// 用户相关API
export const userApi = {
  login: (username: string, password: string) => 
    apiClient.post('/login', { username, password }),
  
  register: (username: string, password: string, category: string) => 
    apiClient.post('/register', { username, password, category }),
  
  getRecord: (username: string) => 
    apiClient.post('/record', { username })
}

// 视频流API
export const videoApi = {
  startCamera: (cameraType: string) => 
    apiClient.post(`/${cameraType}/start_cameras`),
  
  stopCamera: (cameraType: string) => 
    apiClient.post(`/${cameraType}/stop_cameras`),
  
  getVideoStreamUrl: (cameraType: string, side?: string) => {
    const baseUrl = `${API_BASE_URL}/${cameraType}/video_feed`
    return side ? `${baseUrl}_${side}` : baseUrl
  }
}

// 位置相关API
export const locationApi = {
  getCurrentLocation: () => 
    apiClient.get('/location/current'),
  
  getLocationHistory: (limit: number = 50) => 
    apiClient.get(`/location/history?limit=${limit}`),
  
  addLocation: (lat: number, lng: number) => 
    apiClient.post('/location/add', { lat, lng }),
  
  setCurrentLocation: (lat: number, lng: number) => 
    apiClient.post('/location/set', { lat, lng }),
  
  deleteLocation: (locationId: number) => 
    apiClient.delete(`/location/delete/${locationId}`),
  
  setSpeed: (speed: number) => 
    apiClient.post('/location/speed', { speed }),
  
  setDestination: (lat: number, lng: number) => 
    apiClient.post('/location/destination', { lat, lng })
}

// 新增：YOLO目标检测API
export const yoloApi = {
  processFrame: () => 
    apiClient.post('/yolo/process'),
  
  getStatus: () => 
    apiClient.get('/yolo/status')
}

// 新增：3D音频处理API
export const audioApi = {
  process3DAudio: (azimuthPitchData: any[], audioType: string = 'beep') => 
    apiClient.post('/audio/3d', { 
      azimuth_pitch_data: azimuthPitchData, 
      audio_type: audioType 
    }),
  
  getStatus: () => 
    apiClient.get('/audio/status')
}

// 语音识别API
export const speechApi = {
  // 语音识别
  recognize: async (audioData: string, sampleRate: number = 16000) => {
    const response = await fetch('/api/speech/recognize', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        audio_data: audioData,
        sample_rate: sampleRate
      })
    })
    
    if (!response.ok) {
      throw new Error(`语音识别失败: ${response.status}`)
    }
    
    return response.json()
  },
  
  // 获取语音识别状态
  getStatus: async () => {
    const response = await fetch('/api/speech/status')
    
    if (!response.ok) {
      throw new Error(`获取状态失败: ${response.status}`)
    }
    
    return response.json()
  }
}

// 环境感知API
export const environmentApi = {
  // 处理环境感知帧数据
  processFrame: async () => {
    const response = await fetch('/api/environment/process_frame', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    })
    
    if (!response.ok) {
      throw new Error(`环境感知处理失败: ${response.status}`)
    }
    
    return response.json()
  },

  // 获取环境感知状态
  getStatus: async () => {
    const response = await fetch('/api/environment/status')
    
    if (!response.ok) {
      throw new Error(`获取环境感知状态失败: ${response.status}`)
    }
    
    return response.json()
  },

  // 启动环境感知处理
  start: async () => {
    const response = await fetch('/api/environment/start', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    })
    
    if (!response.ok) {
      throw new Error(`启动环境感知失败: ${response.status}`)
    }
    
    return response.json()
  },

  // 停止环境感知处理
  stop: async () => {
    const response = await fetch('/api/environment/stop', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    })
    
    if (!response.ok) {
      throw new Error(`停止环境感知失败: ${response.status}`)
    }
    
    return response.json()
  },

  // 获取最新环境感知结果
  getLatestResult: async () => {
    const response = await fetch('/api/environment/latest_result')
    
    if (!response.ok) {
      throw new Error(`获取环境感知结果失败: ${response.status}`)
    }
    
    return response.json()
  },

  // 分析当前环境 (保留兼容性)
  analyze: async () => {
    const response = await fetch('/api/yolo/analyze_environment', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    })
    
    if (!response.ok) {
      throw new Error(`环境分析失败: ${response.status}`)
    }
    
    return response.json()
  }
}

// 导航API更新
export const navigationApi = {
  // 开始导航
  start: async (destination: string) => {
    const response = await fetch('/api/navigation/start', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ destination })
    })
    
    if (!response.ok) {
      throw new Error(`导航启动失败: ${response.status}`)
    }
    
    return response.json()
  },
  
  // 停止导航
  stop: async () => {
    const response = await fetch('/api/navigation/stop', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    })
    
    if (!response.ok) {
      throw new Error(`导航停止失败: ${response.status}`)
    }
    
    return response.json()
  },
  
  // 语音导航 - 使用Vosk进行语音识别并设置导航目的地
  voiceNavigate: async (audioFile: Blob) => {
    const formData = new FormData()
    formData.append('audio_file', audioFile, 'recording.wav')
    
    const response = await fetch('/api/navigation/voice_navigate', {
      method: 'POST',
      body: formData
    })
    
    if (!response.ok) {
      throw new Error(`语音导航失败: ${response.status}`)
    }
    
    return response.json()
  },
  
  // 搜索目的地
  search: async (query: string) => {
    const response = await fetch('/api/navigation/search', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query })
    })
    
    if (!response.ok) {
      throw new Error(`搜索目的地失败: ${response.status}`)
    }
    
    return response.json()
  },
  
  // 获取导航状态
  getStatus: async () => {
    const response = await fetch('/api/navigation/status')
    
    if (!response.ok) {
      throw new Error(`获取导航状态失败: ${response.status}`)
    }
    
    return response.json()
  }
}

// 新增：综合系统API
export const integratedApi = {
  getStatus: () => 
    apiClient.get('/integrated/status'),
  
  processFrame: () => 
    apiClient.post('/integrated/process_frame'),
  
  getHealthCheck: () => 
    apiClient.get('/health')
}

// 新增：系统API
export const systemApi = {
  getHealth: () => 
    apiClient.get('/health')
}

// 导出所有API
export default {
  userApi,
  videoApi,
  locationApi,
  yoloApi,
  audioApi,
  speechApi,
  navigationApi,
  integratedApi,
  systemApi
} 