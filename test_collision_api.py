#!/usr/bin/env python3
"""
测试碰撞检测API的行为
验证在没有真实数据时是否正确返回0值
"""

import requests
import json
import time

def test_collision_api():
    """测试碰撞检测API"""
    url = "http://localhost:5000/api/collision/risk"
    
    print("测试碰撞检测API...")
    print(f"请求URL: {url}")
    
    try:
        # 发送GET请求
        response = requests.get(url, timeout=5)
        
        print(f"状态码: {response.status_code}")
        print(f"响应头: {response.headers}")
        
        if response.status_code == 200:
            data = response.json()
            print("响应数据:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            # 验证数据结构
            if data.get('success'):
                max_prob = data.get('max_probability', 0)
                risk_info = data.get('risk', {})
                
                print(f"\n分析结果:")
                print(f"最大碰撞概率: {max_prob}%")
                print(f"风险等级: {risk_info.get('level', 'unknown')}")
                print(f"预测时间: {risk_info.get('time_to_collision', 'unknown')}")
                print(f"警告消息: {risk_info.get('warning_message', 'unknown')}")
                
                # 验证是否为默认值
                if max_prob == 0.0 and risk_info.get('level') == 'low':
                    print("✅ API正确返回了默认值（0%碰撞概率）")
                else:
                    print("⚠️ API返回了非默认值，可能有真实数据或模拟数据")
            else:
                print("❌ API返回success=False")
        else:
            print(f"❌ API返回错误状态码: {response.status_code}")
            print(f"错误内容: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求失败: {e}")
    except Exception as e:
        print(f"❌ 处理响应失败: {e}")

def test_multiple_requests():
    """测试多次请求的一致性"""
    print("\n测试多次请求的一致性...")
    
    results = []
    for i in range(3):
        try:
            response = requests.get("http://localhost:5000/api/collision/risk", timeout=5)
            if response.status_code == 200:
                data = response.json()
                max_prob = data.get('max_probability', 0)
                results.append(max_prob)
                print(f"请求 {i+1}: 碰撞概率 = {max_prob}%")
            else:
                print(f"请求 {i+1}: 失败 (状态码: {response.status_code})")
        except Exception as e:
            print(f"请求 {i+1}: 异常 - {e}")
        
        time.sleep(1)  # 等待1秒
    
    # 分析结果
    if results:
        if all(prob == 0.0 for prob in results):
            print("✅ 所有请求都返回0%碰撞概率（符合预期）")
        elif all(prob == results[0] for prob in results):
            print(f"⚠️ 所有请求返回相同的非零值: {results[0]}%")
        else:
            print(f"⚠️ 请求返回了不同的值: {results}")

if __name__ == "__main__":
    print("碰撞检测API测试工具")
    print("=" * 50)
    
    # 基本测试
    test_collision_api()
    
    # 多次请求测试
    test_multiple_requests()
    
    print("\n测试完成!") 