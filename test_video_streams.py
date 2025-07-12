#!/usr/bin/env python3
"""
测试视频流端点脚本
验证所有视频流端点是否正常工作
"""

import requests
import time
from typing import Dict, List, Tuple

# 视频流端点配置
VIDEO_STREAM_ENDPOINTS = {
    'enhanced_detector': {
        'start': '/enhanced_detector/start',
        'stop': '/enhanced_detector/stop',
        'stream': '/enhanced_detector/video_feed',
        'description': '增强检测器'
    },
    'f_detector_left': {
        'start': '/f_detector/start_cameras',
        'stop': '/f_detector/stop_cameras',
        'stream': '/f_detector/video_feed_left',
        'description': '特征点检测器-左'
    },
    'f_detector_right': {
        'start': '/f_detector/start_cameras',
        'stop': '/f_detector/stop_cameras',
        'stream': '/f_detector/video_feed_right',
        'description': '特征点检测器-右'
    },
    'f_tracker_left': {
        'start': '/f_tracker/start_cameras',
        'stop': '/f_tracker/stop_cameras',
        'stream': '/f_tracker/video_feed_left',
        'description': '特征点追踪器-左'
    },
    'f_tracker_right': {
        'start': '/f_tracker/start_cameras',
        'stop': '/f_tracker/stop_cameras',
        'stream': '/f_tracker/video_feed_right',
        'description': '特征点追踪器-右'
    },
    'd_estimator': {
        'start': '/d_estimator/start_cameras',
        'stop': '/d_estimator/stop_cameras',
        'stream': '/d_estimator/video_feed',
        'description': '深度估计器'
    }
}

BASE_URL = 'http://localhost:5000'

def test_backend_health() -> bool:
    """测试后端健康状态"""
    try:
        response = requests.get(f'{BASE_URL}/api/health', timeout=5)
        if response.status_code == 200:
            print("✅ 后端服务正常运行")
            return True
        else:
            print(f"❌ 后端服务响应异常: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 后端服务连接失败: {e}")
        return False

def test_start_camera(endpoint_name: str, start_url: str) -> bool:
    """测试启动摄像头"""
    try:
        response = requests.post(f'{BASE_URL}{start_url}', timeout=10)
        if response.status_code == 200:
            print(f"✅ {endpoint_name} 启动成功")
            return True
        else:
            print(f"❌ {endpoint_name} 启动失败: {response.status_code}")
            try:
                error_msg = response.json().get('message', 'Unknown error')
                print(f"   错误信息: {error_msg}")
            except:
                print(f"   响应内容: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ {endpoint_name} 启动请求失败: {e}")
        return False

def test_video_stream(endpoint_name: str, stream_url: str) -> bool:
    """测试视频流是否可访问"""
    try:
        response = requests.get(f'{BASE_URL}{stream_url}', timeout=5, stream=True)
        if response.status_code == 200:
            # 检查响应头
            content_type = response.headers.get('Content-Type', '')
            if 'multipart/x-mixed-replace' in content_type:
                print(f"✅ {endpoint_name} 视频流正常")
                return True
            else:
                print(f"❌ {endpoint_name} 视频流响应格式错误: {content_type}")
                return False
        else:
            print(f"❌ {endpoint_name} 视频流访问失败: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ {endpoint_name} 视频流请求失败: {e}")
        return False

def test_stop_camera(endpoint_name: str, stop_url: str) -> bool:
    """测试停止摄像头"""
    try:
        response = requests.post(f'{BASE_URL}{stop_url}', timeout=10)
        if response.status_code == 200:
            print(f"✅ {endpoint_name} 停止成功")
            return True
        else:
            print(f"❌ {endpoint_name} 停止失败: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ {endpoint_name} 停止请求失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🔍 开始测试视频流端点...")
    print("=" * 60)
    
    # 测试后端健康状态
    if not test_backend_health():
        print("\n❌ 后端服务未运行，请先启动后端服务")
        return
    
    print("\n📊 测试结果汇总:")
    print("=" * 60)
    
    results = []
    
    for endpoint_name, config in VIDEO_STREAM_ENDPOINTS.items():
        print(f"\n🔧 测试 {config['description']} ({endpoint_name}):")
        print("-" * 40)
        
        # 测试启动
        start_success = test_start_camera(endpoint_name, config['start'])
        
        if start_success:
            # 等待一下让服务启动
            time.sleep(2)
            
            # 测试视频流
            stream_success = test_video_stream(endpoint_name, config['stream'])
            
            # 测试停止
            stop_success = test_stop_camera(endpoint_name, config['stop'])
            
            results.append({
                'name': endpoint_name,
                'description': config['description'],
                'start': start_success,
                'stream': stream_success,
                'stop': stop_success,
                'overall': start_success and stream_success and stop_success
            })
        else:
            results.append({
                'name': endpoint_name,
                'description': config['description'],
                'start': start_success,
                'stream': False,
                'stop': False,
                'overall': False
            })
    
    # 打印最终结果
    print("\n📈 最终测试结果:")
    print("=" * 60)
    
    success_count = 0
    total_count = len(results)
    
    for result in results:
        status = "✅ 通过" if result['overall'] else "❌ 失败"
        print(f"{result['description']:<20} {status}")
        
        if not result['overall']:
            details = []
            if not result['start']:
                details.append("启动失败")
            if not result['stream']:
                details.append("视频流失败")
            if not result['stop']:
                details.append("停止失败")
            print(f"{'':>20} 详情: {', '.join(details)}")
        else:
            success_count += 1
    
    print(f"\n📊 总体结果: {success_count}/{total_count} 个端点正常工作")
    
    if success_count == total_count:
        print("🎉 所有视频流端点测试通过！")
    else:
        print("⚠️  部分端点存在问题，请检查后端服务和设备连接")
    
    print("\n💡 故障排除建议:")
    print("1. 确保后端服务正在运行 (python main.py)")
    print("2. 检查摄像头设备是否正常连接")
    print("3. 确认端口5000未被其他程序占用")
    print("4. 检查防火墙设置")

if __name__ == "__main__":
    main() 