"""
手势关键点检测
"""
import cv2
import mediapipe as mp
import time
import depthai as dai
from video_show import VideoShow


class GesturePointRecognition(VideoShow):
    def __init__(self, static_image_mode=False, max_num_hands=2,
                 model_complexity=1, min_detection_confidence=0.5,
                 min_tracking_confidence=0.5, output_size=(720, 720)):
        """

        :param static_image_mode:
        :param max_num_hands:
        :param model_complexity:
        :param min_detection_confidence:
        :param min_tracking_confidence:
        :param output_size(int, int): 最后预览窗口的大小（使用cv2.resize())
        """
        super().__init__()
        self.mpHands = mp.solutions.hands
        self.hands = self.mpHands.Hands(static_image_mode, max_num_hands, model_complexity, min_detection_confidence,
                                        min_tracking_confidence)
        self.mpDraw = mp.solutions.drawing_utils
        self.handLmsStyle = self.mpDraw.DrawingSpec(color=(0, 0, 255), thickness=5)
        self.handConStyle = self.mpDraw.DrawingSpec(color=(0, 255, 0), thickness=4)
        self.output_size = output_size
        self.previousTime = 0
        self.currentTime = 0
        self.device = None

    def run(self):
        # 创建管道
        pipeline = dai.Pipeline()

        # 定义RGB相机节点
        cam_rgb = pipeline.createColorCamera()
        # 设置分辨率
        cam_rgb.setPreviewSize(640, 480)
        # 设置帧率
        cam_rgb.setFps(30)
        # 设置色彩模式
        cam_rgb.setInterleaved(False)
        # 设置颜色空间
        cam_rgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)

        # 创建XLinkOut节点用于将数据传输到主机
        xout_rgb = pipeline.createXLinkOut()
        xout_rgb.setStreamName("rgb")
        # 将RGB相机的预览输出连接到XLinkOut节点
        cam_rgb.preview.link(xout_rgb.input)

        # 连接到设备并启动管道
        with dai.Device(pipeline) as self.device:
            # 获取RGB流
            q_rgb = self.device.getOutputQueue(name="rgb", maxSize=4, blocking=False)

            while True:
                # 从队列中获取帧
                in_rgb = q_rgb.tryGet()

                if in_rgb is not None:
                    # 将帧数据转换为OpenCV格式
                    img = in_rgb.getCvFrame()
                    imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    result = self.hands.process(imgRGB)
                    imgHeight, imgWidth = img.shape[:2]

                    if result.multi_hand_landmarks:
                        for hand_landmarks in result.multi_hand_landmarks:
                            self.mpDraw.draw_landmarks(img, hand_landmarks, self.mpHands.HAND_CONNECTIONS,
                                                       self.handLmsStyle, self.handConStyle)
                            for i, lm in enumerate(hand_landmarks.landmark):
                                xPosition = int(lm.x * imgWidth)
                                yPosition = int(lm.y * imgHeight)
                                cv2.putText(img, str(i), (xPosition - 25, yPosition + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                                            (0, 0, 255), 2)
                                if i == 0:
                                    cv2.circle(img, (xPosition, yPosition), 10, (0, 0, 255), cv2.FILLED)

                    self.currentTime = time.time()
                    fps = 1 / (self.currentTime - self.previousTime)
                    self.previousTime = self.currentTime
                    cv2.putText(img, f'FPS: {int(fps)}', (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)
                    img = cv2.resize(img, self.output_size)
                    _, buffer = cv2.imencode('.jpg', img)
                    frame_bytes = buffer.tobytes()

                    # 以 MJPEG 格式返回
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

                # cv2.waitKey(1)
                if not self.continue_running:
                    break

        cv2.destroyAllWindows()

    def shutdown(self):
        self.device.close()


# 一个视频流
if __name__ == "__main__":
    gesture_point_recognition = GesturePointRecognition(output_size=(720, 720))
    gesture_point_recognition.start()  # 创建了一个新线程
    time.sleep(20)
    gesture_point_recognition.close()
    gesture_point_recognition.join()
    print("Done")
