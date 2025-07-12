#!/usr/bin/env python3
"""
后端API测试脚本
用于验证GuideLight系统的后端API是否正常工作
"""

import requests
import json
import time
from datetime import datetime

# 服务器配置
SERVER_URL = "http://localhost:5000"
TIMEOUT = 10

def test_api_endpoint(endpoint, method="GET", data=None, expected_status=200):
    """
    测试API端点
    
    Args:
        endpoint: API端点路径
        method: HTTP方法
        data: 请求数据
        expected_status: 期望的HTTP状态码
    
    Returns:
        (success, result): 测试结果
    """
    try:
        url = f"{SERVER_URL}{endpoint}"
        
        if method.upper() == "GET":
            response = requests.get(url, timeout=TIMEOUT)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, timeout=TIMEOUT)
        else:
            return False, f"不支持的HTTP方法: {method}"
        
        if response.status_code == expected_status:
            try:
                result = response.json()
                return True, result
            except json.JSONDecodeError:
                return True, response.text
        else:
            return False, f"状态码错误: {response.status_code}, 期望: {expected_status}"
    
    except requests.exceptions.ConnectionError:
        return False, "连接失败，请确保后端服务器正在运行"
    except requests.exceptions.Timeout:
        return False, "请求超时"
    except Exception as e:
        return False, f"请求出错: {str(e)}"

def run_all_tests():
    """运行所有测试"""
    
    print("="*60)
    print("GuideLight 后端API测试")
    print("="*60)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"服务器地址: {SERVER_URL}")
    print("-"*60)
    
    # 测试用例列表
    test_cases = [
        # 基础健康检查
        ("/api/health", "GET", None, 200),
        
        # 综合系统状态
        ("/api/integrated/status", "GET", None, 200),
        ("/integrated/status", "GET", None, 200),
        
        # 位置相关API
        ("/location/current", "GET", None, 200),
        ("/location/history", "GET", None, 200),
        
        # 语音识别状态
        ("/api/speech/status", "GET", None, 200),
        
        # 轨迹追踪API
        ("/api/trajectory/status", "GET", None, 200),
        ("/api/collision/risk", "GET", None, 200),
        
        # 用户登录测试
        ("/login", "POST", {"username": "test", "password": "test"}, 201),
        
        # 视频流控制（可能会失败，这是正常的）
        ("/m_detector/start_cameras", "POST", None, 200),
        ("/m_detector/stop_cameras", "POST", None, 200),
    ]
    
    success_count = 0
    total_count = len(test_cases)
    
    for endpoint, method, data, expected_status in test_cases:
        print(f"\n测试: {method} {endpoint}")
        success, result = test_api_endpoint(endpoint, method, data, expected_status)
        
        if success:
            print(f"✅ 成功")
            if isinstance(result, dict):
                print(f"   响应数据: {json.dumps(result, indent=2, ensure_ascii=False)}")
            else:
                print(f"   响应数据: {result}")
            success_count += 1
        else:
            print(f"❌ 失败: {result}")
    
    print("\n" + "="*60)
    print(f"测试完成: {success_count}/{total_count} 个测试通过")
    print(f"成功率: {success_count/total_count*100:.1f}%")
    print("="*60)
    
    return success_count == total_count

def test_video_streams():
    """测试视频流功能"""
    print("\n测试视频流功能...")
    
    # 视频流端点
    video_endpoints = [
        "d_estimator",
        "f_detector", 
        "f_tracker",
        "g_recognition",
        "g_recognizer",
        "m_detector",
        "p_video",
        "s_RGB"
    ]
    
    for endpoint in video_endpoints:
        print(f"\n测试视频流: {endpoint}")
        
        # 尝试启动
        success, result = test_api_endpoint(f"/{endpoint}/start_cameras", "POST")
        if success:
            print(f"✅ 启动成功: {endpoint}")
            
            # 等待一下，然后停止
            time.sleep(1)
            success, result = test_api_endpoint(f"/{endpoint}/stop_cameras", "POST")
            if success:
                print(f"✅ 停止成功: {endpoint}")
            else:
                print(f"❌ 停止失败: {endpoint} - {result}")
        else:
            print(f"❌ 启动失败: {endpoint} - {result}")

def test_location_apis():
    """测试位置相关API"""
    print("\n测试位置相关API...")
    
    # 测试添加位置
    location_data = {
        "lng": 117.283042,
        "lat": 31.844786
    }
    
    success, result = test_api_endpoint("/location/add", "POST", location_data)
    if success:
        print("✅ 添加位置成功")
        
        # 测试获取位置
        success, result = test_api_endpoint("/location/current", "GET")
        if success:
            print("✅ 获取当前位置成功")
            print(f"   位置信息: {result}")
        else:
            print(f"❌ 获取当前位置失败: {result}")
    else:
        print(f"❌ 添加位置失败: {result}")

if __name__ == "__main__":
    # 运行基础测试
    success = run_all_tests()
    
    # 如果基础测试通过，运行更详细的测试
    if success:
        print("\n🎉 基础测试全部通过！运行详细测试...")
        test_location_apis()
        test_video_streams()
    else:
        print("\n⚠️  基础测试有失败项，请检查后端服务器状态")
        print("请确保：")
        print("1. 后端服务器正在运行 (python main.py)")
        print("2. 端口5000没有被占用")
        print("3. 数据库连接正常")
        print("4. 所有依赖库已安装") 