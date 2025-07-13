"""
轨迹追踪和碰撞预警管理器
负责处理物体轨迹追踪和碰撞概率计算
"""

import cv2
import numpy as np
import time
import math
import threading
from collections import defaultdict
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from ultralytics import YOLO
from scipy.spatial.transform import Rotation as R


@dataclass
class TrackedObject:
    """被追踪的物体"""
    id: int
    name: str
    tracks: List[Tuple[float, float, float]] = field(default_factory=list)  # (x, y, timestamp)
    speed: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # (vx, vy, |v|)
    collision_probability: float = 0.0
    last_update: float = 0.0
    color: Tuple[int, int, int] = (255, 255, 255)
    distance: float = 0.0  # 到用户的距离


@dataclass
class CollisionRisk:
    """碰撞风险信息"""
    level: str  # 'low', 'medium', 'high', 'critical'
    probability: float  # 0.0 - 1.0
    time_to_collision: float  # 秒
    warning_message: str
    nearest_object: Optional['DetectedObject'] = None


@dataclass
class DetectedObject:
    """检测到的物体"""
    id: int
    type: str
    position: Tuple[float, float, float]  # (x, y, z)
    distance: float
    velocity: Tuple[float, float, float]  # (vx, vy, vz)
    confidence: float
    timestamp: float


class TrajectoryTracker:
    """轨迹追踪器"""
    
    def __init__(self):
        self.tracks: Dict[int, TrackedObject] = {}
        self.max_track_length = 90  # 最大轨迹点数
        self.track_timeout = 3.0  # 轨迹超时时间（秒）
        self.min_track_points = 5  # 计算速度所需的最小轨迹点数
        self.lock = threading.Lock()
        
    def update_track(self, obj_id: int, name: str, position: Tuple[float, float], 
                    timestamp: float, color: Tuple[int, int, int], distance: float):
        """更新物体轨迹"""
        with self.lock:
            if obj_id not in self.tracks:
                self.tracks[obj_id] = TrackedObject(
                    id=obj_id, 
                    name=name, 
                    color=color,
                    distance=distance
                )
            
            track = self.tracks[obj_id]
            track.tracks.append((position[0], position[1], timestamp))
            track.last_update = timestamp
            track.distance = distance
            
            # 限制轨迹长度
            if len(track.tracks) > self.max_track_length:
                track.tracks.pop(0)
            
            # 清理过期轨迹
            if track.tracks:
                oldest_time = track.tracks[0][2]
                if timestamp - oldest_time > self.track_timeout:
                    track.tracks.pop(0)
            
            # 计算速度
            if len(track.tracks) >= self.min_track_points:
                self._calculate_speed(track)
    
    def _calculate_speed(self, track: TrackedObject):
        """计算物体速度"""
        # 使用最后5个点计算平均速度
        recent_tracks = track.tracks[-5:]
        velocities_x = []
        velocities_y = []
        
        for i in range(len(recent_tracks) - 1):
            x1, y1, t1 = recent_tracks[i]
            x2, y2, t2 = recent_tracks[i + 1]
            
            dt = max(0.01, t2 - t1)  # 避免除零
            vx = (x2 - x1) / dt
            vy = (y2 - y1) / dt
            
            velocities_x.append(vx)
            velocities_y.append(vy)
        
        # 计算平均速度
        avg_vx = np.mean(velocities_x)
        avg_vy = np.mean(velocities_y)
        speed_magnitude = math.sqrt(avg_vx**2 + avg_vy**2)
        
        track.speed = (avg_vx, avg_vy, speed_magnitude)
    
    def clean_expired_tracks(self, current_time: float, active_ids: List[int]):
        """清理过期的轨迹"""
        with self.lock:
            # 删除超时的轨迹
            expired_ids = []
            for obj_id, track in self.tracks.items():
                if current_time - track.last_update > self.track_timeout:
                    expired_ids.append(obj_id)
                elif obj_id not in active_ids:
                    # 物体已经不在视野中
                    expired_ids.append(obj_id)
            
            for obj_id in expired_ids:
                del self.tracks[obj_id]
    
    def get_tracks(self) -> Dict[int, TrackedObject]:
        """获取所有轨迹"""
        with self.lock:
            return self.tracks.copy()
    
    def get_trajectory_data(self) -> Dict[str, Any]:
        """获取轨迹数据用于前端显示"""
        with self.lock:
            data = {}
            for obj_id, track in self.tracks.items():
                data[str(obj_id)] = {
                    'name': track.name,
                    'tracks': track.tracks,
                    'speed': {
                        'vx': track.speed[0],
                        'vy': track.speed[1],
                        'magnitude': track.speed[2]
                    },
                    'collision_probability': track.collision_probability,
                    'color': track.color,
                    'distance': track.distance
                }
            return data
    
    def get_current_position(self):
        """获取当前位置（这里返回None，实际应该从定位系统获取）"""
        # TODO: 集成实际的定位系统
        return None


class CollisionWarning:
    """碰撞预警系统"""
    
    def __init__(self):
        self.center_x = 800  # BEV中心点X坐标
        self.center_y = 800  # BEV中心点Y坐标
        self.collision_radius = 50  # 碰撞半径（像素）
        self.prediction_steps = 16  # 预测步数
        self.time_step = 0.1  # 每步时间间隔（秒）
        self.detected_objects: List[DetectedObject] = []
        self.lock = threading.Lock()
    
    def calculate_collision_probability(self, tracks: Dict[int, TrackedObject]):
        """计算所有物体的碰撞概率 - 基于PyQt原始算法"""
        print(f"🧮 计算碰撞概率，轨迹数量: {len(tracks)}")
        
        for obj_id, track in tracks.items():
            print(f"  处理轨迹 {obj_id}: {len(track.tracks)} 个点")
            
            if len(track.tracks) < 5:
                track.collision_probability = 0.0
                print(f"    ❌ 轨迹点不足 (<5): {len(track.tracks)}")
                continue
                
            if track.speed[2] < 0.1:  # 速度太小，忽略
                track.collision_probability = 0.0
                print(f"    ❌ 速度太小: {track.speed[2]:.3f}")
                continue
            
            # 获取最后的位置
            last_x, last_y, _ = track.tracks[-1]
            vx, vy, speed_magnitude = track.speed
            
            print(f"    位置: ({last_x:.1f}, {last_y:.1f}), 速度: ({vx:.2f}, {vy:.2f}), 速度大小: {speed_magnitude:.2f}")
            
            # 预测轨迹并检查碰撞 - 使用PyQt原始算法
            pro = -1
            print(f"    🎯 预测轨迹，中心点: ({self.center_x}, {self.center_y}), 碰撞半径: 50")
            
            for t in range(1, 16):  # 预测16步
                # 预测未来位置
                predicted_x = vx * t / 10 + last_x
                predicted_y = vy * t / 10 + last_y
                
                # 计算到中心的距离
                distance = math.sqrt(
                    (predicted_x - self.center_x)**2 + 
                    (predicted_y - self.center_y)**2
                )
                
                # 检查是否会发生碰撞（距离小于50像素）
                if distance < 50:
                    pro = t
                    print(f"      ⚠️ 步骤 {t}: 预测碰撞! 距离={distance:.1f} < 50")
                    break
                else:
                    if t <= 3:  # 只显示前几步的详细信息
                        print(f"      ✅ 步骤 {t}: 安全 距离={distance:.1f}")
            
            # 计算碰撞概率
            if pro == -1:
                track.collision_probability = 0.0
                print(f"    💚 无碰撞风险: 概率=0%")
            else:
                track.collision_probability = (16 - pro) / 15
                print(f"    🔴 碰撞风险: 步骤={pro}, 概率={track.collision_probability:.3f} ({track.collision_probability*100:.1f}%)")
        
        print(f"🏁 碰撞概率计算完成")
    
    def get_collision_risk(self) -> CollisionRisk:
        """获取当前碰撞风险"""
        with self.lock:
            if not self.detected_objects:
                return CollisionRisk(
                    level='low',
                    probability=0.0,
                    time_to_collision=float('inf'),
                    warning_message='安全',
                    nearest_object=None
                )
            
            # 找到最近的物体
            nearest_obj = min(self.detected_objects, key=lambda obj: obj.distance)
            
            # 根据距离和速度计算碰撞风险
            if nearest_obj.distance < 1.0:  # 1米内
                level = 'critical'
                message = '危险！请立即停止'
            elif nearest_obj.distance < 2.0:  # 2米内
                level = 'high'
                message = '警告：前方有障碍物'
            elif nearest_obj.distance < 3.0:  # 3米内
                level = 'medium'
                message = '注意：前方有物体'
            else:
                level = 'low'
                message = '安全'
            
            # 计算碰撞时间（简化计算）
            if nearest_obj.velocity[2] > 0.1:  # 物体正在接近
                time_to_collision = nearest_obj.distance / nearest_obj.velocity[2]
            else:
                time_to_collision = float('inf')
            
            # 计算总体碰撞概率
            if time_to_collision < 1.0:
                probability = 0.9
            elif time_to_collision < 2.0:
                probability = 0.7
            elif time_to_collision < 3.0:
                probability = 0.5
            else:
                probability = 0.1
            
            print(f"碰撞概率: {probability}")

            return CollisionRisk(
                level=level,
                probability=probability,
                time_to_collision=time_to_collision,
                warning_message=message,
                nearest_object=nearest_obj
            )
    
    def update_detected_objects(self, objects: List[DetectedObject]):
        """更新检测到的物体列表"""
        with self.lock:
            self.detected_objects = objects
    
    def get_detected_objects(self) -> List[DetectedObject]:
        """获取检测到的物体列表"""
        with self.lock:
            return self.detected_objects.copy()


class TrajectoryCollisionManager:
    """轨迹追踪和碰撞预警管理器"""
    
    def __init__(self):
        self.trajectory_tracker = TrajectoryTracker()
        self.collision_warning = CollisionWarning()
        self.yolo_model = None
        self.is_running = False
        self.processing_thread = None
        self.current_frame = None
        self.current_depth = None
        self.current_imu = None
        self.lock = threading.Lock()
        
        # 连接全局帧缓存
        try:
            from .global_frame_cache import get_global_frame_cache
            self.global_frame_cache = get_global_frame_cache()
            print("✅ 轨迹碰撞管理器已连接到全局帧缓存")
        except Exception as e:
            print(f"⚠️ 轨迹碰撞管理器连接全局帧缓存失败: {e}")
            self.global_frame_cache = None
        
        # 尝试加载YOLO模型
        try:
            self.yolo_model = YOLO('utils/yolov8l-seg.pt')
            print("✅ 轨迹碰撞管理器YOLO模型加载成功")
        except Exception as e:
            print(f"❌ 轨迹碰撞管理器YOLO模型加载失败: {e}")
            self.yolo_model = None
    
    def start(self):
        """启动服务"""
        if not self.is_running:
            self.is_running = True
            self.processing_thread = threading.Thread(target=self._processing_loop)
            self.processing_thread.start()
            print("轨迹追踪和碰撞预警服务已启动")
    
    def stop(self):
        """停止服务"""
        if self.is_running:
            self.is_running = False
            if self.processing_thread:
                self.processing_thread.join()
            print("轨迹追踪和碰撞预警服务已停止")
    
    def update_frame_data(self, frame: np.ndarray, depth: np.ndarray, imu_data: Any):
        """更新帧数据"""
        try:
            print(f"🔄 碰撞检测管理器接收帧数据:")
            print(f"  - 彩色图像: {frame.shape if frame is not None else 'None'}")
            print(f"  - 深度图像: {depth.shape if depth is not None else 'None'}")
            print(f"  - IMU数据: {type(imu_data) if imu_data is not None else 'None'}")
            print(f"  - 运行状态: {self.is_running}")
            
            if frame is None:
                print("⚠️ 彩色图像为空，跳过处理")
                return
                
            if depth is None:
                print("⚠️ 深度图像为空，跳过处理")
                return
            
            with self.lock:
                self.current_frame = frame
                self.current_depth = depth
                self.current_imu = imu_data
                print("✅ 帧数据更新完成")
                
        except Exception as e:
            print(f"❌ 更新帧数据时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def _processing_loop(self):
        """处理循环 - 直接从全局帧缓存获取数据"""
        print("🚀 轨迹碰撞管理器处理循环启动")
        
        while self.is_running:
            try:
                frame = None
                depth = None
                
                # 优先从全局帧缓存获取数据
                if self.global_frame_cache:
                    frame_data = self.global_frame_cache.get_current_frames(['color', 'depth'])
                    frame = frame_data.get('color')
                    depth = frame_data.get('depth')
                    
                    if frame is not None and depth is not None:
                        print(f"📡 从全局帧缓存获取数据: frame={frame.shape}, depth={depth.shape}")
                    else:
                        print("⚠️ 全局帧缓存中无有效数据")
                
                # 如果全局帧缓存无数据，回退到本地缓存
                if frame is None or depth is None:
                    with self.lock:
                        if self.current_frame is None or self.current_depth is None:
                            time.sleep(0.1)
                            continue
                        
                        frame = self.current_frame.copy()
                        depth = self.current_depth.copy()
                        print("📡 使用本地缓存数据")
                
                # 处理帧
                if frame is not None and depth is not None:
                    self._process_frame(frame, depth, None)
                
                # 控制处理频率
                time.sleep(0.1)  # 10 FPS，降低频率避免资源竞争
                
            except Exception as e:
                print(f"❌ 轨迹碰撞管理器处理帧时出错: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(0.5)
    
    def _process_frame(self, frame: np.ndarray, depth: np.ndarray, imu_data: Any):
        """处理单帧数据"""
        print(f"🔍 开始处理帧 - YOLO模型状态: {self.yolo_model is not None}")
        
        if self.yolo_model is None:
            print("❌ YOLO模型未加载")
            return
        
        # 检查图像尺寸是否匹配
        if frame.shape[:2] != depth.shape[:2]:
            print(f"⚠️ 图像尺寸不匹配: frame={frame.shape}, depth={depth.shape}")
            # 将深度图像调整为与彩色图像相同的尺寸
            import cv2
            depth = cv2.resize(depth, (frame.shape[1], frame.shape[0]))
            print(f"✅ 深度图像已调整为: {depth.shape}")
        
        current_time = time.time()
        
        # YOLO检测
        print("🎯 执行YOLO检测...")
        results = self.yolo_model.track(frame, persist=True, verbose=False)
        if not results:
            print("❌ YOLO检测无结果")
            return
        
        print(f"✅ YOLO检测完成，结果数量: {len(results)}")
        
        result = results[0]
        active_ids = []
        detected_objects = []
        
        print(f"📊 检测到的物体数量: {len(result.boxes)}")
        
        # 处理检测结果
        for i in range(len(result.boxes)):
            box = result.boxes[i]
            
            # 获取类别名称
            cls_id = int(box.cls.cpu())
            name = result.names[cls_id]
            conf = float(box.conf.cpu())
            
            print(f"  物体 {i}: {name} (置信度: {conf:.2f})")
            
            # # 只处理人
            # if name != 'person':
            #     print(f"    ❌ 跳过非人类物体: {name}")
            #     continue
            
            # 获取ID
            if result.boxes.id is not None:
                obj_id = int(result.boxes.id[i].cpu())
            else:
                obj_id = i
            
            active_ids.append(obj_id)
            
            # 获取边界框
            bbox = box.xyxy.cpu().numpy()[0]
            
            # 获取掩码（如果有）
            if hasattr(result, 'masks') and result.masks is not None and i < len(result.masks):
                mask = result.masks[i].data[0].cpu().numpy()
                
                # 确保掩码尺寸与深度图像匹配
                if mask.shape != depth.shape[:2]:
                    print(f"⚠️ 掩码尺寸不匹配: mask={mask.shape}, depth={depth.shape[:2]}")
                    import cv2
                    # 将掩码调整为与深度图像相同的尺寸
                    mask = cv2.resize(mask.astype(np.float32), (depth.shape[1], depth.shape[0]))
                    # 重新二值化掩码
                    mask = (mask > 0.5).astype(np.uint8)
                    print(f"✅ 掩码已调整为: {mask.shape}")
            else:
                # 如果没有掩码，使用边界框创建一个，确保尺寸与深度图像匹配
                mask = np.zeros(depth.shape[:2], dtype=np.uint8)
                x1, y1, x2, y2 = bbox.astype(int)
                # 确保边界框坐标在图像范围内
                x1 = max(0, min(x1, depth.shape[1] - 1))
                y1 = max(0, min(y1, depth.shape[0] - 1))
                x2 = max(0, min(x2, depth.shape[1] - 1))
                y2 = max(0, min(y2, depth.shape[0] - 1))
                mask[y1:y2, x1:x2] = 1
            
            # 计算深度和位置
            rows, cols = np.where((mask == 1) & (depth > 0))
            print(f"    有效深度点数量: {len(rows)}")
            
            if len(rows) > 0:
                distances = depth[rows, cols]
                
                # 过滤深度值
                percentile_low = 5
                percentile_high = 85
                low_threshold = np.percentile(distances, percentile_low)
                high_threshold = np.percentile(distances, percentile_high)
                
                valid_mask = (distances >= low_threshold) & (distances <= high_threshold)
                print(f"    过滤后有效点数量: {np.sum(valid_mask)}")
                
                if np.any(valid_mask):
                    selected_distances = distances[valid_mask]
                    median_distance = np.median(selected_distances)
                    print(f"    中位距离: {median_distance:.1f}mm ({median_distance/1000:.2f}m)")
                    
                    # 计算BEV坐标（简化版本）
                    center_x = int((bbox[0] + bbox[2]) / 2)
                    center_y = int((bbox[1] + bbox[3]) / 2)
                    
                    # 转换到BEV坐标系
                    bev_x = 800 + (center_x - 320) * median_distance / 1000
                    bev_y = 800 - median_distance / 10
                    
                    # 生成颜色
                    color = self._generate_color(obj_id)
                    
                    # 更新轨迹
                    self.trajectory_tracker.update_track(
                        obj_id, name, (bev_x, bev_y), 
                        current_time, color, median_distance / 1000
                    )
                    
                    # 创建检测对象
                    detected_obj = DetectedObject(
                        id=obj_id,
                        type=name,
                        position=(bev_x, bev_y, median_distance / 1000),
                        distance=median_distance / 1000,
                        velocity=(0, 0, 0),  # 将从轨迹计算
                        confidence=float(box.conf.cpu()),
                        timestamp=current_time
                    )
                    detected_objects.append(detected_obj)
        
        # 清理过期轨迹
        self.trajectory_tracker.clean_expired_tracks(current_time, active_ids)
        
        # 获取所有轨迹
        tracks = self.trajectory_tracker.get_tracks()
        
        print(f"🎯 活跃轨迹数量: {len(tracks)}")
        print(f"🔍 检测到的物体数量: {len(detected_objects)}")
        
        # 计算碰撞概率
        self.collision_warning.calculate_collision_probability(tracks)
        
        # 更新检测到的物体（带速度信息）
        for obj in detected_objects:
            if obj.id in tracks:
                track = tracks[obj.id]
                obj.velocity = track.speed
                print(f"  物体 {obj.id}: 碰撞概率={track.collision_probability:.3f}")
        
        self.collision_warning.update_detected_objects(detected_objects)
        
        # 输出最终结果
        max_prob = max([track.collision_probability for track in tracks.values()]) if tracks else 0.0
        print(f"💥 最大碰撞概率: {max_prob:.3f} ({max_prob*100:.1f}%)")
    
    def _generate_color(self, seed: int) -> Tuple[int, int, int]:
        """生成随机颜色"""
        np.random.seed(seed)
        return tuple(np.random.randint(0, 255, 3).tolist())
    
    def get_collision_data(self) -> Dict[str, Any]:
        """获取碰撞数据用于前端显示"""
        tracks = self.trajectory_tracker.get_tracks()
        
        # 找到最高碰撞概率
        max_probability = 0.0
        if tracks:
            max_probability = max(track.collision_probability for track in tracks.values())
        
        # 获取碰撞风险
        risk = self.collision_warning.get_collision_risk()
        
        # 安全处理time_to_collision值
        safe_time_to_collision = None
        if risk.time_to_collision != float('inf') and risk.time_to_collision != float('-inf') and risk.time_to_collision == risk.time_to_collision:
            safe_time_to_collision = risk.time_to_collision
        
        return {
            'max_probability': max_probability,
            'risk_level': risk.level,
            'time_to_collision': safe_time_to_collision,
            'warning_message': risk.warning_message,
            'tracks': self.trajectory_tracker.get_trajectory_data(),
            'detected_objects': [
                {
                    'id': obj.id,
                    'type': obj.type,
                    'distance': obj.distance,
                    'position': obj.position
                }
                for obj in self.collision_warning.get_detected_objects()
            ]
        }
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """获取综合状态"""
        tracks = self.trajectory_tracker.get_tracks()
        risk = self.collision_warning.get_collision_risk()
        
        return {
            'is_running': self.is_running,
            'model_loaded': self.yolo_model is not None,
            'active_tracks': len(tracks),
            'collision_risk': {
                'level': risk.level,
                'probability': risk.probability,
                'message': risk.warning_message
            },
            'timestamp': time.time()
        }


# 创建全局实例
trajectory_collision_manager = TrajectoryCollisionManager() 