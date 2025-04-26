# -*- coding: utf-8 -*-

"""
使用 MediaPipe Tasks 进行手势识别
本脚本展示了如何使用 MediaPipe Tasks Python API 在图像中识别手势。
然后下载一个现成的模型。该模型可以识别 7 种手势：👍, 👎, ✌️, ☝️, ✊, 👋, 🤟
有关模型的更多详细信息，请查看 [MediaPipe 文档](https://developers.google.com/mediapipe/solutions/vision/gesture_recognizer#models)。
"""

"""
0 - Unrecognized gesture, label: Unknown
1 - Closed fist, label: Closed_Fist
2 - Open palm, label: Open_Palm
3 - Pointing up, label: Pointing_Up
4 - Thumbs down, label: Thumb_Down
5 - Thumbs up, label: Thumb_Up
6 - Victory, label: Victory
7 - Love, label: ILoveYou
"""

# 如果模型检测到手部但未识别出手势，手势识别器会返回“None”结果。如果模型未检测到手，手势识别器会返回空值。
# 手势识别模型详解网址:
# https://ai.google.dev/edge/mediapipe/solutions/vision/gesture_recognizer?hl=zh-cn

import cv2
import math
import time
import depthai as dai
import mediapipe as mp
from mediapipe.framework.formats import landmark_pb2
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from matplotlib import pyplot as plt
if __name__ == "__main__":
    from video_show import VideoShow
else:
    from utils.video_show import VideoShow


class GestureRecognizer(VideoShow):
    def __init__(self, model_path='./main/resources/gesture_recognizer/gesture_recognizer.task',
                 output_size=(640, 480)):
        """

        :param model_path:
        :param output_size(int, int): 最后输出帧大小（4：3）
        """
        # 初始化 MediaPipe 手势识别器
        super().__init__()
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.GestureRecognizerOptions(base_options=base_options)
        self.recognizer = vision.GestureRecognizer.create_from_options(options)
        self.output_size = output_size

        # 初始化 OAK - D 相机管道
        self.pipeline = dai.Pipeline()
        cam_rgb = self.pipeline.createColorCamera()
        cam_rgb.setPreviewSize(640, 480)
        cam_rgb.setFps(30)
        cam_rgb.setInterleaved(False)
        cam_rgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)

        xout_rgb = self.pipeline.createXLinkOut()
        xout_rgb.setStreamName("rgb")
        cam_rgb.preview.link(xout_rgb.input)

        # 初始化绘图工具
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        self.device = None

    def display_one_image(self, image, title, subplot, titlesize=16):
        """显示一张图像以及预测的类别名称和分数。"""
        plt.subplot(*subplot)
        plt.imshow(image)
        if len(title) > 0:
            plt.title(title, fontsize=int(titlesize), color='black', fontdict={'verticalalignment': 'center'},
                      pad=int(titlesize / 1.5))
        return (subplot[0], subplot[1], subplot[2] + 1)

    def display_gesture_and_hand_landmarks(self, image, top_gesture, multi_hand_landmarks):
        """显示图像，包含手势类别及其分数以及手部关键点。"""
        title = f"{top_gesture.category_name} ({top_gesture.score:.2f})"
        annotated_image = image.copy()

        for hand_landmarks in multi_hand_landmarks:
            hand_landmarks_proto = landmark_pb2.NormalizedLandmarkList()
            hand_landmarks_proto.landmark.extend([
                landmark_pb2.NormalizedLandmark(x=landmark.x, y=landmark.y, z=landmark.z) for landmark in hand_landmarks
            ])

            self.mp_drawing.draw_landmarks(
                annotated_image,
                hand_landmarks_proto,
                self.mp_hands.HAND_CONNECTIONS,
                self.mp_drawing_styles.get_default_hand_landmarks_style(),
                self.mp_drawing_styles.get_default_hand_connections_style())

        cv2.putText(annotated_image, title, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        # cv2.imshow('Gesture Recognition', cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR))
        return annotated_image

    def run(self):
        with dai.Device(self.pipeline) as self.device:
            q_rgb = self.device.getOutputQueue(name="rgb", maxSize=4, blocking=False)

            while True:
                in_rgb = q_rgb.tryGet()

                if in_rgb is not None:
                    img = in_rgb.getCvFrame()
                    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)

                    recognition_result = self.recognizer.recognize(image)

                    if recognition_result.gestures:
                        top_gesture = recognition_result.gestures[0][0]
                        hand_landmarks = recognition_result.hand_landmarks
                        img_rgb = cv2.resize(img_rgb, self.output_size)
                        img_rgb = self.display_gesture_and_hand_landmarks(img_rgb, top_gesture, hand_landmarks)
                        # 以 MJPEG 格式返回
                        _, buffer = cv2.imencode('.jpg', img_rgb)
                        frame_bytes = buffer.tobytes()
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    else:
                        img_rgb = cv2.resize(img_rgb, self.output_size)
                        img = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

                        # if __name__ == "__main__":
                        #     # cv2.imshow(img)
                        #     pass
                        # else:
                        #     # 以 MJPEG 格式返回
                        _, buffer = cv2.imencode('.jpg', img)
                        frame_bytes = buffer.tobytes()
                        yield (b'--frame\r\n'
                            b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            # if __name__ == "__main__":
            #         cv2.waitKey(1)
                if not self.continue_running:
                    break

        cv2.destroyAllWindows()

    def shutdown(self):
        self.device.close()


# 一个视频流
if __name__ == "__main__":
    gesture_recognizer = GestureRecognizer(output_size=(640, 480),
                                           model_path='../resources/gesture_recognizer/gesture_recognizer.task')  # 视频帧一定是4:3 不然会拉伸
    gesture_recognizer.start()  # 创建了一个新线程
    time.sleep(20)
    gesture_recognizer.close()
    gesture_recognizer.join()
    print("Done")
