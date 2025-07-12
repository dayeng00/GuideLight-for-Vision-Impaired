"""
轨迹追踪和碰撞预警模块
移植自PYQT应用中的相关功能
"""

import numpy as np
import time
import math
import threading
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import deque
import logging

logger = logging.getLogger(__name__)

@dataclass
class TrajectoryPoint:
    """轨迹点数据"""
    lng: float
    lat: float
    timestamp: float
    speed: float = 0.0
    direction: float = 0.0  # 方向角（度）
    altitude: float = 0.0
    accuracy: float = 0.0

@dataclass
class DetectedObject:
    """检测到的物体"""
    id: str
    type: str  # 'person', 'vehicle', 'obstacle', etc.
    position: Tuple[float, float]  # (lng, lat)
    distance: float  # 距离（米）
    velocity: Tuple[float, float] = (0.0, 0.0)  # 速度向量
    confidence: float = 0.0
    timestamp: float = 0.0

@dataclass
class CollisionRisk:
    """碰撞风险"""
    level: str  # 'low', 'medium', 'high', 'critical'
    probability: float  # 0-100
    time_to_collision: float  # 预计碰撞时间（秒）
    nearest_object: Optional[DetectedObject] = None
    warning_message: str = ""

class TrajectoryTracker:
    """轨迹追踪器"""
    
    def __init__(self, max_history_points: int = 100):
        self.max_history_points = max_history_points
        self.trajectory_history: deque[TrajectoryPoint] = deque(maxlen=max_history_points)
        self.current_position: Optional[TrajectoryPoint] = None
        self.is_tracking = False
        self.tracking_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        
    def start_tracking(self):
        """开始轨迹追踪"""
        if self.is_tracking:
            return
            
        self.is_tracking = True
        self.tracking_thread = threading.Thread(target=self._tracking_loop)
        self.tracking_thread.daemon = True
        self.tracking_thread.start()
        logger.info("轨迹追踪已启动")
        
    def stop_tracking(self):
        """停止轨迹追踪"""
        self.is_tracking = False
        if self.tracking_thread:
            self.tracking_thread.join(timeout=1.0)
        logger.info("轨迹追踪已停止")
        
    def _tracking_loop(self):
        """轨迹追踪循环"""
        while self.is_tracking:
            try:
                # 模拟获取GPS数据
                current_time = time.time()
                
                # 生成模拟轨迹点
                if self.current_position is None:
                    # 初始位置（合肥工业大学）
                    self.current_position = TrajectoryPoint(
                        lng=117.283042,
                        lat=31.844786,
                        timestamp=current_time
                    )
                else:
                    # 生成下一个位置（模拟移动）
                    self.current_position = self._generate_next_position()
                
                # 添加到历史记录
                with self.lock:
                    self.trajectory_history.append(self.current_position)
                
                time.sleep(1.0)  # 每秒更新一次
                
            except Exception as e:
                logger.error(f"轨迹追踪循环错误: {e}")
                time.sleep(0.5)
                
    def _generate_next_position(self) -> TrajectoryPoint:
        """生成下一个位置（模拟移动）"""
        if not self.trajectory_history:
            return self.current_position
            
        # 计算移动增量
        speed_kmh = 5.0  # 模拟步行速度 5km/h
        speed_ms = speed_kmh * 1000 / 3600  # 转换为米/秒
        
        # 随机方向变化
        direction_change = np.random.uniform(-30, 30)  # 最大30度变化
        current_direction = self.current_position.direction + direction_change
        
        # 计算位置增量
        distance_m = speed_ms * 1.0  # 1秒的移动距离
        
        # 地理坐标增量计算
        lat_change = (distance_m * math.cos(math.radians(current_direction))) / 111000  # 1度纬度约111km
        lng_change = (distance_m * math.sin(math.radians(current_direction))) / (111000 * math.cos(math.radians(self.current_position.lat)))
        
        new_position = TrajectoryPoint(
            lng=self.current_position.lng + lng_change,
            lat=self.current_position.lat + lat_change,
            timestamp=time.time(),
            speed=speed_ms,
            direction=current_direction
        )
        
        return new_position
        
    def get_current_position(self) -> Optional[TrajectoryPoint]:
        """获取当前位置"""
        with self.lock:
            return self.current_position
            
    def get_trajectory_history(self) -> List[TrajectoryPoint]:
        """获取轨迹历史"""
        with self.lock:
            return list(self.trajectory_history)
            
    def get_trajectory_data(self) -> Dict[str, Any]:
        """获取轨迹数据"""
        with self.lock:
            history = list(self.trajectory_history)
            
        if not history:
            return {"points": [], "total_distance": 0.0, "average_speed": 0.0}
            
        # 计算总距离
        total_distance = 0.0
        for i in range(1, len(history)):
            distance = self._calculate_distance(
                history[i-1].lat, history[i-1].lng,
                history[i].lat, history[i].lng
            )
            total_distance += distance
            
        # 计算平均速度
        if len(history) > 1:
            time_span = history[-1].timestamp - history[0].timestamp
            average_speed = total_distance / time_span if time_span > 0 else 0.0
        else:
            average_speed = 0.0
            
        return {
            "points": [
                {
                    "lng": point.lng,
                    "lat": point.lat,
                    "timestamp": point.timestamp,
                    "speed": point.speed,
                    "direction": point.direction
                }
                for point in history
            ],
            "total_distance": total_distance,
            "average_speed": average_speed,
            "current_position": {
                "lng": history[-1].lng,
                "lat": history[-1].lat,
                "timestamp": history[-1].timestamp
            } if history else None
        }
        
    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """计算两点间距离（米）"""
        R = 6371000  # 地球半径（米）
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_lat/2) * math.sin(delta_lat/2) +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lng/2) * math.sin(delta_lng/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c


class CollisionWarningSystem:
    """碰撞预警系统"""
    
    def __init__(self, trajectory_tracker: TrajectoryTracker):
        self.trajectory_tracker = trajectory_tracker
        self.detected_objects: List[DetectedObject] = []
        self.collision_risk: CollisionRisk = CollisionRisk(
            level='low',
            probability=0.0,
            time_to_collision=float('inf')
        )
        self.is_active = False
        self.warning_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        
        # 风险阈值配置
        self.risk_thresholds = {
            'critical': {'distance': 5.0, 'time': 2.0},    # 5米或2秒内
            'high': {'distance': 10.0, 'time': 5.0},       # 10米或5秒内
            'medium': {'distance': 20.0, 'time': 10.0},    # 20米或10秒内
            'low': {'distance': 50.0, 'time': 20.0}        # 50米或20秒内
        }
        
    def start_monitoring(self):
        """开始碰撞监控"""
        if self.is_active:
            return
            
        self.is_active = True
        self.warning_thread = threading.Thread(target=self._monitoring_loop)
        self.warning_thread.daemon = True
        self.warning_thread.start()
        logger.info("碰撞预警系统已启动")
        
    def stop_monitoring(self):
        """停止碰撞监控"""
        self.is_active = False
        if self.warning_thread:
            self.warning_thread.join(timeout=1.0)
        logger.info("碰撞预警系统已停止")
        
    def _monitoring_loop(self):
        """监控循环"""
        while self.is_active:
            try:
                # 获取当前位置
                current_pos = self.trajectory_tracker.get_current_position()
                if current_pos is None:
                    time.sleep(0.1)
                    continue
                    
                # 生成模拟检测对象
                self._generate_simulated_objects(current_pos)
                
                # 计算碰撞风险
                self._calculate_collision_risk(current_pos)
                
                time.sleep(0.1)  # 10Hz频率
                
            except Exception as e:
                logger.error(f"碰撞监控循环错误: {e}")
                time.sleep(0.5)
                
    def _generate_simulated_objects(self, current_pos: TrajectoryPoint):
        """生成模拟检测对象"""
        simulated_objects = []
        current_time = time.time()
        
        # 生成随机的模拟对象
        for i in range(np.random.randint(0, 5)):  # 0-4个对象
            # 随机位置（在当前位置周围）
            distance = np.random.uniform(5, 100)  # 5-100米
            angle = np.random.uniform(0, 360)  # 随机角度
            
            # 计算对象位置
            lat_offset = (distance * math.cos(math.radians(angle))) / 111000
            lng_offset = (distance * math.sin(math.radians(angle))) / (111000 * math.cos(math.radians(current_pos.lat)))
            
            obj_pos = (
                current_pos.lng + lng_offset,
                current_pos.lat + lat_offset
            )
            
            # 随机对象类型
            obj_types = ['person', 'vehicle', 'obstacle', 'cyclist']
            obj_type = np.random.choice(obj_types)
            
            detected_obj = DetectedObject(
                id=f"obj_{i}_{int(current_time)}",
                type=obj_type,
                position=obj_pos,
                distance=distance,
                velocity=(np.random.uniform(-2, 2), np.random.uniform(-2, 2)),
                confidence=np.random.uniform(0.7, 1.0),
                timestamp=current_time
            )
            
            simulated_objects.append(detected_obj)
            
        with self.lock:
            self.detected_objects = simulated_objects
            
    def _calculate_collision_risk(self, current_pos: TrajectoryPoint):
        """计算碰撞风险"""
        if not self.detected_objects:
            risk = CollisionRisk(
                level='low',
                probability=0.0,
                time_to_collision=float('inf')
            )
            with self.lock:
                self.collision_risk = risk
            return
            
        # 找到最近的对象
        nearest_obj = min(self.detected_objects, key=lambda obj: obj.distance)
        
        # 计算碰撞概率
        min_distance = nearest_obj.distance
        
        # 预测碰撞时间
        if nearest_obj.velocity[0] != 0 or nearest_obj.velocity[1] != 0:
            # 基于速度预测
            relative_speed = math.sqrt(
                (current_pos.speed - nearest_obj.velocity[0])**2 +
                (0 - nearest_obj.velocity[1])**2
            )
            time_to_collision = min_distance / relative_speed if relative_speed > 0 else float('inf')
        else:
            time_to_collision = float('inf')
            
        # 根据距离和时间确定风险级别
        if min_distance <= self.risk_thresholds['critical']['distance'] or time_to_collision <= self.risk_thresholds['critical']['time']:
            level = 'critical'
            probability = min(95, 100 - min_distance * 2)
        elif min_distance <= self.risk_thresholds['high']['distance'] or time_to_collision <= self.risk_thresholds['high']['time']:
            level = 'high'
            probability = min(80, 100 - min_distance * 1.5)
        elif min_distance <= self.risk_thresholds['medium']['distance'] or time_to_collision <= self.risk_thresholds['medium']['time']:
            level = 'medium'
            probability = min(60, 100 - min_distance)
        else:
            level = 'low'
            probability = max(0, 50 - min_distance)
            
        # 生成警告消息
        warning_message = self._generate_warning_message(level, nearest_obj, min_distance)
        
        risk = CollisionRisk(
            level=level,
            probability=probability,
            time_to_collision=time_to_collision,
            nearest_object=nearest_obj,
            warning_message=warning_message
        )
        
        with self.lock:
            self.collision_risk = risk
            
    def _generate_warning_message(self, level: str, nearest_obj: DetectedObject, distance: float) -> str:
        """生成警告消息"""
        obj_type_zh = {
            'person': '行人',
            'vehicle': '车辆',
            'obstacle': '障碍物',
            'cyclist': '自行车'
        }
        
        obj_name = obj_type_zh.get(nearest_obj.type, '物体')
        
        if level == 'critical':
            return f"紧急警告！前方{distance:.1f}米处有{obj_name}，请立即停止或改变方向！"
        elif level == 'high':
            return f"高风险警告！前方{distance:.1f}米处有{obj_name}，请注意避让！"
        elif level == 'medium':
            return f"中度风险：前方{distance:.1f}米处有{obj_name}，请保持警惕！"
        else:
            return f"低风险：前方{distance:.1f}米处有{obj_name}，请注意观察！"
            
    def get_collision_risk(self) -> CollisionRisk:
        """获取当前碰撞风险"""
        with self.lock:
            return self.collision_risk
            
    def get_detected_objects(self) -> List[DetectedObject]:
        """获取检测到的对象"""
        with self.lock:
            return self.detected_objects.copy()
            
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        with self.lock:
            risk = self.collision_risk
            objects = self.detected_objects.copy()
            
        return {
            'active': self.is_active,
            'collision_risk': {
                'level': risk.level,
                'probability': risk.probability,
                'time_to_collision': risk.time_to_collision,
                'warning_message': risk.warning_message,
                'nearest_object': {
                    'type': risk.nearest_object.type,
                    'distance': risk.nearest_object.distance,
                    'confidence': risk.nearest_object.confidence
                } if risk.nearest_object else None
            },
            'detected_objects': [
                {
                    'id': obj.id,
                    'type': obj.type,
                    'distance': obj.distance,
                    'position': obj.position,
                    'confidence': obj.confidence
                }
                for obj in objects
            ]
        }


class TrajectoryCollisionManager:
    """轨迹追踪和碰撞预警管理器"""
    
    def __init__(self):
        self.trajectory_tracker = TrajectoryTracker()
        self.collision_warning = CollisionWarningSystem(self.trajectory_tracker)
        self.is_active = False
        
    def start(self):
        """启动系统"""
        if self.is_active:
            return
            
        self.trajectory_tracker.start_tracking()
        self.collision_warning.start_monitoring()
        self.is_active = True
        logger.info("轨迹追踪和碰撞预警系统已启动")
        
    def stop(self):
        """停止系统"""
        if not self.is_active:
            return
            
        self.trajectory_tracker.stop_tracking()
        self.collision_warning.stop_monitoring()
        self.is_active = False
        logger.info("轨迹追踪和碰撞预警系统已停止")
        
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """获取综合状态"""
        trajectory_data = self.trajectory_tracker.get_trajectory_data()
        collision_status = self.collision_warning.get_status()
        
        return {
            'system_active': self.is_active,
            'trajectory': trajectory_data,
            'collision_warning': collision_status,
            'timestamp': time.time()
        } 