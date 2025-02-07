"""
这段代码使用DepthAI库和OpenVINO模型实现了视频中的人物检测与跟踪。
它通过加载预训练的MobileNet SSD模型来检测视频帧中的人物，
并使用ObjectTracker节点对检测到的人物进行跟踪。
最终，代码会在视频帧上绘制检测框、标签、置信度和跟踪ID，并显示处理后的视频帧。
用户可以通过按下'q'键退出程序。
"""
#!/usr/bin/env python3

# 导入必要的库
from pathlib import Path  # 用于处理文件路径
import blobconverter  # 用于从OpenVINO模型库中下载和转换模型
import cv2  # OpenCV库，用于图像处理和显示
import depthai as dai  # DepthAI库，用于与DepthAI设备通信
import numpy as np  # NumPy库，用于数值计算
import time  # 用于时间相关操作
import argparse  # 用于解析命令行参数

# 定义标签映射，这里只检测"person"类别
labelMap = ["person", ""]

# 设置默认的神经网络模型路径和视频路径
nnPathDefault = str((Path(__file__).parent / Path(blobconverter.from_zoo(name='person-detection-retail-0013', shaves=7))).resolve().absolute())
videoPathDefault = str((Path(__file__).parent / Path(
    '../main/resources/learn_YOLO/video/football.mp4')).resolve().absolute())

# 解析命令行参数
parser = argparse.ArgumentParser()
parser.add_argument('-nnPath', help="Path to mobilenet detection network blob", default=nnPathDefault)
parser.add_argument('-v', '--videoPath', help="Path to video frame", default=videoPathDefault)
args = parser.parse_args()

# 创建DepthAI管道
pipeline = dai.Pipeline()

# 定义节点：图像处理、目标跟踪、检测网络
manip = pipeline.create(dai.node.ImageManip)  # 图像处理节点，用于调整图像大小和格式
objectTracker = pipeline.create(dai.node.ObjectTracker)  # 目标跟踪节点，用于跟踪检测到的对象
detectionNetwork = pipeline.create(dai.node.MobileNetDetectionNetwork)  # 检测网络节点，用于运行MobileNet SSD模型

# 定义输出节点
manipOut = pipeline.create(dai.node.XLinkOut)  # 图像处理输出节点
xinFrame = pipeline.create(dai.node.XLinkIn)  # 输入帧节点
trackerOut = pipeline.create(dai.node.XLinkOut)  # 跟踪结果输出节点
xlinkOut = pipeline.create(dai.node.XLinkOut)  # 跟踪帧输出节点
nnOut = pipeline.create(dai.node.XLinkOut)  # 检测结果输出节点

# 设置输出流的名称
manipOut.setStreamName("manip")  # 图像处理输出流的名称
xinFrame.setStreamName("inFrame")  # 输入帧流的名称
xlinkOut.setStreamName("trackerFrame")  # 跟踪帧输出流的名称
trackerOut.setStreamName("tracklets")  # 跟踪结果输出流的名称
nnOut.setStreamName("nn")  # 检测结果输出流的名称

# 设置输入帧的最大数据大小
xinFrame.setMaxDataSize(720*720*3)  # 设置输入帧的最大数据大小

# 配置图像处理节点
manip.initialConfig.setResizeThumbnail(544, 320)  # 设置图像缩放到544x320分辨率
# manip.initialConfig.setResize(384, 384)
# 设置图像处理节点的输出分辨率为 384x384 像素。

manip.initialConfig.setKeepAspectRatio(False)  # squash the image to not lose FOV
# 设置图像处理节点在调整大小时不保持宽高比。
# 如果设置为 False，图像会被拉伸或压缩以适应目标分辨率（384x384），这可能会导致图像变形。
# 注释中提到 "squash the image to not lose FOV"，意思是拉伸图像以避免丢失视野（Field of View, FOV）。

# The NN model expects BGR input. By default ImageManip output type would be same as input (gray in this case)
# 神经网络模型期望输入图像为 BGR 格式。
# 默认情况下，ImageManip 节点的输出类型与输入类型相同（如果输入是灰度图像，则输出也是灰度图像）。
# 因此，需要显式设置输出图像格式为 BGR，以满足神经网络模型的输入要求。
manip.initialConfig.setFrameType(dai.ImgFrame.Type.BGR888p)  # 设置输出图像格式为BGR
manip.inputImage.setBlocking(True)  # 设置输入图像为阻塞模式，确保按顺序处理

# 配置检测网络节点
detectionNetwork.setBlobPath(args.nnPath)  # 设置模型路径
detectionNetwork.setConfidenceThreshold(0.5)  # 设置置信度阈值，过滤低置信度的检测结果
detectionNetwork.input.setBlocking(True)  # 设置输入为阻塞模式

# 配置目标跟踪节点
objectTracker.inputTrackerFrame.setBlocking(True)  # 设置跟踪帧输入为阻塞模式
objectTracker.inputDetectionFrame.setBlocking(True)  # 设置检测帧输入为阻塞模式
objectTracker.inputDetections.setBlocking(True)  # 设置检测结果输入为阻塞模式
objectTracker.setDetectionLabelsToTrack([1])  # 只跟踪"person"类别（标签为1）
# possible tracking types: ZERO_TERM_COLOR_HISTOGRAM, ZERO_TERM_IMAGELESS, SHORT_TERM_IMAGELESS, SHORT_TERM_KCF
objectTracker.setTrackerType(dai.TrackerType.ZERO_TERM_COLOR_HISTOGRAM)  # 设置跟踪算法类型
# take the smallest ID when new object is tracked, possible options: SMALLEST_ID, UNIQUE_ID
objectTracker.setTrackerIdAssignmentPolicy(dai.TrackerIdAssignmentPolicy.SMALLEST_ID)  # 设置ID分配策略

# 链接各个节点
manip.out.link(manipOut.input)  # 将图像处理输出连接到图像处理输出节点
manip.out.link(detectionNetwork.input)  # 将图像处理输出连接到检测网络输入
xinFrame.out.link(manip.inputImage)  # 将输入帧连接到图像处理节点
xinFrame.out.link(objectTracker.inputTrackerFrame)  # 将输入帧连接到跟踪器的跟踪帧输入
detectionNetwork.out.link(nnOut.input)  # 将检测网络输出连接到检测结果输出节点
detectionNetwork.out.link(objectTracker.inputDetections)  # 将检测网络输出连接到跟踪器的检测结果输入
detectionNetwork.passthrough.link(objectTracker.inputDetectionFrame)  # 将检测网络的直通帧连接到跟踪器的检测帧输入
objectTracker.out.link(trackerOut.input)  # 将跟踪器输出连接到跟踪结果输出节点
objectTracker.passthroughTrackerFrame.link(xlinkOut.input)  # 将跟踪器的直通帧连接到跟踪帧输出节点

# 连接并启动管道
with dai.Device(pipeline) as device:

    # 获取输入和输出队列
    qIn = device.getInputQueue(name="inFrame")  # 获取输入帧队列
    trackerFrameQ = device.getOutputQueue(name="trackerFrame", maxSize=4)  # 获取跟踪帧队列
    tracklets = device.getOutputQueue(name="tracklets", maxSize=4)  # 获取跟踪结果队列
    qManip = device.getOutputQueue(name="manip", maxSize=4)  # 获取图像处理输出队列
    qDet = device.getOutputQueue(name="nn", maxSize=4)  # 获取检测结果队列

    # 初始化变量
    startTime = time.monotonic()  # 记录开始时间
    counter = 0  # 帧计数器
    fps = 0  # 帧率
    detections = []  # 存储检测结果
    frame = None  # 存储当前帧

    # 将图像转换为Planar格式
    def to_planar(arr: np.ndarray, shape: tuple) -> np.ndarray:
        return cv2.resize(arr, shape).transpose(2, 0, 1).flatten()  # 调整图像大小并转换为Planar格式

    # 归一化边界框坐标
    # nn data, being the bounding box locations, are in <0..1> range - they need to be normalized with frame width/height
    def frameNorm(frame, bbox):
        normVals = np.full(len(bbox), frame.shape[0])  # 归一化边界框坐标
        normVals[::2] = frame.shape[1]
        return (np.clip(np.array(bbox), 0, 1) * normVals).astype(int)

    # 在帧上显示检测结果
    def displayFrame(name, frame):
        for detection in detections:
            bbox = frameNorm(frame, (detection.xmin, detection.ymin, detection.xmax, detection.ymax))  # 归一化边界框
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (255, 0, 0), 2)  # 绘制边界框
            cv2.putText(frame, labelMap[detection.label], (bbox[0] + 10, bbox[1] + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)  # 绘制标签
            cv2.putText(frame, f"{int(detection.confidence * 100)}%", (bbox[0] + 10, bbox[1] + 40), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)  # 绘制置信度
        cv2.imshow(name, frame)  # 显示帧

    # 打开视频文件
    cap = cv2.VideoCapture(args.videoPath)
    baseTs = time.monotonic()  # 记录基准时间
    simulatedFps = 30  # 模拟帧率
    inputFrameShape = (720, 720)  # 输入帧的分辨率

    # 主循环：逐帧处理视频
    while cap.isOpened():
        read_correctly, frame = cap.read()  # 读取视频帧
        if not read_correctly:
            break

        # 创建DepthAI图像帧并设置属性
        img = dai.ImgFrame()
        img.setType(dai.ImgFrame.Type.BGR888p)  # 设置图像格式为BGR
        img.setData(to_planar(frame, inputFrameShape))  # 设置图像数据
        img.setTimestamp(baseTs)  # 设置时间戳
        baseTs += 1/simulatedFps  # 更新时间戳

        img.setWidth(inputFrameShape[0])  # 设置图像宽度
        img.setHeight(inputFrameShape[1])  # 设置图像高度
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
            roi = t.roi.denormalize(trackerFrame.shape[1], trackerFrame.shape[0])  # 反归一化ROI
            x1 = int(roi.topLeft().x)
            y1 = int(roi.topLeft().y)
            x2 = int(roi.bottomRight().x)
            y2 = int(roi.bottomRight().y)

            try:
                label = labelMap[t.label]  # 获取标签
            except:
                label = t.label

            cv2.putText(trackerFrame, str(label), (x1 + 10, y1 + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)  # 绘制标签
            cv2.putText(trackerFrame, f"ID: {[t.id]}", (x1 + 10, y1 + 35), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)  # 绘制ID
            cv2.putText(trackerFrame, t.status.name, (x1 + 10, y1 + 50), cv2.FONT_HERSHEY_TRIPLEX, 0.5, 255)  # 绘制状态
            cv2.rectangle(trackerFrame, (x1, y1), (x2, y2), color, cv2.FONT_HERSHEY_SIMPLEX)  # 绘制边界框

        # 显示FPS
        cv2.putText(trackerFrame, "Fps: {:.2f}".format(fps), (2, trackerFrame.shape[0] - 4), cv2.FONT_HERSHEY_TRIPLEX, 0.4, color)

        # 显示跟踪帧
        cv2.imshow("tracker", trackerFrame)

        # 按下'q'键退出
        if cv2.waitKey(1) == ord('q'):
            break