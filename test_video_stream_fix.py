#!/usr/bin/env python3
"""
测试视频流修复效果
"""
import requests
import time

def test_video_stream_headers(url):
    """测试视频流的响应头"""
    print(f"🔍 测试视频流: {url}")
    
    try:
        response = requests.get(url, stream=True, timeout=5)
        print(f"  状态码: {response.status_code}")
        print(f"  Content-Type: {response.headers.get('Content-Type', 'None')}")
        print(f"  Cache-Control: {response.headers.get('Cache-Control', 'None')}")
        
        if response.status_code == 200:
            # 读取前几个字节检查MJPEG格式
            chunk = next(response.iter_content(chunk_size=1024))
            
            if b'--frame' in chunk:
                print("  ✅ 检测到MJPEG边界标记")
                
                # 检查JPEG头部
                if b'\xff\xd8' in chunk:
                    print("  ✅ 检测到JPEG头部")
                    return True
                else:
                    print("  ❌ 未检测到JPEG头部")
                    print(f"  前32字节: {chunk[:32]}")
            else:
                print("  ❌ 未检测到MJPEG格式")
                print(f"  前64字节: {chunk[:64]}")
        elif response.status_code == 503:
            print("  ⚠️ 服务不可用（摄像头未启动）")
        else:
            print(f"  ❌ 请求失败: {response.text[:200]}")
            
    except Exception as e:
        print(f"  ❌ 请求异常: {e}")
    
    return False

def main():
    """主测试函数"""
    print("🚀 测试视频流修复效果...")
    print("="*60)
    
    # 测试关键视频流
    test_urls = [
        'http://localhost:5000/d_estimator/video_feed',
        'http://localhost:5000/f_detector/video_feed_left',
        'http://localhost:5000/f_detector/video_feed_right',
        'http://localhost:5000/enhanced_detector/video_feed'
    ]
    
    results = []
    
    for url in test_urls:
        result = test_video_stream_headers(url)
        results.append((url, result))
        print()
        time.sleep(0.5)
    
    print("="*60)
    print("📊 测试结果总结:")
    
    for url, success in results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  {url}: {status}")
    
    success_count = sum(1 for _, success in results if success)
    print(f"\n总体结果: {success_count}/{len(results)} 个视频流测试通过")

if __name__ == "__main__":
    main() 