#!/usr/bin/env python3
"""
GuideLight后端启动脚本
确保所有依赖和模块正确加载后启动Flask服务器
"""

import sys
import os
import time
import subprocess
import requests

def check_dependencies():
    """检查必要的依赖"""
    print("🔍 检查依赖...")
    
    required_packages = [
        'flask',
        'flask-cors',
        'flask-sqlalchemy',
        'depthai',
        'ultralytics',
        'opencv-python',
        'numpy'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}")
    
    if missing_packages:
        print(f"\n⚠️ 缺少以下依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install " + " ".join(missing_packages))
        return False
    
    print("✅ 所有依赖检查通过")
    return True

def check_backend_running():
    """检查后端是否已经在运行"""
    try:
        response = requests.get('http://localhost:5000/api/health', timeout=3)
        if response.status_code == 200:
            print("✅ 后端服务已在运行")
            return True
    except requests.exceptions.RequestException:
        pass
    
    print("ℹ️ 后端服务未运行")
    return False

def start_backend():
    """启动后端服务"""
    print("🚀 启动后端服务...")
    
    # 切换到正确的目录
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)
    
    # 启动Flask应用
    try:
        import subprocess
        process = subprocess.Popen([
            sys.executable, 'main/main.py'
        ], cwd=backend_dir)
        
        # 等待服务启动
        print("⏳ 等待服务启动...")
        for i in range(30):  # 最多等待30秒
            time.sleep(1)
            if check_backend_running():
                print("✅ 后端服务启动成功")
                return True
            print(f"  等待中... ({i+1}/30)")
        
        print("❌ 后端服务启动超时")
        return False
        
    except Exception as e:
        print(f"❌ 启动后端失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("🎯 GuideLight 后端启动器")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        print("\n❌ 依赖检查失败，请安装缺少的包后重试")
        return False
    
    # 检查是否已经运行
    if check_backend_running():
        print("\n✅ 后端服务已在运行，无需重复启动")
        print("🌐 访问地址: http://localhost:5000")
        return True
    
    # 启动后端
    if start_backend():
        print("\n🎉 后端启动成功!")
        print("🌐 API地址: http://localhost:5000")
        print("📊 健康检查: http://localhost:5000/api/health")
        print("\n💡 现在可以启动前端了")
        return True
    else:
        print("\n❌ 后端启动失败")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1) 