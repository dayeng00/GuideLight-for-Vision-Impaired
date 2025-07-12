#!/usr/bin/env python3
"""
数据流调试脚本 - 检查设备管理器、全局帧缓存和环境处理器的状态
"""

import time
import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_device_manager():
    """检查设备管理器状态"""
    print("=" * 50)
    print("🔍 检查设备管理器状态")
    print("=" * 50)
    
    try:
        from utils.device_manager import device_manager
        
        print(f"✅ 设备管理器实例: {device_manager}")
        print(f"📊 是否运行: {device_manager.is_running()}")
        
        if device_manager.is_running():
            print(f"📈 统计信息: {device_manager.get_stats()}")
            print(f"🔗 队列状态: {list(device_manager.queues.keys())}")
            
            # 检查最新数据
            with device_manager.data_lock:
                latest_data = device_manager.latest_data
                print(f"📸 最新数据时间戳: {latest_data.get('timestamp')}")
                print(f"🎨 RGB数据: {'有' if latest_data.get('color') is not None else '无'}")
                print(f"📏 深度数据: {'有' if latest_data.get('depth') is not None else '无'}")
                print(f"📐 IMU数据: {'有' if latest_data.get('imu') is not None else '无'}")
        else:
            print("⚠️ 设备管理器未运行，尝试启动...")
            success = device_manager.start()
            print(f"🚀 启动结果: {'成功' if success else '失败'}")
            
            if success:
                print("⏳ 等待设备初始化...")
                time.sleep(3)
                print(f"📊 启动后状态: {device_manager.is_running()}")
        
        return device_manager.is_running()
        
    except Exception as e:
        print(f"❌ 设备管理器检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_global_frame_cache():
    """检查全局帧缓存状态"""
    print("\n" + "=" * 50)
    print("🔍 检查全局帧缓存状态")
    print("=" * 50)
    
    try:
        from utils.global_frame_cache import get_global_frame_cache
        global_frame_cache = get_global_frame_cache()
        
        print(f"✅ 全局帧缓存实例: {global_frame_cache}")
        
        # 获取统计信息
        stats = global_frame_cache.get_stats()
        print(f"📊 统计信息: {stats}")
        
        # 检查当前帧
        current_frames = global_frame_cache.get_current_frames()
        print(f"📸 当前帧数据:")
        for key, value in current_frames.items():
            if key == 'timestamp':
                print(f"   {key}: {value}")
            else:
                print(f"   {key}: {'有数据' if value is not None else '无数据'}")
        
        return len([v for k, v in current_frames.items() if k != 'timestamp' and v is not None]) > 0
        
    except Exception as e:
        print(f"❌ 全局帧缓存检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_environment_processor():
    """检查环境处理器状态"""
    print("\n" + "=" * 50)
    print("🔍 检查环境处理器状态")
    print("=" * 50)
    
    try:
        from utils.environment_processor import get_environment_processor
        environment_processor = get_environment_processor()
        
        print(f"✅ 环境处理器实例: {environment_processor}")
        
        if environment_processor:
            status = environment_processor.get_status()
            print(f"📊 处理器状态: {status}")
            
            # 检查全局帧缓存连接
            print(f"🔗 全局帧缓存连接: {'已连接' if environment_processor.global_frame_cache else '未连接'}")
            
            # 检查最新结果
            latest_result = environment_processor.get_latest_result()
            print(f"📋 最新结果: {'有' if latest_result else '无'}")
            
            if latest_result:
                print(f"   检测对象数量: {len(latest_result.get('detected_objects', []))}")
                print(f"   处理时间: {latest_result.get('processing_time', 0):.3f}秒")
            
            return True
        else:
            print("❌ 环境处理器未初始化")
            return False
        
    except Exception as e:
        print(f"❌ 环境处理器检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_mock_data_provider():
    """检查模拟数据提供器状态"""
    print("\n" + "=" * 50)
    print("🔍 检查模拟数据提供器状态")
    print("=" * 50)
    
    try:
        from utils.mock_data_provider import get_mock_data_provider
        from utils.global_frame_cache import get_global_frame_cache
        
        global_frame_cache = get_global_frame_cache()
        mock_data_provider = get_mock_data_provider(global_frame_cache)
        
        print(f"✅ 模拟数据提供器实例: {mock_data_provider}")
        
        if mock_data_provider:
            status = mock_data_provider.get_status()
            print(f"📊 提供器状态: {status}")
            
            if not mock_data_provider.is_running:
                print("🚀 启动模拟数据提供器...")
                success = mock_data_provider.start()
                print(f"🎯 启动结果: {'成功' if success else '失败'}")
                
                if success:
                    print("⏳ 等待数据生成...")
                    time.sleep(2)
                    new_status = mock_data_provider.get_status()
                    print(f"📊 启动后状态: {new_status}")
            
            return True
        else:
            print("❌ 模拟数据提供器未初始化")
            return False
        
    except Exception as e:
        print(f"❌ 模拟数据提供器检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_flow():
    """测试完整数据流"""
    print("\n" + "=" * 50)
    print("🔍 测试完整数据流")
    print("=" * 50)
    
    try:
        from utils.environment_processor import get_environment_processor
        environment_processor = get_environment_processor()
        
        if not environment_processor:
            print("❌ 环境处理器不可用")
            return False
        
        # 启动处理
        print("🚀 启动环境处理器...")
        environment_processor.start_processing()
        
        # 等待处理
        print("⏳ 等待数据处理...")
        for i in range(10):
            time.sleep(1)
            result = environment_processor.get_latest_result()
            if result:
                print(f"✅ 第{i+1}秒: 获得处理结果")
                print(f"   检测对象: {len(result.get('detected_objects', []))}")
                print(f"   BEV图像: {'有' if result.get('bev_image_base64') else '无'}")
                return True
            else:
                print(f"⏳ 第{i+1}秒: 等待结果...")
        
        print("❌ 10秒内未获得处理结果")
        return False
        
    except Exception as e:
        print(f"❌ 数据流测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🚀 开始数据流调试检查")
    print("=" * 80)
    
    # 1. 检查设备管理器
    device_ok = check_device_manager()
    
    # 2. 检查全局帧缓存
    cache_ok = check_global_frame_cache()
    
    # 3. 检查环境处理器
    processor_ok = check_environment_processor()
    
    # 4. 检查模拟数据提供器
    mock_ok = check_mock_data_provider()
    
    # 5. 测试数据流
    if processor_ok and (device_ok or mock_ok):
        flow_ok = test_data_flow()
    else:
        flow_ok = False
        print("\n⚠️ 跳过数据流测试，因为前置条件不满足")
    
    # 总结
    print("\n" + "=" * 80)
    print("📋 调试结果总结")
    print("=" * 80)
    print(f"📱 设备管理器: {'✅ 正常' if device_ok else '❌ 异常'}")
    print(f"💾 全局帧缓存: {'✅ 正常' if cache_ok else '❌ 异常'}")
    print(f"🔍 环境处理器: {'✅ 正常' if processor_ok else '❌ 异常'}")
    print(f"🎭 模拟数据提供器: {'✅ 正常' if mock_ok else '❌ 异常'}")
    print(f"🌊 数据流测试: {'✅ 正常' if flow_ok else '❌ 异常'}")
    
    if flow_ok:
        print("\n🎉 数据流正常，环境感知API应该可以返回有效结果")
    else:
        print("\n⚠️ 数据流存在问题，需要修复后才能正常工作")
        
        # 提供修复建议
        print("\n🔧 修复建议:")
        if not device_ok and not mock_ok:
            print("   1. 检查DepthAI设备连接或启动模拟数据提供器")
        if not cache_ok:
            print("   2. 检查全局帧缓存初始化")
        if not processor_ok:
            print("   3. 检查环境处理器初始化和YOLO模型")

if __name__ == "__main__":
    main() 