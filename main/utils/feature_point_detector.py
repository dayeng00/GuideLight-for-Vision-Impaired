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

class FeaturePointDetector(VideoShowOAK):
    def __init__(self, camera_size=720, is_show_fps=True, corner_detector="harris", headless=True):
        """
        :param camera_size: 相机图像大小
        :param is_show_fps: 是否显示帧率
        :param corner_detector: 角点检测方法:"harris"、"shi_thomasi" 默认"harris"(开销较低 性能较低)
        :param headless: 是否不创建窗口，在服务器模式下设为True
        """

        super().__init__(is_show_fps=is_show_fps, camera_size=camera_size)

        self.inputFeatureTrackerConfigQueue = None
        self.headless = headless  # 添加headless标志
        
        #  2025/3/27 NEW： 左右视频流
        self.leftFrame = None
        self.rightFrame = None
        
        # 添加线程控制
        self.thread = None
        self.continue_running = False

        # 定义输入源和输出
        self.featureTrackerLeft = self.pipeline.create(dai.node.FeatureTracker)  # 创建左侧特征跟踪节点
        self.featureTrackerRight = self.pipeline.create(dai.node.FeatureTracker)  # 创建右侧特征跟踪节点

        # 创建输出节点，分别用于输出不同的数据流
        self.xoutPassthroughFrameLeft = self.pipeline.create(dai.node.XLinkOut)  # 左侧相机输出节点
        self.xoutTrackedFeaturesLeft = self.pipeline.create(dai.node.XLinkOut)  # 左侧跟踪特征输出节点
        self.xoutPassthroughFrameRight = self.pipeline.create(dai.node.XLinkOut)  # 右侧相机输出节点
        self.xoutTrackedFeaturesRight = self.pipeline.create(dai.node.XLinkOut)  # 右侧特征跟踪输出节点
        self.xinTrackedFeaturesConfig = self.pipeline.create(dai.node.XLinkIn)  # 配置输入节点（用于改变特征跟踪设置）

        # 设置输出节点的流名称
        self.xoutPassthroughFrameLeft.setStreamName("passthroughFrameLeft")
        self.xoutTrackedFeaturesLeft.setStreamName("trackedFeaturesLeft")
        self.xoutPassthroughFrameRight.setStreamName("passthroughFrameRight")
        self.xoutTrackedFeaturesRight.setStreamName("trackedFeaturesRight")
        self.xinTrackedFeaturesConfig.setStreamName("trackedFeaturesConfig")

        # 禁用光流估算（默认为禁用，防止光流干扰）
        self.featureTrackerLeft.initialConfig.setMotionEstimator(False)
        self.featureTrackerRight.initialConfig.setMotionEstimator(False)

        # 设置节点之间的链接
        self.monoLeft.out.link(self.featureTrackerLeft.inputImage)  # 将左侧相机的输出连接到左侧特征跟踪的输入
        self.featureTrackerLeft.passthroughInputImage.link(self.xoutPassthroughFrameLeft.input)  # 将左侧特征跟踪的输入图像传递给输出
        self.featureTrackerLeft.outputFeatures.link(self.xoutTrackedFeaturesLeft.input)  # 将左侧跟踪到的特征传递给输出
        self.xinTrackedFeaturesConfig.out.link(self.featureTrackerLeft.inputConfig)  # 配置输入连接到左侧特征跟踪

        self.monoRight.out.link(self.featureTrackerRight.inputImage)  # 将右侧相机的输出连接到右侧特征跟踪的输入
        self.featureTrackerRight.passthroughInputImage.link(self.xoutPassthroughFrameRight.input)  # 将右侧特征跟踪的输入图像传递给输出
        self.featureTrackerRight.outputFeatures.link(self.xoutTrackedFeaturesRight.input)  # 将右侧跟踪到的特征传递给输出
        self.xinTrackedFeaturesConfig.out.link(self.featureTrackerRight.inputConfig)  # 配置输入连接到右侧特征跟踪

        # 获取当前特征跟踪配置（可以用来修改配置）
        self.featureTrackerConfig = self.featureTrackerRight.initialConfig.get()
        self.device = None
        # 选择角点检测方法
        if corner_detector == "harris":
            self.featureTrackerConfig.cornerDetector.type = dai.FeatureTrackerConfig.CornerDetector.Type.HARRIS  # 切换到HARRIS角点检测
            print("Using Harris Corner Detector")
        elif corner_detector == "shi_thomasi":
            self.featureTrackerConfig.cornerDetector.type = dai.FeatureTrackerConfig.CornerDetector.Type.SHI_THOMASI  # 切换到SHI_THOMASI角点检测
            print("Using Shi Thomasi Corner Detector")
        else:
            raise ValueError("Unknown corner detector type")

    def draw_features(self, frame, features):
        pointColor = (0, 0, 255)  # 特征点的颜色（红色）
        circleRadius = 2  # 特征点的圆形半径
        for feature in features:
            # 在图像中绘制特征点
            cv2.circle(frame, (int(feature.position.x), int(feature.position.y)), circleRadius, pointColor, -1,
                       cv2.LINE_AA, 0)

    def _run_thread(self):
        """在单独的线程中运行视频处理"""
        try:
            # 检查设备是否可用
            available_devices = dai.Device.getAllAvailableDevices()
            if len(available_devices) == 0:
                print("没有找到可用的摄像头设备")
                self.continue_running = False
                return
            
            print(f"找到 {len(available_devices)} 个可用设备:")
            for device_info in available_devices:
                print(f" - {device_info.getMxId()} (状态: {device_info.state})")
            
            # 连接设备并启动数据流管道
            with dai.Device(self.pipeline) as self.device:
                print("设备已连接，开始处理视频流")
                # 获取输出队列，用于接收处理后的结果
                passthroughImageLeftQueue = self.device.getOutputQueue("passthroughFrameLeft", 8, False)  # 获取左侧相机的传递图像队列
                outputFeaturesLeftQueue = self.device.getOutputQueue("trackedFeaturesLeft", 8, False)  # 获取左侧特征跟踪的输出队列
                passthroughImageRightQueue = self.device.getOutputQueue("passthroughFrameRight", 8, False)  # 获取右侧相机的传递图像队列
                outputFeaturesRightQueue = self.device.getOutputQueue("trackedFeaturesRight", 8, False)  # 获取右侧特征跟踪的输出队列

                self.inputFeatureTrackerConfigQueue = self.device.getInputQueue("trackedFeaturesConfig")  # 获取特征跟踪配置输入队列

                # 发送更新后的特征跟踪配置
                cfg = dai.FeatureTrackerConfig()
                cfg.set(self.featureTrackerConfig)
                self.inputFeatureTrackerConfigQueue.send(cfg)  # 更新特征跟踪配置

                # 在headless模式下不创建或引用任何OpenCV窗口
                if not self.headless:
                    leftWindowName = "left"
                    rightWindowName = "right"
                
                print("开始处理视频流")
                
                # 确保camera_size非零，防止除零错误
                if self.camera_size <= 0:
                    self.camera_size = 720  # 设置默认值
                    print(f"警告: 相机尺寸无效，已设置为默认值 {self.camera_size}")
                
                while self.continue_running:
                    try:
                        # 获取左侧相机的传递帧
                        inPassthroughFrameLeft = passthroughImageLeftQueue.get()
                        passthroughFrameLeft = inPassthroughFrameLeft.getFrame()
                        self.leftFrame = cv2.cvtColor(passthroughFrameLeft, cv2.COLOR_GRAY2BGR)  # 转换为BGR图像，以便显示
                        
                        # 获取右侧相机的传递帧
                        inPassthroughFrameRight = passthroughImageRightQueue.get()
                        passthroughFrameRight = inPassthroughFrameRight.getFrame()
                        self.rightFrame = cv2.cvtColor(passthroughFrameRight, cv2.COLOR_GRAY2BGR)  # 转换为BGR图像，以便显示
                        
                        # 获取左侧跟踪到的特征点
                        trackedFeaturesLeft = outputFeaturesLeftQueue.get().trackedFeatures
                        # 在左侧图像中绘制特征点
                        self.draw_features(self.leftFrame, trackedFeaturesLeft)

                        # 获取右侧跟踪到的特征点
                        trackedFeaturesRight = outputFeaturesRightQueue.get().trackedFeatures
                        # 在右侧图像中绘制特征点
                        self.draw_features(self.rightFrame, trackedFeaturesRight)

                        # 显示FPS
                        try:
                            leftFrame = self.show_fps(self.leftFrame)
                            rightFrame = self.show_fps(self.rightFrame)
                            
                            # 安全地调整图像大小，避免除零错误
                            if self.camera_size > 0 and leftFrame is not None and rightFrame is not None:
                                # 计算图像比例，确保数值有效
                                ratio = max(0.1, 1280 / 720)  # 使用固定比例以避免除零
                                new_width = int(self.camera_size * ratio)
                                new_height = int(self.camera_size)
                                
                                left_frame = cv2.resize(leftFrame, (new_width, new_height))
                                right_frame = cv2.resize(rightFrame, (new_width, new_height))
                                
                                self.leftFrame = left_frame
                                self.rightFrame = right_frame
                        except Exception as resize_error:
                            print(f"调整图像大小时出错: {str(resize_error)}")
                            # 如果调整失败，继续使用原始图像
                            self.leftFrame = leftFrame if leftFrame is not None else self.leftFrame
                            self.rightFrame = rightFrame if rightFrame is not None else self.rightFrame
                        
                        # 添加短暂休眠以避免过度占用CPU
                        time.sleep(0.01)
                    except Exception as frame_error:
                        print(f"处理一帧图像时出错: {str(frame_error)}")
                        time.sleep(0.1)  # 发生错误时稍等片刻

                print("视频处理线程已停止")
        except Exception as e:
            print(f"视频处理发生错误: {str(e)}")
        finally:
            # 确保设备正确关闭
            if self.device is not None:
                try:
                    self.device.close()
                    print("设备已关闭")
                except Exception as e:
                    print(f"关闭设备失败: {str(e)}")
    
    def start(self):
        """启动视频处理线程"""
        try:
            if self.thread is None or not self.thread.is_alive():
                self.continue_running = True
                self.thread = threading.Thread(target=self._run_thread)
                self.thread.daemon = True  # 设置为守护线程，当主线程退出时，该线程也会退出
                self.thread.start()
                print("视频处理线程已启动")
                # 等待线程初始化，确保视频流已开始
                time.sleep(1.0)  # 增加等待时间，以便捕获初始化错误
                return True
            return False
        except Exception as e:
            self.continue_running = False
            print(f"启动视频处理线程失败: {str(e)}")
            raise RuntimeError(f"无法启动摄像头: {str(e)}")
    
    def close(self):
        """安全停止视频处理线程"""
        self.continue_running = False
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(timeout=5.0)  # 等待线程最多5秒钟
            print("线程已关闭")
        return True

    def run(self):
        """为保持兼容性，调用start方法启动线程"""
        self.start()

    def shutdown(self):
        """关闭设备并释放资源"""
        self.close()  # 调用close方法关闭线程
        self.continue_running = False
        try:
            if self.device is not None:
                print("正在关闭设备...")
                self.device.close()
                print("设备已关闭")
        except Exception as e:
            print(f"关闭设备失败: {str(e)}")
            
    # 2025/3/27 NEW：流式传输返回左视频流
    def show_left(self):
        """为前端提供左侧摄像头的MJPEG流"""
        # 不使用无限循环，而是让Flask负责多次调用生成器
        while self.continue_running:  # 保留检查，但不是主循环
            try:
                left_frame = self.leftFrame
                if left_frame is not None:
                    # 将图像编码为JPEG格式
                    _, buffer = cv2.imencode('.jpg', left_frame)
                    frame_bytes = buffer.tobytes()

                    # 以 MJPEG 格式返回单帧
                    yield (b'--frame\r\n'
                          b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    
                    # 让出CPU，避免过度占用资源
                    time.sleep(0.03)  # 约30fps
                else:
                    # 如果图像不可用，等待一会再尝试
                    time.sleep(0.1)
                    # 返回一个空帧或错误消息
                    yield (b'--frame\r\n'
                          b'Content-Type: image/jpeg\r\n\r\n' + b'' + b'\r\n')
            except Exception as e:
                print(f"左摄像头流处理错误: {str(e)}")
                # 出错时返回空帧
                yield (b'--frame\r\n'
                      b'Content-Type: image/jpeg\r\n\r\n' + b'' + b'\r\n')
                time.sleep(0.1)

    # 2025/3/27 NEW：流式传输返回右视频流   
    def show_right(self):
        """为前端提供右侧摄像头的MJPEG流"""
        # 不使用无限循环，而是让Flask负责多次调用生成器
        while self.continue_running:  # 保留检查，但不是主循环
            try:
                right_frame = self.rightFrame
                if right_frame is not None:
                    # 将图像编码为JPEG格式
                    _, buffer = cv2.imencode('.jpg', right_frame)
                    frame_bytes = buffer.tobytes()

                    # 流式传输 MJPEG 即视频流
                    yield (b'--frame\r\n'
                          b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    
                    # 让出CPU，避免过度占用资源
                    time.sleep(0.03)  # 约30fps
                else:
                    # 如果图像不可用，等待一会再尝试
                    time.sleep(0.1)
                    # 返回一个空帧或错误消息
                    yield (b'--frame\r\n'
                          b'Content-Type: image/jpeg\r\n\r\n' + b'' + b'\r\n')
            except Exception as e:
                print(f"右摄像头流处理错误: {str(e)}")
                # 出错时返回空帧
                yield (b'--frame\r\n'
                      b'Content-Type: image/jpeg\r\n\r\n' + b'' + b'\r\n')
                time.sleep(0.1)

# 两个视频流
# 创建FeatureTracker实例并运行
if __name__ == "__main__":
    feature_point_detector = FeaturePointDetector(camera_size=720)
    print(feature_point_detector.camera_size)
    feature_point_detector.start()  # 创建了一个新线程
    time.sleep(8)
    feature_point_detector.close()
    time.sleep(1)  # 等待线程完全关闭
    print("Done")
