"""
特征点检测
"""
'''
错误原因主要是因为 路障检测系统.py ，前端请求视频流是从左右两个摄像头同时调画面，端口拥挤造成报错。socket 可以直接转为 流式传输 ，问题不大。
需求：同时接收两个视频流并展示在前端页面
前提：一个端口只能同时承载一个视频流。
双端口：
解决方案1 ： 开两个端口并写两个 返回视频流 函数                   （更改成本更低）
解决方案2 ： 开两个端口并继承 feature 写 left right 子类
单端口：
解决方案1： ？？？ 直接threaded=True 即可？？？？

'''
import cv2
import time
import threading
from utils.video_show import VideoShowOAK
import depthai as dai
from flask_socketio import SocketIO
import base64
import eventlet
from flask import Flask, Response
eventlet.monkey_patch()

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

from utils.stream_optimizer import get_stream_optimizer

class FeaturePointDetector(VideoShowOAK):
    def __init__(self, camera_size=720, is_show_fps=True, motion_estimation="hardware_accelerated", headless=True):
        super().__init__(camera_size, is_show_fps)
        
        # 全局帧缓存
        from .global_frame_cache import get_global_frame_cache
        self.global_cache = get_global_frame_cache()
        
        self.motion_estimation = motion_estimation
        self.headless = headless
        self.continue_running = True
        
        # 帧数据
        self.left_frame = None
        self.right_frame = None
        self.processing_active = False
        self.processing_thread = None
        
        # 特征跟踪配置 - 简化版本，不设置复杂的配置
        # 由于DepthAI API版本差异，暂时不设置特征跟踪配置
        # 使用默认配置即可
        print("⚠️ 使用默认特征跟踪配置")
        
        # 绘制器
        self.leftTracker = FeaturePointTrackerDrawer("Feature count left", "left", headless)
        self.rightTracker = FeaturePointTrackerDrawer("Feature count right", "right", headless)
        
        print("✅ 特征点检测器初始化完成")
    
    def start(self):
        """启动特征点检测器"""
        if self.processing_active:
            print("⚠️ 特征点检测器已在运行")
            return
        
        print("🚀 启动特征点检测器...")
        
        # 订阅全局帧缓存
        self.global_cache.subscribe("feature_detector", self._on_frame_update)
        
        # 启动处理线程
        self.processing_active = True
        if not self.headless:
            self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
            self.processing_thread.start()
        
        print("✅ 特征点检测器已启动")
    
    def stop(self):
        """停止特征点检测器"""
        if not self.processing_active:
            return
        
        print("🛑 停止特征点检测器...")
        
        # 取消订阅
        self.global_cache.unsubscribe("feature_detector")
        
        # 停止处理线程
        self.processing_active = False
        self.continue_running = False
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=2.0)
        
        print("✅ 特征点检测器已停止")
    
    def _on_frame_update(self, frame_data):
        """帧更新回调"""
        try:
            # 更新左右帧数据
            if 'rectifiedLeft' in frame_data:
                self.left_frame = frame_data['rectifiedLeft']
            
            if 'rectifiedRight' in frame_data:
                self.right_frame = frame_data['rectifiedRight']
                
        except Exception as e:
            print(f"❌ 特征点检测器帧更新失败: {e}")
    
    def _processing_loop(self):
        """处理循环（仅在非headless模式下运行）"""
        print("🔄 特征点检测器处理循环启动")
        
        while self.processing_active and self.continue_running:
            try:
                # 从全局缓存获取最新帧
                current_frames = self.global_cache.get_current_frames(['rectifiedLeft', 'rectifiedRight'])
                
                if 'rectifiedLeft' in current_frames:
                    self.left_frame = current_frames['rectifiedLeft']
                
                if 'rectifiedRight' in current_frames:
                    self.right_frame = current_frames['rectifiedRight']
                
                # 处理帧数据（如果有显示需求）
                if self.left_frame is not None and self.right_frame is not None:
                    # 这里可以添加特征点检测的可视化处理
                    pass
                
                time.sleep(0.03)  # ~30 FPS
                
            except Exception as e:
                print(f"❌ 特征点检测器处理循环错误: {e}")
                time.sleep(0.1)
        
        print("🔄 特征点检测器处理循环已结束")
