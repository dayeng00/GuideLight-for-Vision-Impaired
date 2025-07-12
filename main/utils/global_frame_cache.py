"""
全局帧缓存系统 - 统一管理所有摄像头数据，避免设备冲突
"""
import threading
import time
import queue
import numpy as np
from typing import Dict, Optional, Any, Callable
import cv2


class GlobalFrameCache:
    """全局帧缓存单例，统一管理所有摄像头数据"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self._data_lock = threading.RLock()
        
        # 当前帧数据
        self.current_frames = {
            'color': None,
            'depth': None,
            'rectifiedLeft': None,
            'rectifiedRight': None,
            'imu': None,
            'timestamp': None
        }
        
        # 帧历史缓冲区（保留最近几帧）
        self.frame_history = {
            'color': queue.Queue(maxsize=5),
            'depth': queue.Queue(maxsize=5),
            'rectifiedLeft': queue.Queue(maxsize=5),
            'rectifiedRight': queue.Queue(maxsize=5),
            'imu': queue.Queue(maxsize=5)
        }
        
        # 数据订阅者
        self.subscribers = {}
        
        # 统计信息
        self.stats = {
            'total_frames': 0,
            'current_fps': 0.0,
            'last_fps_time': time.time(),
            'subscribers_count': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # 数据更新回调
        self.update_callbacks = []
        
        print("✅ 全局帧缓存系统初始化完成")
    
    def update_frames(self, frame_data: Dict[str, Any]) -> None:
        """更新帧数据"""
        with self._data_lock:
            current_time = time.time()
            
            # 更新当前帧
            for key, value in frame_data.items():
                if key in self.current_frames and value is not None:
                    self.current_frames[key] = value.copy() if hasattr(value, 'copy') else value
                    
                    # 添加到历史缓冲区
                    if key in self.frame_history:
                        try:
                            self.frame_history[key].put_nowait((current_time, value))
                        except queue.Full:
                            # 移除最旧的帧
                            try:
                                self.frame_history[key].get_nowait()
                                self.frame_history[key].put_nowait((current_time, value))
                            except queue.Empty:
                                pass
            
            self.current_frames['timestamp'] = current_time
            self.stats['total_frames'] += 1
            
            # 计算FPS
            if current_time - self.stats['last_fps_time'] >= 1.0:
                self.stats['current_fps'] = self.stats['total_frames'] / (current_time - self.stats['last_fps_time'])
                self.stats['last_fps_time'] = current_time
                self.stats['total_frames'] = 0
            
            # 通知订阅者
            self._notify_subscribers(frame_data)
            
            # 执行更新回调
            for callback in self.update_callbacks:
                try:
                    callback(frame_data)
                except Exception as e:
                    print(f"⚠️ 帧更新回调执行失败: {e}")
    
    def get_current_frame(self, frame_type: str) -> Optional[Any]:
        """获取当前帧数据"""
        with self._data_lock:
            if frame_type in self.current_frames:
                frame = self.current_frames[frame_type]
                if frame is not None:
                    self.stats['cache_hits'] += 1
                    return frame.copy() if hasattr(frame, 'copy') else frame
                else:
                    self.stats['cache_misses'] += 1
                    return None
            return None
    
    def get_current_frames(self, frame_types: list = None) -> Dict[str, Any]:
        """获取当前多个帧数据"""
        with self._data_lock:
            if frame_types is None:
                frame_types = ['color', 'depth', 'rectifiedLeft', 'rectifiedRight', 'imu']
            
            result = {}
            for frame_type in frame_types:
                frame = self.get_current_frame(frame_type)
                if frame is not None:
                    result[frame_type] = frame
            
            result['timestamp'] = self.current_frames['timestamp']
            return result
    
    def get_frame_history(self, frame_type: str, max_frames: int = 5) -> list:
        """获取帧历史数据"""
        with self._data_lock:
            if frame_type not in self.frame_history:
                return []
            
            history = []
            temp_queue = queue.Queue()
            
            # 从队列中提取数据
            while not self.frame_history[frame_type].empty() and len(history) < max_frames:
                try:
                    item = self.frame_history[frame_type].get_nowait()
                    history.append(item)
                    temp_queue.put(item)
                except queue.Empty:
                    break
            
            # 将数据放回队列
            while not temp_queue.empty():
                try:
                    self.frame_history[frame_type].put_nowait(temp_queue.get_nowait())
                except queue.Full:
                    break
            
            return history
    
    def subscribe(self, subscriber_id: str, callback: Callable) -> None:
        """订阅帧更新"""
        with self._data_lock:
            self.subscribers[subscriber_id] = callback
            self.stats['subscribers_count'] = len(self.subscribers)
            print(f"📡 订阅者 {subscriber_id} 已注册到全局帧缓存")
    
    def unsubscribe(self, subscriber_id: str) -> None:
        """取消订阅"""
        with self._data_lock:
            if subscriber_id in self.subscribers:
                del self.subscribers[subscriber_id]
                self.stats['subscribers_count'] = len(self.subscribers)
                print(f"📡 订阅者 {subscriber_id} 已从全局帧缓存注销")
    
    def _notify_subscribers(self, frame_data: Dict[str, Any]) -> None:
        """通知所有订阅者"""
        for subscriber_id, callback in self.subscribers.items():
            try:
                callback(frame_data)
            except Exception as e:
                print(f"⚠️ 通知订阅者 {subscriber_id} 失败: {e}")
    
    def add_update_callback(self, callback: Callable) -> None:
        """添加帧更新回调"""
        self.update_callbacks.append(callback)
    
    def remove_update_callback(self, callback: Callable) -> None:
        """移除帧更新回调"""
        if callback in self.update_callbacks:
            self.update_callbacks.remove(callback)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._data_lock:
            return {
                'total_frames': self.stats['total_frames'],
                'current_fps': self.stats['current_fps'],
                'subscribers_count': self.stats['subscribers_count'],
                'cache_hits': self.stats['cache_hits'],
                'cache_misses': self.stats['cache_misses'],
                'cache_hit_rate': self.stats['cache_hits'] / max(1, self.stats['cache_hits'] + self.stats['cache_misses']) * 100,
                'available_frame_types': [k for k, v in self.current_frames.items() if v is not None and k != 'timestamp']
            }
    
    def clear_cache(self) -> None:
        """清空缓存"""
        with self._data_lock:
            for key in self.current_frames:
                if key != 'timestamp':
                    self.current_frames[key] = None
            
            for key in self.frame_history:
                while not self.frame_history[key].empty():
                    try:
                        self.frame_history[key].get_nowait()
                    except queue.Empty:
                        break
            
            print("🧹 全局帧缓存已清空")
    
    def is_frame_available(self, frame_type: str) -> bool:
        """检查指定类型的帧是否可用"""
        with self._data_lock:
            return (frame_type in self.current_frames and 
                    self.current_frames[frame_type] is not None)
    
    def wait_for_frame(self, frame_type: str, timeout: float = 1.0) -> Optional[Any]:
        """等待指定类型的帧可用"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            frame = self.get_current_frame(frame_type)
            if frame is not None:
                return frame
            time.sleep(0.01)  # 10ms检查间隔
        return None


# 创建全局实例
global_frame_cache = GlobalFrameCache()


def get_global_frame_cache() -> GlobalFrameCache:
    """获取全局帧缓存实例"""
    return global_frame_cache 