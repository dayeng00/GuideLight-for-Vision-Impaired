
from feature_point_detector import FeaturePointDetector
from feature_point_detector import dai
from flask import Flask
from flask_socketio import SocketIO
import cv2

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")  # 允许跨域 WebSocket 连接


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
                rightFrame = passthroughImageRightQueue.get().getFrame()

                leftFrame = cv2.cvtColor(leftFrame, cv2.COLOR_GRAY2BGR)
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

                # left_Frame for circle
                if not self.continue_running:
                    break

    def show_left(self):
        with self.device:
            passthroughImageLeftQueue = self.device.getOutputQueue("passthroughFrameLeft", 8, False)
            outputFeaturesLeftQueue = self.device.getOutputQueue("trackedFeaturesLeft", 8, False)
            self.inputFeatureTrackerConfigQueue = self.device.getInputQueue("trackedFeaturesConfig")

            cfg = dai.FeatureTrackerConfig()
            cfg.set(self.featureTrackerConfig)
            self.inputFeatureTrackerConfigQueue.send(cfg)

            while True:
                leftFrame = passthroughImageLeftQueue.get().getFrame()
                leftFrame = cv2.cvtColor(leftFrame, cv2.COLOR_GRAY2BGR)

                # 处理特征点
                trackedFeaturesLeft = outputFeaturesLeftQueue.get().trackedFeatures
                self.draw_features(leftFrame, trackedFeaturesLeft)

                # 添加 FPS 显示
                leftFrame = self.show_fps(leftFrame)

                # 调整大小
                leftFrame = cv2.resize(leftFrame, (int(self.camera_size * 1280 / 720), int(self.camera_size)))
                _, buffer = cv2.imencode('.jpg', leftFrame)
                frame_bytes = buffer.tobytes()

                # 以 MJPEG 格式返回
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')  # 显示带有颜色映射的视差图

    def show_right(self):
        with self.device:
            passthroughImageRightQueue = self.device.getOutputQueue("passthroughFrameRight", 8, False)
            outputFeaturesRightQueue = self.device.getOutputQueue("trackedFeaturesRight", 8, False)

            self.inputFeatureTrackerConfigQueue = self.device.getInputQueue("trackedFeaturesConfig")

            cfg = dai.FeatureTrackerConfig()
            cfg.set(self.featureTrackerConfig)
            self.inputFeatureTrackerConfigQueue.send(cfg)

            while True:
                rightFrame = passthroughImageRightQueue.get().getFrame()
                rightFrame = cv2.cvtColor(rightFrame, cv2.COLOR_GRAY2BGR)

                trackedFeaturesRight = outputFeaturesRightQueue.get().trackedFeatures
                self.draw_features(rightFrame, trackedFeaturesRight)

                rightFrame = self.show_fps(rightFrame)

                rightFrame = cv2.resize(rightFrame, (int(self.camera_size * 1280 / 720), int(self.camera_size)))

                _, buffer = cv2.imencode('.jpg', rightFrame)
                frame_bytes = buffer.tobytes()
                # 以 MJPEG 格式返回
                yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')  # 显示带有颜色映射的视差图

    def shutdown(self):
        """ 关闭设备 """
        self.device.close()


feature_stream = None

# 错误点
@socketio.on('connect')
def handle_connect():
    """ 客户端连接时启动视频流 """
    print("客户端已连接！")
    global feature_stream
    feature_stream = FeaturePointStreaming(camera_size=720)
    eventlet.spawn(feature_stream.run)


@socketio.on('disconnect')
def handle_disconnect():
    global feature_stream
    if feature_stream is not None:
        feature_stream.shutdown()
        feature_stream = None
    print("客户端断开链接")


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)
