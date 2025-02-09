// src/services/axios.js

import axios from 'axios'

// 创建 axios 实例
const instance = axios.create({
  baseURL: 'http://localhost:5000',  // 设置请求的基础 URL（可以根据需要修改）
  timeout: 10000,                      // 设置超时时间，单位是毫秒
  headers: {
    'Content-Type': 'application/json', // 默认的请求头
  }
})

// 请求拦截器：可以在请求发送前做一些处理
instance.interceptors.request.use(
  config => {
    // 在这里添加请求前的配置，比如添加 token 等
    // const token = localStorage.getItem('token')  // 假设你有一个 token
    // if (token) {
    //   config.headers['Authorization'] = `Bearer ${token}`
    // }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器：可以在响应返回后做一些处理
instance.interceptors.response.use(
  response => {
    // 你可以在这里做响应数据的处理，例如：处理成功的返回
    return response
  },
  error => {
    // 错误处理
    if (error.response) {
      switch (error.response.status) {
        case 401:
          // 处理未授权的情况，例如跳转到登录页
          break
        case 500:
          // 处理服务器错误
          break
        default:
          break
      }
    }
    return Promise.reject(error)
  }
)

export default instance
