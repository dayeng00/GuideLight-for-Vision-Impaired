"""
视频流优化器 - 统一管理和优化所有视频流
"""
import cv2
import time
import threading
import queue
import logging
from typing import Dict, Optional, Callable, Tuple
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import weakref

logger = logging.getLogger(__name__)

class StreamOptimizer:
    """视频流优化器 - 提供统一的视频流管理和优化"""
    
    def __init__(self, max_workers: int = 4):
        self.streams: Dict[str, 'OptimizedStream'] = {}
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self.is_running = True
        self._lock = threading.Lock()
        
    def create_stream(self, stream_id: str, source_func: Callable, 
                     target_fps: int = 30, buffer_size: int = 3,
                     compression_quality: int = 85) -> 'OptimizedStream':
        """创建优化的视频流"""
        with self._lock:
            if stream_id in self.streams:
                logger.warning(f"流 {stream_id} 已存在，将覆盖")
                self.remove_stream(stream_id)
            
            stream = OptimizedStream(
                stream_id=stream_id,
                source_func=source_func,
                target_fps=target_fps,
                buffer_size=buffer_size,
                compression_quality=compression_quality
            )
            
            self.streams[stream_id] = stream
            logger.info(f"创建视频流: {stream_id}")
            return stream
    
    def remove_stream(self, stream_id: str) -> bool:
        """移除视频流"""
        with self._lock:
            if stream_id in self.streams:
                stream = self.streams[stream_id]
                stream.stop()
                del self.streams[stream_id]
                logger.info(f"移除视频流: {stream_id}")
                return True
            return False
    
    def get_stream(self, stream_id: str) -> Optional['OptimizedStream']:
        """获取视频流"""
        return self.streams.get(stream_id)
    
    def get_stream_stats(self) -> Dict[str, Dict]:
        """获取所有流的统计信息"""
        stats = {}
        for stream_id, stream in self.streams.items():
            stats[stream_id] = stream.get_stats()
        return stats
    
    def cleanup(self):
        """清理所有资源"""
        self.is_running = False
        
        # 停止所有流
        for stream_id in list(self.streams.keys()):
            self.remove_stream(stream_id)
        
        # 关闭线程池
        self.thread_pool.shutdown(wait=True)
        logger.info("视频流优化器已清理")


class OptimizedStream:
    """优化的视频流"""
    
    def __init__(self, stream_id: str, source_func: Callable,
                 target_fps: int = 30, buffer_size: int = 3,
                 compression_quality: int = 85):
        self.stream_id = stream_id
        self.source_func = source_func
        self.target_fps = target_fps
        self.frame_interval = 1.0 / target_fps
        self.compression_quality = compression_quality
        
        # 帧缓冲
        self.frame_buffer = queue.Queue(maxsize=buffer_size)
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        
        # 统计信息
        self.stats = {
            'frames_processed': 0,
            'frames_dropped': 0,
            'avg_fps': 0,
            'encoding_time': 0,
            'last_frame_time': 0,
            'buffer_usage': 0
        }
        
        # 控制变量
        self.is_active = False
        self.processing_thread = None
        self._stop_event = threading.Event()
        
        # 性能监控
        self.fps_calculator = FPSCalculator()
        self.encoding_timer = Timer()
    
    def start(self):
        """启动视频流"""
        if self.is_active:
            return
        
        self.is_active = True
        self._stop_event.clear()
        self.processing_thread = threading.Thread(target=self._process_frames)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        logger.info(f"视频流 {self.stream_id} 已启动")
    
    def stop(self):
        """停止视频流"""
        if not self.is_active:
            return
        
        self.is_active = False
        self._stop_event.set()
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=2)
        
        # 清空缓冲区
        while not self.frame_buffer.empty():
            try:
                self.frame_buffer.get_nowait()
            except queue.Empty:
                break
        
        logger.info(f"视频流 {self.stream_id} 已停止")
    
    def _process_frames(self):
        """处理视频帧的主循环"""
        last_frame_time = 0
        
        while self.is_active and not self._stop_event.is_set():
            try:
                current_time = time.time()
                
                # 控制帧率
                if current_time - last_frame_time < self.frame_interval:
                    time.sleep(0.001)
                    continue
                
                # 获取新帧
                frame = self._get_source_frame()
                if frame is None:
                    time.sleep(0.01)
                    continue
                
                # 更新统计
                self.fps_calculator.update()
                self.stats['frames_processed'] += 1
                self.stats['last_frame_time'] = current_time
                
                # 编码帧
                with self.encoding_timer:
                    encoded_frame = self._encode_frame(frame)
                
                if encoded_frame is not None:
                    # 更新缓冲区
                    self._update_buffer(encoded_frame)
                    
                    # 更新最新帧
                    with self.frame_lock:
                        self.latest_frame = encoded_frame
                
                last_frame_time = current_time
                
            except Exception as e:
                logger.error(f"处理帧时出错 {self.stream_id}: {e}")
                time.sleep(0.1)
    
    def _get_source_frame(self) -> Optional[np.ndarray]:
        """从源获取帧"""
        try:
            return self.source_func()
        except Exception as e:
            logger.error(f"获取源帧失败 {self.stream_id}: {e}")
            return None
    
    def _encode_frame(self, frame: np.ndarray) -> Optional[bytes]:
        """编码帧为JPEG"""
        try:
            # 优化编码参数
            encode_params = [
                cv2.IMWRITE_JPEG_QUALITY, self.compression_quality,
                cv2.IMWRITE_JPEG_OPTIMIZE, 1,
                cv2.IMWRITE_JPEG_PROGRESSIVE, 1
            ]
            
            success, buffer = cv2.imencode('.jpg', frame, encode_params)
            if success:
                return buffer.tobytes()
            return None
        except Exception as e:
            logger.error(f"编码帧失败 {self.stream_id}: {e}")
            return None
    
    def _update_buffer(self, encoded_frame: bytes):
        """更新帧缓冲区"""
        try:
            if self.frame_buffer.full():
                # 丢弃最旧的帧
                try:
                    self.frame_buffer.get_nowait()
                    self.stats['frames_dropped'] += 1
                except queue.Empty:
                    pass
            
            self.frame_buffer.put_nowait(encoded_frame)
            self.stats['buffer_usage'] = self.frame_buffer.qsize()
            
        except queue.Full:
            self.stats['frames_dropped'] += 1
    
    def get_frame(self) -> Optional[bytes]:
        """获取最新帧"""
        with self.frame_lock:
            return self.latest_frame
    
    def get_frame_generator(self):
        """获取帧生成器（用于MJPEG流）"""
        while self.is_active:
            frame = self.get_frame()
            if frame is not None:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            else:
                # 发送空帧或等待
                time.sleep(0.033)  # ~30fps
    
    def get_stats(self) -> Dict:
        """获取流统计信息"""
        stats = self.stats.copy()
        stats['avg_fps'] = self.fps_calculator.get_fps()
        stats['encoding_time'] = self.encoding_timer.get_average()
        return stats


class FPSCalculator:
    """FPS计算器"""
    
    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self.timestamps = []
        self.lock = threading.Lock()
    
    def update(self):
        """更新时间戳"""
        with self.lock:
            current_time = time.time()
            self.timestamps.append(current_time)
            
            # 保持窗口大小
            if len(self.timestamps) > self.window_size:
                self.timestamps.pop(0)
    
    def get_fps(self) -> float:
        """获取当前FPS"""
        with self.lock:
            if len(self.timestamps) < 2:
                return 0.0
            
            time_span = self.timestamps[-1] - self.timestamps[0]
            if time_span > 0:
                return (len(self.timestamps) - 1) / time_span
            return 0.0


class Timer:
    """计时器"""
    
    def __init__(self):
        self.times = []
        self.start_time = None
        self.lock = threading.Lock()
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            elapsed = time.time() - self.start_time
            with self.lock:
                self.times.append(elapsed)
                # 保持最近100次记录
                if len(self.times) > 100:
                    self.times.pop(0)
    
    def get_average(self) -> float:
        """获取平均时间"""
        with self.lock:
            if not self.times:
                return 0.0
            return sum(self.times) / len(self.times)


# 全局流优化器实例
_stream_optimizer = None

def get_stream_optimizer() -> StreamOptimizer:
    """获取全局流优化器实例"""
    global _stream_optimizer
    if _stream_optimizer is None:
        _stream_optimizer = StreamOptimizer()
    return _stream_optimizer

def cleanup_stream_optimizer():
    """清理全局流优化器"""
    global _stream_optimizer
    if _stream_optimizer:
        _stream_optimizer.cleanup()
        _stream_optimizer = None 