#!/usr/bin/env python3
"""
测试增强检测器和碰撞检测的完整流程
"""

import requests
import json
import time

def test_enhanced_detector_flow():
    """测试增强检测器的完整流程"""
    base_url = "http://localhost:5000"
    
    print("=" * 60)
    print("增强检测器和碰撞检测完整流程测试")
    print("=" * 60)
    
    # 1. 启动增强检测器
    print("\n1. 启动增强检测器...")
    try:
        response = requests.post(f"{base_url}/enhanced_detector/start", timeout=10)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
            print("✅ 增强检测器启动成功")
        else:
            print(f"❌ 启动失败: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 启动请求失败: {e}")
        return False
    
    # 2. 等待系统初始化
    print("\n2. 等待系统初始化...")
    time.sleep(3)
    
    # 3. 检查轨迹追踪状态
    print("\n3. 检查轨迹追踪状态...")
    try:
        response = requests.get(f"{base_url}/api/trajectory/status", timeout=5)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"轨迹追踪状态: {json.dumps(data, indent=2, ensure_ascii=False)}")
        else:
            print(f"⚠️ 轨迹追踪状态获取失败: {response.text}")
    except Exception as e:
        print(f"⚠️ 轨迹追踪状态请求失败: {e}")
    
    # 4. 测试碰撞风险API（多次）
    print("\n4. 测试碰撞风险API...")
    for i in range(5):
        try:
            response = requests.get(f"{base_url}/api/collision/risk", timeout=5)
            print(f"请求 {i+1} - 状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                max_prob = data.get('max_probability', 0)
                risk_level = data.get('risk', {}).get('level', 'unknown')
                warning_msg = data.get('risk', {}).get('warning_message', 'unknown')
                tracks = data.get('tracks', {})
                detected_objects = data.get('detected_objects', [])
                
                print(f"  - 最大碰撞概率: {max_prob}%")
                print(f"  - 风险等级: {risk_level}")
                print(f"  - 警告消息: {warning_msg}")
                print(f"  - 活跃轨迹数: {len(tracks)}")
                print(f"  - 检测物体数: {len(detected_objects)}")
                
                if max_prob > 0 or len(tracks) > 0 or len(detected_objects) > 0:
                    print(f"  ✅ 检测到真实数据！")
                    print(f"  详细数据: {json.dumps(data, indent=4, ensure_ascii=False)}")
                    break
                else:
                    print(f"  ⚠️ 暂无检测数据")
            else:
                print(f"  ❌ 请求失败: {response.text}")
        except Exception as e:
            print(f"  ❌ 请求异常: {e}")
        
        if i < 4:  # 不是最后一次
            time.sleep(2)
    
    # 5. 检查视频流
    print("\n5. 检查视频流...")
    try:
        response = requests.get(f"{base_url}/enhanced_detector/video_feed", 
                              timeout=5, stream=True)
        print(f"视频流状态码: {response.status_code}")
        if response.status_code == 200:
            print("✅ 视频流可访问")
            print(f"视频流URL: {base_url}/enhanced_detector/video_feed")
        else:
            print(f"❌ 视频流不可访问: {response.text}")
    except Exception as e:
        print(f"⚠️ 视频流检查失败: {e}")
    
    # 6. 获取轨迹数据
    print("\n6. 获取轨迹数据...")
    try:
        response = requests.get(f"{base_url}/api/trajectory/data", timeout=5)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            trajectory_data = data.get('data', {})
            print(f"轨迹数据项数: {len(trajectory_data)}")
            if trajectory_data:
                print(f"轨迹数据: {json.dumps(trajectory_data, indent=2, ensure_ascii=False)}")
        else:
            print(f"⚠️ 轨迹数据获取失败: {response.text}")
    except Exception as e:
        print(f"⚠️ 轨迹数据请求失败: {e}")
    
    # 7. 获取检测到的对象
    print("\n7. 获取检测到的对象...")
    try:
        response = requests.get(f"{base_url}/api/collision/objects", timeout=5)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            objects = data.get('objects', [])
            print(f"检测到的对象数: {len(objects)}")
            if objects:
                print(f"对象详情: {json.dumps(objects, indent=2, ensure_ascii=False)}")
        else:
            print(f"⚠️ 对象数据获取失败: {response.text}")
    except Exception as e:
        print(f"⚠️ 对象数据请求失败: {e}")
    
    print("\n" + "=" * 60)
    print("测试总结:")
    print("1. 如果看到'检测到真实数据'，说明系统正常工作")
    print("2. 如果所有数据都是0，可能是:")
    print("   - 摄像头没有连接")
    print("   - 视野中没有人物")
    print("   - YOLO模型加载失败")
    print("3. 视频流URL可以在浏览器中查看实时画面")
    print("=" * 60)
    
    return True

def test_stop_enhanced_detector():
    """停止增强检测器"""
    print("\n停止增强检测器...")
    try:
        response = requests.post("http://localhost:5000/enhanced_detector/stop", timeout=10)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
            print("✅ 增强检测器停止成功")
        else:
            print(f"⚠️ 停止失败: {response.text}")
    except Exception as e:
        print(f"⚠️ 停止请求失败: {e}")

if __name__ == "__main__":
    try:
        # 运行完整测试
        test_enhanced_detector_flow()
        
        # 询问是否停止
        user_input = input("\n是否停止增强检测器? (y/n): ")
        if user_input.lower() in ['y', 'yes', '是']:
            test_stop_enhanced_detector()
        else:
            print("增强检测器继续运行...")
            print("你可以访问 http://localhost:5000/enhanced_detector/video_feed 查看视频流")
            
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        test_stop_enhanced_detector()
    except Exception as e:
        print(f"\n\n测试过程中出现异常: {e}") 