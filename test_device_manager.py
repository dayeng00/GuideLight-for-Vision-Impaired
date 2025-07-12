#!/usr/bin/env python3
"""
测试设备管理器和碰撞检测系统
"""

import sys
import time
import os

# 添加路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'main'))

from utils.device_manager import DeviceManager
from utils.enhanced_detector import EnhancedDetector
from utils.trajectory_collision_manager import TrajectoryCollisionManager

def test_device_manager():
    """测试设备管理器"""
    print("🚀 开始测试设备管理器...")
    
    try:
        # 创建设备管理器
        device_manager = DeviceManager()
        print("✅ 设备管理器创建成功")
        
        # 启动设备管理器
        print("🔄 启动设备管理器...")
        if device_manager.start():
            print("✅ 设备管理器启动成功")
            
            # 等待数据
            print("⏳ 等待设备数据...")
            time.sleep(5)
            
            # 检查数据
            data = device_manager.get_latest_data()
            print(f"📊 获取到的数据键: {list(data.keys())}")
            
            if data['color'] is not None:
                print(f"🎨 彩色图像形状: {data['color'].shape}")
            else:
                print("⚠️ 未获取到彩色图像")
                
            if data['depth'] is not None:
                print(f"📏 深度图像形状: {data['depth'].shape}")
            else:
                print("⚠️ 未获取到深度图像")
                
            if data['imu'] is not None:
                print(f"🧭 IMU数据类型: {type(data['imu'])}")
            else:
                print("⚠️ 未获取到IMU数据")
                
            # 停止设备管理器
            print("🛑 停止设备管理器...")
            device_manager.stop()
            print("✅ 设备管理器已停止")
            
        else:
            print("❌ 设备管理器启动失败")
            
    except Exception as e:
        print(f"❌ 设备管理器测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_enhanced_detector():
    """测试增强检测器"""
    print("\n🚀 开始测试增强检测器...")
    
    try:
        # 创建设备管理器
        device_manager = DeviceManager()
        
        # 启动设备管理器
        if device_manager.start():
            print("✅ 设备管理器启动成功")
            
            # 创建增强检测器
            enhanced_detector = EnhancedDetector(
                camera_size=720,
                use_yolo=True,
                confidence_threshold=0.5
            )
            print("✅ 增强检测器创建成功")
            
            # 创建碰撞检测管理器
            collision_manager = TrajectoryCollisionManager()
            enhanced_detector.set_collision_manager(collision_manager)
            collision_manager.start()
            print("✅ 碰撞检测管理器创建并启动成功")
            
            # 启动增强检测器
            if enhanced_detector.start_background_processing():
                print("✅ 增强检测器启动成功")
                
                # 等待处理
                print("⏳ 等待检测处理...")
                time.sleep(10)
                
                # 检查碰撞数据
                collision_data = collision_manager.get_collision_data()
                print(f"🚨 碰撞数据: {collision_data}")
                
                # 停止增强检测器
                enhanced_detector.stop_background_processing()
                collision_manager.stop()
                print("✅ 增强检测器已停止")
                
            else:
                print("❌ 增强检测器启动失败")
            
            # 停止设备管理器
            device_manager.stop()
            
        else:
            print("❌ 设备管理器启动失败")
            
    except Exception as e:
        print(f"❌ 增强检测器测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_collision_api():
    """测试碰撞API"""
    print("\n🚀 开始测试碰撞API...")
    
    try:
        import requests
        
        # 测试碰撞风险API
        print("📡 测试碰撞风险API...")
        response = requests.get("http://localhost:5000/api/collision/risk")
        print(f"响应状态码: {response.status_code}")
        print(f"响应数据: {response.json()}")
        
        # 测试碰撞状态API
        print("📡 测试碰撞状态API...")
        response = requests.get("http://localhost:5000/api/collision/status")
        print(f"响应状态码: {response.status_code}")
        print(f"响应数据: {response.json()}")
        
    except Exception as e:
        print(f"❌ 碰撞API测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 开始系统测试...")
    
    # 测试设备管理器
    test_device_manager()
    
    # 测试增强检测器
    test_enhanced_detector()
    
    # 测试碰撞API（需要后端运行）
    test_collision_api()
    
    print("\n🎉 测试完成!") 