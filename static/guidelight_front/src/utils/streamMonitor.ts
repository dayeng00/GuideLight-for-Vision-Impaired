/**
 * 视频流监控工具
 * 用于监控视频流性能、处理重连和缓存优化
 */

interface StreamStats {
  id: string
  fps: number
  lastFrameTime: number
  errorCount: number
  totalFrames: number
  avgLoadTime: number
  isActive: boolean
}

interface StreamConfig {
  id: string
  url: string
  retryCount: number
  retryDelay: number
  timeout: number
  quality: 'high' | 'medium' | 'low'
}

class StreamMonitor {
  private streams: Map<string, StreamStats> = new Map()
  private configs: Map<string, StreamConfig> = new Map()
  private observers: Map<string, IntersectionObserver> = new Map()
  private retryTimers: Map<string, number> = new Map()
  
  constructor() {
    this.startMonitoring()
  }
  
  /**
   * 注册视频流
   */
  registerStream(config: StreamConfig): void {
    this.configs.set(config.id, config)
    this.streams.set(config.id, {
      id: config.id,
      fps: 0,
      lastFrameTime: 0,
      errorCount: 0,
      totalFrames: 0,
      avgLoadTime: 0,
      isActive: false
    })
    
    console.log(`注册视频流: ${config.id}`)
  }
  
  /**
   * 注销视频流
   */
  unregisterStream(streamId: string): void {
    this.streams.delete(streamId)
    this.configs.delete(streamId)
    
    // 清理重试定时器
    const timer = this.retryTimers.get(streamId)
    if (timer) {
      clearTimeout(timer)
      this.retryTimers.delete(streamId)
    }
    
    // 清理观察器
    const observer = this.observers.get(streamId)
    if (observer) {
      observer.disconnect()
      this.observers.delete(streamId)
    }
    
    console.log(`注销视频流: ${streamId}`)
  }
  
  /**
   * 创建优化的视频流URL
   */
  createOptimizedUrl(baseUrl: string, quality: 'high' | 'medium' | 'low' = 'medium'): string {
    const params = new URLSearchParams()
    
    // 添加缓存破坏参数
    params.append('t', Date.now().toString())
    
    // 根据质量设置参数
    switch (quality) {
      case 'high':
        params.append('q', '95')
        params.append('fps', '30')
        break
      case 'medium':
        params.append('q', '85')
        params.append('fps', '25')
        break
      case 'low':
        params.append('q', '75')
        params.append('fps', '20')
        break
    }
    
    return `${baseUrl}?${params.toString()}`
  }
  
  /**
   * 监控图像元素
   */
  monitorImageElement(img: HTMLImageElement, streamId: string): void {
    const stats = this.streams.get(streamId)
    if (!stats) return
    
    let frameCount = 0
    let lastTime = performance.now()
    
    // 监听加载事件
    const handleLoad = () => {
      const currentTime = performance.now()
      const loadTime = currentTime - stats.lastFrameTime
      
      stats.totalFrames++
      stats.lastFrameTime = currentTime
      stats.avgLoadTime = (stats.avgLoadTime + loadTime) / 2
      stats.errorCount = 0 // 重置错误计数
      stats.isActive = true
      
      // 计算FPS
      frameCount++
      if (currentTime - lastTime >= 1000) {
        stats.fps = frameCount
        frameCount = 0
        lastTime = currentTime
      }
    }
    
    // 监听错误事件
    const handleError = () => {
      stats.errorCount++
      stats.isActive = false
      
      console.warn(`视频流 ${streamId} 加载错误，错误次数: ${stats.errorCount}`)
      
      // 自动重试
      this.retryStream(streamId, img)
    }
    
    img.addEventListener('load', handleLoad)
    img.addEventListener('error', handleError)
    
    // 设置可见性观察器
    this.setupVisibilityObserver(img, streamId)
  }
  
  /**
   * 设置可见性观察器
   */
  private setupVisibilityObserver(img: HTMLImageElement, streamId: string): void {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          const stats = this.streams.get(streamId)
          if (!stats) return
          
          if (entry.isIntersecting) {
            // 元素可见，恢复高质量流
            this.upgradeStreamQuality(streamId, img)
          } else {
            // 元素不可见，降低质量或暂停
            this.downgradeStreamQuality(streamId, img)
          }
        })
      },
      { threshold: 0.1 }
    )
    
    observer.observe(img)
    this.observers.set(streamId, observer)
  }
  
  /**
   * 重试视频流
   */
  private retryStream(streamId: string, img: HTMLImageElement): void {
    const config = this.configs.get(streamId)
    const stats = this.streams.get(streamId)
    
    if (!config || !stats) return
    
    // 清除现有定时器
    const existingTimer = this.retryTimers.get(streamId)
    if (existingTimer) {
      clearTimeout(existingTimer)
    }
    
    // 检查重试次数
    if (stats.errorCount > config.retryCount) {
      console.error(`视频流 ${streamId} 重试次数超限，停止重试`)
      return
    }
    
    // 设置重试定时器
    const timer = setTimeout(() => {
      console.log(`重试视频流 ${streamId}，第 ${stats.errorCount} 次重试`)
      
      // 重新设置图像源
      const newUrl = this.createOptimizedUrl(config.url, config.quality)
      img.src = newUrl
      
      this.retryTimers.delete(streamId)
    }, config.retryDelay * stats.errorCount) // 指数退避
    
    this.retryTimers.set(streamId, timer)
  }
  
  /**
   * 升级流质量
   */
  private upgradeStreamQuality(streamId: string, img: HTMLImageElement): void {
    const config = this.configs.get(streamId)
    if (!config) return
    
    // 如果当前不是高质量，则升级
    if (config.quality !== 'high') {
      config.quality = 'high'
      const newUrl = this.createOptimizedUrl(config.url, 'high')
      img.src = newUrl
      console.log(`升级视频流质量: ${streamId}`)
    }
  }
  
  /**
   * 降级流质量
   */
  private downgradeStreamQuality(streamId: string, img: HTMLImageElement): void {
    const config = this.configs.get(streamId)
    if (!config) return
    
    // 如果当前不是低质量，则降级
    if (config.quality !== 'low') {
      config.quality = 'low'
      const newUrl = this.createOptimizedUrl(config.url, 'low')
      img.src = newUrl
      console.log(`降级视频流质量: ${streamId}`)
    }
  }
  
  /**
   * 获取流统计信息
   */
  getStreamStats(streamId: string): StreamStats | undefined {
    return this.streams.get(streamId)
  }
  
  /**
   * 获取所有流统计信息
   */
  getAllStats(): StreamStats[] {
    return Array.from(this.streams.values())
  }
  
  /**
   * 开始监控
   */
  private startMonitoring(): void {
    // 每秒更新一次统计信息
    setInterval(() => {
      this.updateStats()
    }, 1000)
    
    // 每5秒检查一次流健康状态
    setInterval(() => {
      this.checkStreamHealth()
    }, 5000)
  }
  
  /**
   * 更新统计信息
   */
  private updateStats(): void {
    const currentTime = performance.now()
    
    this.streams.forEach((stats, streamId) => {
      // 检查流是否活跃
      if (currentTime - stats.lastFrameTime > 5000) {
        stats.isActive = false
        stats.fps = 0
      }
    })
  }
  
  /**
   * 检查流健康状态
   */
  private checkStreamHealth(): void {
    this.streams.forEach((stats, streamId) => {
      if (!stats.isActive && stats.errorCount > 0) {
        console.warn(`视频流 ${streamId} 不健康，FPS: ${stats.fps}, 错误: ${stats.errorCount}`)
      }
    })
  }
  
  /**
   * 清理所有资源
   */
  cleanup(): void {
    // 清理所有定时器
    this.retryTimers.forEach(timer => clearTimeout(timer))
    this.retryTimers.clear()
    
    // 清理所有观察器
    this.observers.forEach(observer => observer.disconnect())
    this.observers.clear()
    
    // 清理数据
    this.streams.clear()
    this.configs.clear()
    
    console.log('视频流监控器已清理')
  }
}

// 创建全局实例
export const streamMonitor = new StreamMonitor()

// 导出类型
export type { StreamStats, StreamConfig }
export default StreamMonitor 