import depthai as dai
import cv2
import numpy as np
import time
from pathlib import Path
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import os

class GestureRecognizer:
    def __init__(self):
        self.pipeline = dai.Pipeline()
        self.is_running = True
        self.last_frame = None
        self.error_count = 0
        self.max_retries = 3
        self.retry_delay = 1.0  # 重试延迟，单位秒
        self.debug_mode = True  # 启用调试模式
        self.recognized_gestures = set()  # 跟踪已识别的手势
        self.all_gestures = [
            "Unknown", "Closed_Fist", "Open_Palm", "Pointing_Up", 
            "Thumb_Down", "Thumb_Up", "Victory", "ILoveYou"
        ]
        
        self._setup_pipeline()
        self._setup_mediapipe()
        
    def _setup_pipeline(self):
        print("Creating Gesture Recognition Pipeline...")
        cam_rgb = self.pipeline.create(dai.node.ColorCamera)
        cam_rgb.setPreviewSize(640, 400)
        cam_rgb.setBoardSocket(dai.CameraBoardSocket.RGB)
        cam_rgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
        cam_rgb.setInterleaved(False)
        cam_rgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.RGB)
        
        xout_rgb = self.pipeline.create(dai.node.XLinkOut)
        xout_rgb.setStreamName("rgb")
        cam_rgb.preview.link(xout_rgb.input)
        
        # 创建设备并启动管道
        try:
            self.device = dai.Device(self.pipeline)
            # 启动数据流
            self.q_rgb = self.device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
            print("Pipeline created and started successfully")
        except Exception as e:
            print(f"设备初始化失败: {e}")
            raise
    
    def _setup_mediapipe(self):
        try:
            # 检查模型文件是否存在
            model_path = 'main/resources/gesture_recognizer/gesture_recognizer.task'
            if not os.path.exists(model_path):
                print(f"警告: 模型文件不存在: {model_path}")
                # 尝试查找替代路径
                alternative_paths = [
                    './main/models/gesture_recognizer.task',
                    './resources/gesture_recognizer/gesture_recognizer.task',
                    './models/gesture_recognizer.task'
                ]
                for alt_path in alternative_paths:
                    if os.path.exists(alt_path):
                        model_path = alt_path
                        print(f"找到替代模型: {model_path}")
                        break
                
                if not os.path.exists(model_path):
                    print("严重错误: 无法找到手势识别模型文件!")
            
            print(f"使用模型文件: {model_path}")
            
            # 设置 MediaPipe 手势识别器
            base_options = python.BaseOptions(model_asset_path=model_path)
            options = vision.GestureRecognizerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.IMAGE,
                num_hands=2,
                min_hand_detection_confidence=0.3,  # 降低检测置信度阈值
                min_hand_presence_confidence=0.3,   # 降低手部存在置信度阈值
                min_tracking_confidence=0.3         # 降低跟踪置信度阈值
            )
            self.recognizer = vision.GestureRecognizer.create_from_options(options)
            print("MediaPipe 手势识别器初始化成功")
        except Exception as e:
            print(f"MediaPipe 初始化失败: {e}")
            self.recognizer = None
            
    def process_frame(self, frame):
        if frame is None or self.recognizer is None:
            return frame
        
        try:
            # 转换为 MediaPipe 图像格式
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            
            # 处理图像
            recognition_result = self.recognizer.recognize(mp_image)
            
            # 在图像上绘制结果
            annotated_image = frame.copy()
            
            # 添加调试信息
            if self.debug_mode:
                cv2.putText(annotated_image, f"已识别手势: {len(self.recognized_gestures)}/{len(self.all_gestures)}", 
                           (10, annotated_image.shape[0]-20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            for hand_landmarks in recognition_result.hand_landmarks:
                # 绘制手部关键点
                for landmark in hand_landmarks:
                    x = int(landmark.x * frame.shape[1])
                    y = int(landmark.y * frame.shape[0])
                    cv2.circle(annotated_image, (x, y), 5, (0, 255, 0), -1)
                
                # 绘制手部连接线
                connections = mp.solutions.hands.HAND_CONNECTIONS
                for connection in connections:
                    start_idx = connection[0]
                    end_idx = connection[1]
                    
                    start_point = hand_landmarks[start_idx]
                    end_point = hand_landmarks[end_idx]
                    
                    start_x = int(start_point.x * frame.shape[1])
                    start_y = int(start_point.y * frame.shape[0])
                    end_x = int(end_point.x * frame.shape[1])
                    end_y = int(end_point.y * frame.shape[0])
                    
                    cv2.line(annotated_image, (start_x, start_y), (end_x, end_y), (0, 255, 0), 2)
            
            # 添加手势类别标签
            recognized_in_frame = set()
            
            for i, gesture_list in enumerate(recognition_result.gestures):
                if gesture_list:
                    category_name = gesture_list[0].category_name
                    score = gesture_list[0].score
                    recognized_in_frame.add(category_name)
                    
                    # 跟踪识别到的手势类型
                    self.recognized_gestures.add(category_name)
                    
                    text = f"{category_name} ({score:.2f})"
                    # 为多只手的识别结果使用不同的垂直位置
                    cv2.putText(annotated_image, text, (10, 30 + i*40), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            
            # 当前帧识别的所有手势
            if recognized_in_frame and self.debug_mode:
                gesture_text = f"当前识别: {', '.join(recognized_in_frame)}"
                cv2.putText(annotated_image, gesture_text, 
                           (10, annotated_image.shape[0]-50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            return annotated_image
        except Exception as e:
            print(f"处理帧时出错: {e}")
            return frame
            
    def run(self):
        while self.is_running:
            try:
                # 尝试获取帧
                in_rgb = self.q_rgb.tryGet()
                
                if in_rgb is not None:
                    # 成功获取帧，重置错误计数
                    self.error_count = 0
                    
                    # 处理帧
                    frame = in_rgb.getCvFrame()
                    processed_frame = self.process_frame(frame)
                    self.last_frame = processed_frame
                    
                    # 返回处理后的帧
                    ret, jpeg = cv2.imencode('.jpg', processed_frame)
                    if ret:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
                elif self.last_frame is not None:
                    # 如果无法获取新帧但有上一帧，则发送上一帧
                    ret, jpeg = cv2.imencode('.jpg', self.last_frame)
                    if ret:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
                else:
                    # 如果没有帧可用，发送空白帧
                    blank_frame = np.zeros((400, 640, 3), dtype=np.uint8)
                    cv2.putText(blank_frame, "等待相机...", (220, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                    ret, jpeg = cv2.imencode('.jpg', blank_frame)
                    if ret:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
                
                # 短暂延迟以减少CPU占用
                time.sleep(0.03)
                
            except RuntimeError as e:
                if "X_LINK_ERROR" in str(e):
                    self.error_count += 1
                    print(f"相机通信错误 ({self.error_count}/{self.max_retries}): {e}")
                    
                    if self.error_count >= self.max_retries:
                        print("超过最大重试次数，尝试重新初始化设备...")
                        self.shutdown()
                        try:
                            # 重新初始化设备
                            time.sleep(self.retry_delay)
                            self._setup_pipeline()
                            self.error_count = 0
                            print("设备重新初始化成功")
                        except Exception as init_error:
                            print(f"设备重新初始化失败: {init_error}")
                            # 如果重新初始化失败，返回错误帧
                            error_frame = np.zeros((400, 640, 3), dtype=np.uint8)
                            cv2.putText(error_frame, "相机错误 - 请重新启动", (150, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                            ret, jpeg = cv2.imencode('.jpg', error_frame)
                            if ret:
                                yield (b'--frame\r\n'
                                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
                            break
                    else:
                        # 等待一段时间后重试
                        time.sleep(self.retry_delay)
                        
                        # 返回提示错误的帧
                        retry_frame = np.zeros((400, 640, 3), dtype=np.uint8)
                        cv2.putText(retry_frame, f"相机错误 - 重试中 {self.error_count}/{self.max_retries}", (150, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 165, 255), 2)
                        ret, jpeg = cv2.imencode('.jpg', retry_frame)
                        if ret:
                            yield (b'--frame\r\n'
                                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
                else:
                    # 其他类型的运行时错误
                    print(f"运行时错误: {e}")
                    error_frame = np.zeros((400, 640, 3), dtype=np.uint8)
                    cv2.putText(error_frame, f"错误: {str(e)[:30]}...", (100, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    ret, jpeg = cv2.imencode('.jpg', error_frame)
                    if ret:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
            except Exception as e:
                # 捕获所有其他异常
                print(f"发生异常: {e}")
                # 发送错误帧
                error_frame = np.zeros((400, 640, 3), dtype=np.uint8)
                cv2.putText(error_frame, f"错误: {str(e)[:30]}...", (100, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                ret, jpeg = cv2.imencode('.jpg', error_frame)
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
                time.sleep(0.5)
    
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
            
    def shutdown(self):
        print("关闭手势识别器...")
        self.is_running = False
        try:
            if hasattr(self, 'device') and self.device is not None:
                self.device.close()
                print("设备已关闭")
        except Exception as e:
            print(f"关闭设备时出错: {e}")
            
    def __del__(self):
        self.shutdown()