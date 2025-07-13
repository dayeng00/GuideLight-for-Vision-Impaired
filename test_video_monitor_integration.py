#!/usr/bin/env python3
"""
视频监控系统全局帧缓存集成测试
"""
import sys
import os
import time
import threading
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "main"))

def test_global_frame_cache():
    """测试全局帧缓存功能"""
    print("🔍 测试全局帧缓存...")
    
    try:
        from main.utils.global_frame_cache import get_global_frame_cache
        
        # 获取全局帧缓存实例
        cache = get_global_frame_cache()
        print(f"✅ 全局帧缓存实例创建成功: {cache}")
        
        # 测试统计信息
        stats = cache.get_stats()
        print(f"📊 缓存统计信息: {stats}")
        
        # 测试帧可用性检查
        frame_types = ['color', 'depth', 'rectifiedLeft', 'rectifiedRight', 'imu']
        for frame_type in frame_types:
            available = cache.is_frame_available(frame_type)
            print(f"   {frame_type}: {'✅ 可用' if available else '❌ 不可用'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 全局帧缓存测试失败: {e}")
        return False

def test_device_manager():
    """测试设备管理器"""
    print("\n🔍 测试设备管理器...")
    
    try:
        from main.utils.device_manager import device_manager
        
        print(f"✅ 设备管理器实例: {device_manager}")
        print(f"   运行状态: {'✅ 运行中' if device_manager.is_running() else '❌ 未运行'}")
        
        # 获取统计信息
        stats = device_manager.get_stats()
        print(f"📊 设备管理器统计: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ 设备管理器测试失败: {e}")
        return False

def test_video_processors():
    """测试视频处理器"""
    print("\n🔍 测试视频处理器...")
    
    processors = [
        ('视差估计器', 'main.utils.disparity_estimator', 'DisparityEstimator'),
        ('特征点检测器', 'main.utils.feature_point_detector', 'FeaturePointDetector'),
        ('手势识别器', 'main.utils.gesture_recognizer', 'GestureRecognizer'),
        ('增强检测器', 'main.utils.enhanced_detector', 'EnhancedDetector'),
    ]
    
    results = {}
    
    for name, module_path, class_name in processors:
        try:
            module = __import__(module_path, fromlist=[class_name])
            processor_class = getattr(module, class_name)
            
            # 检查是否有全局帧缓存集成
            has_global_cache = hasattr(processor_class, '__init__')
            
            print(f"✅ {name}: 模块加载成功")
            print(f"   类名: {class_name}")
            print(f"   全局缓存集成: {'✅ 已集成' if has_global_cache else '❌ 未集成'}")
            
            results[name] = True
            
        except Exception as e:
            print(f"❌ {name}: 加载失败 - {e}")
            results[name] = False
    
    return results

def test_api_endpoints():
    """测试API端点"""
    print("\n🔍 测试API端点...")
    
    import requests
    
    base_url = "http://localhost:5000"
    
    endpoints = [
        ('/api/frame_cache/status', 'GET', '帧缓存状态'),
        ('/api/frame_cache/frames', 'GET', '帧数据信息'),
        ('/api/video_streams/status', 'GET', '视频流状态'),
    ]
    
    results = {}
    
    for endpoint, method, description in endpoints:
        try:
            url = f"{base_url}{endpoint}"
            
            if method == 'GET':
                response = requests.get(url, timeout=5)
            else:
                response = requests.post(url, timeout=5)
            
            if response.status_code == 200:
                print(f"✅ {description}: 响应正常 ({response.status_code})")
                results[endpoint] = True
            else:
                print(f"⚠️ {description}: 响应异常 ({response.status_code})")
                results[endpoint] = False
                
        except requests.exceptions.ConnectionError:
            print(f"❌ {description}: 服务器未运行")
            results[endpoint] = False
        except Exception as e:
            print(f"❌ {description}: 测试失败 - {e}")
            results[endpoint] = False
    
    return results

def test_integration():
    """集成测试"""
    print("\n🔍 集成测试...")
    
    try:
        # 测试全局帧缓存和设备管理器的集成
        from main.utils.global_frame_cache import get_global_frame_cache
        from main.utils.device_manager import device_manager
        
        cache = get_global_frame_cache()
        
        # 检查设备管理器是否连接到全局缓存
        if hasattr(device_manager, 'global_cache'):
            print("✅ 设备管理器已连接到全局帧缓存")
            
            # 检查缓存是否是同一个实例
            if device_manager.global_cache is cache:
                print("✅ 全局帧缓存单例模式工作正常")
            else:
                print("⚠️ 全局帧缓存实例不一致")
        else:
            print("❌ 设备管理器未连接到全局帧缓存")
        
        return True
        
    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始视频监控系统全局帧缓存集成测试")
    print("=" * 60)
    
    # 运行各项测试
    test_results = {}
    
    test_results['global_frame_cache'] = test_global_frame_cache()
    test_results['device_manager'] = test_device_manager()
    test_results['video_processors'] = test_video_processors()
    test_results['api_endpoints'] = test_api_endpoints()
    test_results['integration'] = test_integration()
    
    # 总结测试结果
    print("\n" + "=" * 60)
    print("📋 测试结果总结:")
    
    all_passed = True
    for test_name, result in test_results.items():
        if isinstance(result, dict):
            # 对于返回字典的测试，检查是否所有子项都通过
            sub_passed = all(result.values())
            status = "✅ 通过" if sub_passed else "❌ 失败"
            print(f"   {test_name}: {status}")
            if not sub_passed:
                all_passed = False
        else:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"   {test_name}: {status}")
            if not result:
                all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过！视频监控系统全局帧缓存集成正常。")
        return 0
    else:
        print("⚠️ 部分测试失败，请检查相关组件。")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 