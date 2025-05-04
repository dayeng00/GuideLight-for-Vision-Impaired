"""
位置模拟器
用于模拟用户在地图上行走的路径
"""

import math
import time
import random
import threading
from datetime import datetime

class LocationSimulator:
    """位置模拟器，可以模拟用户在地图上行走的路径"""
    
    def __init__(self, start_lat=39.9087, start_lng=116.3975, speed=1.0):
        """初始化位置模拟器
        
        Args:
            start_lat: 起始纬度（默认位置在北京）
            start_lng: 起始经度
            speed: 移动速度 (米/秒)
        """
        self.current_lat = start_lat
        self.current_lng = start_lng
        self.speed = speed  # 米/秒
        self.is_running = False
        self.simulation_thread = None
        self.route = []  # 存储路径点
        self.callbacks = []  # 位置更新回调函数列表
        self.lock = threading.Lock()
        
        # 行走模式相关参数
        self.direction = random.uniform(0, 2 * math.pi)  # 初始方向（弧度）
        self.direction_change_prob = 0.2  # 每次更新改变方向的概率
        self.max_direction_change = math.pi / 4  # 最大方向变化（弧度）
        
        # 添加起始点
        self.add_route_point(start_lat, start_lng)
    
    def add_route_point(self, lat, lng):
        """添加路径点"""
        with self.lock:
            self.route.append({
                'latitude': lat,
                'longitude': lng,
                'timestamp': datetime.now().isoformat()
            })
            # 只保留最近的100个点
            if len(self.route) > 100:
                self.route = self.route[-100:]
    
    def get_current_location(self):
        """获取当前位置"""
        with self.lock:
            return {
                'latitude': self.current_lat,
                'longitude': self.current_lng,
                'timestamp': datetime.now().isoformat(),
                'speed': self.speed
            }
    
    def get_route(self):
        """获取路径"""
        with self.lock:
            return list(self.route)  # 返回副本
    
    def _compute_new_position(self):
        """计算新位置
        
        基于当前速度和方向，计算新的经纬度坐标
        使用Haversine公式的逆运算
        """
        # 地球半径（米）
        R = 6371000.0
        
        # 可能改变方向
        if random.random() < self.direction_change_prob:
            # 随机改变方向，但不要太突然
            self.direction += random.uniform(
                -self.max_direction_change, 
                self.max_direction_change
            )
        
        # 每次更新移动的距离（米）
        distance = self.speed
        
        # 计算新的纬度
        new_lat = self.current_lat + (distance * math.cos(self.direction) / R) * (180.0 / math.pi)
        
        # 计算新的经度
        # 注意：在不同纬度，经度的距离不同
        new_lng = self.current_lng + (
            (distance * math.sin(self.direction) / R) * (180.0 / math.pi)
            / math.cos(self.current_lat * math.pi / 180.0)
        )
        
        return new_lat, new_lng
    
    def _simulation_loop(self):
        """模拟循环，更新位置"""
        while self.is_running:
            try:
                # 计算新位置
                new_lat, new_lng = self._compute_new_position()
                
                # 更新当前位置
                with self.lock:
                    self.current_lat = new_lat
                    self.current_lng = new_lng
                
                # 添加到路径
                self.add_route_point(new_lat, new_lng)
                
                # 调用回调函数
                location = self.get_current_location()
                for callback in self.callbacks:
                    try:
                        callback(location)
                    except Exception as e:
                        print(f"回调函数异常: {e}")
                
                # 等待一段时间再更新
                time.sleep(1.0)  # 每秒更新一次
                
            except Exception as e:
                print(f"模拟异常: {e}")
                time.sleep(1.0)
    
    def start_simulation(self):
        """开始模拟"""
        if self.is_running:
            print("模拟已在运行")
            return
        
        self.is_running = True
        self.simulation_thread = threading.Thread(target=self._simulation_loop)
        self.simulation_thread.daemon = True  # 设为守护线程
        self.simulation_thread.start()
        print("位置模拟已启动")
    
    def stop_simulation(self):
        """停止模拟"""
        if not self.is_running:
            print("模拟未运行")
            return
        
        self.is_running = False
        if self.simulation_thread:
            self.simulation_thread.join(timeout=2)
        print("位置模拟已停止")
    
    def set_speed(self, speed):
        """设置移动速度"""
        with self.lock:
            self.speed = max(0.1, min(20.0, speed))  # 限制速度范围
    
    def set_position(self, lat, lng):
        """手动设置当前位置"""
        with self.lock:
            self.current_lat = lat
            self.current_lng = lng
            self.add_route_point(lat, lng)
    
    def add_callback(self, callback_func):
        """添加位置更新回调函数
        
        回调函数应接受一个参数，即当前位置信息字典
        """
        self.callbacks.append(callback_func)
    
    def remove_callback(self, callback_func):
        """移除回调函数"""
        if callback_func in self.callbacks:
            self.callbacks.remove(callback_func)
    
    def set_destination(self, dest_lat, dest_lng, speed=None):
        """设置目的地，使模拟器向该目的地移动
        
        Args:
            dest_lat: 目的地纬度
            dest_lng: 目的地经度
            speed: 可选，移动速度
        """
        if speed is not None:
            self.set_speed(speed)
        
        # 计算方向（弧度）
        delta_lng = dest_lng - self.current_lng
        delta_lat = dest_lat - self.current_lat
        
        # 处理经度跨越180度的情况
        if delta_lng > 180:
            delta_lng -= 360
        elif delta_lng < -180:
            delta_lng += 360
        
        # 计算方向角度（以北为0度，顺时针）
        self.direction = math.atan2(
            delta_lng * math.cos(math.radians(self.current_lat)), 
            delta_lat
        )


# 示例用法
if __name__ == "__main__":
    # 创建模拟器（以北京为起点）
    simulator = LocationSimulator(start_lat=39.9087, start_lng=116.3975, speed=5.0)
    
    # 定义回调函数
    def location_callback(location):
        print(f"当前位置: 纬度 {location['latitude']:.6f}, 经度 {location['longitude']:.6f}")
    
    # 添加回调
    simulator.add_callback(location_callback)
    
    # 开始模拟
    simulator.start_simulation()
    
    try:
        # 运行一分钟后设置新目的地
        time.sleep(30)
        print("设置新目的地：天安门")
        simulator.set_destination(39.9073, 116.3913)
        
        time.sleep(30)
        print("增加速度")
        simulator.set_speed(10.0)
        
        time.sleep(30)
    except KeyboardInterrupt:
        pass
    finally:
        # 停止模拟
        simulator.stop_simulation() 