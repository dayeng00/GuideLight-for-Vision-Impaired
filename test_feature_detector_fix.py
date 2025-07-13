#!/usr/bin/env python3
"""
测试特征点检测器修复
"""
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "main"))

def test_feature_detector_import():
    """测试特征点检测器导入"""
    try:
        from main.utils.feature_point_detector import FeaturePointDetector
        print("✅ FeaturePointDetector 导入成功")
        return True
    except Exception as e:
        print(f"❌ FeaturePointDetector 导入失败: {e}")
        return False

def test_feature_detector_instantiation():
    """测试特征点检测器实例化"""
    try:
        from main.utils.feature_point_detector import FeaturePointDetector
        
        # 测试实例化
        detector = FeaturePointDetector(headless=True)
        print("✅ FeaturePointDetector 实例化成功")
        
        # 检查必要的方法
        methods_to_check = ['run_left', 'run_right', 'start', 'stop', 'shutdown']
        
        for method_name in methods_to_check:
            if hasattr(detector, method_name):
                print(f"✅ {method_name} 方法存在")
            else:
                print(f"❌ {method_name} 方法不存在")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ FeaturePointDetector 实例化失败: {e}")
        return False

def test_global_cache_integration():
    """测试全局缓存集成"""
    try:
        from main.utils.feature_point_detector import FeaturePointDetector
        from main.utils.global_frame_cache import get_global_frame_cache
        
        detector = FeaturePointDetector(headless=True)
        cache = get_global_frame_cache()
        
        # 检查是否有全局缓存引用
        if hasattr(detector, 'global_cache'):
            print("✅ 特征点检测器已连接到全局帧缓存")
            
            # 检查是否是同一个实例
            if detector.global_cache is cache:
                print("✅ 全局帧缓存引用正确")
                return True
            else:
                print("⚠️ 全局帧缓存引用不一致")
                return False
        else:
            print("❌ 特征点检测器未连接到全局帧缓存")
            return False
            
    except Exception as e:
        print(f"❌ 全局缓存集成测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始特征点检测器修复验证")
    print("=" * 50)
    
    tests = [
        ("导入测试", test_feature_detector_import),
        ("实例化测试", test_feature_detector_instantiation),
        ("全局缓存集成测试", test_global_cache_integration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}...")
        result = test_func()
        results.append((test_name, result))
        
        if result:
            print(f"✅ {test_name}通过")
        else:
            print(f"❌ {test_name}失败")
    
    # 总结
    print("\n" + "=" * 50)
    print("📋 测试结果总结:")
    
    all_passed = True
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"   {test_name}: {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 所有测试通过！特征点检测器修复成功。")
        print("💡 现在可以尝试启动 f_detector 摄像头了。")
        return 0
    else:
        print("⚠️ 部分测试失败，需要进一步检查。")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 