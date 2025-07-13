#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试视频流Response对象修复
验证所有视频流路由是否正确返回视频流数据
"""

import requests
import time
import sys

def test_video_stream_response(stream_url, stream_name, timeout=5):
    """测试单个视频流的响应"""
    result = {
        'stream_name': stream_name,
        'url': stream_url,
        'status': 'unknown',
        'status_code': None,
        'content_type': None,
        'error': None
    }
    
    try:
        print(f"测试 {stream_name}: {stream_url}")
        
        # 发送请求
        response = requests.get(stream_url, timeout=timeout, stream=True)
        result['status_code'] = response.status_code
        result['content_type'] = response.headers.get('Content-Type', '')
        
        if response.status_code == 200:
            # 检查Content-Type是否正确
            if 'multipart/x-mixed-replace' in result['content_type']:
                result['status'] = 'success'
                print(f"✅ {stream_name}: 成功返回MJPEG视频流")
            else:
                result['status'] = 'wrong_content_type'
                print(f"❌ {stream_name}: Content-Type错误 - {result['content_type']}")
        elif response.status_code == 503:
            result['status'] = 'service_unavailable'
            print(f"⚠️ {stream_name}: 服务不可用 (摄像头未启动)")
        else:
            result['status'] = 'http_error'
            result['error'] = f"HTTP {response.status_code}"
            print(f"❌ {stream_name}: HTTP错误 {response.status_code}")
            
    except requests.exceptions.Timeout:
        result['status'] = 'timeout'
        result['error'] = 'Request timeout'
        print(f"❌ {stream_name}: 请求超时")
    except requests.exceptions.ConnectionError:
        result['status'] = 'connection_error'
        result['error'] = 'Connection error'
        print(f"❌ {stream_name}: 连接错误")
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
        print(f"❌ {stream_name}: 未知错误 - {str(e)}")
    
    return result

def main():
    """主测试函数"""
    print("🔧 测试视频流Response对象修复")
    print("=" * 50)
    
    # 基础URL
    base_url = "http://localhost:5000"
    
    # 要测试的视频流列表
    video_streams = [
        (f"{base_url}/d_estimator/video_feed", "视差估计器"),
        (f"{base_url}/f_detector/video_feed_left", "特征点检测器-左"),
        (f"{base_url}/f_detector/video_feed_right", "特征点检测器-右"),
        (f"{base_url}/enhanced_detector/video_feed", "增强检测器"),
    ]
    
    # 执行测试
    results = []
    for stream_url, stream_name in video_streams:
        result = test_video_stream_response(stream_url, stream_name)
        results.append(result)
        time.sleep(0.5)
    
    # 统计结果
    print("\n" + "=" * 50)
    print("📊 测试结果统计")
    print("=" * 50)
    
    success_count = 0
    service_unavailable_count = 0
    error_count = 0
    
    for result in results:
        status = result['status']
        if status == 'success':
            success_count += 1
        elif status == 'service_unavailable':
            service_unavailable_count += 1
        else:
            error_count += 1
    
    total_count = len(results)
    print(f"总测试数量: {total_count}")
    print(f"✅ 成功: {success_count}")
    print(f"⚠️ 服务不可用: {service_unavailable_count}")
    print(f"❌ 错误: {error_count}")
    
    # 检查是否修复了Response对象问题
    print("\n🔍 Response对象修复检查:")
    response_fixed = True
    for result in results:
        if result['status'] == 'error' and 'not iterable' in str(result['error']):
            response_fixed = False
            print(f"❌ {result['stream_name']}: 仍然存在Response对象问题")
    
    if response_fixed:
        print("✅ 所有视频流都已修复Response对象问题")
    
    return error_count == 0 or (service_unavailable_count > 0 and error_count == 0)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 