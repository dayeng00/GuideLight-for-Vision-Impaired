#!/usr/bin/env python3
"""
测试环境感知修复脚本
"""

import time
import sys
import os
import requests

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_environment_api():
    """测试环境感知API"""
    print("🧪 测试环境感知API")
    print("=" * 50)
    
    base_url = "http://localhost:5000"
    
    try:
        # 1. 测试环境感知状态
        print("1️⃣ 测试环境感知状态...")
        response = requests.get(f"{base_url}/api/environment/status", timeout=5)
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
        
        # 2. 启动环境感知处理
        print("\n2️⃣ 启动环境感知处理...")
        response = requests.post(f"{base_url}/api/environment/start", timeout=5)
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
        
        # 3. 等待一些时间让数据处理
        print("\n3️⃣ 等待数据处理...")
        for i in range(5):
            print(f"   等待 {i+1}/5 秒...")
            time.sleep(1)
        
        # 4. 测试获取最新结果
        print("\n4️⃣ 测试获取最新结果...")
        for attempt in range(5):
            response = requests.get(f"{base_url}/api/environment/latest_result", timeout=5)
            print(f"   尝试 {attempt+1}: 状态码 {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ 成功获取结果!")
                print(f"   检测对象数量: {len(result.get('result', {}).get('detected_objects', []))}")
                print(f"   处理时间: {result.get('result', {}).get('processing_time', 0):.3f}秒")
                return True
            else:
                print(f"   ❌ 失败: {response.json()}")
                time.sleep(2)
        
        print("❌ 5次尝试后仍无法获取结果")
        return False
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保后端服务器正在运行")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_mock_data_api():
    """测试模拟数据API"""
    print("\n🎭 测试模拟数据API")
    print("=" * 50)
    
    base_url = "http://localhost:5000"
    
    try:
        # 1. 测试模拟数据状态
        print("1️⃣ 测试模拟数据状态...")
        response = requests.get(f"{base_url}/api/mock_data/status", timeout=5)
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
        
        # 2. 启动模拟数据
        print("\n2️⃣ 启动模拟数据...")
        response = requests.post(f"{base_url}/api/mock_data/start", timeout=5)
        print(f"   状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 开始环境感知修复测试")
    print("=" * 80)
    
    # 测试模拟数据API
    mock_ok = test_mock_data_api()
    
    # 测试环境感知API
    env_ok = test_environment_api()
    
    # 总结
    print("\n" + "=" * 80)
    print("📋 测试结果总结")
    print("=" * 80)
    print(f"🎭 模拟数据API: {'✅ 正常' if mock_ok else '❌ 异常'}")
    print(f"🔍 环境感知API: {'✅ 正常' if env_ok else '❌ 异常'}")
    
    if env_ok:
        print("\n🎉 修复成功！环境感知API现在可以返回有效结果")
    else:
        print("\n⚠️ 修复未完成，请检查后端服务器日志")

if __name__ == "__main__":
    main() 