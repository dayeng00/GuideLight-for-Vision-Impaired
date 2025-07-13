"""
手势识别器 - 使用全局帧缓存获取数据
"""
import cv2
import numpy as np
import time
from utils.video_show import VideoShowOAK
from .global_frame_cache import get_global_frame_cache
from utils.device_manager import device_manager


class GestureRecognizer(VideoShowOAK):
    def __init__(self, camera_size=720, is_show_fps=True):
        super().__init__(camera_size, is_show_fps)
        
        # 获取全局帧缓存
        self.global_cache = get_global_frame_cache()
        
        # 获取设备管理器
        self.device_manager = device_manager
        
        # 运行状态
        self.is_running = True
        self.continue_running = True
        
        # 帧数据
        self.current_frame = None
        self.last_frame = None
        
        # 错误计数
        self.error_count = 0
        self.max_errors = 10
        
        print("✅ 手势识别器初始化完成，使用全局帧缓存")

    def start(self):
        """启动手势识别器"""
        self.is_running = True
        self.continue_running = True
        print("🎥 手势识别器已启动")

    def stop(self):
        """停止手势识别器"""
        self.is_running = False
        self.continue_running = False
        print("🛑 手势识别器已停止")

    def process_frame(self, frame):
        """处理单帧图像进行手势识别"""
        try:
            if frame is None:
                return None
            
            # 这里可以添加具体的手势识别逻辑
            # 目前仅作为示例，显示原始帧
            processed_frame = frame.copy()
            
            # 添加一些基本的手势识别标识
            h, w = processed_frame.shape[:2]
            cv2.putText(processed_frame, "Gesture Recognition", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # 显示帧率
            processed_frame = self.show_fps(processed_frame)
            
            # 调整图像大小
            if self.camera_size > 0:
                new_width = int(self.camera_size * 1280 / 720)
                new_height = int(self.camera_size)
                processed_frame = cv2.resize(processed_frame, (new_width, new_height))
            
            return processed_frame
            
        except Exception as e:
            print(f"❌ 手势识别处理错误: {e}")
            return None

    def run(self):
        """主运行循环 - 使用全局帧缓存"""
        print("🎥 开始手势识别视频流生成...")
        
        # 确保设备管理器正在运行
        if not self.device_manager.is_running():
            print("⚠️ 设备管理器未运行，尝试启动...")
            try:
                self.device_manager.start()
                time.sleep(2)  # 等待设备启动
            except Exception as e:
                print(f"❌ 启动设备管理器失败: {e}")
                return

        retry_count = 0
        max_retries = 3
        
        while self.is_running and self.continue_running:
            try:
                # 从全局帧缓存获取彩色帧
                current_frames = self.global_cache.get_current_frames(['color'])
                
                if 'color' not in current_frames or current_frames['color'] is None:
                    # 如果没有彩色帧数据，等待一下
                    time.sleep(0.05)
                    continue
                
                frame = current_frames['color']
                
                # 检查帧是否有效
                if frame is None or frame.size == 0:
                    print("收到空彩色帧，跳过处理")
                    time.sleep(0.01)
                    continue
                
                # 成功获取帧，重置错误计数
                self.error_count = 0
                retry_count = 0  # 重置重试计数
                
                # 处理帧
                processed_frame = self.process_frame(frame)
                
                if processed_frame is not None:
                    self.last_frame = processed_frame
                    
                    # 编码为JPEG
                    ret, jpeg = cv2.imencode('.jpg', processed_frame)
                    if ret:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
                elif self.last_frame is not None:
                    # 如果无法处理新帧但有上一帧，则发送上一帧
                    ret, jpeg = cv2.imencode('.jpg', self.last_frame)
                    if ret:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
                else:
                    # 如果没有帧可用，发送占位符帧
                    placeholder_frame = self._generate_placeholder_frame()
                    ret, jpeg = cv2.imencode('.jpg', placeholder_frame)
                    if ret:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
                
                # 短暂延迟以控制帧率
                time.sleep(0.03)  # ~30fps
                
            except Exception as e:
                self.error_count += 1
                print(f"⚠️ 手势识别器处理错误: {e}")
                
                if self.error_count >= self.max_errors:
                    print(f"❌ 手势识别器错误次数过多，停止运行")
                    break
                
                # 短暂休眠后重试
                time.sleep(0.1)
        
        print("🎥 手势识别视频流生成已停止")

    def _generate_placeholder_frame(self):
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
            text = "Waiting for camera data..."
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
            self.is_running = False
            self.continue_running = False
            print("✅ 手势识别器已安全关闭")
        except Exception as e:
            print(f"❌ 关闭手势识别器时出错: {e}")

    def get_gesture_tips(self):
        """返回手势使用提示"""
        tips = {
            "Thumb_Up": "竖起大拇指，其他手指握拳",
            "Thumb_Down": "大拇指向下，其他手指握拳",
            "Victory": "食指和中指成V形，其他手指握拳",
            "ILoveYou": "伸出大拇指、食指和小指(摇滚手势)",
            "Closed_Fist": "握紧拳头",
            "Open_Palm": "张开手掌，手指分开",
            "Pointing_Up": "食指向上指，其他手指握拳"
        }
        return tips

    def __del__(self):
        self.shutdown()