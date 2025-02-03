"""
这段代码使用 DepthAI 库进行双目相机图像的特征追踪，
能够通过 FeatureTracker 节点追踪图像中的特征点，
并通过不同的运动估计方法（如 Lucas-Kanade 光流法 和硬件加速的运动估计）进行处理。
最终在图像上绘制特征点路径，并支持用户通过界面进行交互控制，选择特征追踪的持续帧数和估算方法。
"""
# !/usr/bin/env python3

import cv2
import depthai as dai
from collections import deque


# FeatureTrackerDrawer 类用于绘制和管理特征点的轨迹
class FeatureTrackerDrawer:
    # 设置绘制参数
    lineColor = (200, 0, 200)  # 轨迹线的颜色（紫色）
    pointColor = (0, 0, 255)   # 特征点的颜色（红色）
    circleRadius = 2           # 特征点的圆半径
    maxTrackedFeaturesPathLength = 30   # 最大的追踪路径长度
    # for how many frames the feature is tracked
    trackedFeaturesPathLength = 10      # 默认的特征点追踪路径长度（由滑动条控制）

    # 初始化一些参数
    trackedIDs = None           # 当前被追踪的特征点 ID 集合
    trackedFeaturesPath = None  # 存储每个特征点追踪路径的字典

    def onTrackBar(self, val):
        # 滑动条回调函数，用于动态调整特征点的追踪路径长度
        FeatureTrackerDrawer.trackedFeaturesPathLength = val
        pass

    def trackFeaturePath(self, features):
        # 更新特征点的路径
        newTrackedIDs = set()
        for currentFeature in features:
            currentID = currentFeature.id
            newTrackedIDs.add(currentID)

            # 如果该特征点第一次出现，初始化路径
            if currentID not in self.trackedFeaturesPath:
                self.trackedFeaturesPath[currentID] = deque()

            path = self.trackedFeaturesPath[currentID]

            # 添加当前特征点的位置到路径
            path.append(currentFeature.position)
            while (len(path) > max(1, FeatureTrackerDrawer.trackedFeaturesPathLength)):
                path.popleft()

            self.trackedFeaturesPath[currentID] = path

        # 移除不再被追踪的特征点
        featuresToRemove = set()
        for oldId in self.trackedIDs:
            if oldId not in newTrackedIDs:
                featuresToRemove.add(oldId)

        for id in featuresToRemove:
            self.trackedFeaturesPath.pop(id)

        self.trackedIDs = newTrackedIDs

    # 绘制特征点和它们的路径
    def drawFeatures(self, img):

        cv2.setTrackbarPos(self.trackbarName, self.windowName, FeatureTrackerDrawer.trackedFeaturesPathLength)

        for featurePath in self.trackedFeaturesPath.values():
            path = featurePath

            # 绘制特征点路径
            for j in range(len(path) - 1):
                src = (int(path[j].x), int(path[j].y))
                dst = (int(path[j + 1].x), int(path[j + 1].y))
                cv2.line(img, src, dst, self.lineColor, 1, cv2.LINE_AA, 0)

            # 绘制特征点
            j = len(path) - 1
            cv2.circle(img, (int(path[j].x), int(path[j].y)), self.circleRadius, self.pointColor, -1, cv2.LINE_AA, 0)

    # 初始化特征追踪绘制器
    def __init__(self, trackbarName, windowName):
        self.trackbarName = trackbarName
        self.windowName = windowName
        cv2.namedWindow(windowName)  # 创建窗口
        cv2.createTrackbar(trackbarName, windowName, FeatureTrackerDrawer.trackedFeaturesPathLength,
                           FeatureTrackerDrawer.maxTrackedFeaturesPathLength, self.onTrackBar)
        self.trackedIDs = set()      # 存储追踪的特征点 ID
        self.trackedFeaturesPath = dict()  # 存储特征点路径（字典格式）


# 创建 DepthAI 管道（pipeline）
pipeline = dai.Pipeline()

# 定义源节点和输出节点
monoLeft = pipeline.create(dai.node.MonoCamera)
monoRight = pipeline.create(dai.node.MonoCamera)
featureTrackerLeft = pipeline.create(dai.node.FeatureTracker)
featureTrackerRight = pipeline.create(dai.node.FeatureTracker)

# 创建 XLink 输出节点，用于发送帧和追踪结果
xoutPassthroughFrameLeft = pipeline.create(dai.node.XLinkOut)
xoutTrackedFeaturesLeft = pipeline.create(dai.node.XLinkOut)
xoutPassthroughFrameRight = pipeline.create(dai.node.XLinkOut)
xoutTrackedFeaturesRight = pipeline.create(dai.node.XLinkOut)
xinTrackedFeaturesConfig = pipeline.create(dai.node.XLinkIn)

# 设置输出流的名称
xoutPassthroughFrameLeft.setStreamName("passthroughFrameLeft")
xoutTrackedFeaturesLeft.setStreamName("trackedFeaturesLeft")
xoutPassthroughFrameRight.setStreamName("passthroughFrameRight")
xoutTrackedFeaturesRight.setStreamName("trackedFeaturesRight")
xinTrackedFeaturesConfig.setStreamName("trackedFeaturesConfig")

# 设置相机分辨率
monoLeft.setResolution(dai.MonoCameraProperties.SensorResolution.THE_720_P)
monoLeft.setBoardSocket(dai.CameraBoardSocket.LEFT)
monoRight.setResolution(dai.MonoCameraProperties.SensorResolution.THE_720_P)
monoRight.setBoardSocket(dai.CameraBoardSocket.RIGHT)

# 连接各个节点
monoLeft.out.link(featureTrackerLeft.inputImage)
featureTrackerLeft.passthroughInputImage.link(xoutPassthroughFrameLeft.input)
featureTrackerLeft.outputFeatures.link(xoutTrackedFeaturesLeft.input)
xinTrackedFeaturesConfig.out.link(featureTrackerLeft.inputConfig)

monoRight.out.link(featureTrackerRight.inputImage)
featureTrackerRight.passthroughInputImage.link(xoutPassthroughFrameRight.input)
featureTrackerRight.outputFeatures.link(xoutTrackedFeaturesRight.input)
xinTrackedFeaturesConfig.out.link(featureTrackerRight.inputConfig)

# 配置硬件资源
# By default the least mount of resources are allocated
# increasing it improves performance
numShaves = 2
numMemorySlices = 2
featureTrackerLeft.setHardwareResources(numShaves, numMemorySlices)
featureTrackerRight.setHardwareResources(numShaves, numMemorySlices)

# 获取当前的配置
featureTrackerConfig = featureTrackerRight.initialConfig.get()
print("Press 's' to switch between Lucas-Kanade optical flow and hardware accelerated motion estimation!")

# 连接设备并启动管道
with dai.Device(pipeline) as device:
    # 获取输出队列
    passthroughImageLeftQueue = device.getOutputQueue("passthroughFrameLeft", 8, False)
    outputFeaturesLeftQueue = device.getOutputQueue("trackedFeaturesLeft", 8, False)
    passthroughImageRightQueue = device.getOutputQueue("passthroughFrameRight", 8, False)
    outputFeaturesRightQueue = device.getOutputQueue("trackedFeaturesRight", 8, False)

    inputFeatureTrackerConfigQueue = device.getInputQueue("trackedFeaturesConfig")

    # 创建显示窗口和特征绘制器
    leftWindowName = "left"
    leftFeatureDrawer = FeatureTrackerDrawer("Feature tracking duration (frames)", leftWindowName)

    rightWindowName = "right"
    rightFeatureDrawer = FeatureTrackerDrawer("Feature tracking duration (frames)", rightWindowName)

    # 循环处理图像帧
    while True:
        # 获取左侧图像和右侧图像
        inPassthroughFrameLeft = passthroughImageLeftQueue.get()
        passthroughFrameLeft = inPassthroughFrameLeft.getFrame()
        leftFrame = cv2.cvtColor(passthroughFrameLeft, cv2.COLOR_GRAY2BGR)

        inPassthroughFrameRight = passthroughImageRightQueue.get()
        passthroughFrameRight = inPassthroughFrameRight.getFrame()
        rightFrame = cv2.cvtColor(passthroughFrameRight, cv2.COLOR_GRAY2BGR)

        # 获取并绘制左侧和右侧图像中的特征点
        trackedFeaturesLeft = outputFeaturesLeftQueue.get().trackedFeatures
        leftFeatureDrawer.trackFeaturePath(trackedFeaturesLeft)
        leftFeatureDrawer.drawFeatures(leftFrame)

        trackedFeaturesRight = outputFeaturesRightQueue.get().trackedFeatures
        rightFeatureDrawer.trackFeaturePath(trackedFeaturesRight)
        rightFeatureDrawer.drawFeatures(rightFrame)

        # 显示图像
        cv2.imshow(leftWindowName, leftFrame)
        cv2.imshow(rightWindowName, rightFrame)

        # 按键控制
        key = cv2.waitKey(1)
        if key == ord('q'):
            break
        elif key == ord('s'):
            # 切换运动估算方法（光流 vs 硬件加速）
            if featureTrackerConfig.motionEstimator.type == dai.FeatureTrackerConfig.MotionEstimator.Type.LUCAS_KANADE_OPTICAL_FLOW:
                featureTrackerConfig.motionEstimator.type = dai.FeatureTrackerConfig.MotionEstimator.Type.HW_MOTION_ESTIMATION
                print("Switching to hardware accelerated motion estimation")
            else:
                featureTrackerConfig.motionEstimator.type = dai.FeatureTrackerConfig.MotionEstimator.Type.LUCAS_KANADE_OPTICAL_FLOW
                print("Switching to Lucas-Kanade optical flow")

            cfg = dai.FeatureTrackerConfig()
            cfg.set(featureTrackerConfig)
            inputFeatureTrackerConfigQueue.send(cfg)
