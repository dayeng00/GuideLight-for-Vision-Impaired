"""
代码功能总结：
硬件初始化：配置RGB摄像头、单目摄像头、立体深度计算和对象跟踪器。
神经网络加载：加载MobileNet-SSD模型进行对象检测。
对象跟踪：在RGB图像上跟踪检测到的对象，并显示其3D坐标。
帧率计算：实时计算并显示帧率。
可视化：在图像上绘制检测框、标签、ID、状态和3D坐标。
关键点：
深度感知：通过立体摄像头计算深度信息。
对象跟踪：使用颜色直方图或图像特征进行对象跟踪。
实时性：通过非阻塞模式和队列优化实时性能。
"""

# !/usr/bin/env python3

from pathlib import Path
import blobconverter
import cv2
import depthai as dai
import numpy as np
from utils.video_show import VideoShow
import time
import argparse


# 该类没有继承VideoShowOAK类 因为我懒得改了
class SpatialObjectTracker(VideoShow):
    def __init__(self, nnPath=blobconverter.from_zoo(name='mobilenet-ssd', shaves=6),
                 fullFrameTracking=False, output_size=(720, 720)):
        """

        :param nnPath:
        :param fullFrameTracking:
        :param output_size: (int, int) 预览窗口大小（最后resize)
        """
        super().__init__()
        self.nnPath = nnPath
        self.fullFrameTracking = fullFrameTracking
        self.labelMap = ["background", "aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair",
                         "cow",
                         "diningtable", "dog", "horse", "motorbike", "person", "pottedplant", "sheep", "sofa", "train",
                         "tvmonitor"]
        self.pipeline = dai.Pipeline()
        self.setup_pipeline()
        self.output_size = output_size
        self.device = None

    def setup_pipeline(self):
        # 定义节点和输出
        camRgb = self.pipeline.create(dai.node.ColorCamera)
        spatialDetectionNetwork = self.pipeline.create(dai.node.MobileNetSpatialDetectionNetwork)
        monoLeft = self.pipeline.create(dai.node.MonoCamera)
        monoRight = self.pipeline.create(dai.node.MonoCamera)
        stereo = self.pipeline.create(dai.node.StereoDepth)
        objectTracker = self.pipeline.create(dai.node.ObjectTracker)

        xoutRgb = self.pipeline.create(dai.node.XLinkOut)
        trackerOut = self.pipeline.create(dai.node.XLinkOut)

        xoutRgb.setStreamName("preview")
        trackerOut.setStreamName("tracklets")

        # 设置RGB摄像头属性
        camRgb.setPreviewSize(300, 300)
        camRgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
        camRgb.setInterleaved(False)
        camRgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)

        # 设置单目摄像头属性
        monoLeft.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
        monoLeft.setBoardSocket(dai.CameraBoardSocket.CAM_B)
        monoRight.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
        monoRight.setBoardSocket(dai.CameraBoardSocket.CAM_C)

        # 设置立体深度计算节点属性
        stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.DEFAULT)
        stereo.setDepthAlign(dai.CameraBoardSocket.CAM_A)
        stereo.setOutputSize(monoLeft.getResolutionWidth(), monoLeft.getResolutionHeight())

        # 设置空间检测网络属性
        spatialDetectionNetwork.setBlobPath(self.nnPath)
        spatialDetectionNetwork.setConfidenceThreshold(0.5)
        spatialDetectionNetwork.input.setBlocking(False)
        spatialDetectionNetwork.setBoundingBoxScaleFactor(0.5)
        spatialDetectionNetwork.setDepthLowerThreshold(100)
        spatialDetectionNetwork.setDepthUpperThreshold(5000)

        # 设置对象跟踪器属性
        objectTracker.setDetectionLabelsToTrack([15])  # 只跟踪人
        objectTracker.setTrackerType(dai.TrackerType.ZERO_TERM_COLOR_HISTOGRAM)
        objectTracker.setTrackerIdAssignmentPolicy(dai.TrackerIdAssignmentPolicy.SMALLEST_ID)

        # 链接节点
        monoLeft.out.link(stereo.left)
        monoRight.out.link(stereo.right)
        camRgb.preview.link(spatialDetectionNetwork.input)
        objectTracker.passthroughTrackerFrame.link(xoutRgb.input)
        objectTracker.out.link(trackerOut.input)

        if self.fullFrameTracking:
            camRgb.setPreviewKeepAspectRatio(False)
            camRgb.video.link(objectTracker.inputTrackerFrame)
            objectTracker.inputTrackerFrame.setBlocking(False)
            objectTracker.inputTrackerFrame.setQueueSize(2)
        else:
            spatialDetectionNetwork.passthrough.link(objectTracker.inputTrackerFrame)

        spatialDetectionNetwork.passthrough.link(objectTracker.inputDetectionFrame)
        spatialDetectionNetwork.out.link(objectTracker.inputDetections)
        stereo.depth.link(spatialDetectionNetwork.inputDepth)

    def run(self):
        with dai.Device(self.pipeline) as self.device:
            preview = self.device.getOutputQueue("preview", 4, False)
            tracklets = self.device.getOutputQueue("tracklets", 4, False)

            startTime = time.monotonic()
            counter = 0
            fps = 0
            color = (255, 255, 255)

            while True:
                imgFrame = preview.get()
                track = tracklets.get()

                counter += 1
                current_time = time.monotonic()
                if (current_time - startTime) > 1:
                    fps = counter / (current_time - startTime)
                    counter = 0
                    startTime = current_time

                frame = imgFrame.getCvFrame()
                trackletsData = track.tracklets

                for t in trackletsData:
                    roi = t.roi.denormalize(frame.shape[1], frame.shape[0])
                    x1 = int(roi.topLeft().x)
                    y1 = int(roi.topLeft().y)
                    x2 = int(roi.bottomRight().x)
                    y2 = int(roi.bottomRight().y)

                    try:
                        label = self.labelMap[t.label]
                    except:
                        label = t.label

                    cv2.putText(frame, str(label), (x1 + 10, y1 + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
                    cv2.putText(frame, f"ID: {[t.id]}", (x1 + 10, y1 + 35), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
                    cv2.putText(frame, t.status.name, (x1 + 10, y1 + 50), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, cv2.FONT_HERSHEY_SIMPLEX)

                    cv2.putText(frame, f"X: {int(t.spatialCoordinates.x)} mm", (x1 + 10, y1 + 65),
                                cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
                    cv2.putText(frame, f"Y: {int(t.spatialCoordinates.y)} mm", (x1 + 10, y1 + 80),
                                cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
                    cv2.putText(frame, f"Z: {int(t.spatialCoordinates.z)} mm", (x1 + 10, y1 + 95),
                                cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)

                cv2.putText(frame, "NN fps: {:.2f}".format(fps), (2, frame.shape[0] - 4), cv2.FONT_HERSHEY_TRIPLEX, 0.4,
                            color)
                frame = cv2.resize(frame, self.output_size)
                _, buffer = cv2.imencode('.jpg', frame)
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
    spatial_object_tracker = SpatialObjectTracker()
    spatial_object_tracker.start()  # 创建了一个新线程
    time.sleep(20)
    spatial_object_tracker.close()
    spatial_object_tracker.join()
    print("Done")
