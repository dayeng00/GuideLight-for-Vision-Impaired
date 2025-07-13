import threading
import time
import numpy as np
import cv2
import base64
import json
from datetime import datetime

# 尝试导入YOLO，如果失败则使用模拟模式
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
    print("✅ YOLO模块导入成功")
except ImportError:
    YOLO_AVAILABLE = False
    print("⚠️ YOLO模块不可用，将使用模拟检测模式")

class MockDetection:
    """模拟检测结果"""
    def __init__(self, name, bbox, confidence=0.85, distance=2000):
        self.name = name
        self.bbox = bbox  # [x1, y1, x2, y2]
        self.confidence = confidence
        self.distance = distance  # 毫米
        self.color = self._get_color_for_class(name)
    
    def _get_color_for_class(self, name):
        """根据类别名称生成颜色"""
        colors = {
            'person': [0, 255, 0],
            'car': [255, 0, 0],
            'bicycle': [0, 0, 255],
            'bus': [255, 255, 0]
        }
        return colors.get(name, [128, 128, 128])

class EnvironmentProcessor:
    def __init__(self):
        self.is_processing = False
        self.stop_event = threading.Event()
        self.processing_thread = None
        self.global_frame_cache = None
        
        # 统计信息
        self.frame_count = 0
        self.tracked_objects = 0
        self.active_tracks = 0
        self.total_processing_time = 0
        self.avg_processing_time = 0
        
        # 最新结果
        self.latest_result = None
        self.result_lock = threading.Lock()
        
        # 轨迹碰撞管理器连接
        self.trajectory_collision_manager = None
        
        # YOLO模型（如果可用）
        self.yolo_model = None
        if YOLO_AVAILABLE:
            try:
                # 尝试加载YOLO模型
                self.yolo_model = YOLO('yolo11n.pt')  # 使用较小的模型
                print("✅ YOLO模型加载成功")
            except Exception as e:
                print(f"⚠️ YOLO模型加载失败: {e}")
                self.yolo_model = None
        
        # 模拟对象（用于演示）
        self.mock_objects = [
            {'name': 'person', 'x': 320, 'y': 200, 'vx': 1, 'vy': 0.5},
            {'name': 'car', 'x': 500, 'y': 300, 'vx': -2, 'vy': 0}
        ]
        
        print("✅ 环境感知处理器初始化完成")
    
    def set_global_frame_cache(self, global_frame_cache):
        """设置全局帧缓存"""
        self.global_frame_cache = global_frame_cache
        print("🔗 环境处理器已连接到全局帧缓存")
    
    def set_trajectory_collision_manager(self, manager):
        """设置轨迹碰撞管理器"""
        self.trajectory_collision_manager = manager
        print("🔗 环境处理器已连接到轨迹碰撞管理器")
    
    def start_processing(self):
        """启动处理"""
        if self.is_processing:
            print("⚠️ 环境感知处理已在运行")
            return False
        
        self.is_processing = True
        self.stop_event.clear()
        
        # 启动轨迹碰撞管理器（如果已连接）
        # 注释掉自动启动，避免与独立启动的轨迹碰撞管理器冲突
        # if self.trajectory_collision_manager and not self.trajectory_collision_manager.is_running:
        #     print("🚀 启动轨迹碰撞管理器...")
        #     self.trajectory_collision_manager.start()
        print("⚠️ 环境感知处理器不再自动启动轨迹碰撞管理器，避免数据竞争")
        
        self.processing_thread = threading.Thread(target=self.continuous_processing, daemon=True)
        self.processing_thread.start()
        
        print("🚀 环境感知处理器已启动")
        return True
    
    def stop_processing(self):
        """停止处理"""
        if not self.is_processing:
            return
        
        self.is_processing = False
        self.stop_event.set()
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5)
        
        print("🛑 环境感知处理器已停止")
    
    def continuous_processing(self):
        """持续处理循环"""
        print("🚀 环境感知处理器开始持续处理")
        
        while self.is_processing and not self.stop_event.is_set():
            try:
                start_time = time.time()
                
                # 获取图像数据
                rgb_image = self._get_image_data()
                
                if rgb_image is not None:
                    # 处理帧
                    result = self.process_frame(rgb_image)
                    
                    # 注释掉向轨迹碰撞管理器传递帧数据的逻辑，避免数据竞争
                    # 轨迹碰撞管理器应该直接从全局帧缓存获取数据
                    # if self.trajectory_collision_manager and self.trajectory_collision_manager.is_running:
                    #     # 尝试从全局帧缓存获取深度数据
                    #     depth_data = None
                    #     if self.global_frame_cache:
                    #         frame_data = self.global_frame_cache.get_latest_data()
                    #         if frame_data:
                    #             depth_data = frame_data.get('depth')
                    #     
                    #     # 如果没有深度数据，创建模拟深度数据
                    #     if depth_data is None:
                    #         import numpy as np
                    #         depth_data = np.ones((rgb_image.shape[0], rgb_image.shape[1]), dtype=np.uint16) * 1000
                    #     
                    #     print("📡 向轨迹碰撞管理器传递帧数据...")
                    #     self.trajectory_collision_manager.update_frame_data(
                    #         rgb_image, depth_data, None
                    #     )
                    print("🔄 环境感知处理器独立处理，不干扰轨迹碰撞管理器")
                    
                    # 更新统计信息
                    processing_time = time.time() - start_time
                    self.frame_count += 1
                    self.total_processing_time += processing_time
                    self.avg_processing_time = self.total_processing_time / self.frame_count
                    
                    # 保存最新结果
                    with self.result_lock:
                        self.latest_result = result
                    
                    # 打印状态（每30帧一次）
                    if self.frame_count % 30 == 0:
                        print(f"📊 环境处理器状态: 帧数={self.frame_count}, 对象数={len(result.get('detected_objects', []))}, 平均处理时间={self.avg_processing_time*1000:.2f}ms")
                
                # 控制处理频率（约10 FPS）
                time.sleep(0.1)
                
            except Exception as e:
                print(f"❌ 环境处理错误: {e}")
                time.sleep(1)
    
    def _get_image_data(self):
        """获取图像数据"""
        if self.global_frame_cache:
            # 从全局帧缓存获取数据
            frames = self.global_frame_cache.get_current_frames(['color'])
            return frames.get('color')
        else:
            # 生成模拟图像
            return self._generate_mock_image()
    
    def _generate_mock_image(self):
        """生成模拟图像"""
        img = np.ones((360, 640, 3), dtype=np.uint8) * 50  # 深灰色背景
        
        # 添加地面
        cv2.rectangle(img, (0, 250), (640, 360), (70, 70, 70), -1)
        
        # 更新模拟对象位置
        for obj in self.mock_objects:
            obj['x'] += obj['vx']
            obj['y'] += obj['vy']
            
            # 边界反弹
            if obj['x'] <= 0 or obj['x'] >= 640:
                obj['vx'] *= -1
            if obj['y'] <= 0 or obj['y'] >= 360:
                obj['vy'] *= -1
            
            # 保持在边界内
            obj['x'] = max(0, min(640, obj['x']))
            obj['y'] = max(0, min(360, obj['y']))
            
            # 绘制对象
            if obj['name'] == 'person':
                cv2.rectangle(img, (int(obj['x']-15), int(obj['y']-30)), 
                             (int(obj['x']+15), int(obj['y'])), (0, 255, 0), -1)
            elif obj['name'] == 'car':
                cv2.rectangle(img, (int(obj['x']-30), int(obj['y']-15)), 
                             (int(obj['x']+30), int(obj['y']+15)), (255, 0, 0), -1)
        
        return img
    
    def process_frame(self, rgb_image):
        """处理单帧图像"""
        start_time = time.time()
        
        # 进行目标检测
        detected_objects = []
        
        if self.yolo_model is not None:
            # 使用真实YOLO检测
            try:
                results = self.yolo_model(rgb_image, verbose=False)
                for r in results:
                    if r.boxes is not None:
                        for i, box in enumerate(r.boxes):
                            bbox = box.xyxy[0].cpu().numpy()
                            conf = box.conf[0].cpu().numpy()
                            cls = int(box.cls[0].cpu().numpy())
                            name = self.yolo_model.names[cls]
                            
                            detected_objects.append({
                                'id': f"obj_{i}",
                                'name': name,
                                'bbox': bbox.tolist(),
                                'confidence': float(conf),
                                'distance': 2000.0,  # 模拟距离
                                'color': [0, 255, 0]  # 绿色
                            })
            except Exception as e:
                print(f"YOLO检测错误: {e}")
        
        if not detected_objects:
            # 使用模拟检测
            for i, obj in enumerate(self.mock_objects):
                detected_objects.append({
                    'id': f"mock_{i}",
                    'name': obj['name'],
                    'bbox': [obj['x']-30, obj['y']-30, obj['x']+30, obj['y']+30],
                    'confidence': 0.85,
                    'distance': 2000.0,
                    'color': [0, 255, 0] if obj['name'] == 'person' else [255, 0, 0]
                })
        
        # 生成BEV图像
        bev_image = self._generate_bev_image(detected_objects)
        
        # 编码BEV图像为base64
        bev_base64 = self._encode_image_to_base64(bev_image)
        
        # 计算碰撞概率
        collision_probability = self._calculate_collision_probability(detected_objects)
        
        processing_time = time.time() - start_time
        
        return {
            'timestamp': datetime.now().isoformat(),
            'frame_count': self.frame_count,
            'processing_time': processing_time,
            'detected_objects': detected_objects,
            'collision_probability': collision_probability,
            'bev_image_base64': bev_base64,
            'tracked_objects': len(detected_objects),
            'active_tracks': len(detected_objects)
        }
    
    def _generate_bev_image(self, detected_objects):
        """生成鸟瞰图"""
        # 创建830x830的BEV图像（匹配前端期望尺寸）
        bev = np.ones((830, 830, 3), dtype=np.uint8) * 255  # 白色背景
        
        center = (415, 415)  # 中心点
        
        # 绘制中心点
        cv2.circle(bev, center, 5, (255, 0, 0), -1)
        
        # 绘制同心圆（距离标识）
        for radius in [50, 100, 200, 300]:
            cv2.circle(bev, center, radius, (200, 200, 200), 1)
        
        # 绘制检测到的对象
        for obj in detected_objects:
            # 计算BEV坐标（简化映射）
            bbox = obj['bbox']
            obj_center_x = (bbox[0] + bbox[2]) / 2
            obj_center_y = (bbox[1] + bbox[3]) / 2
            
            # 映射到BEV坐标
            bev_x = int(center[0] + (obj_center_x - 320) * 0.5)
            bev_y = int(center[1] + (obj_center_y - 180) * 0.5)
            
            # 确保在图像范围内
            bev_x = max(0, min(829, bev_x))
            bev_y = max(0, min(829, bev_y))
            
            # 绘制对象
            color = tuple(obj['color'])
            cv2.circle(bev, (bev_x, bev_y), 10, color, -1)
            
            # 添加标签
            cv2.putText(bev, obj['name'], (bev_x - 20, bev_y - 15), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        return bev
    
    def _encode_image_to_base64(self, image):
        """将图像编码为base64字符串"""
        try:
            _, buffer = cv2.imencode('.jpg', image)
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            return img_base64
        except Exception as e:
            print(f"图像编码错误: {e}")
            return ""
    
    def _calculate_collision_probability(self, detected_objects):
        """计算碰撞概率"""
        if not detected_objects:
            return 0.0
        
        # 简化的碰撞概率计算
        max_risk = 0.0
        for obj in detected_objects:
            if obj['name'] in ['person', 'car', 'bicycle']:
                # 基于距离和对象类型计算风险
                distance = obj['distance']
                if distance < 1000:  # 1米内
                    risk = 0.8
                elif distance < 2000:  # 2米内
                    risk = 0.4
                elif distance < 3000:  # 3米内
                    risk = 0.2
                else:
                    risk = 0.1
                
                max_risk = max(max_risk, risk)
        
        return max_risk
    
    def get_latest_result(self):
        """获取最新处理结果"""
        with self.result_lock:
            return self.latest_result
    
    def get_status(self):
        """获取处理器状态"""
        return {
            'is_processing': self.is_processing,
            'frame_count': self.frame_count,
            'avg_processing_time': self.avg_processing_time,
            'tracked_objects': self.tracked_objects,
            'active_tracks': self.active_tracks,
            'has_global_cache': self.global_frame_cache is not None,
            'yolo_available': self.yolo_model is not None
        }

# 单例模式
_environment_processor = None

def get_environment_processor():
    """获取环境处理器实例"""
    global _environment_processor
    if _environment_processor is None:
        _environment_processor = EnvironmentProcessor()
    return _environment_processor 