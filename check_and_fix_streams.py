#!/usr/bin/env python3
"""
检查并修复视频流问题
"""

import os
import sys
import subprocess
import time
import requests
import webbrowser

def print_status(message, status="info"):
    """打印状态信息"""
    symbols = {
        "info": "ℹ️",
        "success": "✅",
        "error": "❌",
        "warning": "⚠️"
    }
    print(f"{symbols.get(status, '•')} {message}")

def check_backend():
    """检查后端是否运行"""
    try:
        response = requests.get('http://localhost:5000/api/health', timeout=2)
        if response.status_code == 200:
            print_status("后端服务正在运行", "success")
            return True
    except:
        pass
    
    print_status("后端服务未运行", "error")
    return False

def start_backend():
    """启动后端服务"""
    print_status("正在启动后端服务...", "info")
    
    # 使用start_backend.py脚本
    if os.path.exists('start_backend.py'):
        subprocess.Popen([sys.executable, 'start_backend.py'], 
                        creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0)
        
        # 等待后端启动
        for i in range(10):
            time.sleep(2)
            if check_backend():
                print_status("后端服务启动成功", "success")
                return True
        
        print_status("后端服务启动超时", "error")
        return False
    else:
        print_status("找不到start_backend.py文件", "error")
        return False

def check_frontend():
    """检查前端是否运行"""
    ports = [5173, 3000, 8080]
    
    for port in ports:
        try:
            response = requests.get(f'http://localhost:{port}', timeout=1)
            if response.status_code == 200:
                print_status(f"前端服务正在运行 (端口 {port})", "success")
                return True, port
        except:
            pass
    
    print_status("前端服务未运行", "warning")
    return False, None

def test_video_streams():
    """测试视频流是否可访问"""
    print_status("测试视频流端点...", "info")
    
    streams = [
        ('增强检测器', '/enhanced_detector/video_feed'),
        ('特征检测-左', '/f_detector/video_feed_left'),
        ('特征检测-右', '/f_detector/video_feed_right'),
        ('特征追踪-左', '/f_tracker/video_feed_left'),
        ('特征追踪-右', '/f_tracker/video_feed_right'),
        ('深度估计', '/d_estimator/video_feed')
    ]
    
    accessible = 0
    for name, endpoint in streams:
        url = f'http://localhost:5000{endpoint}'
        try:
            response = requests.get(url, stream=True, timeout=2)
            response.close()
            
            if response.status_code == 200:
                print_status(f"  {name}: 可访问", "success")
                accessible += 1
            elif response.status_code == 404:
                print_status(f"  {name}: 未启动", "warning")
            else:
                print_status(f"  {name}: 错误 ({response.status_code})", "error")
        except:
            print_status(f"  {name}: 无法连接", "error")
    
    return accessible

def start_cameras():
    """启动所有摄像头"""
    print_status("启动摄像头...", "info")
    
    cameras = [
        ('enhanced_detector', '增强检测器'),
        ('f_detector', '特征检测器'),
        ('f_tracker', '特征追踪器'),
        ('d_estimator', '深度估计器')
    ]
    
    started = 0
    for cam_type, name in cameras:
        try:
            url = f'http://localhost:5000/{cam_type}/start'
            if cam_type in ['f_detector', 'f_tracker']:
                url = f'http://localhost:5000/{cam_type}/start_cameras'
            
            response = requests.post(url, timeout=10)
            if response.status_code == 200:
                print_status(f"  {name}: 启动成功", "success")
                started += 1
            else:
                print_status(f"  {name}: 启动失败 ({response.status_code})", "error")
        except Exception as e:
            print_status(f"  {name}: 启动异常 - {type(e).__name__}", "error")
        
        time.sleep(1)  # 避免同时启动太多摄像头
    
    return started

def open_test_page():
    """打开测试页面"""
    print_status("创建测试页面...", "info")
    
    html_content = '''<!DOCTYPE html>
<html>
<head>
    <title>GuideLight 视频流测试</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f0f0f0;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .video-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .video-card {
            background: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .video-card h3 {
            margin: 0 0 10px 0;
            color: #555;
        }
        .video-feed {
            width: 100%;
            height: 200px;
            background: #000;
            border-radius: 4px;
        }
        .status {
            margin-top: 10px;
            font-size: 14px;
        }
        .status.success { color: green; }
        .status.error { color: red; }
        .controls {
            text-align: center;
            margin: 20px 0;
        }
        button {
            padding: 10px 20px;
            margin: 0 5px;
            border: none;
            border-radius: 4px;
            background: #4CAF50;
            color: white;
            cursor: pointer;
        }
        button:hover {
            background: #45a049;
        }
    </style>
</head>
<body>
    <h1>GuideLight 视频流测试页面</h1>
    
    <div class="controls">
        <button onclick="refreshAll()">刷新所有流</button>
        <button onclick="startAll()">启动所有流</button>
    </div>
    
    <div class="video-grid">
        <div class="video-card">
            <h3>增强检测器</h3>
            <img class="video-feed" id="enhanced" 
                 src="http://localhost:5000/enhanced_detector/video_feed"
                 onerror="handleError('enhanced', this)">
            <div class="status" id="status-enhanced">加载中...</div>
        </div>
        
        <div class="video-card">
            <h3>特征检测-左</h3>
            <img class="video-feed" id="f-detect-left" 
                 src="http://localhost:5000/f_detector/video_feed_left"
                 onerror="handleError('f-detect-left', this)">
            <div class="status" id="status-f-detect-left">加载中...</div>
        </div>
        
        <div class="video-card">
            <h3>特征检测-右</h3>
            <img class="video-feed" id="f-detect-right" 
                 src="http://localhost:5000/f_detector/video_feed_right"
                 onerror="handleError('f-detect-right', this)">
            <div class="status" id="status-f-detect-right">加载中...</div>
        </div>
        
        <div class="video-card">
            <h3>特征追踪-左</h3>
            <img class="video-feed" id="f-track-left" 
                 src="http://localhost:5000/f_tracker/video_feed_left"
                 onerror="handleError('f-track-left', this)">
            <div class="status" id="status-f-track-left">加载中...</div>
        </div>
        
        <div class="video-card">
            <h3>特征追踪-右</h3>
            <img class="video-feed" id="f-track-right" 
                 src="http://localhost:5000/f_tracker/video_feed_right"
                 onerror="handleError('f-track-right', this)">
            <div class="status" id="status-f-track-right">加载中...</div>
        </div>
        
        <div class="video-card">
            <h3>深度估计</h3>
            <img class="video-feed" id="depth" 
                 src="http://localhost:5000/d_estimator/video_feed"
                 onerror="handleError('depth', this)">
            <div class="status" id="status-depth">加载中...</div>
        </div>
    </div>
    
    <script>
        let errorCounts = {};
        
        function handleError(id, img) {
            errorCounts[id] = (errorCounts[id] || 0) + 1;
            const status = document.getElementById('status-' + id);
            
            if (errorCounts[id] > 3) {
                status.textContent = '连接失败';
                status.className = 'status error';
            } else {
                status.textContent = '重试中...';
                setTimeout(() => {
                    img.src = img.src.split('?')[0] + '?t=' + Date.now();
                }, 2000);
            }
        }
        
        function refreshAll() {
            const imgs = document.querySelectorAll('.video-feed');
            imgs.forEach(img => {
                errorCounts[img.id] = 0;
                img.src = img.src.split('?')[0] + '?t=' + Date.now();
                const status = document.getElementById('status-' + img.id);
                status.textContent = '加载中...';
                status.className = 'status';
            });
        }
        
        async function startAll() {
            const cameras = [
                {type: 'enhanced_detector', endpoint: '/enhanced_detector/start'},
                {type: 'f_detector', endpoint: '/f_detector/start_cameras'},
                {type: 'f_tracker', endpoint: '/f_tracker/start_cameras'},
                {type: 'd_estimator', endpoint: '/d_estimator/start'}
            ];
            
            for (const cam of cameras) {
                try {
                    const response = await fetch('http://localhost:5000' + cam.endpoint, {
                        method: 'POST'
                    });
                    console.log(cam.type + ':', response.ok ? '启动成功' : '启动失败');
                } catch (e) {
                    console.error(cam.type + ':', e);
                }
            }
            
            setTimeout(refreshAll, 2000);
        }
        
        // 监听图片加载成功
        document.querySelectorAll('.video-feed').forEach(img => {
            img.onload = function() {
                const status = document.getElementById('status-' + this.id);
                status.textContent = '正常';
                status.className = 'status success';
                errorCounts[this.id] = 0;
            };
        });
    </script>
</body>
</html>'''
    
    # 保存HTML文件
    with open('test_video_streams.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # 打开浏览器
    webbrowser.open('test_video_streams.html')
    print_status("测试页面已在浏览器中打开", "success")

def main():
    """主函数"""
    print("="*60)
    print("GuideLight 视频流检查和修复工具")
    print("="*60)
    
    # 1. 检查后端
    if not check_backend():
        if not start_backend():
            print_status("无法启动后端服务，请手动启动", "error")
            return
    
    # 2. 检查前端
    frontend_running, port = check_frontend()
    if frontend_running:
        print_status(f"前端地址: http://localhost:{port}", "info")
    
    # 3. 测试视频流
    accessible = test_video_streams()
    
    # 4. 如果没有可访问的流，尝试启动
    if accessible == 0:
        print_status("没有可访问的视频流，尝试启动摄像头...", "warning")
        started = start_cameras()
        
        if started > 0:
            print_status("等待摄像头初始化...", "info")
            time.sleep(3)
            
            # 重新测试
            accessible = test_video_streams()
    
    # 5. 打开测试页面
    open_test_page()
    
    # 6. 总结
    print("\n" + "="*60)
    print_status("诊断完成", "info")
    print(f"  - 后端服务: {'运行中' if check_backend() else '未运行'}")
    print(f"  - 前端服务: {'运行中' if frontend_running else '未运行'}")
    print(f"  - 可访问的视频流: {accessible}/6")
    print("\n提示:")
    print("  1. 如果视频流仍无画面，请检查浏览器控制台 (F12)")
    print("  2. 确保摄像头设备已正确连接")
    print("  3. 检查是否有其他程序占用摄像头")
    print("="*60)

if __name__ == "__main__":
    main() 