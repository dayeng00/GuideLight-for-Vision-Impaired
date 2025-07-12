"""
YOLO目标检测和碰撞预警处理器
移植自HFUT-MVNS-main/System_V1的核心功能
"""

import cv2
import numpy as np
import math
import time
import threading
from ultralytics import YOLO
from scipy.spatial.transform import Rotation as R
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 摄像头参数
HFOV = 68.7938003540039
VFOV = 42.12409823672219

# YOLO检测的目标类别
LABELS_DICT = {
    0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 4: "airplane",
    5: "bus", 6: "train", 7: "truck", 8: "boat", 9: "traffic light",
    10: "fire hydrant", 11: "stop sign", 12: "parking meter", 13: "bench",
    56: "chair", 57: "couch", 58: "potted plant", 59: "bed", 60: "dining table",
    61: "toilet", 62: "tv", 63: "laptop", 67: "cell phone", 72: "refrigerator", 73: "book"
}

# 关注的目标类别
OBJECTS_OF_INTEREST = [LABELS_DICT[i] for i in 
                      [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 56, 57, 58, 59, 60, 61, 62, 63, 67, 68, 72, 73]]

class YOLOProcessor:
    def __init__(self, model_path='resources/yolo11n/yolo11n.pt'):
        """
        初始化YOLO处理器
        
        Args:
            model_path: YOLO模型路径
        """
        self.model = None
        self.model_path = model_path
        self.tracks = {}  # 轨迹跟踪
        self.speeds = {}  # 速度计算
        self.collision_probability = {}  # 碰撞概率
        self.is_running = False
        self.lock = threading.Lock()
        
        # 初始化模型
        self._load_model()
        
    def _load_model(self):
        """加载YOLO模型"""
        try:
            self.model = YOLO(self.model_path)
            logger.info(f"YOLO模型加载成功: {self.model_path}")
        except Exception as e:
            logger.error(f"YOLO模型加载失败: {e}")
            # 尝试使用备用模型
            try:
                self.model = YOLO('yolo11n.pt')
                logger.info("使用默认YOLO模型")
            except Exception as e2:
                logger.error(f"默认YOLO模型也加载失败: {e2}")
                raise
    
    def get_spatial_coordinates(self, dist, bbox, axis='x'):
        """
        计算空间坐标
        
        Args:
            dist: 距离数组
            bbox: 边界框数组
            axis: 坐标轴 ('x' 或 'y')
            
        Returns:
            坐标数组
        """
        if axis == 'x':
            center_pos = (bbox[:, 0] + bbox[:, 2]) / 2.0
            diff_from_center = 320 - center_pos
            cam_width = np.tan(np.radians(HFOV / 2)) * dist
            coord = cam_width * (diff_from_center / 320)
        elif axis == 'y':
            center_pos = (bbox[:, 1] + bbox[:, 3]) / 2.0
            diff_from_center = center_pos - 180
            cam_height = np.tan(np.radians(VFOV / 2)) * dist
            coord = cam_height * (diff_from_center / 180)
        else:
            raise ValueError("Axis must be 'x' or 'y'")
        
        return coord
    
    def calculate_azimuth_pitch(self, col, row, distance):
        """
        计算方位角和俯仰角
        
        Args:
            col: 列坐标
            row: 行坐标
            distance: 距离
            
        Returns:
            (azimuth_angle, pitch_angle): 方位角和俯仰角
        """
        dx = 320 - col
        dy = 160 - row
        
        if dx >= 0:
            azimuth_angle = np.degrees(np.arctan(dx / distance))
        else:
            azimuth_angle = 360 + np.degrees(np.arctan(dx / distance))
            
        if dy >= 0:
            pitch_angle = np.degrees(np.arctan(dy / distance))
        else:
            pitch_angle = np.degrees(np.arctan(dy / distance))
            
        return azimuth_angle, pitch_angle
    
    def create_bev_background(self):
        """创建BEV背景图像"""
        R = 800
        BEV = np.ones((2*R, 2*R, 3), np.uint8) * 100
        
        # 绘制同心圆
        cv2.circle(BEV, (R, R), radius=50, color=(0, 0, 233), thickness=1)
        cv2.circle(BEV, (R, R), radius=100, color=(133, 133, 133), thickness=2)
        cv2.circle(BEV, (R, R), radius=300, color=(133, 133, 133), thickness=2)
        cv2.circle(BEV, (R, R), radius=500, color=(133, 133, 133), thickness=2)
        cv2.circle(BEV, (R, R), radius=800, color=(133, 133, 133), thickness=2)
        
        return BEV
    
    def process_frame(self, img_bgr, img_depth=None, imu_data=None):
        """
        处理单帧图像
        
        Args:
            img_bgr: BGR图像
            img_depth: 深度图像（可选）
            imu_data: IMU数据（可选）
            
        Returns:
            处理结果字典
        """
        if self.model is None:
            return None
            
        current_time = time.time()
        
        # YOLO目标检测和跟踪
        results = self.model.track(img_bgr, persist=True, verbose=False)[0]
        
        # 提取检测结果
        detections = []
        azimuth_pitch_data = []
        
        with self.lock:
            for i in range(len(results.boxes) if results.boxes is not None else 0):
                box = results.boxes[i]
                
                # 获取类别名称
                class_id = int(box.cls.cpu().numpy()[0])
                class_name = LABELS_DICT.get(class_id, "unknown")
                
                # 只处理感兴趣的目标
                if class_name not in OBJECTS_OF_INTEREST:
                    continue
                
                # 获取边界框坐标
                bbox = box.xyxy.cpu().numpy()[0].astype(int)
                confidence = float(box.conf.cpu().numpy()[0])
                
                detection = {
                    'class_name': class_name,
                    'bbox': bbox.tolist(),
                    'confidence': confidence,
                    'center': [(bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2]
                }
                
                # 如果有深度信息，计算3D位置
                if img_depth is not None and results.masks is not None and i < len(results.masks):
                    mask = results.masks[i].data[0][12:-12, :].int().cpu().numpy()
                    
                    # 计算深度信息
                    rows, cols = np.where((mask == 1) & (img_depth != 0))
                    if len(rows) > 0:
                        distances = img_depth[rows, cols]
                        
                        # 使用百分位数过滤异常值
                        low_threshold = np.percentile(distances, 10)
                        high_threshold = np.percentile(distances, 85)
                        
                        valid_mask = (distances >= low_threshold) & (distances <= high_threshold)
                        selected_rows = rows[valid_mask]
                        selected_cols = cols[valid_mask]
                        selected_distances = distances[valid_mask]
                        
                        if len(selected_distances) > 0:
                            col = np.median(selected_cols)
                            row = np.median(selected_rows)
                            dist = np.median(selected_distances)
                            
                            # 计算方位角和俯仰角
                            azimuth_angle, pitch_angle = self.calculate_azimuth_pitch(col, row, dist)
                            
                            detection.update({
                                'distance': float(dist),
                                'azimuth_angle': float(azimuth_angle),
                                'pitch_angle': float(pitch_angle),
                                'spatial_position': [float(col), float(row)]
                            })
                            
                            azimuth_pitch_data.append([class_name, azimuth_angle, pitch_angle, dist])
                            
                            # 计算空间坐标用于轨迹跟踪
                            if imu_data is not None:
                                bboxes = np.column_stack([selected_cols, selected_rows, selected_cols, selected_rows])
                                Xs = self.get_spatial_coordinates(selected_distances, bboxes, 'x') / 10
                                Ys = self.get_spatial_coordinates(selected_distances, bboxes, 'y') / 10
                                Zs = selected_distances / 10
                                points = np.column_stack((Ys, Xs, Zs))
                                
                                # 应用IMU旋转
                                if hasattr(imu_data, 'rotationVector'):
                                    quat = np.array([
                                        imu_data.rotationVector.i,
                                        imu_data.rotationVector.j,
                                        imu_data.rotationVector.k,
                                        imu_data.rotationVector.real
                                    ])
                                    rotation = R.from_quat(quat)
                                    rotated_points = rotation.apply(points)
                                    
                                    # 转换坐标系
                                    coords = rotated_points[:, :2]
                                    coords[:, 0] += 800
                                    coords[:, 1] = -coords[:, 1] + 800
                                    coords = coords.astype(int)
                                    
                                    if coords.size > 0 and results.boxes.id is not None:
                                        track_id = int(results.boxes.id[i].cpu().numpy())
                                        self._update_track(track_id, coords, current_time)
                
                detections.append(detection)
            
            # 更新轨迹和计算碰撞概率
            collision_risk = self._calculate_collision_probability(current_time)
            
            # 清理过期轨迹
            self._cleanup_tracks(current_time)
        
        # 生成BEV图像
        bev_image = self._generate_bev_image()
        
        return {
            'detections': detections,
            'azimuth_pitch_data': azimuth_pitch_data,
            'collision_risk': collision_risk,
            'bev_image': bev_image,
            'tracks': dict(self.tracks),
            'timestamp': current_time
        }
    
    def _update_track(self, track_id, coords, timestamp):
        """更新轨迹信息"""
        if track_id not in self.tracks:
            self.tracks[track_id] = []
        
        # 添加新的轨迹点
        median_x = np.median(coords[:, 0])
        median_y = np.median(coords[:, 1])
        self.tracks[track_id].append((median_x, median_y, timestamp))
        
        # 限制轨迹长度
        if len(self.tracks[track_id]) > 90:
            self.tracks[track_id].pop(0)
    
    def _calculate_collision_probability(self, current_time):
        """计算碰撞概率"""
        collision_probs = {}
        
        for track_id, track in self.tracks.items():
            if len(track) >= 5:
                # 计算最近5个点的速度
                recent_track = track[-5:]
                velocities_x = []
                velocities_y = []
                
                for i in range(len(recent_track) - 1):
                    x1, y1, t1 = recent_track[i]
                    x2, y2, t2 = recent_track[i + 1]
                    
                    distance_x = x2 - x1
                    distance_y = y2 - y1
                    time_diff = max(0.01, t2 - t1)
                    
                    velocities_x.append(distance_x / time_diff)
                    velocities_y.append(distance_y / time_diff)
                
                # 计算平均速度
                avg_vel_x = np.mean(velocities_x)
                avg_vel_y = np.mean(velocities_y)
                speed = math.sqrt(avg_vel_x**2 + avg_vel_y**2)
                
                self.speeds[track_id] = (avg_vel_x, avg_vel_y, speed)
                
                # 预测碰撞
                collision_time = -1
                last_pos = track[-1]
                
                for t in range(1, 16):  # 预测未来1.5秒
                    predicted_x = avg_vel_x * t / 10 + last_pos[0]
                    predicted_y = avg_vel_y * t / 10 + last_pos[1]
                    
                    # 计算与中心点的距离
                    dist_to_center = math.sqrt((predicted_x - 800)**2 + (predicted_y - 800)**2)
                    
                    if dist_to_center < 50:  # 50像素碰撞半径
                        collision_time = t
                        break
                
                if collision_time == -1:
                    collision_probs[track_id] = 0
                else:
                    collision_probs[track_id] = (16 - collision_time) / 15
        
        self.collision_probability = collision_probs
        
        # 返回最高碰撞概率
        return max(collision_probs.values()) if collision_probs else 0
    
    def _cleanup_tracks(self, current_time):
        """清理过期轨迹"""
        expired_tracks = []
        
        for track_id, track in self.tracks.items():
            if track:
                last_time = track[-1][2]
                if current_time - last_time > 3:  # 3秒未更新则删除
                    expired_tracks.append(track_id)
        
        for track_id in expired_tracks:
            del self.tracks[track_id]
            if track_id in self.speeds:
                del self.speeds[track_id]
            if track_id in self.collision_probability:
                del self.collision_probability[track_id]
    
    def _generate_bev_image(self):
        """生成BEV鸟瞰图"""
        bev = self.create_bev_background()
        
        # 绘制轨迹
        for track_id, track in self.tracks.items():
            if len(track) > 1:
                # 绘制轨迹线
                points = np.array([(int(x), int(y)) for x, y, _ in track])
                cv2.polylines(bev, [points], False, (0, 255, 0), 2)
                
                # 绘制当前位置
                if track:
                    current_pos = track[-1]
                    cv2.circle(bev, (int(current_pos[0]), int(current_pos[1])), 8, (0, 0, 255), -1)
                    
                    # 显示碰撞概率
                    if track_id in self.collision_probability:
                        prob = self.collision_probability[track_id]
                        color = (0, 255, 0) if prob < 0.3 else (0, 255, 255) if prob < 0.7 else (0, 0, 255)
                        cv2.putText(bev, f"{prob:.2f}", 
                                  (int(current_pos[0]), int(current_pos[1]) - 10),
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        return bev
    
    def get_collision_risk_level(self):
        """获取碰撞风险等级"""
        if not self.collision_probability:
            return "low"
        
        max_prob = max(self.collision_probability.values())
        
        if max_prob < 0.1:
            return "low"
        elif max_prob < 0.3:
            return "medium"
        elif max_prob < 0.5:
            return "high"
        else:
            return "critical"
    
    def get_status(self):
        """获取处理器状态"""
        return {
            'model_loaded': self.model is not None,
            'active_tracks': len(self.tracks),
            'collision_risk': self.get_collision_risk_level(),
            'max_collision_probability': max(self.collision_probability.values()) if self.collision_probability else 0
        } 