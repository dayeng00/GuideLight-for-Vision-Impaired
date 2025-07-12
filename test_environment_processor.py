#!/usr/bin/env python3
"""
测试环境感知处理器
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'main'))

import cv2
import numpy as np
import time
import requests
from utils.global_frame_cache import get_global_frame_cache
from utils.environment_processor import get_environment_processor

def create_test_frame():
    """创建测试帧数据"""
    # 创建一个640x360的测试图像
    img = np.zeros((360, 640, 3), dtype=np.uint8)
    
    # 添加一些颜色和形状来模拟场景
    cv2.rectangle(img, (100, 100), (200, 200), (0, 255, 0), -1)  # 绿色矩形
    cv2.circle(img, (400, 180), 50, (255, 0, 0), -1)  # 蓝色圆形
    cv2.rectangle(img, (500, 250), (600, 350), (0, 0, 255), -1)  # 红色矩形
    
    # 添加一些文字
    cv2.putText(img, "Test Frame", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # 创建对应的深度图
    depth = np.full((360, 640), 2000, dtype=np.uint16)  # 2米深度
    depth[100:200, 100:200] = 1500  # 绿色矩形区域1.5米
    depth[130:230, 350:450] = 3000  # 蓝色圆形区域3米
    depth[250:350, 500:600] = 1000  # 红色矩形区域1米
    
    return img, depth

def test_environment_processor():
    """测试环境感知处理器"""
    print("🧪 开始测试环境感知处理器...")
    
    # 获取全局帧缓存和环境感知处理器
    frame_cache = get_global_frame_cache()
    env_processor = get_environment_processor()
    
    if not frame_cache:
        print("❌ 无法获取全局帧缓存")
        return False
        
    if not env_processor:
        print("❌ 无法获取环境感知处理器")
        return False
    
    # 连接全局帧缓存
    env_processor.set_global_frame_cache(frame_cache)
    
    # 启动环境感知处理器
    env_processor.start_processing()
    
    print("📡 开始向全局帧缓存发送测试数据...")
    
    # 发送测试数据
    for i in range(10):
        img, depth = create_test_frame()
        
        # 为了模拟变化，稍微移动对象
        offset = i * 10
        img = np.roll(img, offset, axis=1)
        depth = np.roll(depth, offset, axis=1)
        
        frame_data = {
            'color': img,
            'depth': depth,
            'timestamp': time.time()
        }
        
        frame_cache.update_frames(frame_data)
        print(f"📤 发送第 {i+1} 帧测试数据")
        
        time.sleep(0.5)  # 等待0.5秒
    
    # 等待处理
    print("⏳ 等待环境感知处理器处理数据...")
    time.sleep(3)
    
    # 检查结果
    result = env_processor.get_latest_result()
    
    if result:
        print("✅ 环境感知处理器工作正常!")
        print(f"📊 处理结果:")
        print(f"   - 检测对象数量: {len(result.get('detected_objects', []))}")
        print(f"   - 处理时间: {result.get('performance', {}).get('processing_time', 0):.3f}s")
        print(f"   - 帧数: {result.get('performance', {}).get('frame_count', 0)}")
        print(f"   - 碰撞概率: {result.get('collision_probability', 0):.2f}")
        
        # 测试API
        print("🌐 测试API端点...")
        try:
            response = requests.get('http://localhost:5000/api/environment/latest_result')
            if response.status_code == 200:
                api_result = response.json()
                if api_result.get('success'):
                    print("✅ API端点工作正常!")
                    print(f"   - API返回对象数量: {len(api_result.get('result', {}).get('detected_objects', []))}")
                else:
                    print("⚠️ API返回失败:", api_result.get('error'))
            else:
                print(f"❌ API请求失败: {response.status_code}")
        except Exception as e:
            print(f"❌ API测试出错: {e}")
        
        return True
    else:
        print("❌ 环境感知处理器没有返回结果")
        return False

def test_api_directly():
    """直接测试API"""
    print("🌐 直接测试环境感知API...")
    
    try:
        # 启动处理器
        response = requests.post('http://localhost:5000/api/environment/start')
        print(f"启动处理器: {response.status_code} - {response.text}")
        
        # 等待一下
        time.sleep(2)
        
        # 检查状态
        response = requests.get('http://localhost:5000/api/environment/status')
        print(f"处理器状态: {response.status_code} - {response.text}")
        
        # 获取结果
        response = requests.get('http://localhost:5000/api/environment/latest_result')
        print(f"最新结果: {response.status_code} - {response.text[:200]}...")
        
    except Exception as e:
        print(f"API测试出错: {e}")

if __name__ == "__main__":
    print("🔬 环境感知处理器测试")
    print("=" * 50)
    
    # 测试处理器
    success = test_environment_processor()
    
    print("\n" + "=" * 50)
    
    # 测试API
    test_api_directly()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 测试完成 - 环境感知处理器工作正常!")
    else:
        print("😞 测试完成 - 环境感知处理器存在问题") 