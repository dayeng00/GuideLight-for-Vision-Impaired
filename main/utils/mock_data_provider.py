"""
模拟数据提供器 - 为环境感知处理器提供测试数据
"""
import cv2
import numpy as np
import time
import threading
from typing import Optional


class MockDataProvider:
    """模拟数据提供器"""
    
    def __init__(self, global_frame_cache):
        self.global_frame_cache = global_frame_cache
        self.is_running = False
        self.thread = None
        self.stop_event = threading.Event()
        
        # 帧生成参数
        self.target_fps = 10
        self.frame_count = 0
        self.last_frame_time = time.time()
        self.current_fps = 0.0
        self.fps = 0.0  # 添加fps属性
        
        # 模拟对象
        self.objects = [
            {
                'type': 'person',
                'position': [320, 300],  # [x, y]
                'velocity': [2, 0],      # [vx, vy] 像素/帧
                'size': [30, 60],        # [width, height]
                'color': (0, 255, 0),    # BGR
                'distance': 2000,        # 毫米
                'id': 1
            },
            {
                'type': 'car',
                'position': [100, 250],
                'velocity': [3, 1],
                'size': [80, 40],
                'color': (255, 0, 0),
                'distance': 3000,
                'id': 2
            }
        ]
        
        print("🎭 模拟数据提供器初始化完成")
    
    def _update_object_positions(self):
        """更新对象位置"""
        for obj in self.objects:
            # 更新位置
            obj['position'][0] += obj['velocity'][0]
            obj['position'][1] += obj['velocity'][1]
            
            # 边界反弹
            if obj['position'][0] <= obj['size'][0]//2 or obj['position'][0] >= 640 - obj['size'][0]//2:
                obj['velocity'][0] *= -1
            if obj['position'][1] <= obj['size'][1] or obj['position'][1] >= 360:
                obj['velocity'][1] *= -1
            
            # 保持在边界内
            obj['position'][0] = max(obj['size'][0]//2, min(640 - obj['size'][0]//2, obj['position'][0]))
            obj['position'][1] = max(obj['size'][1], min(360, obj['position'][1]))
    
    def _generate_data_loop(self):
        """数据生成循环"""
        print("🎭 模拟数据生成器开始运行")
        
        while self.is_running:
            try:
                start_time = time.time()
                
                # 生成RGB图像
                rgb_image = self._generate_rgb_image()
                
                # 生成深度图像
                depth_image = self._generate_depth_image()
                
                # 更新全局帧缓存
                frame_data = {
                    'color': rgb_image,
                    'depth': depth_image,
                    'timestamp': time.time()
                }
                
                if self.global_frame_cache:
                    self.global_frame_cache.update_frames(frame_data)
                    
                    # 每100帧打印一次状态
                    if self.frame_count % 100 == 0:
                        print(f"🎭 模拟数据: 已生成 {self.frame_count} 帧, FPS: {self.current_fps:.1f}")
                else:
                    print("⚠️ 模拟数据: 全局帧缓存不可用")
                
                # 更新统计
                self.frame_count += 1
                self.last_frame_time = time.time()
                
                # 计算FPS
                elapsed = time.time() - start_time
                if elapsed > 0:
                    self.current_fps = 1.0 / elapsed
                
                # 控制帧率
                sleep_time = max(0, 1.0/self.target_fps - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            except Exception as e:
                print(f"⚠️ 模拟数据生成错误: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(0.1)
        
        print("🛑 模拟数据生成器停止运行")
    
    def start(self):
        """启动模拟数据生成"""
        if self.is_running:
            print("⚠️ 模拟数据生成器已在运行")
            return False
        
        self.is_running = True
        self.stop_event.clear()
        
        # 启动生成线程
        self.thread = threading.Thread(target=self._generate_data_loop, daemon=True)
        self.thread.start()
        
        print("✅ 模拟数据生成器启动成功")
        return True
    
    def stop(self):
        """停止模拟数据生成"""
        self.is_running = False
        self.stop_event.set()
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        
        print("🛑 模拟数据提供器已停止")
    
    def get_status(self):
        """获取模拟数据提供器状态"""
        return {
            'is_running': self.is_running,
            'frame_count': self.frame_count,
            'target_fps': self.target_fps,
            'current_fps': self.current_fps,
            'fps': self.current_fps,  # 使用current_fps作为fps
            'objects_count': len(self.objects)
        }

    def _generate_rgb_image(self):
        """生成RGB图像"""
        # 创建基础背景
        img = np.ones((360, 640, 3), dtype=np.uint8) * 50  # 深灰色背景
        
        # 添加地面纹理
        cv2.rectangle(img, (0, 250), (640, 360), (70, 70, 70), -1)
        
        # 更新对象位置
        self._update_object_positions()
        
        # 绘制移动对象
        for obj in self.objects:
            x, y = int(obj['position'][0]), int(obj['position'][1])
            w, h = obj['size']
            
            # 确保对象在图像范围内
            if 0 <= x < 640 and 0 <= y < 360:
                color = obj['color']
                
                if obj['type'] == 'person':
                    # 绘制简单的人形
                    cv2.rectangle(img, (x-w//2, y-h), (x+w//2, y), color, -1)
                    cv2.circle(img, (x, y-h-10), 8, color, -1)  # 头部
                elif obj['type'] == 'car':
                    # 绘制简单的车形
                    cv2.rectangle(img, (x-w//2, y-h), (x+w//2, y), color, -1)
                    # 车轮
                    cv2.circle(img, (x-w//3, y), 5, (0, 0, 0), -1)
                    cv2.circle(img, (x+w//3, y), 5, (0, 0, 0), -1)
        
        return img
    
    def _generate_depth_image(self):
        """生成深度图像"""
        # 创建基础深度图（距离以毫米为单位）
        depth = np.full((360, 640), 5000, dtype=np.uint16)  # 5米默认距离
        
        # 地面渐变（近处浅，远处深）
        for y in range(250, 360):
            distance = 1000 + (y - 250) * 30  # 1-4米
            depth[y, :] = distance
        
        # 为移动对象添加深度
        for obj in self.objects:
            x, y = int(obj['position'][0]), int(obj['position'][1])
            w, h = obj['size']
            distance = obj['distance']
            
            # 确保对象在图像范围内
            if 0 <= x < 640 and 0 <= y < 360:
                x1, y1 = max(0, x-w//2), max(0, y-h)
                x2, y2 = min(640, x+w//2), min(360, y)
                depth[y1:y2, x1:x2] = distance
        
        return depth

# 全局实例
mock_data_provider = None

def get_mock_data_provider(global_frame_cache=None):
    """获取模拟数据提供器实例"""
    global mock_data_provider
    if mock_data_provider is None:
        mock_data_provider = MockDataProvider(global_frame_cache)
    elif global_frame_cache and not mock_data_provider.global_frame_cache:
        mock_data_provider.global_frame_cache = global_frame_cache
    return mock_data_provider 