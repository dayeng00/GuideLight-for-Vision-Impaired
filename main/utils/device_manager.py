"""
DepthAI 设备管理器 - 统一管理设备访问，避免设备冲突
"""
import depthai as dai
import threading
import time
import numpy as np
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import queue
from .global_frame_cache import get_global_frame_cache


class DeviceManager:
    """设备管理器单例，确保整个应用只使用一个设备实例"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.device = None
        self.pipeline = None
        self.queues = {}
        self.running = False
        self.thread = None
        self.data_lock = threading.RLock()  # 使用RLock支持重入
        
        # 线程池用于异步处理订阅者回调
        self.executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="device_callback")
        
        # 获取全局帧缓存
        self.global_cache = get_global_frame_cache()
        
        # 最新的帧数据 - 使用多个缓冲区提高并发性能
        self.frame_buffers = {
            'color': queue.Queue(maxsize=3),
            'depth': queue.Queue(maxsize=3),
            'rectifiedLeft': queue.Queue(maxsize=3),
            'rectifiedRight': queue.Queue(maxsize=3),
            'imu': queue.Queue(maxsize=3)
        }
        
        # 最新数据快照
        self.latest_data = {
            'color': None,
            'depth': None,
            'rectifiedLeft': None,
            'rectifiedRight': None,
            'imu': None,
            'timestamp': None
        }
        
        # 数据订阅者（保持向后兼容）
        self.subscribers = {}
        
        # 性能统计
        self.stats = {
            'frames_processed': 0,
            'current_fps': 0,
            'last_fps_time': time.time(),
            'subscribers_notified': 0,
            'extraction_success_count': 0,
            'extraction_error_count': 0
        }
        
        # 调试计数器
        self.debug_counters = {
            'successful_extractions': 0,
            'failed_extractions': 0,
            'total_processed': 0
        }
        
        # 自动设置管道
        self._setup_pipeline()
    
    def _setup_pipeline(self):
        """设置DepthAI管道"""
        print("🔧 设置统一设备管道...")
        
        # 创建管道
        self.pipeline = dai.Pipeline()
        
        # 创建节点
        colorCam = self.pipeline.create(dai.node.ColorCamera)
        monoLeft = self.pipeline.create(dai.node.MonoCamera)
        monoRight = self.pipeline.create(dai.node.MonoCamera)
        stereo = self.pipeline.create(dai.node.StereoDepth)
        imu = self.pipeline.create(dai.node.IMU)
        sync = self.pipeline.create(dai.node.Sync)
        xoutGrp = self.pipeline.create(dai.node.XLinkOut)
        
        # 配置彩色摄像头
        colorCam.setPreviewSize(640, 360)
        colorCam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
        colorCam.setInterleaved(False)
        colorCam.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
        colorCam.setFps(30)
        
        # 配置单目摄像头
        monoLeft.setResolution(dai.MonoCameraProperties.SensorResolution.THE_720_P)
        monoLeft.setCamera("left")
        monoLeft.setFps(30)
        monoRight.setResolution(dai.MonoCameraProperties.SensorResolution.THE_720_P)
        monoRight.setCamera("right")
        monoRight.setFps(30)
        
        # 配置立体深度
        stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_ACCURACY)
        stereo.initialConfig.setMedianFilter(dai.MedianFilter.KERNEL_7x7)
        stereo.setLeftRightCheck(True)
        stereo.setSubpixel(False)
        # 设置深度图像对齐到彩色摄像头，并确保尺寸匹配
        stereo.setDepthAlign(dai.CameraBoardSocket.CAM_A)
        # 设置深度图像输出尺寸与彩色图像一致
        stereo.setOutputSize(640, 360)
        monoLeft.out.link(stereo.left)
        monoRight.out.link(stereo.right)
        
        # 配置IMU
        imu.enableIMUSensor(dai.IMUSensor.ROTATION_VECTOR, 400)
        imu.setBatchReportThreshold(1)
        imu.setMaxBatchReports(10)
        
        # 配置同步
        sync.setSyncThreshold(timedelta(milliseconds=50))
        colorCam.preview.link(sync.inputs["color"])
        stereo.depth.link(sync.inputs["depth"])
        stereo.rectifiedLeft.link(sync.inputs["rectifiedLeft"])
        stereo.rectifiedRight.link(sync.inputs["rectifiedRight"])
        imu.out.link(sync.inputs["imu"])
        
        # 输出
        xoutGrp.setStreamName("xoutGrp")
        sync.out.link(xoutGrp.input)
        
        print("✅ 统一设备管道设置完成")
    
    def start(self):
        """启动设备"""
        with self._lock:
            if self.running:
                print("⚠️ 设备已经在运行")
                return True
            
            if self.device is not None:
                print("⚠️ 设备实例已存在，先停止现有设备")
                self._cleanup_device()
            
            try:
                print("🚀 启动设备管理器...")
                self.device = dai.Device(self.pipeline)
                
                # 获取设备信息
                print(f"📱 设备信息:")
                print(f"   MxId: {self.device.getDeviceInfo().getMxId()}")
                print(f"   USB速度: {self.device.getUsbSpeed()}")
                print(f"   连接的摄像头: {self.device.getConnectedCameras()}")
                print(f"   摄像头传感器: {self.device.getCameraSensorNames()}")
                print(f"   连接的IMU: {self.device.getConnectedIMU()}")
                
                # 获取输出队列 - 使用非阻塞模式
                self.queues['xoutGrp'] = self.device.getOutputQueue("xoutGrp", maxSize=8, blocking=False)
                
                # 启动数据处理线程
                self.running = True
                self.thread = threading.Thread(target=self._data_processing_loop, daemon=True)
                self.thread.start()
                
                print("✅ 设备管理器启动成功")
                return True
                
            except Exception as e:
                print(f"❌ 设备管理器启动失败: {e}")
                self._cleanup_device()
                return False
    
    def stop(self):
        """停止设备"""
        with self._lock:
            if not self.running:
                print("⚠️ 设备未在运行")
                return
            
            print("🛑 停止设备管理器...")
            self.running = False
            
            # 等待数据处理线程结束
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=2.0)
            
            # 清理设备
            self._cleanup_device()
            
            # 关闭线程池
            if self.executor:
                self.executor.shutdown(wait=True)
            
            # 清空全局缓存
            self.global_cache.clear_cache()
            
            print("✅ 设备管理器已停止")
    
    def _cleanup_device(self):
        """清理设备资源"""
        if self.device:
            try:
                self.device.close()
            except:
                pass
            self.device = None
        self.queues.clear()
    
    def is_running(self):
        """检查设备是否在运行"""
        return self.running and self.device is not None
    
    def _data_processing_loop(self):
        """数据处理循环"""
        print("🔄 开始数据处理循环...")
        
        consecutive_errors = 0
        max_consecutive_errors = 10
        last_log_time = time.time()
        log_interval = 5.0  # 每5秒输出一次状态
        data_count = 0
        
        while self.running:
            try:
                if not self.queues.get('xoutGrp'):
                    time.sleep(0.05)
                    continue
                
                # 使用tryGet()避免阻塞
                msgGrp = self.queues['xoutGrp'].tryGet()
                if msgGrp is None:
                    time.sleep(0.005)  # 5ms等待
                    continue
                
                # 提取数据
                extracted_data = self._extract_message_data(msgGrp)
                
                if extracted_data:
                    # 更新本地缓存
                    with self.data_lock:
                        for key, value in extracted_data.items():
                            self.latest_data[key] = value
                        self.latest_data['timestamp'] = time.time()
                    
                    # 更新全局帧缓存
                    self.global_cache.update_frames(extracted_data)
                    
                    # 通知订阅者（保持向后兼容）
                    self._notify_subscribers(extracted_data)
                    
                    # 更新统计
                    data_count += 1
                    self.stats['frames_processed'] += 1
                    consecutive_errors = 0
                else:
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        print(f"⚠️ 连续 {consecutive_errors} 次数据提取失败，暂停处理")
                        time.sleep(1.0)
                        consecutive_errors = 0
                
                # 定期输出状态
                current_time = time.time()
                if current_time - last_log_time >= log_interval:
                    success_rate = (self.debug_counters['successful_extractions'] / 
                                  max(1, self.debug_counters['total_processed'])) * 100
                    print(f"📊 数据处理状态: 已处理{data_count}帧数据, FPS: {self.stats['current_fps']:.1f}, "
                          f"订阅者: {len(self.subscribers)}, 数据提取成功率: {success_rate:.1f}% "
                          f"({self.debug_counters['successful_extractions']}/{self.debug_counters['total_processed']})")
                    last_log_time = current_time
                    data_count = 0
                
                # 计算FPS
                if current_time - self.stats['last_fps_time'] >= 1.0:
                    self.stats['current_fps'] = self.stats['frames_processed'] / (current_time - self.stats['last_fps_time'])
                    self.stats['last_fps_time'] = current_time
                    self.stats['frames_processed'] = 0
                
            except Exception as e:
                consecutive_errors += 1
                print(f"❌ 数据处理循环错误: {e}")
                if consecutive_errors >= max_consecutive_errors:
                    print(f"⚠️ 错误过多，停止数据处理")
                    break
                time.sleep(0.1)
        
        print("🔄 数据处理循环已结束")
    
    def _extract_message_data(self, msgGrp):
        """提取消息数据 - 参考HFUT-MVNS的正确访问方式"""
        try:
            extracted_data = {}
            self.debug_counters['total_processed'] += 1
            
            # 只在前3次处理时打印详细调试信息
            debug_mode = self.debug_counters['total_processed'] <= 3
            
            if debug_mode:
                print(f"🔍 开始处理MessageGroup (第{self.debug_counters['total_processed']}次)")
            
            # 参考HFUT-MVNS的正确访问方式：
            # self.img_BGR = self.msgGrp['color'].getCvFrame()
            # self.img_D = self.msgGrp['depth'].getCvFrame()
            # self.img_rectifiedLeft = self.msgGrp['rectifiedLeft'].getCvFrame()
            # self.img_rectifiedRight = self.msgGrp['rectifiedRight'].getCvFrame()
            # self.imu = self.msgGrp['imu'].packets[0]
            
            # 提取彩色图像
            try:
                color_frame = msgGrp['color'].getCvFrame()
                if color_frame is not None:
                    extracted_data['color'] = color_frame
                    if debug_mode:
                        print(f"✅ 成功提取彩色图像: {color_frame.shape}")
            except (KeyError, AttributeError) as e:
                if debug_mode:
                    print(f"⚠️ 提取彩色图像失败: {e}")
            
            # 提取深度图像
            try:
                depth_frame = msgGrp['depth'].getCvFrame()
                if depth_frame is not None:
                    extracted_data['depth'] = depth_frame
                    if debug_mode:
                        print(f"✅ 成功提取深度图像: {depth_frame.shape}")
            except (KeyError, AttributeError) as e:
                if debug_mode:
                    print(f"⚠️ 提取深度图像失败: {e}")
            
            # 提取左侧矫正图像
            try:
                left_frame = msgGrp['rectifiedLeft'].getCvFrame()
                if left_frame is not None:
                    extracted_data['rectifiedLeft'] = left_frame
                    if debug_mode:
                        print(f"✅ 成功提取左侧图像: {left_frame.shape}")
            except (KeyError, AttributeError) as e:
                if debug_mode:
                    print(f"⚠️ 提取左侧图像失败: {e}")
            
            # 提取右侧矫正图像
            try:
                right_frame = msgGrp['rectifiedRight'].getCvFrame()
                if right_frame is not None:
                    extracted_data['rectifiedRight'] = right_frame
                    if debug_mode:
                        print(f"✅ 成功提取右侧图像: {right_frame.shape}")
            except (KeyError, AttributeError) as e:
                if debug_mode:
                    print(f"⚠️ 提取右侧图像失败: {e}")
            
            # 提取IMU数据
            try:
                imu_data = msgGrp['imu'].packets[0]
                if imu_data is not None:
                    extracted_data['imu'] = imu_data
                    if debug_mode:
                        print(f"✅ 成功提取IMU数据: {type(imu_data)}")
            except (KeyError, AttributeError, IndexError) as e:
                if debug_mode:
                    print(f"⚠️ 提取IMU数据失败: {e}")
            
            # 统计提取结果
            if extracted_data:
                self.debug_counters['successful_extractions'] += 1
                if debug_mode:
                    print(f"✅ 成功提取数据: {list(extracted_data.keys())}")
            else:
                self.debug_counters['failed_extractions'] += 1
                if debug_mode:
                    print("⚠️ 未成功提取任何数据")
            
            return extracted_data
            
        except Exception as e:
            self.debug_counters['failed_extractions'] += 1
            print(f"❌ 提取消息数据时发生错误: {e}")
            return {}
    
    def _notify_subscribers(self, data):
        """通知订阅者"""
        if not self.subscribers:
            return
        
        for subscriber_id, callback in self.subscribers.items():
            try:
                # 在线程池中异步执行回调
                self.executor.submit(self._safe_callback, subscriber_id, callback, data)
            except Exception as e:
                print(f"⚠️ 提交订阅者 {subscriber_id} 回调失败: {e}")
    
    def _safe_callback(self, subscriber_id, callback, data):
        """安全执行回调函数"""
        try:
            callback(data)
            self.stats['subscribers_notified'] += 1
        except Exception as e:
            print(f"⚠️ 订阅者 {subscriber_id} 回调执行失败: {e}")
    
    def subscribe(self, subscriber_id: str, callback):
        """订阅数据更新"""
        with self.data_lock:
            self.subscribers[subscriber_id] = callback
            # 同时订阅全局缓存
            self.global_cache.subscribe(subscriber_id, callback)
            print(f"📡 订阅者 {subscriber_id} 已注册")
    
    def unsubscribe(self, subscriber_id: str):
        """取消订阅"""
        with self.data_lock:
            if subscriber_id in self.subscribers:
                del self.subscribers[subscriber_id]
                self.global_cache.unsubscribe(subscriber_id)
                print(f"📡 订阅者 {subscriber_id} 已注销")
    
    def get_latest_data(self):
        """获取最新数据"""
        with self.data_lock:
            return self.latest_data.copy()
    
    def get_stats(self):
        """获取统计信息"""
        with self.data_lock:
            return {
                **self.stats,
                'debug_counters': self.debug_counters.copy(),
                'global_cache_stats': self.global_cache.get_stats()
            }


# 创建全局设备管理器实例
device_manager = DeviceManager() 