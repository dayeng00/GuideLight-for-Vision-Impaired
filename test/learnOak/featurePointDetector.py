"""
此代码用于进行实现目标追踪的特征点查找
"""
"""
**角点检测**（Corner Detection）是计算机视觉中用于检测图像中具有显著变化的点的技术，
这些点通常是图像中变化最剧烈的地方，比如物体的边缘或纹理的交点。
角点检测是特征检测中的一个重要步骤，经常用于图像匹配、跟踪、立体视觉、三维重建等应用。

在代码中使用了两种经典的角点检测方法：**Harris角点检测** 和 **Shi-Thomasi角点检测**。
下面分别介绍这两种方法及其区别。

### 1. Harris 角点检测 (Harris Corner Detection)

**Harris角点检测**是由 Chris Harris 和 Mike Stephens 在1988年提出的一种经典的角点检测算法。
它基于图像的局部结构特征，通过计算图像的梯度来识别角点。

#### 原理：
- **梯度计算**：首先，计算图像的水平和垂直方向的梯度，得到图像在每个像素点的梯度信息（即图像亮度变化的程度）。
- **自相关矩阵**：然后，计算图像局部区域的自相关矩阵（Harris矩阵），该矩阵反映了该区域的变化信息。
  - 该矩阵描述了图像在局部区域内的变化模式，它的特征值可以揭示图像的结构：如果特征值较大，说明该点是一个角点。
- **响应函数**：通过计算响应函数（R值），来评估每个点是否是角点。R值大，说明该点是一个角点。

#### Harris 角点的特点：
- **适用于局部变化较大的区域**，能够检测到图像中的“角”或“交点”。
- 对于噪声较为敏感，需要后续的非最大值抑制（Non-maximum Suppression）来精确定位角点。
- 在不同的尺度下表现较差，尤其在图像缩放或者旋转时，鲁棒性较差。

#### 优缺点：
- **优点**：计算简单，易于实现，效果较好。
- **缺点**：对噪声敏感，角点定位不够精确，对尺度变化和旋转不够鲁棒。

### 2. Shi-Tomasi 角点检测 (Shi-Tomasi Corner Detection)

**Shi-Tomasi角点检测**是由 **Jianbo Shi** 和 **C. Tomasi** 提出的，
作为 Harris 角点检测的改进版。它实际上是 Harris 角点检测方法的一个简化和优化版本，
特别在计算复杂度和角点选择的准确度上进行了改进。

#### 原理：
- **自相关矩阵**：与 Harris 角点检测类似，Shi-Tomasi 角点检测也利用自相关矩阵来描述图像区域的变化。
- **最小特征值**：Shi-Tomasi 方法主要是基于自相关矩阵的 **最小特征值** 来判断角点。
  - 如果最小特征值较大，说明该区域具有较强的角点特征。
  - Harris方法使用的是自相关矩阵的两个特征值（最大的两个特征值），而 Shi-Tomasi 方法只用最小的特征值来判断，这让它对角点检测的响应更加准确。
- **角点响应函数**：如果最小特征值大于某个阈值，该点被认为是角点。

#### Shi-Tomasi 角点的特点：
- **更加鲁棒**：与 Harris 方法相比，Shi-Tomasi 方法在实际应用中通常会检测到更可靠、更精确的角点，尤其是在纹理较弱的区域。
- **改进的响应函数**：由于使用了最小特征值，Shi-Tomasi 方法比 Harris 更加灵敏，能够更好地区分图像中的角点。
- **自适应性强**：相较于 Harris 方法，Shi-Tomasi 在不同的图像内容、噪声环境下更为稳定。

#### 优缺点：
- **优点**：比 Harris 方法更加准确，尤其是在复杂和弱纹理的图像中。
- **缺点**：计算复杂度稍高，速度较慢（虽然一般也足够高效）。

### 3. Harris 和 Shi-Tomasi 的区别

| 特性                        | Harris 角点检测                      | Shi-Tomasi 角点检测                  |
|-----------------------------|--------------------------------------|-------------------------------------|
| **计算基础**                | 基于自相关矩阵的两个特征值         | 基于自相关矩阵的最小特征值         |
| **角点检测的灵敏度**         | 对于某些场景，可能漏检一些角点      | 更加鲁棒，检测的角点更加精确       |
| **对噪声的敏感性**           | 对噪声较为敏感，需要后续抑制       | 更加鲁棒，对噪声的容忍度较高       |
| **计算复杂度**               | 相对较低                             | 较高（计算最小特征值和响应函数） |
| **旋转和尺度不变性**         | 不具备尺度和旋转不变性              | 不具备尺度不变性，但在旋转上更稳定|
| **实现难度**                 | 简单，易于实现                      | 稍微复杂一些                         |
| **应用场景**                 | 在纹理丰富、噪声较少的图像中表现较好| 在图像内容复杂、纹理较弱的场景中表现更好 |

### 总结：
- **Harris角点检测**：适用于图像中明显的角点，计算简单，但对噪声敏感，且对旋转和尺度变化不够鲁棒。
- **Shi-Tomasi角点检测**：是 Harris 方法的改进版，能更精确地识别角点，
并且在大多数情况下比 Harris 方法更加鲁棒，特别是对于噪声较多或纹理较弱的图像。

在代码中通过按 's' 键来切换这两种方法，这让你可以根据实际应用场景选择最合适的角点检测算法。
"""
# !/usr/bin/env python3


import cv2
import depthai as dai

# 创建Pipeline（数据流管道）
pipeline = dai.Pipeline()

# 定义输入源和输出
monoLeft = pipeline.create(dai.node.MonoCamera)  # 创建左侧单目相机节点
monoRight = pipeline.create(dai.node.MonoCamera)  # 创建右侧单目相机节点
featureTrackerLeft = pipeline.create(dai.node.FeatureTracker)  # 创建左侧特征跟踪节点
featureTrackerRight = pipeline.create(dai.node.FeatureTracker)  # 创建右侧特征跟踪节点

# 创建输出节点，分别用于输出不同的数据流
xoutPassthroughFrameLeft = pipeline.create(dai.node.XLinkOut)  # 左侧相机输出节点
xoutTrackedFeaturesLeft = pipeline.create(dai.node.XLinkOut)  # 左侧跟踪特征输出节点
xoutPassthroughFrameRight = pipeline.create(dai.node.XLinkOut)  # 右侧相机输出节点
xoutTrackedFeaturesRight = pipeline.create(dai.node.XLinkOut)  # 右侧跟踪特征输出节点
xinTrackedFeaturesConfig = pipeline.create(dai.node.XLinkIn)  # 配置输入节点（用于改变特征跟踪设置）

# 设置输出节点的流名称
xoutPassthroughFrameLeft.setStreamName("passthroughFrameLeft")
xoutTrackedFeaturesLeft.setStreamName("trackedFeaturesLeft")
xoutPassthroughFrameRight.setStreamName("passthroughFrameRight")
xoutTrackedFeaturesRight.setStreamName("trackedFeaturesRight")
xinTrackedFeaturesConfig.setStreamName("trackedFeaturesConfig")

# 配置相机属性
monoLeft.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)  # 设置左侧单目相机分辨率为400P
monoLeft.setBoardSocket(dai.CameraBoardSocket.LEFT)  # 设置相机为左侧相机
monoRight.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)  # 设置右侧单目相机分辨率为400P
monoRight.setBoardSocket(dai.CameraBoardSocket.RIGHT)  # 设置相机为右侧相机

# 禁用光流估算（默认为禁用，防止光流干扰）
featureTrackerLeft.initialConfig.setMotionEstimator(False)
featureTrackerRight.initialConfig.setMotionEstimator(False)

# 设置节点之间的链接
monoLeft.out.link(featureTrackerLeft.inputImage)  # 将左侧相机的输出连接到左侧特征跟踪的输入
featureTrackerLeft.passthroughInputImage.link(xoutPassthroughFrameLeft.input)  # 将左侧特征跟踪的输入图像传递给输出
featureTrackerLeft.outputFeatures.link(xoutTrackedFeaturesLeft.input)  # 将左侧跟踪到的特征传递给输出
xinTrackedFeaturesConfig.out.link(featureTrackerLeft.inputConfig)  # 配置输入连接到左侧特征跟踪

monoRight.out.link(featureTrackerRight.inputImage)  # 将右侧相机的输出连接到右侧特征跟踪的输入
featureTrackerRight.passthroughInputImage.link(xoutPassthroughFrameRight.input)  # 将右侧特征跟踪的输入图像传递给输出
featureTrackerRight.outputFeatures.link(xoutTrackedFeaturesRight.input)  # 将右侧跟踪到的特征传递给输出
xinTrackedFeaturesConfig.out.link(featureTrackerRight.inputConfig)  # 配置输入连接到右侧特征跟踪

# 获取当前特征跟踪配置（可以用来修改配置）
featureTrackerConfig = featureTrackerRight.initialConfig.get()

print("Press 's' to switch between Harris and Shi-Thomasi corner detector!")  # 提示用户可以通过按's'键切换检测方法

# 连接设备并启动数据流管道
with dai.Device(pipeline) as device:
    # 获取输出队列，用于接收处理后的结果
    passthroughImageLeftQueue = device.getOutputQueue("passthroughFrameLeft", 8, False)  # 获取左侧相机的传递图像队列
    outputFeaturesLeftQueue = device.getOutputQueue("trackedFeaturesLeft", 8, False)  # 获取左侧特征跟踪的输出队列
    passthroughImageRightQueue = device.getOutputQueue("passthroughFrameRight", 8, False)  # 获取右侧相机的传递图像队列
    outputFeaturesRightQueue = device.getOutputQueue("trackedFeaturesRight", 8, False)  # 获取右侧特征跟踪的输出队列

    inputFeatureTrackerConfigQueue = device.getInputQueue("trackedFeaturesConfig")  # 获取特征跟踪配置输入队列

    # 设置显示窗口的名称
    leftWindowName = "left"
    rightWindowName = "right"


    # 用于绘制跟踪特征的函数
    def drawFeatures(frame, features):
        pointColor = (0, 0, 255)  # 特征点的颜色（红色）
        circleRadius = 2  # 特征点的圆形半径
        for feature in features:
            # 在图像中绘制特征点
            cv2.circle(frame, (int(feature.position.x), int(feature.position.y)), circleRadius, pointColor, -1,
                       cv2.LINE_AA, 0)


    while True:
        # 获取左侧相机的传递帧
        inPassthroughFrameLeft = passthroughImageLeftQueue.get()
        passthroughFrameLeft = inPassthroughFrameLeft.getFrame()
        leftFrame = cv2.cvtColor(passthroughFrameLeft, cv2.COLOR_GRAY2BGR)  # 转换为BGR图像，以便显示

        # 获取右侧相机的传递帧
        inPassthroughFrameRight = passthroughImageRightQueue.get()
        passthroughFrameRight = inPassthroughFrameRight.getFrame()
        rightFrame = cv2.cvtColor(passthroughFrameRight, cv2.COLOR_GRAY2BGR)  # 转换为BGR图像，以便显示

        # 获取左侧跟踪到的特征点
        trackedFeaturesLeft = outputFeaturesLeftQueue.get().trackedFeatures
        # 在左侧图像中绘制特征点
        drawFeatures(leftFrame, trackedFeaturesLeft)

        # 获取右侧跟踪到的特征点
        trackedFeaturesRight = outputFeaturesRightQueue.get().trackedFeatures
        # 在右侧图像中绘制特征点
        drawFeatures(rightFrame, trackedFeaturesRight)

        # 显示左右图像
        cv2.imshow(leftWindowName, leftFrame)
        cv2.imshow(rightWindowName, rightFrame)

        key = cv2.waitKey(1)  # 获取按键
        if key == ord('q'):  # 按'q'退出程序
            break
        elif key == ord('s'):  # 按's'切换特征检测方法
            if featureTrackerConfig.cornerDetector.type == dai.FeatureTrackerConfig.CornerDetector.Type.HARRIS:
                featureTrackerConfig.cornerDetector.type = dai.FeatureTrackerConfig.CornerDetector.Type.SHI_THOMASI  # 切换到Shi-Thomasi角点检测
                print("Switching to Shi-Thomasi")
            else:
                featureTrackerConfig.cornerDetector.type = dai.FeatureTrackerConfig.CornerDetector.Type.HARRIS  # 切换到Harris角点检测
                print("Switching to Harris")

            # 发送更新后的特征跟踪配置
            cfg = dai.FeatureTrackerConfig()
            cfg.set(featureTrackerConfig)
            inputFeatureTrackerConfigQueue.send(cfg)  # 更新特征跟踪配置
