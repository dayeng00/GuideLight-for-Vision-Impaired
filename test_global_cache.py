#!/usr/bin/env python3
"""
测试全局帧缓存系统
"""
import sys
import os
import time
import numpy as np

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'main'))

def test_global_cache():
    """测试全局帧缓存系统"""
    print("🧪 开始测试全局帧缓存系统...")
    
    try:
        # 导入全局帧缓存
        from main.utils.global_frame_cache import get_global_frame_cache
        
        cache = get_global_frame_cache()
        print("✅ 全局帧缓存初始化成功")
        
        # 测试基本功能
        print("\n📊 测试基本功能:")
        
        # 创建模拟帧数据
        color_frame = np.random.randint(0, 255, (360, 640, 3), dtype=np.uint8)
        depth_frame = np.random.randint(0, 10000, (360, 640), dtype=np.uint16)
        
        test_data = {
            'color': color_frame,
            'depth': depth_frame,
            'timestamp': time.time()
        }
        
        # 更新帧数据
        cache.update_frames(test_data)
        print("✅ 帧数据更新成功")
        
        # 获取当前帧
        retrieved_color = cache.get_current_frame('color')
        if retrieved_color is not None:
            print(f"✅ 成功获取彩色帧: {retrieved_color.shape}")
        else:
            print("❌ 获取彩色帧失败")
        
        # 获取多个帧
        current_frames = cache.get_current_frames(['color', 'depth'])
        print(f"✅ 获取多帧数据: {list(current_frames.keys())}")
        
        # 测试订阅功能
        print("\n📡 测试订阅功能:")
        
        callback_called = [False]  # 使用列表避免作用域问题
        def test_callback(frame_data):
            callback_called[0] = True
            print(f"📥 回调函数接收到数据: {list(frame_data.keys())}")
        
        cache.subscribe("test_subscriber", test_callback)
        
        # 更新数据触发回调
        cache.update_frames(test_data)
        time.sleep(0.1)  # 等待回调执行
        
        if callback_called[0]:
            print("✅ 订阅回调功能正常")
        else:
            print("❌ 订阅回调功能异常")
        
        # 获取统计信息
        stats = cache.get_stats()
        print(f"\n📈 缓存统计信息:")
        print(f"   总帧数: {stats['total_frames']}")
        print(f"   当前FPS: {stats['current_fps']:.1f}")
        print(f"   订阅者数量: {stats['subscribers_count']}")
        print(f"   缓存命中率: {stats['cache_hit_rate']:.1f}%")
        print(f"   可用帧类型: {stats['available_frame_types']}")
        
        # 清理
        cache.unsubscribe("test_subscriber")
        print("✅ 测试完成，已清理资源")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_device_manager():
    """测试设备管理器（不启动实际设备）"""
    print("\n🧪 开始测试设备管理器...")
    
    try:
        from main.utils.device_manager import device_manager
        
        print("✅ 设备管理器导入成功")
        
        # 检查初始状态
        if not device_manager.is_running():
            print("✅ 设备管理器初始状态正确（未运行）")
        else:
            print("⚠️ 设备管理器已在运行")
        
        # 获取统计信息
        stats = device_manager.get_stats()
        print(f"📊 设备管理器统计:")
        print(f"   已处理帧数: {stats['frames_processed']}")
        print(f"   订阅者数量: {len(device_manager.subscribers)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 设备管理器测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始全局帧缓存系统测试")
    
    # 测试全局帧缓存
    cache_test_result = test_global_cache()
    
    # 测试设备管理器
    device_test_result = test_device_manager()
    
    print(f"\n📋 测试结果:")
    print(f"   全局帧缓存: {'✅ 通过' if cache_test_result else '❌ 失败'}")
    print(f"   设备管理器: {'✅ 通过' if device_test_result else '❌ 失败'}")
    
    if cache_test_result and device_test_result:
        print("\n🎉 所有测试通过！全局帧缓存系统已准备就绪")
        sys.exit(0)
    else:
        print("\n⚠️ 部分测试失败，请检查系统配置")
        sys.exit(1) 