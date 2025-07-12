#!/usr/bin/env python3
"""
测试前端访问视频流的脚本
检查所有可能的问题
"""

import requests
import time
import subprocess
import sys

def print_section(title):
    """打印分隔线"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

def check_backend_running():
    """检查后端是否运行"""
    print_section("1. 检查后端服务状态")
    
    try:
        # 检查5000端口
        response = requests.get('http://localhost:5000/api/health', timeout=2)
        if response.status_code == 200:
            print("✅ 后端服务正在运行 (端口 5000)")
            return True
        else:
            print(f"❌ 后端服务响应异常: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到后端服务 (端口 5000)")
        print("   请确保后端服务已启动: python start_backend.py")
        return False
    except Exception as e:
        print(f"❌ 检查后端服务时出错: {e}")
        return False

def check_frontend_running():
    """检查前端是否运行"""
    print_section("2. 检查前端服务状态")
    
    try:
        # 检查5173端口（Vite默认端口）
        response = requests.get('http://localhost:5173', timeout=2)
        if response.status_code == 200:
            print("✅ 前端服务正在运行 (端口 5173)")
            return True
    except:
        pass
    
    try:
        # 检查3000端口（备用端口）
        response = requests.get('http://localhost:3000', timeout=2)
        if response.status_code == 200:
            print("✅ 前端服务正在运行 (端口 3000)")
            return True
    except:
        pass
    
    print("❌ 前端服务未运行")
    print("   请在前端目录运行: npm run dev")
    return False

def check_cors_headers():
    """检查CORS配置"""
    print_section("3. 检查CORS跨域配置")
    
    try:
        # 模拟前端请求
        headers = {
            'Origin': 'http://localhost:5173',
            'Referer': 'http://localhost:5173/'
        }
        response = requests.options('http://localhost:5000/api/health', headers=headers, timeout=2)
        
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers')
        }
        
        if cors_headers['Access-Control-Allow-Origin']:
            print(f"✅ CORS已配置:")
            for key, value in cors_headers.items():
                if value:
                    print(f"   {key}: {value}")
            return True
        else:
            print("❌ CORS未正确配置")
            return False
    except Exception as e:
        print(f"❌ 检查CORS时出错: {e}")
        return False

def check_video_endpoints():
    """检查视频流端点"""
    print_section("4. 检查视频流端点可访问性")
    
    endpoints = [
        ('增强检测器', 'http://localhost:5000/enhanced_detector/video_feed'),
        ('特征检测-左', 'http://localhost:5000/f_detector/video_feed_left'),
        ('特征检测-右', 'http://localhost:5000/f_detector/video_feed_right'),
        ('特征追踪-左', 'http://localhost:5000/f_tracker/video_feed_left'),
        ('特征追踪-右', 'http://localhost:5000/f_tracker/video_feed_right'),
        ('深度估计', 'http://localhost:5000/d_estimator/video_feed')
    ]
    
    accessible = 0
    for name, url in endpoints:
        try:
            # 只检查端点是否响应，不下载整个流
            response = requests.get(url, stream=True, timeout=2)
            response.close()
            
            if response.status_code == 200:
                print(f"✅ {name}: 可访问")
                accessible += 1
            else:
                print(f"❌ {name}: 状态码 {response.status_code}")
        except Exception as e:
            print(f"❌ {name}: 无法访问 - {type(e).__name__}")
    
    print(f"\n总计: {accessible}/{len(endpoints)} 个端点可访问")
    return accessible > 0

def check_camera_status():
    """检查摄像头启动状态"""
    print_section("5. 检查摄像头启动状态")
    
    cameras = [
        ('enhanced_detector', '增强检测器'),
        ('f_detector', '特征检测器'),
        ('f_tracker', '特征追踪器'),
        ('d_estimator', '深度估计器')
    ]
    
    started = 0
    for cam_type, name in cameras:
        try:
            # 尝试启动摄像头
            response = requests.post(f'http://localhost:5000/{cam_type}/start_cameras', timeout=5)
            if response.status_code == 200:
                print(f"✅ {name}: 启动成功")
                started += 1
                time.sleep(0.5)  # 给摄像头一些初始化时间
            else:
                print(f"❌ {name}: 启动失败 - {response.status_code}")
        except Exception as e:
            print(f"❌ {name}: 启动失败 - {type(e).__name__}")
    
    print(f"\n总计: {started}/{len(cameras)} 个摄像头启动成功")
    return started > 0

def suggest_fixes():
    """提供修复建议"""
    print_section("修复建议")
    
    print("""
1. 如果后端未运行:
   cd GuideLight-for-Vision-Impaired
   python start_backend.py

2. 如果前端未运行:
   cd GuideLight-for-Vision-Impaired/static/guidelight_front
   npm install (如果是第一次运行)
   npm run dev

3. 如果视频流无法访问:
   - 检查摄像头是否正确连接
   - 确保没有其他程序占用摄像头
   - 尝试重启后端服务

4. 如果CORS问题:
   - 确保后端Flask应用启用了CORS
   - 检查前端API配置的URL是否正确

5. 浏览器控制台检查:
   - 打开浏览器开发者工具 (F12)
   - 查看Console标签页是否有错误
   - 查看Network标签页检查请求状态
""")

def main():
    """主函数"""
    print("GuideLight 前端视频流问题诊断工具")
    print("="*60)
    
    # 执行检查
    backend_ok = check_backend_running()
    frontend_ok = check_frontend_running()
    
    if backend_ok:
        cors_ok = check_cors_headers()
        video_ok = check_video_endpoints()
        camera_ok = check_camera_status()
        
        # 总结
        print_section("诊断结果")
        if backend_ok and frontend_ok and video_ok:
            print("✅ 系统基本正常，视频流应该可以显示")
            print("   如果仍无画面，请检查:")
            print("   1. 浏览器控制台是否有错误")
            print("   2. 网络请求是否被防火墙阻止")
            print("   3. 摄像头驱动是否正常")
        else:
            print("❌ 发现问题，请按照上述建议修复")
    else:
        print("\n❌ 后端服务未运行，请先启动后端服务")
    
    # 显示修复建议
    suggest_fixes()

if __name__ == "__main__":
    main() 