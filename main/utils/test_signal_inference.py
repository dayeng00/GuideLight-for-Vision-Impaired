#!/usr/bin/env python
# coding: utf-8

"""
用户行为识别推理模型测试脚本
"""

import numpy as np
import pandas as pd
import json
import requests
import time
from signal_user_inference import SignalUserInference, get_signal_user_inference

def create_test_data():
    """
    创建测试数据
    """
    # 创建模拟的传感器数据
    num_samples = 60
    
    test_data = {
        'cell_id': np.random.randint(0, 100, num_samples),
        'gps_id': np.random.randint(0, 30, num_samples),
        'wifi_id': np.random.randint(0, 50, num_samples),
        'cell_num': np.random.randint(1, 10, num_samples),
        'dBm': np.random.uniform(-100, -50, num_samples),
        'gps_num': np.random.randint(1, 15, num_samples),
        'Latitude': np.random.uniform(31.8, 31.9, num_samples),
        'Longitude': np.random.uniform(117.2, 117.3, num_samples),
        'Altitude': np.random.uniform(10, 100, num_samples),
        'wifi_num': np.random.randint(1, 20, num_samples),
        'SNR': np.random.uniform(0, 30, num_samples),
        'RSSI': np.random.uniform(-80, -30, num_samples),
        'Acc_x': np.random.uniform(-2, 2, num_samples),
        'Acc_y': np.random.uniform(-2, 2, num_samples),
        'Acc_z': np.random.uniform(8, 12, num_samples),
        'Gyr_x': np.random.uniform(-1, 1, num_samples),
        'Gyr_y': np.random.uniform(-1, 1, num_samples),
        'Gyr_z': np.random.uniform(-1, 1, num_samples),
        'Mag_x': np.random.uniform(-50, 50, num_samples),
        'Mag_y': np.random.uniform(-50, 50, num_samples),
        'Mag_z': np.random.uniform(-50, 50, num_samples),
        'Ori_w': np.random.uniform(-1, 1, num_samples),
        'Ori_x': np.random.uniform(-1, 1, num_samples),
        'Ori_y': np.random.uniform(-1, 1, num_samples),
        'Ori_z': np.random.uniform(-1, 1, num_samples),
        'LAcc_x': np.random.uniform(-2, 2, num_samples),
        'LAcc_y': np.random.uniform(-2, 2, num_samples),
        'LAcc_z': np.random.uniform(-2, 2, num_samples),
        'Pressure': np.random.uniform(1000, 1020, num_samples)
    }
    
    return pd.DataFrame(test_data)

def create_different_behavior_data():
    """
    创建不同行为模式的测试数据
    """
    behaviors = {
        'stationary': {  # 静止
            'Acc_x': np.random.normal(0, 0.1, 60),
            'Acc_y': np.random.normal(0, 0.1, 60),
            'Acc_z': np.random.normal(9.8, 0.1, 60),
            'Gyr_x': np.random.normal(0, 0.05, 60),
            'Gyr_y': np.random.normal(0, 0.05, 60),
            'Gyr_z': np.random.normal(0, 0.05, 60),
        },
        'walking': {  # 走路
            'Acc_x': np.random.normal(0, 1.0, 60),
            'Acc_y': np.random.normal(0, 1.0, 60),
            'Acc_z': np.random.normal(9.8, 1.5, 60),
            'Gyr_x': np.random.normal(0, 0.3, 60),
            'Gyr_y': np.random.normal(0, 0.3, 60),
            'Gyr_z': np.random.normal(0, 0.3, 60),
        },
        'running': {  # 跑步
            'Acc_x': np.random.normal(0, 2.0, 60),
            'Acc_y': np.random.normal(0, 2.0, 60),
            'Acc_z': np.random.normal(9.8, 3.0, 60),
            'Gyr_x': np.random.normal(0, 0.8, 60),
            'Gyr_y': np.random.normal(0, 0.8, 60),
            'Gyr_z': np.random.normal(0, 0.8, 60),
        },
        'vehicle': {  # 车辆
            'Acc_x': np.random.normal(0, 0.5, 60),
            'Acc_y': np.random.normal(0, 0.5, 60),
            'Acc_z': np.random.normal(9.8, 0.3, 60),
            'Gyr_x': np.random.normal(0, 0.2, 60),
            'Gyr_y': np.random.normal(0, 0.2, 60),
            'Gyr_z': np.random.normal(0, 0.2, 60),
        }
    }
    
    test_datasets = {}
    
    for behavior_name, behavior_data in behaviors.items():
        # 创建基础数据
        base_data = create_test_data()
        
        # 替换特定的传感器数据
        for sensor, values in behavior_data.items():
            base_data[sensor] = values
        
        test_datasets[behavior_name] = base_data
    
    return test_datasets

def test_local_inference():
    """
    测试本地推理功能
    """
    print("=" * 50)
    print("测试本地推理功能")
    print("=" * 50)
    
    try:
        # 创建推理实例
        inference = get_signal_user_inference()
        
        # 获取模型信息
        model_info = inference.get_model_info()
        print(f"模型状态: {model_info['model_loaded']}")
        print(f"标签: {model_info['labels']}")
        print(f"窗口大小: {model_info['window_size']}")
        print(f"特征维度: {model_info['feature_size']}")
        
        # 创建测试数据
        test_data = create_test_data()
        print(f"\n测试数据形状: {test_data.shape}")
        print(f"测试数据列: {test_data.columns.tolist()}")
        
        # 进行预测
        print("\n进行预测...")
        result = inference.predict(test_data)
        
        print(f"预测结果:")
        print(f"  - 预测类别: {result['predicted_class']}")
        print(f"  - 预测标签: {result['predicted_label']}")
        print(f"  - 置信度: {result['confidence']:.4f}")
        print(f"  - 所有概率:")
        for label, prob in result['probabilities'].items():
            print(f"    {label}: {prob:.4f}")
        
        return True
        
    except Exception as e:
        print(f"本地推理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_different_behaviors():
    """
    测试不同行为模式的识别
    """
    print("\n" + "=" * 50)
    print("测试不同行为模式的识别")
    print("=" * 50)
    
    try:
        inference = get_signal_user_inference()
        behavior_datasets = create_different_behavior_data()
        
        for behavior_name, data in behavior_datasets.items():
            print(f"\n测试 {behavior_name} 行为模式:")
            result = inference.predict(data)
            
            print(f"  - 预测标签: {result['predicted_label']}")
            print(f"  - 置信度: {result['confidence']:.4f}")
            
            # 显示前3个最高概率
            sorted_probs = sorted(result['probabilities'].items(), key=lambda x: x[1], reverse=True)
            print(f"  - 前3个概率:")
            for i, (label, prob) in enumerate(sorted_probs[:3]):
                print(f"    {i+1}. {label}: {prob:.4f}")
        
        return True
        
    except Exception as e:
        print(f"不同行为模式测试失败: {e}")
        return False

def test_api_endpoints():
    """
    测试API接口
    """
    print("\n" + "=" * 50)
    print("测试API接口")
    print("=" * 50)
    
    base_url = "http://localhost:5000"
    
    # 测试状态接口
    try:
        print("测试状态接口...")
        response = requests.get(f"{base_url}/api/signal/status")
        if response.status_code == 200:
            status = response.json()
            print(f"状态: {status}")
        else:
            print(f"状态接口请求失败: {response.status_code}")
    except Exception as e:
        print(f"状态接口测试失败: {e}")
    
    # 测试模型信息接口
    try:
        print("\n测试模型信息接口...")
        response = requests.get(f"{base_url}/api/signal/model_info")
        if response.status_code == 200:
            model_info = response.json()
            print(f"模型信息: {model_info['model_info']['model_loaded']}")
        else:
            print(f"模型信息接口请求失败: {response.status_code}")
    except Exception as e:
        print(f"模型信息接口测试失败: {e}")
    
    # 测试预测接口
    try:
        print("\n测试预测接口...")
        test_data = create_test_data()
        
        # 转换为JSON格式
        data_dict = test_data.to_dict('list')
        
        response = requests.post(
            f"{base_url}/api/signal/predict",
            json=data_dict,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"预测结果: {result['prediction']['predicted_label']}")
            print(f"置信度: {result['prediction']['confidence']:.4f}")
        else:
            print(f"预测接口请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
    except Exception as e:
        print(f"预测接口测试失败: {e}")

def test_batch_prediction():
    """
    测试批量预测
    """
    print("\n" + "=" * 50)
    print("测试批量预测")
    print("=" * 50)
    
    try:
        inference = get_signal_user_inference()
        
        # 创建多个测试样本
        test_samples = []
        for i in range(3):
            test_data = create_test_data()
            test_samples.append(test_data)
        
        # 进行批量预测
        results = inference.predict_batch(test_samples)
        
        print(f"批量预测结果 ({len(results)} 个样本):")
        for i, result in enumerate(results):
            if 'error' not in result:
                print(f"  样本 {i+1}: {result['predicted_label']} (置信度: {result['confidence']:.4f})")
            else:
                print(f"  样本 {i+1}: 错误 - {result['error']}")
        
        return True
        
    except Exception as e:
        print(f"批量预测测试失败: {e}")
        return False

def main():
    """
    主测试函数
    """
    print("用户行为识别推理模型测试")
    print("=" * 50)
    
    # 测试本地推理
    success_local = test_local_inference()
    
    # 测试不同行为模式
    success_behaviors = test_different_behaviors()
    
    # 测试批量预测
    success_batch = test_batch_prediction()
    
    # 测试API接口
    print("\n注意: API接口测试需要先启动Flask服务器")
    test_api_endpoints()
    
    # 总结
    print("\n" + "=" * 50)
    print("测试总结")
    print("=" * 50)
    print(f"本地推理测试: {'✓' if success_local else '✗'}")
    print(f"不同行为模式测试: {'✓' if success_behaviors else '✗'}")
    print(f"批量预测测试: {'✓' if success_batch else '✗'}")
    
    if success_local and success_behaviors and success_batch:
        print("\n所有本地测试通过！")
    else:
        print("\n部分测试失败，请检查错误信息。")

if __name__ == "__main__":
    main() 