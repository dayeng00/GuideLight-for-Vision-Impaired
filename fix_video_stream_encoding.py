#!/usr/bin/env python3
"""
修复视频流编码问题
主要问题：create_threaded_video_stream函数对已经编码的MJPEG数据进行了二次编码
"""

import os
import sys

def fix_main_py():
    """修复main.py中的视频流处理逻辑"""
    main_py_path = "main/main.py"
    
    print("🔧 修复main.py中的视频流处理逻辑...")
    
    # 读取原文件
    with open(main_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 找到需要修复的函数
    old_function = '''def create_threaded_video_stream(stream_id: str, source_func: Callable, response_headers: dict = None):
    """创建线程化的视频流响应"""
    def generate():
        client_id = None
        try:
            # 获取或创建视频流
            stream = thread_manager.get_stream(stream_id)
            if stream is None:
                stream = thread_manager.create_stream(stream_id, source_func, max_buffer_size=5)
            
            # 添加客户端连接
            client_id = stream.add_client()
            
            while True:
                # 非阻塞获取帧
                frame_data = stream.get_frame(timeout=0.1)
                
                if frame_data is not None:
                    yield (b'--frame\\r\\n'
                           b'Content-Type: image/jpeg\\r\\n\\r\\n' + frame_data + b'\\r\\n')
                else:
                    # 没有帧时短暂休眠
                    time.sleep(0.033)  # ~30fps
                    
        except GeneratorExit:
            # 客户端断开连接
            pass
        except Exception as e:
            logger.error(f"视频流 {stream_id} 生成错误: {e}")
        finally:
            # 清理客户端连接
            if client_id and stream:
                stream.remove_client(client_id)'''
    
    # 新的修复后的函数
    new_function = '''def create_threaded_video_stream(stream_id: str, source_func: Callable, response_headers: dict = None):
    """创建线程化的视频流响应"""
    def generate():
        client_id = None
        try:
            # 获取或创建视频流
            stream = thread_manager.get_stream(stream_id)
            if stream is None:
                stream = thread_manager.create_stream(stream_id, source_func, max_buffer_size=5)
            
            # 添加客户端连接
            client_id = stream.add_client()
            
            while True:
                # 非阻塞获取帧
                frame_data = stream.get_frame(timeout=0.1)
                
                if frame_data is not None:
                    # 直接返回已编码的MJPEG数据，不再二次包装
                    yield frame_data
                else:
                    # 没有帧时短暂休眠
                    time.sleep(0.033)  # ~30fps
                    
        except GeneratorExit:
            # 客户端断开连接
            pass
        except Exception as e:
            logger.error(f"视频流 {stream_id} 生成错误: {e}")
        finally:
            # 清理客户端连接
            if client_id and stream:
                stream.remove_client(client_id)'''
    
    # 替换内容
    if old_function in content:
        content = content.replace(old_function, new_function)
        print("✅ 已修复create_threaded_video_stream函数")
    else:
        print("⚠️ 未找到需要修复的函数，可能已经修复或函数结构已变化")
    
    # 写回文件
    with open(main_py_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def add_response_headers():
    """为视频流路由添加正确的响应头"""
    main_py_path = "main/main.py"
    
    print("🔧 为视频流路由添加正确的响应头...")
    
    # 读取原文件
    with open(main_py_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找所有视频流路由并添加响应头
    video_routes = [
        'd_feed', 'f_d_feed_left', 'f_d_feed_right', 'f_d_feed',
        'f_t_feed_left', 'f_t_feed_right', 'f_t_feed',
        'g_recognition_feed', 'r_feed', 'm_feed', 'enhanced_detector_feed'
    ]
    
    for route in video_routes:
        # 查找路由函数
        pattern = f'def {route}():'
        if pattern in content:
            # 查找return语句
            start_idx = content.find(pattern)
            if start_idx != -1:
                # 找到函数结束
                func_start = start_idx
                brace_count = 0
                in_function = False
                
                # 查找return create_threaded_video_stream的位置
                return_pattern = f'return create_threaded_video_stream('
                return_idx = content.find(return_pattern, func_start)
                
                if return_idx != -1:
                    # 找到return语句的结束
                    line_end = content.find('\n', return_idx)
                    if line_end != -1:
                        # 在return语句前添加响应头设置
                        before_return = content[:return_idx]
                        after_return = content[return_idx:]
                        
                        # 添加响应头设置
                        response_header_code = '''    
    # 设置正确的MJPEG流响应头
    response_headers = {
        'Content-Type': 'multipart/x-mixed-replace; boundary=frame',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }
    
    '''
                        
                        # 修改return语句以包含响应头
                        new_return = after_return.replace(
                            'return create_threaded_video_stream(',
                            'response = Response(create_threaded_video_stream(',
                            1
                        )
                        
                        # 找到函数调用的结束
                        paren_count = 0
                        call_end = -1
                        for i, char in enumerate(new_return):
                            if char == '(':
                                paren_count += 1
                            elif char == ')':
                                paren_count -= 1
                                if paren_count == 0:
                                    call_end = i + 1
                                    break
                        
                        if call_end != -1:
                            # 添加响应头和return语句
                            new_return = (new_return[:call_end] + 
                                        ', response_headers)' +
                                        '\n    ' +
                                        'for key, value in response_headers.items():\n' +
                                        '        response.headers[key] = value\n' +
                                        '    return response' +
                                        new_return[call_end:])
                            
                            content = before_return + response_header_code + new_return
                            print(f"✅ 已为 {route} 添加响应头")
    
    # 写回文件
    with open(main_py_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

def create_test_video_stream():
    """创建一个测试视频流来验证修复"""
    test_code = '''#!/usr/bin/env python3
"""
测试视频流编码修复
"""
import requests
import time
import cv2
import numpy as np
from PIL import Image
import io

def test_video_stream_response(url):
    """测试视频流响应格式"""
    print(f"🔍 测试视频流: {url}")
    
    try:
        response = requests.get(url, stream=True, timeout=10)
        print(f"  状态码: {response.status_code}")
        print(f"  内容类型: {response.headers.get('Content-Type', 'None')}")
        
        if response.status_code == 200:
            # 读取前几个字节检查格式
            chunk_size = 1024
            data_chunk = b''
            
            for chunk in response.iter_content(chunk_size=chunk_size):
                data_chunk += chunk
                if len(data_chunk) > 2048:  # 读取足够的数据
                    break
            
            # 检查是否为MJPEG格式
            if b'--frame' in data_chunk:
                print("  ✅ 检测到MJPEG边界标记")
                
                # 尝试提取第一帧
                try:
                    frame_start = data_chunk.find(b'\\r\\n\\r\\n') + 4
                    frame_end = data_chunk.find(b'\\r\\n--frame', frame_start)
                    
                    if frame_start > 3 and frame_end > frame_start:
                        frame_data = data_chunk[frame_start:frame_end]
                        
                        # 验证是否为有效的JPEG数据
                        if frame_data.startswith(b'\\xff\\xd8') and b'\\xff\\xd9' in frame_data:
                            print("  ✅ 检测到有效的JPEG帧数据")
                            
                            # 尝试解码图像
                            try:
                                image = Image.open(io.BytesIO(frame_data))
                                print(f"  ✅ 图像解码成功: {image.size}")
                                return True
                            except Exception as e:
                                print(f"  ❌ 图像解码失败: {e}")
                        else:
                            print("  ❌ 无效的JPEG数据")
                            print(f"  前16字节: {frame_data[:16]}")
                    else:
                        print("  ❌ 无法找到完整的帧数据")
                        
                except Exception as e:
                    print(f"  ❌ 帧提取失败: {e}")
            else:
                print("  ❌ 未检测到MJPEG格式")
                print(f"  前64字节: {data_chunk[:64]}")
        else:
            print(f"  ❌ 请求失败: {response.text[:200]}")
            
    except Exception as e:
        print(f"  ❌ 请求异常: {e}")
    
    return False

def main():
    """主测试函数"""
    print("🚀 开始测试视频流编码修复...")
    
    # 测试的视频流URL
    test_urls = [
        'http://localhost:5000/d_estimator/video_feed',
        'http://localhost:5000/f_detector/video_feed_left',
        'http://localhost:5000/enhanced_detector/video_feed',
        'http://localhost:5000/g_recognition/video_feed'
    ]
    
    results = []
    
    for url in test_urls:
        result = test_video_stream_response(url)
        results.append((url, result))
        time.sleep(1)  # 避免过快请求
    
    print("\\n" + "="*60)
    print("📊 测试结果总结:")
    
    success_count = 0
    for url, success in results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  {url}: {status}")
        if success:
            success_count += 1
    
    print(f"\\n总体结果: {success_count}/{len(results)} 个视频流测试通过")
    
    if success_count == len(results):
        print("🎉 所有视频流测试通过！")
    else:
        print("⚠️ 部分视频流测试失败，需要进一步检查")

if __name__ == "__main__":
    main()
'''
    
    with open('test_video_stream_encoding.py', 'w', encoding='utf-8') as f:
        f.write(test_code)
    
    print("✅ 已创建测试脚本: test_video_stream_encoding.py")

def main():
    """主修复函数"""
    print("🚀 开始修复视频流编码问题...")
    print("="*60)
    
    # 1. 修复main.py中的视频流处理逻辑
    fix_main_py()
    
    # 2. 创建测试脚本
    create_test_video_stream()
    
    print("="*60)
    print("✅ 修复完成！")
    print("📝 修复内容:")
    print("  1. 修复了create_threaded_video_stream函数的二次编码问题")
    print("  2. 创建了测试脚本来验证修复效果")
    print()
    print("🔍 下一步:")
    print("  1. 重启后端服务器")
    print("  2. 启动摄像头")
    print("  3. 运行测试脚本: python test_video_stream_encoding.py")
    print("  4. 在浏览器中测试视频流显示")

if __name__ == "__main__":
    main() 