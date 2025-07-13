"""
手势关键点检测 - 使用全局帧缓存系统
"""
import cv2
import mediapipe as mp
import time
import numpy as np
from typing import Optional

if __name__ == "__main__":
    from video_show import VideoShow
    from global_frame_cache import GlobalFrameCache
else:
    from utils.video_show import VideoShow
    from utils.global_frame_cache import GlobalFrameCache


class GesturePointRecognition(VideoShow):
    def __init__(self, static_image_mode=False, max_num_hands=2,
                 model_complexity=1, min_detection_confidence=0.5,
                 min_tracking_confidence=0.5, output_size=(720, 720)):
        """
        手势关键点检测器 - 使用全局帧缓存
        
        :param static_image_mode: 静态图像模式
        :param max_num_hands: 最大手数
        :param model_complexity: 模型复杂度
        :param min_detection_confidence: 最小检测置信度
        :param min_tracking_confidence: 最小跟踪置信度
        :param output_size: 输出尺寸
        """
        super().__init__()
        
        # MediaPipe 手势识别初始化
        self.mpHands = mp.solutions.hands
        self.hands = self.mpHands.Hands(
            static_image_mode=static_image_mode,
            max_num_hands=max_num_hands,
            model_complexity=model_complexity,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        self.mpDraw = mp.solutions.drawing_utils
        self.handLmsStyle = self.mpDraw.DrawingSpec(color=(0, 0, 255), thickness=5)
        self.handConStyle = self.mpDraw.DrawingSpec(color=(0, 255, 0), thickness=4)
        
        # 配置参数
        self.output_size = output_size
        self.previousTime = 0
        self.currentTime = 0
        
        # 全局帧缓存
        self.global_cache = GlobalFrameCache()
        
        # 运行状态
        self.is_running = False
        self.last_frame = None
        self.error_count = 0
        self.max_errors = 10
        
        print("✅ 手势特征点识别器初始化完成，使用全局帧缓存")

    def process_frame(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        处理单帧图像，检测手势关键点
        
        Args:
            frame: 输入帧
            
        Returns:
            处理后的帧，包含手势关键点标注
        """
        try:
            if frame is None or frame.size == 0:
                return None
            
            # 转换颜色空间用于MediaPipe处理
            imgRGB = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = self.hands.process(imgRGB)
            
            # 复制原始帧用于绘制
            output_frame = frame.copy()
            imgHeight, imgWidth = output_frame.shape[:2]

            # 绘制手势关键点
            if result.multi_hand_landmarks:
                for hand_landmarks in result.multi_hand_landmarks:
                    # 绘制手势连接线和关键点
                    self.mpDraw.draw_landmarks(
                        output_frame, 
                        hand_landmarks, 
                        self.mpHands.HAND_CONNECTIONS,
                        self.handLmsStyle, 
                        self.handConStyle
                    )
                    
                    # 标注关键点编号
                    for i, lm in enumerate(hand_landmarks.landmark):
                        xPosition = int(lm.x * imgWidth)
                        yPosition = int(lm.y * imgHeight)
                        
                        # 绘制关键点编号
                        cv2.putText(
                            output_frame, 
                            str(i), 
                            (xPosition - 25, yPosition + 5), 
                            cv2.FONT_HERSHEY_SIMPLEX, 
                            0.4,
                            (0, 0, 255), 
                            2
                        )
                        
                        # 特别标注手腕关键点
                        if i == 0:
                            cv2.circle(output_frame, (xPosition, yPosition), 10, (0, 0, 255), cv2.FILLED)

            # 添加FPS信息
            self.currentTime = time.time()
            if self.previousTime > 0:
                fps = 1 / (self.currentTime - self.previousTime)
                cv2.putText(
                    output_frame, 
                    f'FPS: {int(fps)}', 
                    (30, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    1, 
                    (255, 0, 0), 
                    3
                )
            self.previousTime = self.currentTime
            
            # 调整输出尺寸
            if self.output_size != (imgWidth, imgHeight):
                output_frame = cv2.resize(output_frame, self.output_size)
            
            return output_frame
            
        except Exception as e:
            print(f"⚠️ 手势关键点检测处理错误: {e}")
            return None

    def run(self):
        """
        运行手势关键点检测，从全局帧缓存获取数据
        """
        print("🚀 启动手势关键点检测...")
        self.is_running = True
        
        # 向全局帧缓存注册订阅者
        self.global_cache.subscribe("gesture_recognition", self._on_frame_update)
        
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
                retry_count = 0
                
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
                print(f"⚠️ 手势关键点检测错误: {e}")
                
                if self.error_count >= self.max_errors:
                    print(f"❌ 手势关键点检测错误次数过多，停止运行")
                    break
                
                # 短暂休眠后重试
                time.sleep(0.1)
        
        print("🎥 手势关键点检测视频流生成已停止")

    def _generate_placeholder_frame(self) -> np.ndarray:
        """生成占位符帧"""
        try:
            # 创建占位符图像
            placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
            
            # 添加文本信息
            cv2.putText(
                placeholder, 
                'Gesture Point Recognition', 
                (50, 200), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                1, 
                (255, 255, 255), 
                2
            )
            cv2.putText(
                placeholder, 
                'Waiting for camera data...', 
                (50, 280), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.8, 
                (0, 255, 255), 
                2
            )
            
            # 调整到输出尺寸
            if self.output_size != (640, 480):
                placeholder = cv2.resize(placeholder, self.output_size)
            
            return placeholder
            
        except Exception as e:
            print(f"⚠️ 生成占位符帧失败: {e}")
            # 返回简单的黑色帧
            return np.zeros((self.output_size[1], self.output_size[0], 3), dtype=np.uint8)

    def _on_frame_update(self, frame_data):
        """帧更新回调"""
        # 这里可以添加实时处理逻辑
        pass

    def shutdown(self):
        """关闭手势关键点检测器"""
        print("🔄 关闭手势关键点检测器...")
        self.is_running = False
        
        # 取消订阅
        if hasattr(self, 'global_cache'):
            self.global_cache.unsubscribe("gesture_recognition")
        
        print("✅ 手势关键点检测器已关闭")


# 测试代码
if __name__ == "__main__":
    gesture_point_recognition = GesturePointRecognition(output_size=(720, 720))
    gesture_point_recognition.start()
    time.sleep(20)
    gesture_point_recognition.close()
    gesture_point_recognition.join()
    print("Done")
