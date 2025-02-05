"""
此代码演示了双目视差和深度估计
"""
#!/usr/bin/env python3

import cv2  # 导入OpenCV库，用于图像处理和显示
import depthai as dai  # 导入DepthAI库，用于与OAK设备的通信和控制
import numpy as np  # 导入NumPy库，用于数值计算和数组操作

# 配置深度图生成的参数
extended_disparity = False  # 是否启用扩展视差范围，False表示不启用
subpixel = False  # 是否启用子像素精度，False表示不启用
lr_check = True  # 是否启用左右视差检查，True表示启用，用于处理遮挡问题

# 创建DepthAI的管道（Pipeline），用于定义数据处理流程
pipeline = dai.Pipeline()

# 定义单目摄像头节点和深度图节点
monoLeft = pipeline.create(dai.node.MonoCamera)  # 创建左单目摄像头节点
monoRight = pipeline.create(dai.node.MonoCamera)  # 创建右单目摄像头节点
depth = pipeline.create(dai.node.StereoDepth)  # 创建深度图节点
xout = pipeline.create(dai.node.XLinkOut)  # 创建输出节点，用于将数据传输到主机

xout.setStreamName("disparity")  # 设置输出流的名称

# 配置左、右单目摄像头的属性
monoLeft.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)  # 设置左摄像头分辨率为400P
monoLeft.setBoardSocket(dai.CameraBoardSocket.LEFT)  # 设置左摄像头的标识
monoRight.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)  # 设置右摄像头分辨率为400P
monoRight.setBoardSocket(dai.CameraBoardSocket.RIGHT)  # 设置右摄像头的标识

# 配置深度图节点的属性
depth.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_DENSITY)  # 设置深度图生成模式为高密度
# 设置中值滤波器，选项包括：MEDIAN_OFF, KERNEL_3x3, KERNEL_5x5, KERNEL_7x7（默认）
depth.initialConfig.setMedianFilter(dai.MedianFilter.KERNEL_7x7)
depth.setLeftRightCheck(lr_check)  # 设置是否启用左右视差检查
depth.setExtendedDisparity(extended_disparity)  # 设置是否启用扩展视差范围
depth.setSubpixel(subpixel)  # 设置是否启用子像素精度

# 将左、右摄像头的输出连接到深度图节点的输入
monoLeft.out.link(depth.left)  # 左摄像头输出连接到深度图节点的左输入
monoRight.out.link(depth.right)  # 右摄像头输出连接到深度图节点的右输入
depth.disparity.link(xout.input)  # 深度图节点的视差输出连接到输出节点的输入

# 连接到设备并启动管道
with dai.Device(pipeline) as device:

    # 获取输出队列，用于从设备获取视差图数据
    q = device.getOutputQueue(name="disparity", maxSize=4, blocking=False)

    while True:
        inDisparity = q.get()  # 从队列中获取视差图数据，阻塞调用，直到有新数据到达
        frame = inDisparity.getFrame()  # 获取视差图的帧数据
        # 对帧数据进行归一化处理，以便更好地显示
        frame = (frame * (255 / depth.initialConfig.getMaxDisparity())).astype(np.uint8)

        cv2.imshow("disparity", frame)  # 显示原始的视差图

        # 使用颜色映射增强视差图的可视化效果
        # 可用的颜色映射选项：https://docs.opencv.org/3.4/d3/d50/group__imgproc__colormap.html
        frame = cv2.applyColorMap(frame, cv2.COLORMAP_JET)  # 应用JET颜色映射
        cv2.imshow("disparity_color", frame)  # 显示带有颜色映射的视差图

        if cv2.waitKey(1) == ord('q'):  # 按下'q'键退出循环
            break