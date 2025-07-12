"""
多线程管理器 - 彻底解决Flask视频流阻塞问题
"""
import threading
import queue
import time
import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, Optional, Callable, Any, Generator
import weakref
import logging
from collections import defaultdict
import uuid
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class StreamStats:
    """视频流统计信息"""
    frames_generated: int = 0
    frames_served: int = 0
    clients_connected: int = 0
    last_frame_time: float = field(default_factory=time.time)
    fps: float = 0.0
    errors: int = 0
    start_time: float = field(default_factory=time.time)
    
    def update_fps(self):
        """更新FPS统计"""
        current_time = time.time()
        if current_time - self.last_frame_time >= 1.0:
            self.fps = self.frames_generated / (current_time - self.last_frame_time)
            self.frames_generated = 0
            self.last_frame_time = current_time


class ThreadSafeVideoStream:
    """完全非阻塞的线程安全视频流"""
    
    def __init__(self, stream_id: str, source_func: Callable, max_buffer_size: int = 5):
        self.stream_id = stream_id
        self.source_func = source_func
        self.max_buffer_size = max_buffer_size
        
        # 多级缓冲系统
        self.frame_buffer = queue.Queue(maxsize=max_buffer_size)
        self.latest_frame = None
        self.frame_lock = threading.RLock()
        
        # 控制标志
        self.is_running = False
        self.is_paused = False
        self.worker_thread = None
        self.stop_event = threading.Event()
        
        # 统计信息
        self.stats = StreamStats()
        
        # 客户端管理
        self.clients = set()
        self.client_lock = threading.Lock()
        
        # 性能优化
        self.adaptive_fps = True
        self.target_fps = 30
        self.min_fps = 5
        self.frame_skip_threshold = 3
        
        # 错误处理
        self.consecutive_errors = 0
        self.max_consecutive_errors = 10
        
        logger.info(f"创建视频流: {stream_id}")
    
    def start(self):
        """启动视频流"""
        if self.is_running:
            logger.warning(f"视频流 {self.stream_id} 已在运行")
            return
        
        self.is_running = True
        self.stop_event.clear()
        self.worker_thread = threading.Thread(
            target=self._worker_loop, 
            daemon=True,
            name=f"VideoStream-{self.stream_id}"
        )
        self.worker_thread.start()
        logger.info(f"视频流 {self.stream_id} 已启动")
    
    def stop(self):
        """停止视频流"""
        if not self.is_running:
            return
        
        self.is_running = False
        self.stop_event.set()
        
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=2)
        
        # 清理缓冲区
        while not self.frame_buffer.empty():
            try:
                self.frame_buffer.get_nowait()
            except queue.Empty:
                break
        
        logger.info(f"视频流 {self.stream_id} 已停止")
    
    def pause(self):
        """暂停视频流"""
        self.is_paused = True
        logger.info(f"视频流 {self.stream_id} 已暂停")
    
    def resume(self):
        """恢复视频流"""
        self.is_paused = False
        logger.info(f"视频流 {self.stream_id} 已恢复")
    
    def add_client(self, client_id: str = None):
        """添加客户端"""
        if client_id is None:
            client_id = str(uuid.uuid4())
        
        with self.client_lock:
            self.clients.add(client_id)
            self.stats.clients_connected = len(self.clients)
        
        logger.debug(f"客户端 {client_id} 连接到视频流 {self.stream_id}")
        return client_id
    
    def remove_client(self, client_id: str):
        """移除客户端"""
        with self.client_lock:
            self.clients.discard(client_id)
            self.stats.clients_connected = len(self.clients)
        
        logger.debug(f"客户端 {client_id} 从视频流 {self.stream_id} 断开")
    
    def get_frame(self, timeout: float = 0.1) -> Optional[bytes]:
        """获取帧数据（非阻塞）"""
        try:
            # 首先尝试从缓冲区获取最新帧
            frame_data = None
            try:
                frame_data = self.frame_buffer.get_nowait()
            except queue.Empty:
                # 如果缓冲区为空，使用最新帧
                with self.frame_lock:
                    frame_data = self.latest_frame
            
            if frame_data is not None:
                self.stats.frames_served += 1
                return frame_data
            
            return None
            
        except Exception as e:
            logger.error(f"获取帧失败: {e}")
            return None
    
    def _worker_loop(self):
        """工作线程主循环"""
        logger.info(f"视频流 {self.stream_id} 工作线程启动")
        
        try:
            # 获取帧生成器
            frame_generator = self._get_frame_generator()
            
            while self.is_running and not self.stop_event.is_set():
                try:
                    # 检查是否暂停
                    if self.is_paused:
                        time.sleep(0.1)
                        continue
                    
                    # 获取下一帧
                    frame_data = next(frame_generator, None)
                    
                    if frame_data is None:
                        # 没有帧数据，短暂休眠
                        time.sleep(0.01)
                        continue
                    
                    # 更新统计
                    self.stats.frames_generated += 1
                    self.stats.update_fps()
                    self.consecutive_errors = 0
                    
                    # 只有在有客户端时才缓存帧
                    if self.stats.clients_connected > 0:
                        self._cache_frame(frame_data)
                    
                    # 动态调整帧率
                    if self.adaptive_fps:
                        self._adjust_frame_rate()
                    
                except StopIteration:
                    logger.info(f"视频流 {self.stream_id} 生成器结束")
                    break
                except Exception as e:
                    self.consecutive_errors += 1
                    self.stats.errors += 1
                    
                    if self.consecutive_errors <= 3:
                        logger.error(f"视频流 {self.stream_id} 处理错误: {e}")
                    
                    if self.consecutive_errors >= self.max_consecutive_errors:
                        logger.error(f"视频流 {self.stream_id} 连续错误过多，停止")
                        break
                    
                    time.sleep(0.1)
        
        except Exception as e:
            logger.error(f"视频流 {self.stream_id} 工作线程异常: {e}")
        finally:
            logger.info(f"视频流 {self.stream_id} 工作线程结束")
    
    def _get_frame_generator(self) -> Generator:
        """获取帧生成器"""
        try:
            generator = self.source_func()
            if hasattr(generator, '__iter__'):
                return generator
            else:
                # 如果source_func返回单个值，包装成生成器
                def single_frame_generator():
                    while self.is_running:
                        frame = self.source_func()
                        if frame is not None:
                            yield frame
                        time.sleep(1/self.target_fps)
                return single_frame_generator()
        except Exception as e:
            logger.error(f"获取帧生成器失败: {e}")
            return iter([])
    
    def _cache_frame(self, frame_data: bytes):
        """缓存帧数据"""
        with self.frame_lock:
            # 更新最新帧
            self.latest_frame = frame_data
            
            # 清理旧的缓冲区
            while self.frame_buffer.qsize() >= self.max_buffer_size:
                try:
                    self.frame_buffer.get_nowait()
                except queue.Empty:
                    break
            
            # 添加新帧
            try:
                self.frame_buffer.put_nowait(frame_data)
            except queue.Full:
                pass  # 缓冲区满时忽略
    
    def _adjust_frame_rate(self):
        """动态调整帧率"""
        if self.stats.clients_connected == 0:
            # 没有客户端时降低帧率
            time.sleep(1/self.min_fps)
        elif self.stats.clients_connected > 2:
            # 多个客户端时稍微降低帧率
            time.sleep(1/(self.target_fps * 0.8))
        else:
            # 正常帧率
            time.sleep(1/self.target_fps)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'stream_id': self.stream_id,
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'clients_connected': self.stats.clients_connected,
            'frames_generated': self.stats.frames_generated,
            'frames_served': self.stats.frames_served,
            'fps': self.stats.fps,
            'errors': self.stats.errors,
            'uptime': time.time() - self.stats.start_time,
            'buffer_size': self.frame_buffer.qsize(),
            'max_buffer_size': self.max_buffer_size
        }


class ThreadManager:
    """高性能多线程管理器"""
    
    def __init__(self, max_workers: int = 12, max_request_threads: int = 8):
        self.max_workers = max_workers
        self.max_request_threads = max_request_threads
        
        # 线程池
        self.worker_pool = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="VideoWorker"
        )
        self.request_pool = ThreadPoolExecutor(
            max_workers=max_request_threads,
            thread_name_prefix="RequestHandler"
        )
        
        # 视频流管理
        self.streams: Dict[str, ThreadSafeVideoStream] = {}
        self.streams_lock = threading.RLock()
        
        # 全局统计
        self.global_stats = {
            'streams_created': 0,
            'streams_active': 0,
            'total_clients': 0,
            'total_frames_served': 0,
            'start_time': time.time()
        }
        
        # 监控线程
        self.monitor_thread = None
        self.monitor_running = False
        
        logger.info(f"线程管理器初始化完成: {max_workers} 工作线程, {max_request_threads} 请求线程")
    
    def create_stream(self, stream_id: str, source_func: Callable, 
                     max_buffer_size: int = 5, auto_start: bool = True) -> ThreadSafeVideoStream:
        """创建视频流"""
        with self.streams_lock:
            if stream_id in self.streams:
                logger.warning(f"视频流 {stream_id} 已存在")
                return self.streams[stream_id]
            
            stream = ThreadSafeVideoStream(stream_id, source_func, max_buffer_size)
            self.streams[stream_id] = stream
            self.global_stats['streams_created'] += 1
            
            if auto_start:
                stream.start()
                self.global_stats['streams_active'] += 1
            
            logger.info(f"创建视频流: {stream_id}")
            return stream
    
    def get_stream(self, stream_id: str) -> Optional[ThreadSafeVideoStream]:
        """获取视频流"""
        with self.streams_lock:
            return self.streams.get(stream_id)
    
    def remove_stream(self, stream_id: str):
        """移除视频流"""
        with self.streams_lock:
            if stream_id in self.streams:
                stream = self.streams[stream_id]
                stream.stop()
                del self.streams[stream_id]
                self.global_stats['streams_active'] -= 1
                logger.info(f"移除视频流: {stream_id}")
    
    def start_monitoring(self):
        """启动监控线程"""
        if self.monitor_running:
            return
        
        self.monitor_running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="StreamMonitor"
        )
        self.monitor_thread.start()
        logger.info("流监控已启动")
    
    def stop_monitoring(self):
        """停止监控线程"""
        self.monitor_running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1)
        logger.info("流监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.monitor_running:
            try:
                # 更新全局统计
                with self.streams_lock:
                    active_streams = sum(1 for s in self.streams.values() if s.is_running)
                    total_clients = sum(s.stats.clients_connected for s in self.streams.values())
                    total_frames = sum(s.stats.frames_served for s in self.streams.values())
                    
                    self.global_stats.update({
                        'streams_active': active_streams,
                        'total_clients': total_clients,
                        'total_frames_served': total_frames
                    })
                
                # 每30秒输出一次统计
                if int(time.time()) % 30 == 0:
                    self._log_stats()
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"监控循环错误: {e}")
                time.sleep(5)
    
    def _log_stats(self):
        """输出统计信息"""
        uptime = time.time() - self.global_stats['start_time']
        logger.info(f"=== 线程管理器统计 (运行时间: {uptime:.1f}s) ===")
        logger.info(f"活跃流: {self.global_stats['streams_active']}/{self.global_stats['streams_created']}")
        logger.info(f"总客户端: {self.global_stats['total_clients']}")
        logger.info(f"总帧数: {self.global_stats['total_frames_served']}")
        
        # 输出各个流的详细统计
        with self.streams_lock:
            for stream_id, stream in self.streams.items():
                if stream.is_running:
                    stats = stream.get_stats()
                    logger.info(f"  {stream_id}: {stats['clients_connected']} 客户端, {stats['fps']:.1f} FPS, {stats['frames_served']} 帧")
    
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有统计信息"""
        with self.streams_lock:
            stream_stats = {}
            for stream_id, stream in self.streams.items():
                stream_stats[stream_id] = stream.get_stats()
            
            return {
                'global': self.global_stats,
                'streams': stream_stats,
                'thread_pools': {
                    'worker_pool_active': self.worker_pool._threads,
                    'request_pool_active': self.request_pool._threads
                }
            }
    
    def shutdown(self):
        """关闭线程管理器"""
        logger.info("正在关闭线程管理器...")
        
        # 停止监控
        self.stop_monitoring()
        
        # 停止所有流
        with self.streams_lock:
            for stream in self.streams.values():
                stream.stop()
            self.streams.clear()
        
        # 关闭线程池
        self.worker_pool.shutdown(wait=True)
        self.request_pool.shutdown(wait=True)
        
        logger.info("线程管理器已关闭")
    
    def __del__(self):
        """析构函数"""
        try:
            self.shutdown()
        except:
            pass


# 全局线程管理器实例
thread_manager = ThreadManager(max_workers=12, max_request_threads=8)

# 启动监控
thread_manager.start_monitoring()

logger.info("线程管理器模块已加载") 