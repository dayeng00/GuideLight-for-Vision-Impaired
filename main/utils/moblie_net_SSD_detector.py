"""
MobileNetSSD 目标检测
"""
from pathlib import Path
import blobconverter
import cv2
import time
import depthai
import numpy as np
from utils.video_show import VideoShowOAK


class OakDMobileNetSSD(VideoShowOAK):
    def __init__(self, camera_size=720, is_show_fps=True, model_name='mobilenet-ssd', confidence_threshold=0.5,
                 preview_size=(300, 300), output_size=(600, 600)):
        """

        :param camera_size:
        :param is_show_fps:
        :param model_name:
        :param confidence_threshold: 置信度
        :param preview_size:  (int, int) 目标检测模型的输入尺寸
        :param output_size: (int, int)  展示结果的图片尺寸
        """
        super().__init__(camera_size=camera_size, is_show_fps=is_show_fps)
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.preview_size = preview_size
        self.output_size = output_size
        self.frame = None
        self.detections = []

        self._setup_pipeline()
        self.device = None
    def _setup_pipeline(self):
        # 设置彩色相机
        cam_rgb = self.pipeline.createColorCamera()
        cam_rgb.setPreviewSize(self.preview_size[0], self.preview_size[1])
        cam_rgb.setInterleaved(False)

        # 创建神经网络
        detection_nn = self.pipeline.createMobileNetDetectionNetwork()
        detection_nn.setBlobPath(blobconverter.from_zoo(name=self.model_name, shaves=6))
        detection_nn.setConfidenceThreshold(self.confidence_threshold)
        cam_rgb.preview.link(detection_nn.input)

        # 创建XLinkOut节点
        xout_rgb = self.pipeline.createXLinkOut()
        xout_rgb.setStreamName("rgb")
        cam_rgb.preview.link(xout_rgb.input)

        xout_nn = self.pipeline.createXLinkOut()
        xout_nn.setStreamName("nn")
        detection_nn.out.link(xout_nn.input)

    def _frame_norm(self, frame, bbox):
        normVals = np.full(len(bbox), frame.shape[0])
        normVals[::2] = frame.shape[1]
        return (np.clip(np.array(bbox), 0, 1) * normVals).astype(int)

    def run(self):
        with depthai.Device(self.pipeline) as self.device:
            q_rgb = self.device.getOutputQueue("rgb")
            q_nn = self.device.getOutputQueue("nn")

            while True:
                in_rgb = q_rgb.tryGet()
                in_nn = q_nn.tryGet()

                if in_rgb is not None:
                    self.frame = in_rgb.getCvFrame()

                if in_nn is not None:
                    self.detections = in_nn.detections

                if self.frame is not None:
                    for detection in self.detections:
                        bbox = self._frame_norm(self.frame,
                                                (detection.xmin, detection.ymin, detection.xmax, detection.ymax))
                        cv2.rectangle(self.frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (255, 0, 0), 2)

                    self.frame = cv2.resize(self.frame, self.output_size)
                    self.frame = self.show_fps(self.frame)
                    _, buffer = cv2.imencode('.jpg', self.frame)
                    frame_bytes = buffer.tobytes()

                    # 以 MJPEG 格式返回
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

                # cv2.waitKey(1)
                if not self.continue_running:
                    break
    def shutdown(self):
        self.device.close()

# 一个视频流
if __name__ == "__main__":
    oakd_mobilenet_SSD = OakDMobileNetSSD(camera_size=720, preview_size=(300, 300))
    oakd_mobilenet_SSD.start()  # 创建了一个新线程
    time.sleep(20)
    oakd_mobilenet_SSD.close()
    oakd_mobilenet_SSD.join()
    print("Done")
