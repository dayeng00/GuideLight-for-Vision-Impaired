#!/usr/bin/env python3
"""
测试图像尺寸匹配
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'main'))

import time
import numpy as np
from main.utils.device_manager import device_manager
from main.utils.global_frame_cache import get_global_frame_cache

def test_image_sizes():
    """测试图像尺寸是否匹配"""
    print("🧪 开始测试图像尺寸...")
    
    # 获取全局帧缓存
    global_cache = get_global_frame_cache()
    
    # 启动设备管理器
    print("🚀 启动设备管理器...")
    if not device_manager.start():
        print("❌ 设备管理器启动失败")
        return False
    
    # 等待数据稳定
    print("⏳ 等待数据稳定...")
    time.sleep(3)
    
    # 获取当前帧数据
    frame_data = global_cache.get_current_frames(['color', 'depth'])
    
    if not frame_data:
        print("❌ 未获取到帧数据")
        device_manager.stop()
        return False
    
    # 检查图像尺寸
    success = True
    
    if 'color' in frame_data:
        color_frame = frame_data['color']
        print(f"🎨 彩色图像尺寸: {color_frame.shape}")
    else:
        print("❌ 未获取到彩色图像")
        success = False
    
    if 'depth' in frame_data:
        depth_frame = frame_data['depth']
        print(f"📏 深度图像尺寸: {depth_frame.shape}")
    else:
        print("❌ 未获取到深度图像")
        success = False
    
    # 检查尺寸是否匹配
    if 'color' in frame_data and 'depth' in frame_data:
        color_shape = frame_data['color'].shape[:2]  # (height, width)
        depth_shape = frame_data['depth'].shape[:2]  # (height, width)
        
        if color_shape == depth_shape:
            print(f"✅ 图像尺寸匹配: {color_shape}")
        else:
            print(f"❌ 图像尺寸不匹配: 彩色={color_shape}, 深度={depth_shape}")
            success = False
    
    # 停止设备管理器
    device_manager.stop()
    
    return success

if __name__ == "__main__":
    try:
        result = test_image_sizes()
        if result:
            print("✅ 图像尺寸测试通过")
            exit(0)
        else:
            print("❌ 图像尺寸测试失败")
            exit(1)
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        exit(1) 