import axios from 'axios';
import type { AxiosResponse } from 'axios';

// 创建axios实例
const apiClient = axios.create({
  baseURL: '/',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  }
});

// 系统API
export const systemApi = {
  // 获取系统健康状态
  getHealth: () => apiClient.get('/api/health'),
};

// 位置API
export const locationApi = {
  // 获取当前位置
  getCurrentLocation: () => apiClient.get('/location/current'),

  // 获取位置历史记录
  getLocationHistory: (limit = 50) => apiClient.get(`/location/history?limit=${limit}`),

  // 添加新位置
  addLocation: (lat: number, lng: number, userId?: number) => apiClient.post('/location/add', { lat, lng, user_id: userId }),

  // 设置当前位置
  setCurrentLocation: (lat: number, lng: number, userId?: number) => apiClient.post('/location/set', { lat, lng, user_id: userId }),

  // 删除位置记录
  deleteLocation: (locationId: number) => apiClient.delete(`/location/delete/${locationId}`),

  // 设置移动速度
  setSpeed: (speed: number) => apiClient.post('/location/speed', { speed }),

  // 设置目的地
  setDestination: (lat: number, lng: number) => apiClient.post('/location/destination', { lat, lng }),
};

// 视频流API
export const videoApi = {
  // 记录上次请求时间，用于防抖处理
  lastRequestTime: {
    start: {},
    stop: {},
  },
  debounceDelay: 1000, // 防抖延迟时间（毫秒）

  // 获取摄像头状态
  getCameraStatus: () => apiClient.get('/api/cameras/status'),

  // 开启摄像头
  startCamera: (type: string) => apiClient.post(`/${type}/start_cameras`),

  // 关闭摄像头
  stopCamera: (type: string) => apiClient.post(`/${type}/stop_cameras`),

  // 获取视频流URL
  getVideoStreamUrl: (type: string, side?: string): string => {
    if (side && (type === 'f_detector' || type === 'f_tracker')) {
      return `/${type}/video_feed_${side}`;
    }
    return `/${type}/video_feed`;
  },
};

// 用户API
export const userApi = {
  // 用户登录
  login: (username: string, password: string) => apiClient.post('/login', { username, password }),

  // 用户注册
  register: (username: string, password: string, category: string) => apiClient.post('/register', { username, password, category }),
};

export default {
  get: apiClient.get,
  post: apiClient.post,
  put: apiClient.put,
  delete: apiClient.delete,
  systemApi,
  locationApi,
  videoApi,
  userApi
}; 