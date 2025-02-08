import eventlet
eventlet.monkey_patch()

from flask import Flask
from flask_socketio import SocketIO
import cv2
import base64
import depthai as dai
from utils.feature_point_tracker import FeaturePointTracker

# 初始化 Flask & SocketIO
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

class FeaturePointTrackerStreaming(FeaturePointTracker):
    def __init__(self, camera_size=720, motion_estimation="hardware_accelerated"):
        super().__init__(camera_size=camera_size, motion_estimation=motion_estimation)

    def run(self):
        """ 运行原始的特征点检测，并添加 WebSocket 传输 """
        with dai.Device(self.pipeline) as device:
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

                # OpenCV 显示窗口
                cv2.imshow(leftWindowName, leftFrame)
                cv2.imshow(rightWindowName, rightFrame)

                # **确保在 Flask 应用上下文中调用 socketio.emit**
                with app.app_context():
                    _, buffer_left = cv2.imencode('.jpg', leftFrame)
                    _, buffer_right = cv2.imencode('.jpg', rightFrame)

                    left_base64 = base64.b64encode(buffer_left).decode('utf-8')
                    right_base64 = base64.b64encode(buffer_right).decode('utf-8')

                    socketio.emit('video_stream', {'id': 1, 'frame': left_base64})
                    socketio.emit('video_stream', {'id': 2, 'frame': right_base64})

                if not self.continue_running:
                    break

    def shutdown(self):
        self.device.close()

@socketio.on('connect')
def handle_connect():
    """ 客户端连接时启动视频流 """
    print("客户端已连接！")
    global feature_stream
    feature_stream = FeaturePointTrackerStreaming(camera_size=720)
    eventlet.spawn(feature_stream.run)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5174, debug=True)
