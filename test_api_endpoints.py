#!/usr/bin/env python3
"""
测试API端点是否正常工作
"""

import requests
import time
import json

def test_health_endpoint():
    """测试健康检查端点"""
    print("🧪 测试健康检查端点...")
    try:
        response = requests.get('http://localhost:5000/api/health', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ 健康检查成功")
            print(f"   状态: {data.get('status', 'unknown')}")
            print(f"   视频模块: {data.get('modules', {}).get('video_modules', False)}")
            print(f"   模块可用性: {data.get('modules', {})}")
            return True
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 健康检查异常: {e}")
        return False

def test_start_camera_endpoints():
    """测试摄像头启动端点"""
    endpoints = [
        'enhanced_detector/start',
        'f_detector/start_cameras',
        'f_tracker/start_cameras',
        'd_estimator/start_cameras'
    ]
    
    results = {}
    
    for endpoint in endpoints:
        print(f"🧪 测试 {endpoint}...")
        try:
            response = requests.post(f'http://localhost:5000/{endpoint}', timeout=10)
            if response.status_code in [200, 429]:  # 200成功，429频率限制也是正常的
                print(f"✅ {endpoint} 正常")
                results[endpoint] = True
            else:
                print(f"❌ {endpoint} 失败: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   错误信息: {error_data.get('message', '未知错误')}")
                except:
                    print(f"   原始响应: {response.text}")
                results[endpoint] = False
        except Exception as e:
            print(f"❌ {endpoint} 异常: {e}")
            results[endpoint] = False
    
    return results

def test_video_feed_endpoints():
    """测试视频流端点"""
    endpoints = [
        'enhanced_detector/video_feed',
        'f_detector/video_feed_left',
        'f_detector/video_feed_right',
        'f_tracker/video_feed_left',
        'f_tracker/video_feed_right',
        'd_estimator/video_feed'
    ]
    
    results = {}
    
    for endpoint in endpoints:
        print(f"🧪 测试视频流 {endpoint}...")
        try:
            response = requests.get(f'http://localhost:5000/{endpoint}', timeout=5, stream=True)
            if response.status_code == 200:
                # 检查是否是图像数据
                content_type = response.headers.get('content-type', '')
                if 'image' in content_type or 'multipart' in content_type:
                    print(f"✅ {endpoint} 视频流正常")
                    results[endpoint] = True
                else:
                    print(f"⚠️ {endpoint} 响应类型异常: {content_type}")
                    results[endpoint] = False
            else:
                print(f"❌ {endpoint} 失败: {response.status_code}")
                results[endpoint] = False
        except Exception as e:
            print(f"❌ {endpoint} 异常: {e}")
            results[endpoint] = False
    
    return results

def main():
    """主测试函数"""
    print("=" * 60)
    print("🧪 GuideLight API端点测试")
    print("=" * 60)
    
    # 测试健康检查
    if not test_health_endpoint():
        print("\n❌ 后端服务未运行或不健康，请先启动后端")
        return False
    
    print("\n" + "=" * 40)
    print("📡 测试摄像头启动端点")
    print("=" * 40)
    
    # 测试摄像头启动端点
    camera_results = test_start_camera_endpoints()
    
    print("\n" + "=" * 40)
    print("📹 测试视频流端点")
    print("=" * 40)
    
    # 测试视频流端点
    video_results = test_video_feed_endpoints()
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    print("摄像头启动端点:")
    for endpoint, result in camera_results.items():
        status = "✅ 正常" if result else "❌ 异常"
        print(f"  {endpoint}: {status}")
    
    print("\n视频流端点:")
    for endpoint, result in video_results.items():
        status = "✅ 正常" if result else "❌ 异常"
        print(f"  {endpoint}: {status}")
    
    # 计算成功率
    total_tests = len(camera_results) + len(video_results)
    successful_tests = sum(camera_results.values()) + sum(video_results.values())
    success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"\n总体成功率: {success_rate:.1f}% ({successful_tests}/{total_tests})")
    
    if success_rate >= 80:
        print("🎉 API端点测试大部分通过，系统基本正常")
        return True
    else:
        print("⚠️ 多个API端点异常，请检查后端配置")
        return False

if __name__ == "__main__":
    main() 