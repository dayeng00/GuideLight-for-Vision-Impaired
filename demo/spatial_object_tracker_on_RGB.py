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

#!/usr/bin/env python3

from pathlib import Path

import blobconverter
import cv2
import depthai as dai
import numpy as np
import time
import argparse

# 定义标签映射，用于将检测到的对象索引映射到对应的类别名称
labelMap = ["background", "aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair", "cow",
            "diningtable", "dog", "horse", "motorbike", "person", "pottedplant", "sheep", "sofa", "train", "tvmonitor"]

# 默认的神经网络模型路径
nnPathDefault = str((Path(__file__).parent / Path('../models/mobilenet-ssd_openvino_2021.4_5shave.blob')).resolve().absolute())

# 创建参数解析器
parser = argparse.ArgumentParser()
parser.add_argument('nnPath', nargs='?', help="Path to mobilenet detection network blob", default=nnPathDefault)
parser.add_argument('-ff', '--full_frame', action="store_true", help="Perform tracking on full RGB frame", default=False)

# 解析命令行参数
args = parser.parse_args()

# 是否在全帧上进行跟踪
fullFrameTracking = args.full_frame

# 创建DepthAI管道
pipeline = dai.Pipeline()

# 定义节点和输出
camRgb = pipeline.create(dai.node.ColorCamera)  # RGB摄像头
spatialDetectionNetwork = pipeline.create(dai.node.MobileNetSpatialDetectionNetwork)  # 空间检测网络
monoLeft = pipeline.create(dai.node.MonoCamera)  # 左单目摄像头
monoRight = pipeline.create(dai.node.MonoCamera)  # 右单目摄像头
stereo = pipeline.create(dai.node.StereoDepth)  # 立体深度计算
objectTracker = pipeline.create(dai.node.ObjectTracker)  # 对象跟踪器

xoutRgb = pipeline.create(dai.node.XLinkOut)  # RGB图像输出
trackerOut = pipeline.create(dai.node.XLinkOut)  # 跟踪结果输出

xoutRgb.setStreamName("preview")  # 设置RGB图像输出流名称
trackerOut.setStreamName("tracklets")  # 设置跟踪结果输出流名称

# 设置RGB摄像头属性
camRgb.setPreviewSize(300, 300)  # 预览图像大小
camRgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)  # 分辨率设置为1080P
camRgb.setInterleaved(False)  # 设置图像数据为非交错格式
camRgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)  # 设置颜色顺序为BGR

# 设置左单目摄像头属性
monoLeft.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)  # 分辨率设置为400P
monoLeft.setBoardSocket(dai.CameraBoardSocket.CAM_B)

# 设置右单目摄像头属性
monoRight.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)  # 分辨率设置为400P
monoRight.setBoardSocket(dai.CameraBoardSocket.CAM_C)

# 设置立体深度计算节点属性
stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.DEFAULT)  # 设置为高密度深度图模式
stereo.setDepthAlign(dai.CameraBoardSocket.CAM_A)  # 将深度图对齐到RGB摄像头的视角
stereo.setOutputSize(monoLeft.getResolutionWidth(), monoLeft.getResolutionHeight())  # 设置输出大小与单目摄像头一致

# 设置空间检测网络属性
spatialDetectionNetwork.setBlobPath(blobconverter.from_zoo(name='mobilenet-ssd', shaves=6))  # 设置神经网络模型路径
spatialDetectionNetwork.setConfidenceThreshold(0.5)  # 设置置信度阈值
spatialDetectionNetwork.input.setBlocking(False)  # 设置输入为非阻塞模式
spatialDetectionNetwork.setBoundingBoxScaleFactor(0.5)  # 设置边界框缩放因子
spatialDetectionNetwork.setDepthLowerThreshold(100)  # 设置深度下限阈值
spatialDetectionNetwork.setDepthUpperThreshold(5000)  # 设置深度上限阈值

# 设置对象跟踪器属性
objectTracker.setDetectionLabelsToTrack([15])  # 只跟踪人（标签15对应"person"）
# 设置跟踪器类型：ZERO_TERM_COLOR_HISTOGRAM, ZERO_TERM_IMAGELESS, SHORT_TERM_IMAGELESS, SHORT_TERM_KCF
objectTracker.setTrackerType(dai.TrackerType.ZERO_TERM_COLOR_HISTOGRAM)
# 设置跟踪器ID分配策略：SMALLEST_ID（最小ID）或UNIQUE_ID（唯一ID）
objectTracker.setTrackerIdAssignmentPolicy(dai.TrackerIdAssignmentPolicy.SMALLEST_ID)

# 链接节点
monoLeft.out.link(stereo.left)  # 左单目摄像头输出链接到立体深度计算的左输入
monoRight.out.link(stereo.right)  # 右单目摄像头输出链接到立体深度计算的右输入

camRgb.preview.link(spatialDetectionNetwork.input)  # RGB摄像头预览输出链接到空间检测网络的输入
objectTracker.passthroughTrackerFrame.link(xoutRgb.input)  # 跟踪器帧输出链接到RGB图像输出
objectTracker.out.link(trackerOut.input)  # 跟踪器输出链接到跟踪结果输出

# 如果启用全帧跟踪
if fullFrameTracking:
    camRgb.setPreviewKeepAspectRatio(False)  # 不保持预览图像的宽高比
    camRgb.video.link(objectTracker.inputTrackerFrame)  # RGB摄像头视频输出链接到跟踪器的输入帧
    objectTracker.inputTrackerFrame.setBlocking(False)  # 设置输入帧为非阻塞模式
    objectTracker.inputTrackerFrame.setQueueSize(2)  # 设置输入帧队列大小为2
else:
    spatialDetectionNetwork.passthrough.link(objectTracker.inputTrackerFrame)  # 空间检测网络的直通输出链接到跟踪器的输入帧

spatialDetectionNetwork.passthrough.link(objectTracker.inputDetectionFrame)  # 空间检测网络的直通输出链接到跟踪器的检测帧输入
spatialDetectionNetwork.out.link(objectTracker.inputDetections)  # 空间检测网络的输出链接到跟踪器的检测输入
stereo.depth.link(spatialDetectionNetwork.inputDepth)  # 立体深度计算的深度输出链接到空间检测网络的深度输入

# 连接设备并启动管道
with dai.Device(pipeline) as device:

    # 获取输出队列
    preview = device.getOutputQueue("preview", 4, False)  # RGB图像输出队列
    tracklets = device.getOutputQueue("tracklets", 4, False)  # 跟踪结果输出队列

    startTime = time.monotonic()  # 记录开始时间
    counter = 0  # 帧计数器
    fps = 0  # 帧率
    color = (255, 255, 255)  # 文本颜色

    # 主循环
    while(True):
        imgFrame = preview.get()  # 获取RGB图像帧
        track = tracklets.get()  # 获取跟踪结果

        counter += 1  # 帧计数器加1
        current_time = time.monotonic()  # 获取当前时间
        if (current_time - startTime) > 1:  # 如果超过1秒
            fps = counter / (current_time - startTime)  # 计算帧率
            counter = 0  # 重置帧计数器
            startTime = current_time  # 重置开始时间

        frame = imgFrame.getCvFrame()  # 将RGB图像帧转换为OpenCV格式
        trackletsData = track.tracklets  # 获取跟踪数据

        # 遍历每个跟踪对象
        for t in trackletsData:
            roi = t.roi.denormalize(frame.shape[1], frame.shape[0])  # 获取归一化后的ROI区域
            x1 = int(roi.topLeft().x)  # 左上角x坐标
            y1 = int(roi.topLeft().y)  # 左上角y坐标
            x2 = int(roi.bottomRight().x)  # 右下角x坐标
            y2 = int(roi.bottomRight().y)  # 右下角y坐标

            try:
                label = labelMap[t.label]  # 获取对象标签
            except:
                label = t.label  # 如果标签不在映射表中，直接使用原始标签

            # 在图像上绘制标签、ID和状态
            cv2.putText(frame, str(label), (x1 + 10, y1 + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
            cv2.putText(frame, f"ID: {[t.id]}", (x1 + 10, y1 + 35), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
            cv2.putText(frame, t.status.name, (x1 + 10, y1 + 50), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, cv2.FONT_HERSHEY_SIMPLEX)

            # 在图像上绘制对象的3D坐标
            cv2.putText(frame, f"X: {int(t.spatialCoordinates.x)} mm", (x1 + 10, y1 + 65), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
            cv2.putText(frame, f"Y: {int(t.spatialCoordinates.y)} mm", (x1 + 10, y1 + 80), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
            cv2.putText(frame, f"Z: {int(t.spatialCoordinates.z)} mm", (x1 + 10, y1 + 95), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)

        # 在图像上显示帧率
        cv2.putText(frame, "NN fps: {:.2f}".format(fps), (2, frame.shape[0] - 4), cv2.FONT_HERSHEY_TRIPLEX, 0.4, color)

        # 显示图像
        cv2.imshow("tracker", frame)

        # 按下'q'键退出
        if cv2.waitKey(1) == ord('q'):
            break