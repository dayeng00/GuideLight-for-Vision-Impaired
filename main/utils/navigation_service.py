"""
导航服务模块
移植自HFUT-MVNS-main/System_V1的导航功能
"""

import requests
import json
import time
import logging
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import threading

logger = logging.getLogger(__name__)

@dataclass
class Location:
    """位置信息"""
    latitude: float
    longitude: float
    address: str = ""
    name: str = ""

@dataclass
class RouteStep:
    """路径步骤"""
    instruction: str
    distance: float
    duration: float
    start_location: Location
    end_location: Location
    polyline: str = ""

@dataclass
class Route:
    """路径信息"""
    steps: List[RouteStep]
    total_distance: float
    total_duration: float
    overview_polyline: str = ""
    bounds: Dict = None

class AmapService:
    """高德地图服务"""
    
    def __init__(self, api_key: str = "ac5e6845a081b25303b11702c3196f50"):
        """
        初始化高德地图服务
        
        Args:
            api_key: 高德地图API密钥
        """
        self.api_key = api_key
        self.base_url = "https://restapi.amap.com/v3"
        self.session = requests.Session()
        self.session.timeout = 10
        
        # 默认城市
        self.default_city = "合肥"
        
        # 缓存
        self.geocode_cache = {}
        self.route_cache = {}
        
    def geocode(self, address: str, city: str = None) -> Optional[Location]:
        """
        地理编码：地址转坐标
        
        Args:
            address: 地址
            city: 城市
            
        Returns:
            位置信息
        """
        if not city:
            city = self.default_city
            
        # 检查缓存
        cache_key = f"{city}:{address}"
        if cache_key in self.geocode_cache:
            return self.geocode_cache[cache_key]
        
        try:
            url = f"{self.base_url}/geocode/geo"
            params = {
                'key': self.api_key,
                'address': address,
                'city': city,
                'output': 'json'
            }
            
            response = self.session.get(url, params=params)
            data = response.json()
            
            if data.get('status') == '1' and data.get('geocodes'):
                geocode = data['geocodes'][0]
                location_str = geocode.get('location', '')
                
                if location_str:
                    lng, lat = map(float, location_str.split(','))
                    location = Location(
                        latitude=lat,
                        longitude=lng,
                        address=geocode.get('formatted_address', address),
                        name=address
                    )
                    
                    # 缓存结果
                    self.geocode_cache[cache_key] = location
                    return location
            
            logger.warning(f"地理编码失败: {address}")
            return None
            
        except Exception as e:
            logger.error(f"地理编码请求失败: {e}")
            return None
    
    def reverse_geocode(self, latitude: float, longitude: float) -> Optional[str]:
        """
        逆地理编码：坐标转地址
        
        Args:
            latitude: 纬度
            longitude: 经度
            
        Returns:
            地址字符串
        """
        try:
            url = f"{self.base_url}/geocode/regeo"
            params = {
                'key': self.api_key,
                'location': f"{longitude},{latitude}",
                'output': 'json',
                'radius': 1000,
                'extensions': 'base'
            }
            
            response = self.session.get(url, params=params)
            data = response.json()
            
            if data.get('status') == '1' and data.get('regeocode'):
                return data['regeocode'].get('formatted_address', '')
            
            return None
            
        except Exception as e:
            logger.error(f"逆地理编码请求失败: {e}")
            return None
    
    def get_walking_route(self, start: Location, end: Location) -> Optional[Route]:
        """
        获取步行路径
        
        Args:
            start: 起点
            end: 终点
            
        Returns:
            路径信息
        """
        try:
            # 检查缓存
            cache_key = f"{start.longitude},{start.latitude}:{end.longitude},{end.latitude}"
            if cache_key in self.route_cache:
                return self.route_cache[cache_key]
            
            url = f"{self.base_url}/direction/walking"
            params = {
                'key': self.api_key,
                'origin': f"{start.longitude},{start.latitude}",
                'destination': f"{end.longitude},{end.latitude}",
                'output': 'json'
            }
            
            response = self.session.get(url, params=params)
            data = response.json()
            
            if data.get('status') == '1' and data.get('route'):
                route_data = data['route']
                paths = route_data.get('paths', [])
                
                if paths:
                    path = paths[0]
                    steps_data = path.get('steps', [])
                    
                    steps = []
                    for step_data in steps_data:
                        # 解析步骤坐标
                        polyline = step_data.get('polyline', '')
                        coordinates = self._parse_polyline(polyline)
                        
                        if coordinates:
                            start_coord = coordinates[0]
                            end_coord = coordinates[-1]
                            
                            step = RouteStep(
                                instruction=step_data.get('instruction', ''),
                                distance=float(step_data.get('distance', 0)),
                                duration=float(step_data.get('duration', 0)),
                                start_location=Location(start_coord[1], start_coord[0]),
                                end_location=Location(end_coord[1], end_coord[0]),
                                polyline=polyline
                            )
                            steps.append(step)
                    
                    route = Route(
                        steps=steps,
                        total_distance=float(path.get('distance', 0)),
                        total_duration=float(path.get('duration', 0)),
                        overview_polyline=path.get('polyline', '')
                    )
                    
                    # 缓存结果
                    self.route_cache[cache_key] = route
                    return route
            
            logger.warning("获取步行路径失败")
            return None
            
        except Exception as e:
            logger.error(f"获取步行路径请求失败: {e}")
            return None
    
    def _parse_polyline(self, polyline: str) -> List[Tuple[float, float]]:
        """
        解析polyline字符串为坐标列表
        
        Args:
            polyline: polyline字符串
            
        Returns:
            坐标列表
        """
        try:
            coordinates = []
            points = polyline.split(';')
            
            for point in points:
                if ',' in point:
                    lng, lat = map(float, point.split(','))
                    coordinates.append((lng, lat))
            
            return coordinates
            
        except Exception as e:
            logger.error(f"解析polyline失败: {e}")
            return []
    
    def search_nearby(self, location: Location, keywords: str, radius: int = 1000) -> List[Location]:
        """
        搜索附近地点
        
        Args:
            location: 中心位置
            keywords: 搜索关键词
            radius: 搜索半径（米）
            
        Returns:
            附近地点列表
        """
        try:
            url = f"{self.base_url}/place/around"
            params = {
                'key': self.api_key,
                'location': f"{location.longitude},{location.latitude}",
                'keywords': keywords,
                'radius': radius,
                'output': 'json'
            }
            
            response = self.session.get(url, params=params)
            data = response.json()
            
            places = []
            if data.get('status') == '1' and data.get('pois'):
                for poi in data['pois']:
                    location_str = poi.get('location', '')
                    if location_str:
                        lng, lat = map(float, location_str.split(','))
                        place = Location(
                            latitude=lat,
                            longitude=lng,
                            address=poi.get('address', ''),
                            name=poi.get('name', '')
                        )
                        places.append(place)
            
            return places
            
        except Exception as e:
            logger.error(f"搜索附近地点失败: {e}")
            return []

class NavigationService:
    """导航服务"""
    
    def __init__(self, api_key: str = "ac5e6845a081b25303b11702c3196f50"):
        """
        初始化导航服务
        
        Args:
            api_key: 高德地图API密钥
        """
        self.amap_service = AmapService(api_key)
        self.current_location = None
        self.current_route = None
        self.is_navigating = False
        self.navigation_thread = None
        
        # 导航状态
        self.current_step_index = 0
        self.navigation_start_time = None
        
        # 回调函数
        self.navigation_callbacks = {
            'step_changed': [],
            'destination_reached': [],
            'navigation_started': [],
            'navigation_stopped': []
        }
    
    def set_current_location(self, latitude: float, longitude: float, address: str = ""):
        """
        设置当前位置
        
        Args:
            latitude: 纬度
            longitude: 经度
            address: 地址
        """
        self.current_location = Location(latitude, longitude, address)
        logger.info(f"当前位置已更新: {latitude}, {longitude}")
    
    def start_navigation(self, destination: str) -> Dict:
        """
        开始导航
        
        Args:
            destination: 目的地
            
        Returns:
            导航结果
        """
        if not self.current_location:
            return {
                'success': False,
                'error': '当前位置未设置'
            }
        
        # 地理编码目的地
        dest_location = self.amap_service.geocode(destination)
        if not dest_location:
            return {
                'success': False,
                'error': f'无法找到目的地: {destination}'
            }
        
        # 获取路径
        route = self.amap_service.get_walking_route(self.current_location, dest_location)
        if not route:
            return {
                'success': False,
                'error': '无法规划路径'
            }
        
        # 开始导航
        self.current_route = route
        self.is_navigating = True
        self.current_step_index = 0
        self.navigation_start_time = time.time()
        
        # 启动导航线程
        self.navigation_thread = threading.Thread(target=self._navigation_loop)
        self.navigation_thread.daemon = True
        self.navigation_thread.start()
        
        # 触发回调
        self._trigger_callbacks('navigation_started', {
            'destination': destination,
            'route': route
        })
        
        return {
            'success': True,
            'destination': destination,
            'route': self._route_to_dict(route),
            'current_step': self._get_current_step()
        }
    
    def stop_navigation(self):
        """停止导航"""
        if self.is_navigating:
            self.is_navigating = False
            self.current_route = None
            self.current_step_index = 0
            
            # 等待导航线程结束
            if self.navigation_thread:
                self.navigation_thread.join(timeout=1)
            
            # 触发回调
            self._trigger_callbacks('navigation_stopped', {})
            
            logger.info("导航已停止")
    
    def _navigation_loop(self):
        """导航循环"""
        while self.is_navigating and self.current_route:
            try:
                # 检查是否到达目的地
                if self.current_step_index >= len(self.current_route.steps):
                    self._trigger_callbacks('destination_reached', {})
                    self.stop_navigation()
                    break
                
                # 模拟导航进度（实际应用中应该基于GPS位置）
                current_step = self.current_route.steps[self.current_step_index]
                
                # 检查是否应该进入下一步
                # 这里简化处理，实际应该基于用户位置
                time.sleep(5)  # 模拟每5秒进入下一步
                
                self.current_step_index += 1
                self._trigger_callbacks('step_changed', {
                    'step_index': self.current_step_index,
                    'current_step': self._get_current_step()
                })
                
            except Exception as e:
                logger.error(f"导航循环错误: {e}")
                time.sleep(1)
    
    def _get_current_step(self) -> Optional[Dict]:
        """获取当前步骤"""
        if not self.current_route or self.current_step_index >= len(self.current_route.steps):
            return None
        
        step = self.current_route.steps[self.current_step_index]
        return {
            'instruction': step.instruction,
            'distance': step.distance,
            'duration': step.duration,
            'remaining_steps': len(self.current_route.steps) - self.current_step_index - 1
        }
    
    def get_navigation_status(self) -> Dict:
        """获取导航状态"""
        if not self.is_navigating:
            return {
                'is_navigating': False,
                'current_location': self._location_to_dict(self.current_location) if self.current_location else None
            }
        
        elapsed_time = time.time() - self.navigation_start_time if self.navigation_start_time else 0
        
        return {
            'is_navigating': True,
            'current_location': self._location_to_dict(self.current_location) if self.current_location else None,
            'route': self._route_to_dict(self.current_route) if self.current_route else None,
            'current_step': self._get_current_step(),
            'step_index': self.current_step_index,
            'elapsed_time': elapsed_time
        }
    
    def search_destination(self, query: str) -> List[Dict]:
        """
        搜索目的地
        
        Args:
            query: 搜索关键词
            
        Returns:
            搜索结果列表
        """
        if not self.current_location:
            # 使用默认位置搜索
            default_location = Location(31.844786, 117.283042, "合肥工业大学")
            results = self.amap_service.search_nearby(default_location, query)
        else:
            results = self.amap_service.search_nearby(self.current_location, query)
        
        return [self._location_to_dict(loc) for loc in results]
    
    def get_address_from_coordinates(self, latitude: float, longitude: float) -> Optional[str]:
        """
        根据坐标获取地址
        
        Args:
            latitude: 纬度
            longitude: 经度
            
        Returns:
            地址字符串
        """
        return self.amap_service.reverse_geocode(latitude, longitude)
    
    def calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        计算两点间距离（米）
        
        Args:
            lat1, lng1: 第一个点的纬度和经度
            lat2, lng2: 第二个点的纬度和经度
            
        Returns:
            距离（米）
        """
        # 使用Haversine公式计算距离
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
    
    def add_navigation_callback(self, event: str, callback):
        """
        添加导航回调
        
        Args:
            event: 事件类型
            callback: 回调函数
        """
        if event in self.navigation_callbacks:
            self.navigation_callbacks[event].append(callback)
    
    def _trigger_callbacks(self, event: str, data: Dict):
        """触发回调"""
        if event in self.navigation_callbacks:
            for callback in self.navigation_callbacks[event]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"回调执行失败: {e}")
    
    def _location_to_dict(self, location: Location) -> Dict:
        """将Location对象转换为字典"""
        return {
            'latitude': location.latitude,
            'longitude': location.longitude,
            'address': location.address,
            'name': location.name
        }
    
    def _route_to_dict(self, route: Route) -> Dict:
        """将Route对象转换为字典"""
        return {
            'steps': [
                {
                    'instruction': step.instruction,
                    'distance': step.distance,
                    'duration': step.duration,
                    'start_location': self._location_to_dict(step.start_location),
                    'end_location': self._location_to_dict(step.end_location)
                }
                for step in route.steps
            ],
            'total_distance': route.total_distance,
            'total_duration': route.total_duration,
            'overview_polyline': route.overview_polyline
        }
    
    def get_status(self) -> Dict:
        """获取服务状态"""
        return {
            'service_available': True,
            'current_location_set': self.current_location is not None,
            'is_navigating': self.is_navigating,
            'cache_size': {
                'geocode': len(self.amap_service.geocode_cache),
                'route': len(self.amap_service.route_cache)
            }
        } 