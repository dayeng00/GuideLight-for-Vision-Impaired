"""
这段代码使用DepthAI库和OpenVINO模型来实现视频中的人物检测与跟踪。
它通过加载预训练的MobileNet SSD模型来检测视频帧中的人物，
并使用ObjectTracker节点对检测到的人物进行跟踪。
最终，代码会在视频帧上绘制检测框、标签、置信度和跟踪ID，并显示处理后的视频帧。
"""
#!/usr/bin/env python3

from pathlib import Path
import blobconverter
import cv2
import depthai as dai
import numpy as np
import time
import argparse

# 定义标签映射，这里只检测"person"类别
labelMap = ["person", ""]

# 设置默认的神经网络模型路径和视频路径
nnPathDefault = str((Path(__file__).parent / Path('../models/person-detection-retail-0013_openvino_2021.4_7shave.blob')).resolve().absolute())
videoPathDefault = str((Path(__file__).parent / Path('../video/football.mp4')).resolve().absolute())

# 解析命令行参数
parser = argparse.ArgumentParser()
parser.add_argument('-nnPath', help="Path to mobilenet detection network blob", default=nnPathDefault)
parser.add_argument('-v', '--videoPath', help="Path to video frame", default=videoPathDefault)
args = parser.parse_args()

# 创建DepthAI管道
pipeline = dai.Pipeline()

# 定义节点：图像处理、目标跟踪、检测网络
manip = pipeline.create(dai.node.ImageManip)
objectTracker = pipeline.create(dai.node.ObjectTracker)
detectionNetwork = pipeline.create(dai.node.MobileNetDetectionNetwork)

# 定义输出节点
manipOut = pipeline.create(dai.node.XLinkOut)
xinFrame = pipeline.create(dai.node.XLinkIn)
trackerOut = pipeline.create(dai.node.XLinkOut)
xlinkOut = pipeline.create(dai.node.XLinkOut)
nnOut = pipeline.create(dai.node.XLinkOut)

# 设置输出流的名称
manipOut.setStreamName("manip")
xinFrame.setStreamName("inFrame")
xlinkOut.setStreamName("trackerFrame")
trackerOut.setStreamName("tracklets")
nnOut.setStreamName("nn")

# 设置输入帧的最大数据大小
xinFrame.setMaxDataSize(1920*1080*3)

# 配置图像处理节点
manip.initialConfig.setResizeThumbnail(544, 320)
manip.initialConfig.setFrameType(dai.ImgFrame.Type.BGR888p)
manip.inputImage.setBlocking(True)

# 配置检测网络节点
detectionNetwork.setBlobPath(blobconverter.from_zoo(name='mobilenet-ssd', shaves=6))
detectionNetwork.setConfidenceThreshold(0.5)
detectionNetwork.input.setBlocking(True)

# 配置目标跟踪节点
objectTracker.inputTrackerFrame.setBlocking(True)
objectTracker.inputDetectionFrame.setBlocking(True)
objectTracker.inputDetections.setBlocking(True)
objectTracker.setDetectionLabelsToTrack([1])  # 只跟踪"person"类别
objectTracker.setTrackerType(dai.TrackerType.ZERO_TERM_COLOR_HISTOGRAM)  # 设置跟踪类型
objectTracker.setTrackerIdAssignmentPolicy(dai.TrackerIdAssignmentPolicy.SMALLEST_ID)  # 设置ID分配策略

# 链接各个节点
manip.out.link(manipOut.input)
manip.out.link(detectionNetwork.input)
xinFrame.out.link(manip.inputImage)
xinFrame.out.link(objectTracker.inputTrackerFrame)
detectionNetwork.out.link(nnOut.input)
detectionNetwork.out.link(objectTracker.inputDetections)
detectionNetwork.passthrough.link(objectTracker.inputDetectionFrame)
objectTracker.out.link(trackerOut.input)
objectTracker.passthroughTrackerFrame.link(xlinkOut.input)

# 连接并启动管道
with dai.Device(pipeline) as device:

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
    detections = []
    frame = None

    # 将图像转换为Planar格式
    def to_planar(arr: np.ndarray, shape: tuple) -> np.ndarray:
        return cv2.resize(arr, shape).transpose(2, 0, 1).flatten()

    # 归一化边界框坐标
    def frameNorm(frame, bbox):
        normVals = np.full(len(bbox), frame.shape[0])
        normVals[::2] = frame.shape[1]
        return (np.clip(np.array(bbox), 0, 1) * normVals).astype(int)

    # 在帧上显示检测结果
    def displayFrame(name, frame):
        for detection in detections:
            bbox = frameNorm(frame, (detection.xmin, detection.ymin, detection.xmax, detection.ymax))
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (255, 0, 0), 2)
            cv2.putText(frame, labelMap[detection.label], (bbox[0] + 10, bbox[1] + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
            cv2.putText(frame, f"{int(detection.confidence * 100)}%", (bbox[0] + 10, bbox[1] + 40), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
        cv2.imshow(name, frame)

    # 打开视频文件
    cap = cv2.VideoCapture(args.videoPath)
    baseTs = time.monotonic()
    simulatedFps = 30
    inputFrameShape = (1920, 1080)

    # 主循环：逐帧处理视频
    while cap.isOpened():
        read_correctly, frame = cap.read()
        if not read_correctly:
            break

        # 创建DepthAI图像帧并设置属性
        img = dai.ImgFrame()
        img.setType(dai.ImgFrame.Type.BGR888p)
        img.setData(to_planar(frame, inputFrameShape))
        img.setTimestamp(baseTs)
        baseTs += 1/simulatedFps

        img.setWidth(inputFrameShape[0])
        img.setHeight(inputFrameShape[1])
        qIn.send(img)  # 发送图像帧到输入队列

        # 获取跟踪帧
        trackFrame = trackerFrameQ.tryGet()
        if trackFrame is None:
            continue

        # 获取跟踪结果和检测结果
        track = tracklets.get()
        manip = qManip.get()
        inDet = qDet.get()

        # 计算FPS
        counter+=1
        current_time = time.monotonic()
        if (current_time - startTime) > 1 :
            fps = counter / (current_time - startTime)
            counter = 0
            startTime = current_time

        # 更新检测结果
        detections = inDet.detections
        manipFrame = manip.getCvFrame()
        displayFrame("nn", manipFrame)

        # 在跟踪帧上绘制跟踪结果
        color = (255, 0, 0)
        trackerFrame = trackFrame.getCvFrame()
        trackletsData = track.tracklets
        for t in trackletsData:
            roi = t.roi.denormalize(trackerFrame.shape[1], trackerFrame.shape[0])
            x1 = int(roi.topLeft().x)
            y1 = int(roi.topLeft().y)
            x2 = int(roi.bottomRight().x)
            y2 = int(roi.bottomRight().y)

            try:
                label = labelMap[t.label]
            except:
                label = t.label

            cv2.putText(trackerFrame, str(label), (x1 + 10, y1 + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
            cv2.putText(trackerFrame, f"ID: {[t.id]}", (x1 + 10, y1 + 35), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
            cv2.putText(trackerFrame, t.status.name, (x1 + 10, y1 + 50), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)
            cv2.rectangle(trackerFrame, (x1, y1), (x2, y2), color, cv2.FONT_HERSHEY_SIMPLEX)

        # 显示FPS
        cv2.putText(trackerFrame, "Fps: {:.2f}".format(fps), (2, trackerFrame.shape[0] - 4), cv2.FONT_HERSHEY_TRIPLEX, 0.4, color)

        # 显示跟踪帧
        cv2.imshow("tracker", trackerFrame)

        # 按下'q'键退出
        if cv2.waitKey(1) == ord('q'):
            break