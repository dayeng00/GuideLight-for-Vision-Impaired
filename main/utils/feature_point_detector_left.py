"""
需要重写一遍流式传输，但问题在于视频流要从同一个dai出发，那么就要在，left or right 这里面把dai给传过去， 左调右 或者右调左
"""
import eventlet

eventlet.monkey_patch()
from utils.feature_point_detector import FeaturePointDetector # 引入封装类
from flask import Flask
from flask_socketio import SocketIO
from utils.feature_point_detector import dai
import cv2
import base64

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")  # 允许跨域 WebSocket 连接

# TODO: 左右视频流分离
class FeaturePointStreaming(FeaturePointDetector):
    def __init__(self, camera_size=720):
        super().__init__(camera_size=camera_size)

    def run(self):
        """ 运行原始的特征点检测，并添加 WebSocket 传输 """
        with self.device:
            passthroughImageLeftQueue = self.device.getOutputQueue("passthroughFrameLeft", 8, False)
            outputFeaturesLeftQueue = self.device.getOutputQueue("trackedFeaturesLeft", 8, False)
            passthroughImageRightQueue = self.device.getOutputQueue("passthroughFrameRight", 8, False)
            outputFeaturesRightQueue = self.device.getOutputQueue("trackedFeaturesRight", 8, False)

            self.inputFeatureTrackerConfigQueue = self.device.getInputQueue("trackedFeaturesConfig")

            cfg = dai.FeatureTrackerConfig()
            cfg.set(self.featureTrackerConfig)
            self.inputFeatureTrackerConfigQueue.send(cfg)

            while True:
                # 获取左右相机的帧
                leftFrame = passthroughImageLeftQueue.get().getFrame()
                leftFrame = cv2.cvtColor(leftFrame, cv2.COLOR_GRAY2BGR)

                rightFrame = passthroughImageRightQueue.get().getFrame()
                rightFrame = cv2.cvtColor(rightFrame, cv2.COLOR_GRAY2BGR)


                # 处理特征点
                trackedFeaturesLeft = outputFeaturesLeftQueue.get().trackedFeatures
                self.draw_features(leftFrame, trackedFeaturesLeft)

                trackedFeaturesRight = outputFeaturesRightQueue.get().trackedFeatures
                self.draw_features(rightFrame, trackedFeaturesRight)

                # 添加 FPS 显示
                leftFrame = self.show_fps(leftFrame)

                # 调整大小
                leftFrame = cv2.resize(leftFrame, (int(self.camera_size * 1280 / 720), int(self.camera_size)))
                rightFrame = cv2.resize(rightFrame, (int(self.camera_size * 1280 / 720), int(self.camera_size)))

                # # TODO: 放弃WebSocket，流式传输即可
                # # 新增：转换为 Base64 并通过 WebSocket 发送
                # _, buffer_left = cv2.imencode('.jpg', leftFrame)
                # _, buffer_right = cv2.imencode('.jpg', rightFrame)

                # left_base64 = base64.b64encode(buffer_left).decode('utf-8')
                # right_base64 = base64.b64encode(buffer_right).decode('utf-8')

                # socketio.emit('video_stream', {'id': 1, 'frame': left_base64})
                # socketio.emit('video_stream', {'id': 2, 'frame': right_base64})

                if not self.continue_running:
                    break

    def shutdown(self):
        """ 关闭设备 """
        self.device.close()


@socketio.on('connect')
def handle_connect():
    """ 客户端连接时启动视频流 """
    print("客户端已连接！")
    global feature_stream
    feature_stream = FeaturePointStreaming(camera_size=720)
    eventlet.spawn(feature_stream.run)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5173, debug=True)
