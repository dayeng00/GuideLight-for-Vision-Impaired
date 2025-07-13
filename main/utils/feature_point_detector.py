"""
特征点检测 - 使用全局帧缓存获取数据
"""
import cv2
import time
import threading
import numpy as np
from utils.video_show import VideoShowOAK
import depthai as dai
from .global_frame_cache import get_global_frame_cache
from utils.device_manager import device_manager

class FeaturePointDetector(VideoShowOAK):
    def __init__(self, camera_size=720, is_show_fps=True, motion_estimation="hardware_accelerated", headless=True):
        super().__init__(camera_size, is_show_fps)
        
        # 全局帧缓存
        self.global_cache = get_global_frame_cache()
        
        # 设备管理器
        self.device_manager = device_manager
        
        self.motion_estimation = motion_estimation
        self.headless = headless
        self.continue_running = True
        
        # 帧数据
        self.left_frame = None
        self.right_frame = None
        self.last_left_frame = None
        self.last_right_frame = None
        
        # 运行状态
        self.processing_active = False
        self.processing_thread = None
        
        print("✅ 特征点检测器初始化完成，使用全局帧缓存")
    
    def start(self):
        """启动特征点检测器"""
        if self.processing_active:
            print("⚠️ 特征点检测器已在运行")
            return
        
        print("🚀 启动特征点检测器...")
        
        # 确保设备管理器正在运行
        if not self.device_manager.is_running():
            print("⚠️ 设备管理器未运行，尝试启动...")
            try:
                self.device_manager.start()
                time.sleep(2)  # 等待设备启动
            except Exception as e:
                print(f"❌ 启动设备管理器失败: {e}")
                return
        
        # 订阅全局帧缓存
        self.global_cache.subscribe("feature_detector", self._on_frame_update)
        
        # 启动处理线程
        self.processing_active = True
        self.continue_running = True
        
        if not self.headless:
            self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
            self.processing_thread.start()
        
        print("✅ 特征点检测器已启动")
    
    def stop(self):
        """停止特征点检测器"""
        if not self.processing_active:
            return
        
        print("🛑 停止特征点检测器...")
        
        # 取消订阅
        self.global_cache.unsubscribe("feature_detector")
        
        # 停止处理线程
        self.processing_active = False
        self.continue_running = False
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=2.0)
        
        print("✅ 特征点检测器已停止")
    
    def _on_frame_update(self, frame_data):
        """帧更新回调"""
        try:
            # 更新左右帧数据
            if 'rectifiedLeft' in frame_data:
                self.left_frame = frame_data['rectifiedLeft']
            
            if 'rectifiedRight' in frame_data:
                self.right_frame = frame_data['rectifiedRight']
                
        except Exception as e:
            print(f"❌ 特征点检测器帧更新失败: {e}")
    
    def _processing_loop(self):
        """处理循环（仅在非headless模式下运行）"""
        print("🔄 特征点检测器处理循环启动")
        
        while self.processing_active and self.continue_running:
            try:
                # 从全局缓存获取最新帧
                current_frames = self.global_cache.get_current_frames(['rectifiedLeft', 'rectifiedRight'])
                
                if 'rectifiedLeft' in current_frames:
                    self.left_frame = current_frames['rectifiedLeft']
                
                if 'rectifiedRight' in current_frames:
                    self.right_frame = current_frames['rectifiedRight']
                
                # 处理帧数据（如果有显示需求）
                if self.left_frame is not None and self.right_frame is not None:
                    # 这里可以添加特征点检测的可视化处理
                    pass
                
                time.sleep(0.03)  # ~30 FPS
                
            except Exception as e:
                print(f"❌ 特征点检测器处理循环错误: {e}")
                time.sleep(0.1)
        
        print("🔄 特征点检测器处理循环已结束")

    def run_left(self):
        """左摄像头视频流生成器"""
        print("🎥 开始左摄像头特征点检测视频流生成...")
        
        # 确保设备管理器正在运行
        if not self.device_manager.is_running():
            print("⚠️ 设备管理器未运行，尝试启动...")
            try:
                self.device_manager.start()
                time.sleep(2)
            except Exception as e:
                print(f"❌ 启动设备管理器失败: {e}")
                return
        
        while self.continue_running:
            try:
                # 从全局帧缓存获取左侧矫正帧
                current_frames = self.global_cache.get_current_frames(['rectifiedLeft'])
                
                if 'rectifiedLeft' not in current_frames or current_frames['rectifiedLeft'] is None:
                    time.sleep(0.05)
                    continue
                
                frame = current_frames['rectifiedLeft']
                
                # 处理帧
                processed_frame = self._process_left_frame(frame)
                
                if processed_frame is not None:
                    # 编码为JPEG
                    _, buffer = cv2.imencode('.jpg', processed_frame)
                    frame_bytes = buffer.tobytes()
                    
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                else:
                    # 生成占位符帧
                    placeholder = self._generate_placeholder_frame("Left Camera - Waiting for data...")
                    _, buffer = cv2.imencode('.jpg', placeholder)
                    frame_bytes = buffer.tobytes()
                    
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
                time.sleep(0.03)  # ~30fps
                
            except Exception as e:
                print(f"⚠️ 左摄像头特征点检测错误: {e}")
                time.sleep(0.1)
        
        print("🎥 左摄像头特征点检测视频流生成已停止")

    def run_right(self):
        """右摄像头视频流生成器"""
        print("🎥 开始右摄像头特征点检测视频流生成...")
        
        # 确保设备管理器正在运行
        if not self.device_manager.is_running():
            print("⚠️ 设备管理器未运行，尝试启动...")
            try:
                self.device_manager.start()
                time.sleep(2)
            except Exception as e:
                print(f"❌ 启动设备管理器失败: {e}")
                return
        
        while self.continue_running:
            try:
                # 从全局帧缓存获取右侧矫正帧
                current_frames = self.global_cache.get_current_frames(['rectifiedRight'])
                
                if 'rectifiedRight' not in current_frames or current_frames['rectifiedRight'] is None:
                    time.sleep(0.05)
                    continue
                
                frame = current_frames['rectifiedRight']
                
                # 处理帧
                processed_frame = self._process_right_frame(frame)
                
                if processed_frame is not None:
                    # 编码为JPEG
                    _, buffer = cv2.imencode('.jpg', processed_frame)
                    frame_bytes = buffer.tobytes()
                    
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                else:
                    # 生成占位符帧
                    placeholder = self._generate_placeholder_frame("Right Camera - Waiting for data...")
                    _, buffer = cv2.imencode('.jpg', placeholder)
                    frame_bytes = buffer.tobytes()
                    
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
                time.sleep(0.03)  # ~30fps
                
            except Exception as e:
                print(f"⚠️ 右摄像头特征点检测错误: {e}")
                time.sleep(0.1)
        
        print("🎥 右摄像头特征点检测视频流生成已停止")

    def _process_left_frame(self, frame):
        """处理左侧帧"""
        try:
            if frame is None:
                return None
            
            # 转换为灰度图像进行特征点检测
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
            
            # 使用FAST特征点检测器
            fast = cv2.FastFeatureDetector_create(threshold=50)
            keypoints = fast.detect(gray, None)
            
            # 在原图上绘制特征点
            result_frame = cv2.drawKeypoints(frame, keypoints, None, color=(0, 255, 0))
            
            # 添加信息文本
            cv2.putText(result_frame, f"Left Camera - Features: {len(keypoints)}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # 显示帧率
            result_frame = self.show_fps(result_frame)
            
            # 调整图像大小
            if self.camera_size > 0:
                new_width = int(self.camera_size * 1280 / 720)
                new_height = int(self.camera_size)
                result_frame = cv2.resize(result_frame, (new_width, new_height))
            
            self.last_left_frame = result_frame.copy()
            return result_frame
            
        except Exception as e:
            print(f"❌ 左侧帧处理失败: {e}")
            return self.last_left_frame

    def _process_right_frame(self, frame):
        """处理右侧帧"""
        try:
            if frame is None:
                return None
            
            # 转换为灰度图像进行特征点检测
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
            
            # 使用FAST特征点检测器
            fast = cv2.FastFeatureDetector_create(threshold=50)
            keypoints = fast.detect(gray, None)
            
            # 在原图上绘制特征点
            result_frame = cv2.drawKeypoints(frame, keypoints, None, color=(255, 0, 0))
            
            # 添加信息文本
            cv2.putText(result_frame, f"Right Camera - Features: {len(keypoints)}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
            
            # 显示帧率
            result_frame = self.show_fps(result_frame)
            
            # 调整图像大小
            if self.camera_size > 0:
                new_width = int(self.camera_size * 1280 / 720)
                new_height = int(self.camera_size)
                result_frame = cv2.resize(result_frame, (new_width, new_height))
            
            self.last_right_frame = result_frame.copy()
            return result_frame
            
        except Exception as e:
            print(f"❌ 右侧帧处理失败: {e}")
            return self.last_right_frame

    def _generate_placeholder_frame(self, text="Waiting for camera data..."):
        """生成占位符帧"""
        try:
            # 创建占位符图像
            if self.camera_size > 0:
                width = int(self.camera_size * 1280 / 720)
                height = int(self.camera_size)
            else:
                width = 1280
                height = 720
            
            placeholder = np.zeros((height, width, 3), dtype=np.uint8)
            
            # 添加文本
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
            text_x = (width - text_size[0]) // 2
            text_y = (height + text_size[1]) // 2
            
            cv2.putText(placeholder, text, (text_x, text_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            return placeholder
            
        except Exception as e:
            print(f"❌ 生成占位符帧失败: {e}")
            return np.zeros((720, 1280, 3), dtype=np.uint8)

    def shutdown(self):
        """安全关闭"""
        try:
            self.continue_running = False
            self.stop()
            print("✅ 特征点检测器已安全关闭")
        except Exception as e:
            print(f"❌ 关闭特征点检测器时出错: {e}")
