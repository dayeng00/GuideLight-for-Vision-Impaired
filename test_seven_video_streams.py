#!/usr/bin/env python3
"""
测试所有7个视频流的前后端配置
"""
import requests
import time
from typing import Dict, List, Tuple

BASE_URL = "http://localhost:5000"

# 7个主要视频流配置
VIDEO_STREAMS = [
    {
        'id': 'd_estimator',
        'name': '视差估计',
        'hasDual': False,
        'start_url': '/d_estimator/start_cameras',
        'stop_url': '/d_estimator/stop_cameras',
        'stream_urls': ['/d_estimator/video_feed']
    },
    {
        'id': 'f_detector',
        'name': '特征点检测',
        'hasDual': True,
        'start_url': '/f_detector/start_cameras',
        'stop_url': '/f_detector/stop_cameras',
        'stream_urls': ['/f_detector/video_feed_left', '/f_detector/video_feed_right', '/f_detector/video_feed']
    },
    {
        'id': 'f_tracker',
        'name': '特征点追踪',
        'hasDual': True,
        'start_url': '/f_tracker/start_cameras',
        'stop_url': '/f_tracker/stop_cameras',
        'stream_urls': ['/f_tracker/video_feed_left', '/f_tracker/video_feed_right', '/f_tracker/video_feed']
    },
    {
        'id': 'g_recognition',
        'name': '手势特征点识别',
        'hasDual': False,
        'start_url': '/g_recognition/start_cameras',
        'stop_url': '/g_recognition/stop_cameras',
        'stream_urls': ['/g_recognition/video_feed']
    },
    {
        'id': 'g_recognizer',
        'name': '手势类别判断',
        'hasDual': False,
        'start_url': '/g_recognizer/start_cameras',
        'stop_url': '/g_recognizer/stop_cameras',
        'stream_urls': ['/g_recognizer/video_feed']
    },
    {
        'id': 'm_detector',
        'name': 'MobileNetSSD目标检测',
        'hasDual': False,
        'start_url': '/m_detector/start_cameras',
        'stop_url': '/m_detector/stop_cameras',
        'stream_urls': ['/m_detector/video_feed']
    },
    {
        'id': 'enhanced_detector',
        'name': '增强检测器',
        'hasDual': False,
        'start_url': '/enhanced_detector/start_cameras',
        'stop_url': '/enhanced_detector/stop_cameras',
        'stream_urls': ['/enhanced_detector/video_feed']
    }
]

def test_api_endpoints():
    """测试API端点可用性"""
    print("🔍 测试API端点可用性...")
    
    results = []
    
    for stream in VIDEO_STREAMS:
        stream_id = stream['id']
        name = stream['name']
        
        print(f"\n📹 测试 {name} ({stream_id}):")
        
        # 测试启动端点
        try:
            response = requests.post(f"{BASE_URL}{stream['start_url']}", timeout=5)
            start_status = f"✅ 启动: {response.status_code}"
            if response.status_code != 200:
                start_status += f" - {response.text[:100]}"
        except Exception as e:
            start_status = f"❌ 启动失败: {str(e)[:50]}"
        
        # 测试停止端点
        try:
            response = requests.post(f"{BASE_URL}{stream['stop_url']}", timeout=5)
            stop_status = f"✅ 停止: {response.status_code}"
            if response.status_code != 200:
                stop_status += f" - {response.text[:100]}"
        except Exception as e:
            stop_status = f"❌ 停止失败: {str(e)[:50]}"
        
        # 测试视频流端点
        stream_statuses = []
        for stream_url in stream['stream_urls']:
            try:
                response = requests.get(f"{BASE_URL}{stream_url}", timeout=3, stream=True)
                if response.status_code == 200:
                    stream_statuses.append(f"✅ {stream_url}")
                else:
                    stream_statuses.append(f"❌ {stream_url}: {response.status_code}")
            except Exception as e:
                stream_statuses.append(f"❌ {stream_url}: {str(e)[:30]}")
        
        results.append({
            'id': stream_id,
            'name': name,
            'start': start_status,
            'stop': stop_status,
            'streams': stream_statuses
        })
        
        print(f"  {start_status}")
        print(f"  {stop_status}")
        for stream_status in stream_statuses:
            print(f"  {stream_status}")
    
    return results

def test_frontend_config():
    """测试前端配置"""
    print("\n🎨 测试前端配置...")
    
    # 读取前端配置
    try:
        with open('static/guidelight_front/src/views/VideoMonitor.vue', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查摄像头类型配置
        configured_cameras = []
        for stream in VIDEO_STREAMS:
            if f"id: '{stream['id']}'" in content:
                configured_cameras.append(stream['id'])
                print(f"✅ 前端已配置: {stream['name']} ({stream['id']})")
            else:
                print(f"❌ 前端未配置: {stream['name']} ({stream['id']})")
        
        print(f"\n📊 前端配置统计:")
        print(f"  已配置摄像头: {len(configured_cameras)}/7")
        print(f"  配置列表: {configured_cameras}")
        
        return configured_cameras
        
    except Exception as e:
        print(f"❌ 读取前端配置失败: {e}")
        return []

def test_video_stream_access():
    """测试视频流访问"""
    print("\n🎥 测试视频流访问...")
    
    # 测试关键的视频流
    test_streams = [
        '/enhanced_detector/video_feed',
        '/f_detector/video_feed_left',
        '/f_detector/video_feed_right',
        '/f_detector/video_feed',
        '/d_estimator/video_feed'
    ]
    
    for stream_url in test_streams:
        try:
            response = requests.get(f"{BASE_URL}{stream_url}", timeout=2, stream=True)
            if response.status_code == 200:
                print(f"✅ {stream_url} - 可访问")
            elif response.status_code == 503:
                print(f"⚠️ {stream_url} - 服务不可用（摄像头未启动）")
            elif response.status_code == 404:
                print(f"❌ {stream_url} - 路由不存在")
            else:
                print(f"❌ {stream_url} - 状态码: {response.status_code}")
        except Exception as e:
            print(f"❌ {stream_url} - 错误: {str(e)[:50]}")

def generate_html_test_page():
    """生成HTML测试页面"""
    print("\n📄 生成HTML测试页面...")
    
    html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GuideLight 7个视频流测试</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .stream-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .stream-card { border: 1px solid #ddd; padding: 15px; border-radius: 8px; }
        .stream-card h3 { margin-top: 0; color: #333; }
        .controls { margin-bottom: 10px; }
        .btn { padding: 8px 16px; margin: 5px; border: none; border-radius: 4px; cursor: pointer; }
        .btn-start { background-color: #4CAF50; color: white; }
        .btn-stop { background-color: #f44336; color: white; }
        img { max-width: 100%; height: auto; border: 1px solid #ccc; }
        .dual-view { display: flex; gap: 10px; }
        .dual-view img { width: 48%; }
    </style>
</head>
<body>
    <div class="container">
        <h1>GuideLight 7个视频流测试页面</h1>
        <p>这个页面用于测试所有7个视频流的启动和显示功能。</p>
        
        <div class="stream-grid">
"""
    
    for stream in VIDEO_STREAMS:
        stream_id = stream['id']
        name = stream['name']
        is_dual = stream['hasDual']
        
        html_content += f"""
            <div class="stream-card">
                <h3>{name}</h3>
                <div class="controls">
                    <button class="btn btn-start" onclick="startCamera('{stream_id}')">启动</button>
                    <button class="btn btn-stop" onclick="stopCamera('{stream_id}')">停止</button>
                </div>
                <div id="{stream_id}-status">状态: 未启动</div>
                <div class="video-container">
"""
        
        if is_dual:
            html_content += f"""
                    <div class="dual-view">
                        <img id="{stream_id}-left" src="about:blank" alt="左视图" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjE1MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjE1MCIgZmlsbD0iI2Y4ZjhmOCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBkb21pbmFudC1iYXNlbGluZT0ibWlkZGxlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjE0cHgiIGZpbGw9IiM5OTkiPuW3puinhuWbvjwvdGV4dD48L3N2Zz4='" />
                        <img id="{stream_id}-right" src="about:blank" alt="右视图" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjE1MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjE1MCIgZmlsbD0iI2Y4ZjhmOCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBkb21pbmFudC1iYXNlbGluZT0ibWlkZGxlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjE0cHgiIGZpbGw9IiM5OTkiPuWPs+inhuWbvjwvdGV4dD48L3N2Zz4='" />
                    </div>
"""
        else:
            html_content += f"""
                    <img id="{stream_id}-single" src="about:blank" alt="视频流" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMzAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2Y4ZjhmOCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBkb21pbmFudC1iYXNlbGluZT0ibWlkZGxlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjE2cHgiIGZpbGw9IiM5OTkiPuinhumikeWktOeQhzwvdGV4dD48L3N2Zz4='" />
"""
        
        html_content += """
                </div>
            </div>
"""
    
    html_content += """
        </div>
    </div>
    
    <script>
        const BASE_URL = 'http://localhost:5000';
        
        async function startCamera(cameraType) {
            const statusElement = document.getElementById(cameraType + '-status');
            statusElement.textContent = '状态: 启动中...';
            
            try {
                const response = await fetch(`${BASE_URL}/${cameraType}/start_cameras`, {
                    method: 'POST'
                });
                
                if (response.ok) {
                    statusElement.textContent = '状态: 已启动';
                    updateVideoStreams(cameraType);
                } else {
                    statusElement.textContent = '状态: 启动失败';
                }
            } catch (error) {
                statusElement.textContent = '状态: 启动错误 - ' + error.message;
            }
        }
        
        async function stopCamera(cameraType) {
            const statusElement = document.getElementById(cameraType + '-status');
            statusElement.textContent = '状态: 停止中...';
            
            try {
                const response = await fetch(`${BASE_URL}/${cameraType}/stop_cameras`, {
                    method: 'POST'
                });
                
                if (response.ok) {
                    statusElement.textContent = '状态: 已停止';
                    clearVideoStreams(cameraType);
                } else {
                    statusElement.textContent = '状态: 停止失败';
                }
            } catch (error) {
                statusElement.textContent = '状态: 停止错误 - ' + error.message;
            }
        }
        
        function updateVideoStreams(cameraType) {
            const timestamp = Date.now();
            const dualCameras = ['f_detector', 'f_tracker'];
            
            if (dualCameras.includes(cameraType)) {
                const leftImg = document.getElementById(cameraType + '-left');
                const rightImg = document.getElementById(cameraType + '-right');
                
                if (leftImg) leftImg.src = `${BASE_URL}/${cameraType}/video_feed_left?t=${timestamp}`;
                if (rightImg) rightImg.src = `${BASE_URL}/${cameraType}/video_feed_right?t=${timestamp}`;
            } else {
                const singleImg = document.getElementById(cameraType + '-single');
                if (singleImg) singleImg.src = `${BASE_URL}/${cameraType}/video_feed?t=${timestamp}`;
            }
        }
        
        function clearVideoStreams(cameraType) {
            const dualCameras = ['f_detector', 'f_tracker'];
            
            if (dualCameras.includes(cameraType)) {
                const leftImg = document.getElementById(cameraType + '-left');
                const rightImg = document.getElementById(cameraType + '-right');
                
                if (leftImg) leftImg.src = 'about:blank';
                if (rightImg) rightImg.src = 'about:blank';
            } else {
                const singleImg = document.getElementById(cameraType + '-single');
                if (singleImg) singleImg.src = 'about:blank';
            }
        }
    </script>
</body>
</html>
"""
    
    with open('test_seven_streams.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("✅ HTML测试页面已生成: test_seven_streams.html")
    print("📖 使用方法:")
    print("  1. 确保后端服务器运行在 http://localhost:5000")
    print("  2. 在浏览器中打开 test_seven_streams.html")
    print("  3. 点击各个摄像头的'启动'按钮测试视频流")

def main():
    """主函数"""
    print("🚀 开始测试GuideLight的7个视频流...")
    print("=" * 60)
    
    # 测试API端点
    api_results = test_api_endpoints()
    
    # 测试前端配置
    frontend_config = test_frontend_config()
    
    # 测试视频流访问
    test_video_stream_access()
    
    # 生成HTML测试页面
    generate_html_test_page()
    
    print("\n" + "=" * 60)
    print("📊 测试总结:")
    print(f"  配置的视频流: {len(VIDEO_STREAMS)}")
    print(f"  前端已配置: {len(frontend_config)}/7")
    
    working_streams = sum(1 for result in api_results if '✅' in result['start'])
    print(f"  可用的API端点: {working_streams}/7")
    
    print("\n🎯 建议:")
    print("  1. 使用生成的HTML页面测试所有视频流")
    print("  2. 确保设备管理器正在运行")
    print("  3. 检查摄像头硬件连接")
    
    return api_results, frontend_config

if __name__ == "__main__":
    main() 