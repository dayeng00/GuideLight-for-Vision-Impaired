#!/usr/bin/env python3
"""
测试碰撞概率预测系统
"""

import requests
import time
import json


def test_enhanced_detector():
    """测试增强检测器API"""
    base_url = "http://localhost:5000"
    
    print("=== 测试增强检测器系统 ===\n")
    
    # 1. 启动增强检测器
    print("1. 启动增强检测器...")
    try:
        response = requests.post(f"{base_url}/enhanced_detector/start")
        if response.ok:
            data = response.json()
            print(f"   ✓ 增强检测器已启动")
            print(f"   碰撞追踪: {data.get('collision_tracking', False)}")
        else:
            print(f"   ✗ 启动失败: {response.text}")
            return
    except Exception as e:
        print(f"   ✗ 连接失败: {e}")
        return
    
    # 等待系统初始化
    time.sleep(2)
    
    # 2. 获取碰撞风险数据
    print("\n2. 获取实时碰撞风险数据...")
    for i in range(5):
        try:
            response = requests.get(f"{base_url}/api/collision/risk")
            if response.ok:
                data = response.json()
                print(f"\n   第 {i+1} 次检测:")
                print(f"   最大碰撞概率: {data.get('max_probability', 0):.1f}%")
                
                if 'risk' in data:
                    risk = data['risk']
                    print(f"   风险等级: {risk.get('level', 'unknown')}")
                    print(f"   警告信息: {risk.get('warning_message', '')}")
                    
                    if risk.get('nearest_object'):
                        obj = risk['nearest_object']
                        print(f"   最近物体: {obj.get('type', 'unknown')} - 距离: {obj.get('distance', 0):.2f}m")
                
                if 'detected_objects' in data:
                    print(f"   检测到的物体数量: {len(data['detected_objects'])}")
            else:
                print(f"   ✗ 获取失败: {response.text}")
        except Exception as e:
            print(f"   ✗ 请求失败: {e}")
        
        time.sleep(1)
    
    # 3. 获取轨迹数据
    print("\n3. 获取轨迹追踪数据...")
    try:
        response = requests.get(f"{base_url}/api/trajectory/data")
        if response.ok:
            data = response.json()
            if data.get('success'):
                print(f"   ✓ 轨迹数据获取成功")
                trajectory_data = data.get('data', {})
                print(f"   追踪物体数: {len(trajectory_data.get('objects', []))}")
            else:
                print(f"   ✗ 获取失败")
        else:
            print(f"   ✗ 请求失败: {response.text}")
    except Exception as e:
        print(f"   ✗ 请求失败: {e}")
    
    # 4. 停止增强检测器
    print("\n4. 停止增强检测器...")
    try:
        response = requests.post(f"{base_url}/enhanced_detector/stop")
        if response.ok:
            print(f"   ✓ 增强检测器已停止")
        else:
            print(f"   ✗ 停止失败: {response.text}")
    except Exception as e:
        print(f"   ✗ 请求失败: {e}")
    
    print("\n=== 测试完成 ===")


def test_video_stream():
    """测试视频流"""
    base_url = "http://localhost:5000"
    
    print("\n=== 测试视频流 ===")
    print("访问以下URL查看视频流:")
    print(f"  增强检测器: {base_url}/enhanced_detector/video_feed")
    print(f"  目标检测: {base_url}/m_detector/video_feed")
    print(f"  深度估计: {base_url}/d_estimator/video_feed")


def main():
    print("碰撞概率预测系统测试\n")
    
    # 测试增强检测器
    test_enhanced_detector()
    
    # 显示视频流URL
    test_video_stream()
    
    print("\n提示: 请确保后端服务器正在运行 (python main.py)")
    print("      并且已连接OAK-D相机设备")


if __name__ == "__main__":
    main() 