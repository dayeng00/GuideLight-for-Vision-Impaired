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
    def __init__(self, camera_size=720, is_show_fps=True, corner_detector="harris"):
        """
        :param camera_size:
        :param is_show_fps:
        :param corner_detector:角点检测方法:"harris"、"shi_thomasi" 默认"harris"(开销较低 性能较低)
        """

        super().__init__(is_show_fps=is_show_fps, camera_size=camera_size)

        self.inputFeatureTrackerConfigQueue = None

        #  2025/3/27 NEW： 左右视频流
        self.leftFrame = None
        self.rightFrame = None

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

    def run(self):
        # 连接设备并启动数据流管道
        with dai.Device(self.pipeline) as self.device:

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

            # 设置显示窗口的名称
            # leftWindowName = "left"
            # rightWindowName = "right"

            while True:
                # 获取左侧相机的传递帧
                inPassthroughFrameLeft = passthroughImageLeftQueue.get()
                passthroughFrameLeft = inPassthroughFrameLeft.getFrame()
                leftFrame = cv2.cvtColor(passthroughFrameLeft, cv2.COLOR_GRAY2BGR)  # 转换为BGR图像，以便显示

                # 获取右侧相机的传递帧
                inPassthroughFrameRight = passthroughImageRightQueue.get()
                passthroughFrameRight = inPassthroughFrameRight.getFrame()
                rightFrame = cv2.cvtColor(passthroughFrameRight, cv2.COLOR_GRAY2BGR)  # 转换为BGR图像，以便显示

                # 获取左侧跟踪到的特征点
                trackedFeaturesLeft = outputFeaturesLeftQueue.get().trackedFeatures
                # 在左侧图像中绘制特征点
                self.draw_features(leftFrame, trackedFeaturesLeft)

                # 获取右侧跟踪到的特征点
                trackedFeaturesRight = outputFeaturesRightQueue.get().trackedFeatures
                # 在右侧图像中绘制特征点
                self.draw_features(rightFrame, trackedFeaturesRight)

                leftFrame = self.show_fps(leftFrame)

                # 调整图像大小
                left_frame = cv2.resize(leftFrame, (int(self.camera_size * 1280 / 720), int(self.camera_size)))
                right_frame = cv2.resize(rightFrame, (int(self.camera_size * 1280 / 720), int(self.camera_size)))

                self.leftFrame = left_frame
                self.rightFrame = right_frame
                # # **新增：转换为 Base64 并通过 WebSocket 发送**
                # _, buffer_left = cv2.imencode('.jpg', leftFrame)
                # _, buffer_right = cv2.imencode('.jpg', rightFrame)

                # left_base64 = base64.b64encode(buffer_left).decode('utf-8')
                # right_base64 = base64.b64encode(buffer_right).decode('utf-8')

                # socketio.emit('video_stream', {'id': 1, 'frame': left_base64})
                # socketio.emit('video_stream', {'id': 2, 'frame': right_base64})

                # # cv2.waitKey(1)  # 获取按键

                # TODO: 转左右流流式传输

                if not self.continue_running:
                    break
    # 2025/3/27 NEW：流式传输返回左视频流
    def show_left(self):
        left_frame = self.leftFrame

        _, buffer = cv2.imencode('.jpg', left_frame)
        frame_bytes = buffer.tobytes()

        # 以 MJPEG 格式返回
        yield (b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    # 2025/3/27 NEW：流式传输返回右视频流   
    def show_right(self):
        right_frame = self.rightFrame

        _, buffer = cv2.imencode('.jpg', right_frame)
        frame_bytes = buffer.tobytes()

        # 流式传输 MJPEG 即视频流
        yield (b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n') 

    # 2025/3/27 NEW: 撤销调用
    def shutdown(self):
        self.device.close()


# 两个视频流
# 创建FeatureTracker实例并运行
if __name__ == "__main__":
    feature_point_detector = FeaturePointDetector(camera_size=720)
    print(feature_point_detector.camera_size)
    feature_point_detector.start()  # 创建了一个新线程
    time.sleep(8)
    feature_point_detector.close()
    feature_point_detector.join()
    print("Done")
