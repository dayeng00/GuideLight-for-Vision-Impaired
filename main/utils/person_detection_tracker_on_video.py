#!/usr/bin/env python3

import blobconverter
import cv2
import depthai as dai
import numpy as np
import time
from video_show import VideoShow


class PersonDetectionTrackerOnVideo(VideoShow):
    def __init__(self, nnPath=blobconverter.from_zoo(name='person-detection-retail-0013', shaves=7),
                 videoPath=r"../resources/learn_YOLO/video/football.mp4",
                 camera_size=720, is_show_fps=True):
        """
        初始化PersonDetectionTracker类。

        :param nnPath: 神经网络模型的路径
        :param videoPath: 视频文件的路径
        """
        super().__init__(camera_size=camera_size, is_show_fps=is_show_fps)
        self.nnPath = nnPath
        self.videoPath = videoPath
        self.labelMap = ["person", ""]
        self.pipeline = dai.Pipeline()
        self.setup_pipeline()

    def setup_pipeline(self):
        """
        设置DepthAI管道，包括图像处理、目标跟踪、检测网络等节点。
        """
        # 定义节点
        self.manip = self.pipeline.create(dai.node.ImageManip)
        self.objectTracker = self.pipeline.create(dai.node.ObjectTracker)
        self.detectionNetwork = self.pipeline.create(dai.node.MobileNetDetectionNetwork)

        # 定义输出节点
        self.manipOut = self.pipeline.create(dai.node.XLinkOut)
        self.xinFrame = self.pipeline.create(dai.node.XLinkIn)
        self.trackerOut = self.pipeline.create(dai.node.XLinkOut)
        self.xlinkOut = self.pipeline.create(dai.node.XLinkOut)
        self.nnOut = self.pipeline.create(dai.node.XLinkOut)

        # 设置输出流的名称
        self.manipOut.setStreamName("manip")
        self.xinFrame.setStreamName("inFrame")
        self.xlinkOut.setStreamName("trackerFrame")
        self.trackerOut.setStreamName("tracklets")
        self.nnOut.setStreamName("nn")

        # 设置输入帧的最大数据大小
        self.xinFrame.setMaxDataSize(720 * 720 * 3)

        # 配置图像处理节点
        self.manip.initialConfig.setResizeThumbnail(544, 320)
        self.manip.initialConfig.setKeepAspectRatio(False)
        self.manip.initialConfig.setFrameType(dai.ImgFrame.Type.BGR888p)
        self.manip.inputImage.setBlocking(True)

        # 配置检测网络节点
        self.detectionNetwork.setBlobPath(self.nnPath)
        self.detectionNetwork.setConfidenceThreshold(0.5)
        self.detectionNetwork.input.setBlocking(True)

        # 配置目标跟踪节点
        self.objectTracker.inputTrackerFrame.setBlocking(True)
        self.objectTracker.inputDetectionFrame.setBlocking(True)
        self.objectTracker.inputDetections.setBlocking(True)
        self.objectTracker.setDetectionLabelsToTrack([1])
        self.objectTracker.setTrackerType(dai.TrackerType.ZERO_TERM_COLOR_HISTOGRAM)
        self.objectTracker.setTrackerIdAssignmentPolicy(dai.TrackerIdAssignmentPolicy.SMALLEST_ID)

        # 链接各个节点
        self.manip.out.link(self.manipOut.input)
        self.manip.out.link(self.detectionNetwork.input)
        self.xinFrame.out.link(self.manip.inputImage)
        self.xinFrame.out.link(self.objectTracker.inputTrackerFrame)
        self.detectionNetwork.out.link(self.nnOut.input)
        self.detectionNetwork.out.link(self.objectTracker.inputDetections)
        self.detectionNetwork.passthrough.link(self.objectTracker.inputDetectionFrame)
        self.objectTracker.out.link(self.trackerOut.input)
        self.objectTracker.passthroughTrackerFrame.link(self.xlinkOut.input)

    def to_planar(self, arr: np.ndarray, shape: tuple) -> np.ndarray:
        """
        将图像转换为Planar格式。

        :param arr: 输入的图像数组
        :param shape: 目标形状
        :return: 转换后的Planar格式图像
        """
        return cv2.resize(arr, shape).transpose(2, 0, 1).flatten()

    def frameNorm(self, frame, bbox):
        """
        归一化边界框坐标。

        :param frame: 当前帧
        :param bbox: 边界框坐标
        :return: 归一化后的边界框坐标
        """
        normVals = np.full(len(bbox), frame.shape[0])
        normVals[::2] = frame.shape[1]
        return (np.clip(np.array(bbox), 0, 1) * normVals).astype(int)

    def displayFrame(self, name, frame):
        """
        在帧上显示检测结果。

        :param name: 窗口名称
        :param frame: 当前帧
        """
        for detection in self.detections:
            bbox = self.frameNorm(frame, (detection.xmin, detection.ymin, detection.xmax, detection.ymax))
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (255, 0, 0), 2)
            cv2.putText(frame, self.labelMap[detection.label], (bbox[0] + 10, bbox[1] + 20), cv2.FONT_HERSHEY_TRIPLEX,
                        0.5, 255)
            cv2.putText(frame, f"{int(detection.confidence * 100)}%", (bbox[0] + 10, bbox[1] + 40),
                        cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
        cv2.imshow(name, frame)

    def run(self):
        """
        运行视频处理主循环。
        """
        with dai.Device(self.pipeline) as device:
            # 获取输入和输出队列
            qIn = device.getInputQueue(name="inFrame")
            trackerFrameQ = device.getOutputQueue(name="trackerFrame", maxSize=4)
            tracklets = device.getOutputQueue(name="tracklets", maxSize=4)
            qManip = device.getOutputQueue(name="manip", maxSize=4)
            qDet = device.getOutputQueue(name="nn", maxSize=4)

            # 初始化变量
            startTime = time.monotonic()
            counter = 0
            fps = 0
            self.detections = []
            frame = None

            # 打开视频文件
            cap = cv2.VideoCapture(self.videoPath)
            baseTs = time.monotonic()
            simulatedFps = 30
            inputFrameShape = (720, 720)

            # 主循环：逐帧处理视频
            while cap.isOpened():
                read_correctly, frame = cap.read()
                if not read_correctly:
                    break

                # 创建DepthAI图像帧并设置属性
                img = dai.ImgFrame()
                img.setType(dai.ImgFrame.Type.BGR888p)
                img.setData(self.to_planar(frame, inputFrameShape))
                img.setTimestamp(baseTs)
                baseTs += 1 / simulatedFps

                img.setWidth(inputFrameShape[0])
                img.setHeight(inputFrameShape[1])
                qIn.send(img)

                # 获取跟踪帧
                trackFrame = trackerFrameQ.tryGet()
                if trackFrame is None:
                    continue

                # 获取跟踪结果和检测结果
                track = tracklets.get()
                manip = qManip.get()
                inDet = qDet.get()

                # 计算FPS
                counter += 1
                current_time = time.monotonic()
                if (current_time - startTime) > 1:
                    fps = counter / (current_time - startTime)
                    counter = 0
                    startTime = current_time

                # 更新检测结果
                self.detections = inDet.detections
                manipFrame = manip.getCvFrame()
                self.displayFrame("nn", manipFrame)

                # 在跟踪帧上绘制跟踪结果
                color = (255, 0, 0)
                trackerFrame = trackFrame.getCvFrame()
                trackletsData = track.tracklets
                for t in trackletsData:
                    if t.status == dai.Tracklet.TrackingStatus.LOST:
                        continue
                    roi = t.roi.denormalize(trackerFrame.shape[1], trackerFrame.shape[0])
                    x1 = int(roi.topLeft().x)
                    y1 = int(roi.topLeft().y)
                    x2 = int(roi.bottomRight().x)
                    y2 = int(roi.bottomRight().y)

                    try:
                        label = self.labelMap[t.label]
                    except:
                        label = t.label

                    cv2.putText(trackerFrame, str(label), (x1 + 10, y1 + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
                    cv2.putText(trackerFrame, f"ID: {[t.id]}", (x1 + 10, y1 + 35), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
                    cv2.putText(trackerFrame, t.status.name, (x1 + 10, y1 + 50), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
                    cv2.rectangle(trackerFrame, (x1, y1), (x2, y2), color, cv2.FONT_HERSHEY_SIMPLEX)

                # 显示FPS
                trackerFrame = self.show_fps(trackerFrame)

                # 显示跟踪帧
                cv2.imshow("tracker", trackerFrame)
                cv2.waitKey(1)
                if not self.continue_running:
                    break

            cap.release()
            cv2.destroyAllWindows()


if __name__ == "__main__":
    person_tracker = PersonDetectionTrackerOnVideo(nnPath=blobconverter.from_zoo(name='person-detection-retail-0013',
                                                                                 shaves=7),
                                                   videoPath=r"../resources/learn_YOLO/video/football.mp4",
                                                   camera_size=720, is_show_fps=False)
    person_tracker.start()  # 创建了一个新线程
    time.sleep(20)
    person_tracker.close()
    person_tracker.join()
    print("Done")
