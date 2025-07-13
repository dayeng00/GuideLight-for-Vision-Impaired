#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
碰撞风险API测试脚本
用于验证修复后的API是否正常工作
"""

import requests
import json
import time

def test_collision_risk_api():
    """测试碰撞风险API"""
    
    base_url = "http://localhost:5000"
    
    print("🧪 开始测试碰撞风险API...")
    
    try:
        # 1. 测试系统状态
        print("\n1️⃣ 测试系统状态...")
        response = requests.get(f"{base_url}/api/collision/system_status")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            status = response.json()
            print(f"系统健康: {status.get('system_healthy', False)}")
            print(f"设备管理器: {status.get('components', {}).get('device_manager', {})}")
            print(f"轨迹碰撞管理器: {status.get('components', {}).get('trajectory_collision_manager', {})}")
        else:
            print(f"❌ 系统状态检查失败: {response.text}")
        
        # 2. 启动碰撞检测系统
        print("\n2️⃣ 启动碰撞检测系统...")
        response = requests.post(f"{base_url}/api/collision/start_system")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"启动成功: {result.get('success', False)}")
            print(f"消息: {result.get('message', '')}")
        else:
            print(f"❌ 系统启动失败: {response.text}")
        
        # 等待系统稳定
        print("\n⏳ 等待系统稳定...")
        time.sleep(3)
        
        # 3. 测试碰撞风险API
        print("\n3️⃣ 测试碰撞风险API...")
        for i in range(5):
            print(f"\n测试第 {i+1} 次:")
            try:
                response = requests.get(f"{base_url}/api/collision/risk", timeout=10)
                print(f"状态码: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ 成功获取碰撞风险数据:")
                    print(f"  - 成功: {data.get('success', False)}")
                    print(f"  - 最大概率: {data.get('max_probability', 0):.2f}%")
                    print(f"  - 风险等级: {data.get('risk', {}).get('level', 'unknown')}")
                    print(f"  - 检测对象数量: {len(data.get('detected_objects', []))}")
                    print(f"  - 是否模拟数据: {data.get('is_mock', 'unknown')}")
                    
                    # 检查最近物体
                    nearest_object = data.get('risk', {}).get('nearest_object')
                    if nearest_object:
                        print(f"  - 最近物体: {nearest_object.get('type', 'unknown')} (距离: {nearest_object.get('distance', 0):.1f}m)")
                    else:
                        print(f"  - 最近物体: 无")
                        
                elif response.status_code == 500:
                    print(f"❌ 服务器内部错误:")
                    try:
                        error_data = response.json()
                        print(f"  错误信息: {error_data.get('error', 'unknown')}")
                    except:
                        print(f"  原始错误: {response.text}")
                elif response.status_code == 503:
                    print(f"⚠️ 服务不可用:")
                    try:
                        error_data = response.json()
                        print(f"  错误信息: {error_data.get('error', 'unknown')}")
                    except:
                        print(f"  原始错误: {response.text}")
                else:
                    print(f"❌ 未知错误 (状态码: {response.status_code})")
                    print(f"  响应: {response.text}")
                    
            except requests.exceptions.Timeout:
                print("❌ 请求超时")
            except requests.exceptions.ConnectionError:
                print("❌ 连接错误 - 请确保服务器正在运行")
            except Exception as e:
                print(f"❌ 请求异常: {e}")
            
            # 等待一段时间再进行下一次测试
            if i < 4:
                time.sleep(2)
        
        print("\n🧪 测试完成!")
        
    except Exception as e:
        print(f"❌ 测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_collision_risk_api() 