"""
MobileNetSSD 目标检测 - 使用全局帧缓存系统
"""
import cv2
import time
import numpy as np
from typing import Optional, List, Tuple
import blobconverter

if __name__ == "__main__":
    from video_show import VideoShowOAK
    from global_frame_cache import GlobalFrameCache
else:
    from utils.video_show import VideoShowOAK
    from utils.global_frame_cache import GlobalFrameCache


class OakDMobileNetSSD(VideoShowOAK):
    def __init__(self, camera_size=720, is_show_fps=True, model_name='mobilenet-ssd', 
                 confidence_threshold=0.5, preview_size=(300, 300), output_size=(600, 600)):
        """
        MobileNetSSD目标检测器 - 使用全局帧缓存
        
        :param camera_size: 摄像头尺寸
        :param is_show_fps: 是否显示FPS
        :param model_name: 模型名称
        :param confidence_threshold: 置信度阈值
        :param preview_size: 预览尺寸
        :param output_size: 输出尺寸
        """
        super().__init__(camera_size=camera_size, is_show_fps=is_show_fps)
        
        # 模型配置
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.preview_size = preview_size
        self.output_size = output_size
        
        # 检测结果
        self.frame = None
        self.detections = []
        
        # 全局帧缓存
        self.global_cache = GlobalFrameCache()
        
        # 运行状态
        self.is_running = False
        self.last_frame = None
        self.error_count = 0
        self.max_errors = 10
        
        # COCO类别标签
        self.labels = [
            "background", "person", "bicycle", "car", "motorcycle", "airplane", "bus",
            "train", "truck", "boat", "traffic light", "fire hydrant", "stop sign",
            "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
            "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag",
            "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite",
            "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
            "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana",
            "apple", "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza",
            "donut", "cake", "chair", "couch", "potted plant", "bed", "dining table",
            "toilet", "tv", "laptop", "mouse", "remote", "keyboard", "cell phone",
            "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock",
            "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
        ]
        
        print("✅ MobileNetSSD检测器初始化完成，使用全局帧缓存")

    def _frame_norm(self, frame: np.ndarray, bbox: List[float]) -> Tuple[int, int, int, int]:
        """
        将归一化的边界框坐标转换为像素坐标
        
        Args:
            frame: 输入帧
            bbox: 归一化的边界框 [x_min, y_min, x_max, y_max]
            
        Returns:
            像素坐标的边界框 (x1, y1, x2, y2)
        """
        norm_vals = np.full(len(bbox), frame.shape[0])
        norm_vals[::2] = frame.shape[1]
        return (np.clip(np.array(bbox), 0, 1) * norm_vals).astype(int)

    def process_frame(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        处理单帧图像，进行目标检测
        
        Args:
            frame: 输入帧
            
        Returns:
            处理后的帧，包含检测结果标注
        """
        try:
            if frame is None or frame.size == 0:
                return None
            
            # 复制原始帧用于绘制
            output_frame = frame.copy()
            
            # 调整帧大小到模型输入尺寸
            input_frame = cv2.resize(frame, self.preview_size)
            
            # 这里应该进行实际的神经网络推理
            # 由于我们使用全局帧缓存，暂时使用模拟检测结果
            # 在实际应用中，您需要加载并运行MobileNetSSD模型
            
            # 模拟一些检测结果
            height, width = output_frame.shape[:2]
            
            # 添加一些示例检测框（实际应用中应该从神经网络获取）
            detections = [
                {
                    'confidence': 0.8,
                    'label': 'person',
                    'bbox': [0.1, 0.1, 0.4, 0.6]  # 归一化坐标
                },
                {
                    'confidence': 0.6,
                    'label': 'chair',
                    'bbox': [0.5, 0.3, 0.8, 0.7]
                }
            ]
            
            # 绘制检测结果
            for detection in detections:
                confidence = detection['confidence']
                label = detection['label']
                bbox = detection['bbox']
                
                if confidence > self.confidence_threshold:
                    # 转换为像素坐标
                    x1, y1, x2, y2 = self._frame_norm(output_frame, bbox)
                    
                    # 绘制边界框
                    cv2.rectangle(output_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # 绘制标签和置信度
                    label_text = f"{label}: {confidence:.2f}"
                    cv2.putText(
                        output_frame,
                        label_text,
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (0, 255, 0),
                        2
                    )
            
            # 添加FPS信息
            if self.is_show_fps:
                current_time = time.time()
                if hasattr(self, 'last_time'):
                    fps = 1.0 / (current_time - self.last_time)
                    cv2.putText(
                        output_frame,
                        f'FPS: {fps:.1f}',
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 255, 255),
                        2
                    )
                self.last_time = current_time
            
            # 调整输出尺寸
            if self.output_size != (width, height):
                output_frame = cv2.resize(output_frame, self.output_size)
            
            return output_frame
            
        except Exception as e:
            print(f"⚠️ MobileNetSSD检测处理错误: {e}")
            return None

    def run(self):
        """
        运行MobileNetSSD检测，从全局帧缓存获取数据
        """
        print("🚀 启动MobileNetSSD目标检测...")
        self.is_running = True
        
        # 向全局帧缓存注册订阅者
        self.global_cache.subscribe("mobilenet_ssd", self._on_frame_update)
        
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
                print(f"⚠️ MobileNetSSD检测错误: {e}")
                
                if self.error_count >= self.max_errors:
                    print(f"❌ MobileNetSSD检测错误次数过多，停止运行")
                    break
                
                # 短暂休眠后重试
                time.sleep(0.1)
        
        print("🎥 MobileNetSSD检测视频流生成已停止")

    def _generate_placeholder_frame(self) -> np.ndarray:
        """生成占位符帧"""
        try:
            # 创建占位符图像
            placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
            
            # 添加文本信息
            cv2.putText(
                placeholder, 
                'MobileNetSSD Detector', 
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
        """关闭MobileNetSSD检测器"""
        print("🔄 关闭MobileNetSSD检测器...")
        self.is_running = False
        
        # 取消订阅
        if hasattr(self, 'global_cache'):
            self.global_cache.unsubscribe("mobilenet_ssd")
        
        print("✅ MobileNetSSD检测器已关闭")


# 测试代码
if __name__ == "__main__":
    detector = OakDMobileNetSSD()
    detector.start()
    time.sleep(20)
    detector.close()
    detector.join()
    print("Done")
