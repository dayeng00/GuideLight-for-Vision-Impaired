#!/usr/bin/env python3
"""
测试增强检测器和碰撞管理器的集成
"""

import time
import requests
import sys
import os

# 添加路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'main'))

def test_enhanced_detector_collision_integration():
    """测试增强检测器和碰撞管理器的集成"""
    
    print("🧪 开始测试增强检测器和碰撞管理器集成...")
    
    base_url = "http://localhost:5000"
    
    try:
        # 1. 启动增强检测器
        print("1️⃣ 启动增强检测器...")
        response = requests.post(f"{base_url}/enhanced_detector/start", timeout=10)
        print(f"   响应状态: {response.status_code}")
        print(f"   响应内容: {response.json()}")
        
        if response.status_code != 200:
            print("❌ 增强检测器启动失败")
            return False
        
        # 等待初始化完成
        print("⏳ 等待初始化完成...")
        time.sleep(3)
        
        # 2. 检查碰撞风险API
        print("2️⃣ 测试碰撞风险API...")
        for i in range(10):
            try:
                response = requests.get(f"{base_url}/api/collision/risk", timeout=5)
                print(f"   第{i+1}次请求 - 状态: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"   碰撞概率: {data.get('collision_probability', 'N/A')}")
                    print(f"   检测到的对象: {len(data.get('detected_objects', []))}")
                    print(f"   活跃轨迹: {len(data.get('active_tracks', []))}")
                else:
                    print(f"   请求失败: {response.text}")
                
                time.sleep(2)
            except Exception as e:
                print(f"   请求出错: {e}")
                time.sleep(1)
        
        # 3. 检查增强检测器状态
        print("3️⃣ 检查增强检测器状态...")
        try:
            response = requests.get(f"{base_url}/enhanced_detector/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"   状态: {data}")
            else:
                print(f"   无法获取状态: {response.status_code}")
        except Exception as e:
            print(f"   状态检查出错: {e}")
        
        print("✅ 测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        return False

if __name__ == "__main__":
    success = test_enhanced_detector_collision_integration()
    if success:
        print("\n🎉 集成测试成功!")
    else:
        print("\n💥 集成测试失败!")
        sys.exit(1) 