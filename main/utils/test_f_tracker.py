
from flask import Flask
from flask_socketio import SocketIO
import cv2

# if __name__ == '__main__':
from feature_point_tracker import FeaturePointTracker
from feature_point_tracker import FeaturePointTrackerDrawer
from feature_point_tracker import dai
# else:
#     from utils.feature_point_tracker import FeaturePointTracker
#     from utils.feature_point_tracker import FeaturePointTrackerDrawer
#     from utils.feature_point_tracker import dai

# 初始化 Flask & SocketIO
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")


class FeaturePointTrackerStreaming(FeaturePointTracker):
    def __init__(self, camera_size=720, motion_estimation="hardware_accelerated"):
        super().__init__(camera_size=camera_size, motion_estimation=motion_estimation)


    def run(self):
        """ 运行原始的特征点检测，并添加 WebSocket 传输 """
        with self.device as device:
            passthroughImageLeftQueue = device.getOutputQueue("passthroughFrameLeft", 8, False)
            outputFeaturesLeftQueue = device.getOutputQueue("trackedFeaturesLeft", 8, False)
            passthroughImageRightQueue = device.getOutputQueue("passthroughFrameRight", 8, False)
            outputFeaturesRightQueue = device.getOutputQueue("trackedFeaturesRight", 8, False)
            inputFeatureTrackerConfigQueue = device.getInputQueue("trackedFeaturesConfig")

            leftWindowName = "left"
            rightWindowName = "right"

            cfg = dai.FeatureTrackerConfig()
            cfg.set(self.featureTrackerConfig)
            inputFeatureTrackerConfigQueue.send(cfg)

            while True:
                inPassthroughFrameLeft = passthroughImageLeftQueue.get()
                leftFrame = cv2.cvtColor(inPassthroughFrameLeft.getFrame(), cv2.COLOR_GRAY2BGR)

                inPassthroughFrameRight = passthroughImageRightQueue.get()
                rightFrame = cv2.cvtColor(inPassthroughFrameRight.getFrame(), cv2.COLOR_GRAY2BGR)

                # 获取特征点数据
                trackedFeaturesLeft = outputFeaturesLeftQueue.get().trackedFeatures
                trackedFeaturesRight = outputFeaturesRightQueue.get().trackedFeatures

                # 绘制特征点
                leftFeatureDrawer = FeaturePointTrackerDrawer("Tracking Left", leftWindowName)
                rightFeatureDrawer = FeaturePointTrackerDrawer("Tracking Right", rightWindowName)
                leftFeatureDrawer.trackFeaturePath(trackedFeaturesLeft)
                leftFeatureDrawer.drawFeatures(leftFrame)
                rightFeatureDrawer.trackFeaturePath(trackedFeaturesRight)
                rightFeatureDrawer.drawFeatures(rightFrame)

                leftFrame = self.show_fps(leftFrame)

                # 调整图像大小
                leftFrame = cv2.resize(leftFrame, (int(self.camera_size * 1280 / 720), int(self.camera_size)))
                rightFrame = cv2.resize(rightFrame, (int(self.camera_size * 1280 / 720), int(self.camera_size)))

                self.leftFrame = leftFrame
                self.rightFrame = rightFrame

                if not self.continue_running:
                    break

    def show_left(self):
        with self.device as device:
            passthroughImageLeftQueue = device.getOutputQueue("passthroughFrameLeft", 8, False)
            outputFeaturesLeftQueue = device.getOutputQueue("trackedFeaturesLeft", 8, False)

            inputFeatureTrackerConfigQueue = device.getInputQueue("trackedFeaturesConfig")

            leftWindowName = "left"
            cfg = dai.FeatureTrackerConfig()
            cfg.set(self.featureTrackerConfig)
            inputFeatureTrackerConfigQueue.send(cfg)

            while True:
                inPassthroughFrameLeft = passthroughImageLeftQueue.get()
                leftFrame = cv2.cvtColor(inPassthroughFrameLeft.getFrame(), cv2.COLOR_GRAY2BGR)

                # 获取特征点数据
                trackedFeaturesLeft = outputFeaturesLeftQueue.get().trackedFeatures
                # 绘制特征点
                leftFeatureDrawer = FeaturePointTrackerDrawer("Tracking Left", leftWindowName)
                leftFeatureDrawer.trackFeaturePath(trackedFeaturesLeft)
                leftFeatureDrawer.drawFeatures(leftFrame)
                leftFrame = self.show_fps(leftFrame)

                # 调整图像大小
                leftFrame = cv2.resize(leftFrame, (int(self.camera_size * 1280 / 720), int(self.camera_size)))

                _, buffer = cv2.imencode('.jpg', leftFrame)
                frame_bytes = buffer.tobytes()

                # 以 MJPEG 格式返回
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')  # 显示带有颜色映射的视差图


    def show_right(self):
        with self.device as device:
            passthroughImageRightQueue = device.getOutputQueue("passthroughFrameRight", 8, False)
            outputFeaturesRightQueue = device.getOutputQueue("trackedFeaturesRight", 8, False)

            inputFeatureTrackerConfigQueue = device.getInputQueue("trackedFeaturesConfig")

            RightWindowName = "right"
            cfg = dai.FeatureTrackerConfig()
            cfg.set(self.featureTrackerConfig)
            inputFeatureTrackerConfigQueue.send(cfg)

        while True:
            inPassthroughFrameRight = passthroughImageRightQueue.get()
            leftFrame = cv2.cvtColor(inPassthroughFrameRight.getFrame(), cv2.COLOR_GRAY2BGR)

            # 获取特征点数据
            trackedFeaturesRight = outputFeaturesRightQueue.get().trackedFeatures
            # 绘制特征点
            rightFeatureDrawer = FeaturePointTrackerDrawer("Tracking Right", RightWindowName)
            rightFeatureDrawer.trackFeaturePath(trackedFeaturesRight)
            rightFeatureDrawer.drawFeatures(RightFrame)
            RightFrame = self.show_fps(RightFrame)

            # 调整图像大小
            RightFrame = cv2.resize(RightFrame, (int(self.camera_size * 1280 / 720), int(self.camera_size)))

            _, buffer = cv2.imencode('.jpg', RightFrame)
            frame_bytes = buffer.tobytes()

            # 以 MJPEG 格式返回
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')  # 显示带有颜色映射的视差图

    def shutdown(self):
        self.device.close()

# 错误点，端口拥挤
@socketio.on('connect')
def handle_connect():
    """ 客户端连接时启动视频流 """
    print("客户端已连接！")
    global feature_stream
    feature_stream = FeaturePointTrackerStreaming(camera_size=720)
    eventlet.spawn(feature_stream.run)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5002, debug=True)
