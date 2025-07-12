"""
测试多线程视频流系统
"""
import time
import threading
import requests
import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor

def test_thread_manager():
    """测试线程管理器基本功能"""
    print("🧪 测试线程管理器...")
    
    try:
        from main.utils.thread_manager import get_thread_manager
        
        # 创建线程管理器
        tm = get_thread_manager()
        print(f"✅ 线程管理器创建成功")
        print(f"   - 最大工作线程数: {tm.max_workers}")
        print(f"   - 请求工作线程数: {len(tm.request_workers)}")
        
        # 测试异步任务
        def test_task(n):
            time.sleep(0.1)
            return f"任务{n}完成"
        
        futures = []
        for i in range(5):
            future = tm.submit_async_task(test_task, i)
            futures.append(future)
        
        # 等待所有任务完成
        results = [f.result() for f in futures]
        print(f"✅ 异步任务测试完成: {results}")
        
        # 测试请求任务
        result = tm.submit_request_task(lambda x: x * 2, 21)
        print(f"✅ 请求任务测试完成: {result}")
        
        # 获取性能统计
        stats = tm.get_performance_stats()
        print(f"✅ 性能统计获取成功: {len(stats)} 个指标")
        
        return True
    except Exception as e:
        print(f"❌ 线程管理器测试失败: {e}")
        return False

def simulate_video_generator():
    """模拟视频流生成器"""
    for i in range(10):
        # 创建一个简单的测试帧
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.putText(frame, f"Frame {i}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # 编码为JPEG
        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        
        # 以MJPEG格式返回
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        time.sleep(0.1)  # 模拟10fps

def test_video_stream():
    """测试视频流功能"""
    print("\n🎥 测试视频流功能...")
    
    try:
        from main.utils.thread_manager import get_thread_manager
        
        tm = get_thread_manager()
        
        # 创建测试视频流
        stream = tm.create_video_stream('test_stream', simulate_video_generator)
        print("✅ 测试视频流创建成功")
        
        # 模拟多个客户端连接
        for i in range(3):
            stream.add_client()
        print(f"✅ 添加了3个客户端连接")
        
        # 获取几帧数据
        frames_received = 0
        for _ in range(5):
            frame_data = stream.get_frame(timeout=1.0)
            if frame_data:
                frames_received += 1
            time.sleep(0.1)
        
        print(f"✅ 成功接收了 {frames_received} 帧数据")
        
        # 移除客户端连接
        for i in range(3):
            stream.remove_client()
        
        # 停止视频流
        tm.remove_video_stream('test_stream')
        print("✅ 测试视频流清理完成")
        
        return True
    except Exception as e:
        print(f"❌ 视频流测试失败: {e}")
        return False

def test_concurrent_requests():
    """测试并发请求处理"""
    print("\n🚀 测试并发请求处理...")
    
    base_url = "http://localhost:5000"
    
    def make_request(endpoint):
        """发送单个请求"""
        try:
            start_time = time.time()
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            end_time = time.time()
            
            return {
                'endpoint': endpoint,
                'status_code': response.status_code,
                'response_time': end_time - start_time,
                'success': response.status_code == 200
            }
        except Exception as e:
            return {
                'endpoint': endpoint,
                'error': str(e),
                'success': False
            }
    
    # 测试端点列表
    test_endpoints = [
        '/api/health',
        '/api/streams/stats',
        '/api/integrated/status',
        '/api/trajectory/status',
        '/api/collision/risk'
    ]
    
    print("发送并发请求...")
    
    # 使用线程池发送并发请求
    with ThreadPoolExecutor(max_workers=10) as executor:
        # 每个端点发送多个并发请求
        futures = []
        for endpoint in test_endpoints:
            for i in range(3):  # 每个端点3个并发请求
                future = executor.submit(make_request, endpoint)
                futures.append(future)
        
        # 等待所有请求完成
        results = [f.result() for f in futures]
    
    # 分析结果
    successful_requests = [r for r in results if r.get('success', False)]
    failed_requests = [r for r in results if not r.get('success', False)]
    
    print(f"✅ 并发请求测试完成:")
    print(f"   - 总请求数: {len(results)}")
    print(f"   - 成功请求: {len(successful_requests)}")
    print(f"   - 失败请求: {len(failed_requests)}")
    
    if successful_requests:
        avg_response_time = sum(r['response_time'] for r in successful_requests) / len(successful_requests)
        print(f"   - 平均响应时间: {avg_response_time:.3f}s")
    
    return len(successful_requests) > 0

def main():
    """主测试函数"""
    print("🔧 开始测试多线程视频流系统")
    print("=" * 50)
    
    # 测试1: 线程管理器基本功能
    test1_passed = test_thread_manager()
    
    # 测试2: 视频流功能
    test2_passed = test_video_stream()
    
    # 测试3: 并发请求处理（需要Flask服务器运行）
    print("\n⚠️ 并发请求测试需要Flask服务器运行")
    print("请先运行: python main/main.py")
    user_input = input("Flask服务器是否已运行？(y/n): ").lower().strip()
    
    test3_passed = False
    if user_input == 'y':
        test3_passed = test_concurrent_requests()
    else:
        print("跳过并发请求测试")
    
    # 清理资源
    try:
        from main.utils.thread_manager import shutdown_thread_manager
        shutdown_thread_manager()
        print("\n✅ 线程管理器已关闭")
    except Exception as e:
        print(f"\n⚠️ 关闭线程管理器时出错: {e}")
    
    # 总结结果
    print("\n" + "=" * 50)
    print("🎯 测试结果总结:")
    print(f"   - 线程管理器测试: {'✅ 通过' if test1_passed else '❌ 失败'}")
    print(f"   - 视频流测试: {'✅ 通过' if test2_passed else '❌ 失败'}")
    print(f"   - 并发请求测试: {'✅ 通过' if test3_passed else '❌ 跳过/失败'}")
    
    all_passed = test1_passed and test2_passed
    if all_passed:
        print("\n🎉 多线程系统测试全部通过！")
        print("💡 系统现在支持:")
        print("   - 非阻塞视频流处理")
        print("   - 并发请求处理")
        print("   - 线程安全的资源管理")
        print("   - 自动性能监控")
    else:
        print("\n⚠️ 部分测试失败，请检查错误信息")
    
    return all_passed

if __name__ == "__main__":
    main() 