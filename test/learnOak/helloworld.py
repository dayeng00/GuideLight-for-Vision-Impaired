"""
此脚本演示了如何使用oakD摄像机的rgb摄像头，并且将捕获的帧交给MoblieNetSSD进行目标检测并且输出含有检测框的帧
"""
# 导入必要的模块
from pathlib import Path

import blobconverter
import cv2
import depthai
import numpy as np

# 创建一个Pipeline对象，它定义了DepthAI设备在运行时要执行的操作
pipeline = depthai.Pipeline()

# 首先，我们需要设置彩色相机作为输出
cam_rgb = pipeline.createColorCamera()
cam_rgb.setPreviewSize(300, 300)  # 设置预览帧的大小为300x300，作为节点的"preview"输出
cam_rgb.setInterleaved(False)  # 不使用交错模式
"""
在相机或视频处理领域，交错模式（Interlaced mode） 是一种视频信号的传输方式。
它将每一帧图像分成两部分（场），其中第一部分包括所有奇数行，第二部分包括所有偶数行。
然后，这两部分交替显示，最终合成完整的图像。
由于现在多数设备已经是逐行扫描 因此默认不使用交错模式
"""

# 接下来，我们需要创建一个神经网络来生成检测结果
detection_nn = pipeline.createMobileNetDetectionNetwork()
# 这里使用blobconverter工具从OpenVINO模型库自动下载并编译MobileNetSSD模型
detection_nn.setBlobPath(blobconverter.from_zoo(name='mobilenet-ssd', shaves=6))
# 设置神经网络的置信度阈值，置信度值在0到1之间
detection_nn.setConfidenceThreshold(0.5)
# 将相机的"preview"输出连接到神经网络的输入，这样神经网络就可以对相机拍摄的图像进行检测
cam_rgb.preview.link(detection_nn.input)

# 创建XLinkOut节点，用于将数据从设备传输到主机
xout_rgb = pipeline.createXLinkOut()
xout_rgb.setStreamName("rgb")  # 设置流的名称为"rgb"
# 将相机的预览帧输出连接到XLink输入，这样图像帧就会传送到主机
cam_rgb.preview.link(xout_rgb.input)

# 同样使用XLinkOut机制接收神经网络的检测结果
xout_nn = pipeline.createXLinkOut()
xout_nn.setStreamName("nn")  # 设置流的名称为"nn"
detection_nn.out.link(xout_nn.input)  # 将神经网络的输出连接到XLinkOut

# 至此，Pipeline配置完成，现在需要找到一个可用的设备来运行Pipeline
# 使用上下文管理器，这样设备在使用完后会自动释放
with depthai.Device(pipeline) as device:
    # 从这个点开始，设备进入“运行”模式，并通过XLink开始发送数据

    # 获取设备的两个输出队列，分别是我们之前设置的"rgb"和"nn"流
    q_rgb = device.getOutputQueue("rgb")
    q_nn = device.getOutputQueue("nn")

    # 定义一些默认值，帧将是来自"rgb"流的图像，detections将包含神经网络的检测结果
    frame = None
    detections = []

    # 由于神经网络返回的检测框坐标值在0到1的范围内，因此需要乘以图像的宽度和高度来获得实际的边界框位置
    def frameNorm(frame, bbox):
        normVals = np.full(len(bbox), frame.shape[0])  # 初始化一个和bbox一样长度的数组，所有值为帧高
        normVals[::2] = frame.shape[1]  # 将数组的偶数位置（x值）赋值为帧宽
        return (np.clip(np.array(bbox), 0, 1) * normVals).astype(int)  # 将bbox的坐标值归一化，并转换为整数

    # 主程序循环，持续获取设备输出并显示结果
    while True:
        # 从神经网络和RGB队列中尝试获取数据包。tryGet将返回数据包，如果没有数据则返回None
        in_rgb = q_rgb.tryGet()
        in_nn = q_nn.tryGet()

        if in_rgb is not None:
            # 如果获取到RGB相机的帧数据，将其转换为OpenCV格式
            frame = in_rgb.getCvFrame()

        if in_nn is not None:
            # 如果获取到神经网络的检测结果，将其保存到detections列表中
            detections = in_nn.detections

        if frame is not None:
            # 如果获取到帧数据，遍历每一个检测结果
            for detection in detections:
                # 对于每个检测框，首先将其归一化到帧的大小
                bbox = frameNorm(frame, (detection.xmin, detection.ymin, detection.xmax, detection.ymax))
                # 在图像上绘制检测框，颜色为蓝色，线条宽度为2
                cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (255, 0, 0), 2)

            # 在完成所有绘制后，显示处理过的图像
            cv2.imshow("preview", frame)

        # 当按下“q”键时退出主循环，从而结束程序
        if cv2.waitKey(1) == ord('q'):
            break
