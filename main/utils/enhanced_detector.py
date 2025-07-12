"""
增强版目标检测器 - 支持深度信息和碰撞检测
"""
from pathlib import Path
import blobconverter
import cv2
import time
import depthai
import numpy as np
import threading
from ultralytics import YOLO
if __name__ == "__main__":
    from video_show import VideoShowOAK
    from device_manager import device_manager
else:
    from utils.video_show import VideoShowOAK
    from utils.device_manager import device_manager


class EnhancedDetector(VideoShowOAK):
    def __init__(self, camera_size=720, is_show_fps=True, confidence_threshold=0.5,
                 preview_size=(640, 480), output_size=(640, 480), use_yolo=True):
        # 只传递VideoShowOAK需要的参数
        super().__init__(camera_size, is_show_fps)
        
        # 保存额外的参数作为实例变量
        self.preview_size = preview_size
        self.output_size = output_size
        
        # 全局帧缓存
        from .global_frame_cache import get_global_frame_cache
        self.global_cache = get_global_frame_cache()
        
        # 设备管理器（保持向后兼容）
        from .device_manager import device_manager
        self.device_manager = device_manager
        
        # 检测参数
        self.confidence_threshold = confidence_threshold
        self.use_yolo = use_yolo
        
        # YOLO模型
        self.yolo_model = None
        if use_yolo:
            try:
                from ultralytics import YOLO
                self.yolo_model = YOLO('yolov8n.pt')
                print("YOLO模型加载成功")
            except Exception as e:
                print(f"YOLO模型加载失败: {e}")
                self.use_yolo = False

        # 碰撞管理器
        self.collision_manager = None
        
        # 数据处理相关
        self.callback_count = 0
        self.processing_active = False
        self.processing_thread = None
        
        # 帧数据缓存
        self.frame = None
        self.depth_frame = None
        self.last_frame = None
        self.last_depth = None
        self.last_imu = None
        
        print("✅ 增强检测器初始化完成")
    
    def set_collision_manager(self, manager):
        """设置碰撞管理器"""
        self.collision_manager = manager
    
    def start_background_processing(self):
        """启动后台处理"""
        if self.processing_active:
            print("⚠️ 增强检测器后台处理已在运行")
            return
        
        print("🚀 启动增强检测器后台处理...")
        
        # 订阅全局帧缓存
        self.global_cache.subscribe("enhanced_detector", self._on_frame_update)
        
        # 启动数据处理线程
        self.processing_active = True
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        
        print("✅ 增强检测器后台处理已启动")
    
    def stop_background_processing(self):
        """停止后台处理"""
        if not self.processing_active:
            return
        
        print("🛑 停止增强检测器后台处理...")
        
        # 取消订阅
        self.global_cache.unsubscribe("enhanced_detector")
        
        # 停止处理线程
        self.processing_active = False
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=2.0)
        
        print("✅ 增强检测器后台处理已停止")
    
    def _on_frame_update(self, frame_data):
        """全局帧缓存更新回调"""
        try:
            self.callback_count += 1
            debug_mode = self.callback_count <= 5  # 只在前5次回调时打印详细信息
            
            if debug_mode:
                print(f"📡 增强检测器接收到帧更新: {list(frame_data.keys())}")
            
            # 更新帧数据
            if 'color' in frame_data and frame_data['color'] is not None:
                self.frame = frame_data['color'].copy()
                self.last_frame = self.frame.copy()
                if debug_mode:
                    print(f"🎨 更新彩色图像: {self.frame.shape}")
            
            if 'depth' in frame_data and frame_data['depth'] is not None:
                self.depth_frame = frame_data['depth'].copy()
                self.last_depth = self.depth_frame.copy()
                if debug_mode:
                    print(f"📏 更新深度图像: {self.depth_frame.shape}")
            
            # 触发帧处理
            if self.frame is not None:
                self._process_frame_data()
                
        except Exception as e:
            print(f"❌ 增强检测器帧更新回调失败: {e}")
    
    def _processing_loop(self):
        """数据处理循环"""
        print("🔄 增强检测器处理循环启动")
        
        while self.processing_active:
            try:
                # 从全局缓存获取最新帧
                current_frames = self.global_cache.get_current_frames(['color', 'depth'])
                
                if current_frames:
                    # 更新本地帧数据
                    if 'color' in current_frames:
                        self.frame = current_frames['color']
                        self.last_frame = self.frame.copy()
                    
                    if 'depth' in current_frames:
                        self.depth_frame = current_frames['depth']
                        self.last_depth = self.depth_frame.copy()
                    
                    # 处理帧数据
                    if self.frame is not None:
                        self._process_frame_data()
                
                time.sleep(0.1)  # 100ms处理间隔
                
            except Exception as e:
                print(f"❌ 增强检测器处理循环错误: {e}")
                time.sleep(0.5)
        
        print("🔄 增强检测器处理循环已结束")
    
    def _process_frame_data(self):
        """处理帧数据并进行检测"""
        try:
            debug_mode = self.callback_count <= 5  # 只在前5次回调时打印详细信息
            
            if debug_mode:
                print("🔍 开始处理帧数据...")
            
            if self.frame is None:
                if debug_mode:
                    print("⚠️ 无法处理 - 帧数据为空")
                return
                
            # YOLO检测
            if self.use_yolo and self.yolo_model is not None:
                if debug_mode:
                    print("🎯 开始YOLO检测...")
                detections = self.yolo_model(self.frame, verbose=False)
                num_detections = len(detections[0].boxes) if detections[0].boxes is not None else 0
                if debug_mode:
                    print(f"🎯 YOLO检测完成，检测到 {num_detections} 个对象")
                
                # 处理检测结果
                if debug_mode:
                    self._process_detections(detections[0])
            else:
                if debug_mode:
                    print("⚠️ YOLO模型未启用或未加载")
                
            # 更新碰撞检测数据
            if hasattr(self, 'collision_manager') and self.collision_manager:
                if debug_mode:
                    print("🚨 更新碰撞检测数据...")
                self.collision_manager.update_frame_data(
                    self.frame, 
                    self.depth_frame, 
                    self.last_imu
                )
                if debug_mode:
                    print("✅ 碰撞检测数据更新完成")
            else:
                if debug_mode:
                    print("⚠️ 碰撞检测管理器未初始化")
                
        except Exception as e:
            print(f"❌ 处理帧数据错误: {e}")
            import traceback
            traceback.print_exc()
    
    def _process_detections(self, detection_result):
        """处理YOLO检测结果"""
        try:
            if detection_result.boxes is None:
                print("📊 无检测结果")
                return
                
            num_detections = len(detection_result.boxes)
            print(f"📊 处理 {num_detections} 个检测结果...")
            
            person_count = 0
            for i, box in enumerate(detection_result.boxes):
                class_id = int(box.cls.cpu().numpy()[0])
                class_name = self.yolo_model.names[class_id]
                confidence = float(box.conf.cpu().numpy()[0])
                
                print(f"  📋 检测 {i+1}: {class_name} (置信度: {confidence:.2f})")
                
                if class_name == 'person':
                    person_count += 1
                    print(f"    👤 检测到人员 #{person_count}")
                    
            print(f"👥 总共检测到 {person_count} 个人员")
            
        except Exception as e:
            print(f"❌ 处理检测结果错误: {e}")
            import traceback
            traceback.print_exc()
    
    def _process_frame(self, frame):
        """处理帧数据"""
        if self.yolo_model and frame is not None:
            try:
                # YOLO检测
                results = self.yolo_model.track(frame, persist=True, verbose=False)
                if results:
                    result = results[0]
                    
                    # 绘制检测结果
                    for i in range(len(result.boxes)):
                        box = result.boxes[i]
                        bbox = box.xyxy.cpu().numpy()[0]
                        cls_id = int(box.cls.cpu())
                        conf = float(box.conf.cpu())
                        
                        if conf > self.confidence_threshold:
                            # 绘制边界框
                            x1, y1, x2, y2 = bbox.astype(int)
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            
                            # 绘制标签
                            label = f"{result.names[cls_id]} {conf:.2f}"
                            cv2.putText(frame, label, (x1, y1 - 10),
                                      cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            except Exception as e:
                print(f"YOLO处理失败: {e}")
        
        return frame
    
    def process_frame(self):
        """处理帧数据并返回编码后的帧"""
        if self.frame is None:
            return None
            
        try:
            # 处理帧
            frame_to_show = self._process_frame(self.frame.copy())
            
            # 显示深度信息（可选）
            if self.depth_frame is not None:
                # 将深度转换为彩色图
                depth_colormap = cv2.applyColorMap(
                    cv2.convertScaleAbs(self.depth_frame, alpha=0.03),
                    cv2.COLORMAP_JET
                )
                # 合并显示
                combined = np.hstack((frame_to_show, depth_colormap))
                frame_to_show = combined
            
            # 调整大小和显示FPS
            frame_to_show = cv2.resize(frame_to_show, self.output_size)
            frame_to_show = self.show_fps(frame_to_show)
            
            # 编码为JPEG
            _, buffer = cv2.imencode('.jpg', frame_to_show)
            frame_bytes = buffer.tobytes()
            
            # 以MJPEG格式返回
            return (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                   
        except Exception as e:
            print(f"⚠️ 帧处理错误: {e}")
            return None
    
    def run(self):
        """主运行循环 - 使用设备管理器"""
        # 检查设备管理器状态，但不强制启动
        if not self.device_manager.is_running():
            print("⚠️ 设备管理器未运行，无法启动视频流")
            return
        
        print("🎥 开始视频流生成...")
        
        while self.continue_running:
            try:
                # 从设备管理器获取最新数据
                data = self.device_manager.get_latest_data()
                
                if data['color'] is not None:
                    self.frame = data['color']
                    self.last_frame = self.frame.copy()
                
                if data['depth'] is not None:
                    self.depth_frame = data['depth']
                    self.last_depth = self.depth_frame.copy()
                
                if data['imu'] is not None:
                    self.last_imu = data['imu']
                
                # 处理帧数据
                if self.frame is not None:
                    processed_frame = self.process_frame()
                    if processed_frame is not None:
                        yield processed_frame
                else:
                    # 如果没有帧数据，等待一下
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"⚠️ 视频流生成错误: {e}")
                time.sleep(0.1)
        
        print("🎥 视频流生成已停止")
    
    def shutdown(self):
        """安全关闭设备"""
        try:
            self.continue_running = False
            self.stop_background_processing()
            print("✅ 增强检测器已安全关闭")
        except Exception as e:
            print(f"❌ 关闭增强检测器时出错: {e}")


# 测试
if __name__ == "__main__":
    detector = EnhancedDetector(camera_size=720, use_yolo=True)
    detector.start()
    time.sleep(30)
    detector.close()
    detector.join()
    print("Done") 