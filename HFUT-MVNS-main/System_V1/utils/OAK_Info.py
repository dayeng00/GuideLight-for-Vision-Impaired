"""
MxId: 1944301091CEFC1200
USB speed: UsbSpeed.SUPER
Connected cameras: [<CameraBoardSocket.CAM_A: 0>,
                    <CameraBoardSocket.CAM_B: 1>,
                    <CameraBoardSocket.CAM_C: 2>]
Cameras Sensor: {<CameraBoardSocket.CAM_C: 2>: 'OV9282',
                 <CameraBoardSocket.CAM_A: 0>: 'IMX378',
                 <CameraBoardSocket.CAM_B: 1>: 'OV9282'}
Connected IMU: BMI270/BN0086
Device Info: DeviceInfo(name=2.5,
                        mxid=1944301091CEFC1200,
                        X_LINK_BOOTED,
                        X_LINK_USB_VSC,
                        X_LINK_MYRIAD_X,
                        X_LINK_SUCCESS)
"""

import depthai as dai
from datetime import timedelta

extended_disparity = False  # 扩展视差，使得最近的深度范围加倍 (视差 from 95 to 190)
subpixel = True  # 开启亚像素级别的精度，用于增加远距离的精度，32级的分数差距
lr_check = True  # 开启左右图像一致性检查，以更好处理遮挡情况

# Create pipeline
pipeline = dai.Pipeline()

# Nodes
color = pipeline.create(dai.node.ColorCamera)
monoLeft = pipeline.create(dai.node.MonoCamera)
monoRight = pipeline.create(dai.node.MonoCamera)
stereo = pipeline.create(dai.node.StereoDepth)
imu = pipeline.create(dai.node.IMU)
"""
Sync 节点主要用于同步多个输入消息流。
在深度相机等设备的应用中，不同的传感器可能会以不同的速率产生数据，例如深度数据、彩色图像数据等。
Sync 节点可以确保这些不同的数据流在时间上对齐，这样在后续处理中可以更准确地使用这些数据。
"""
sync = pipeline.create(dai.node.Sync)
"""
XLinkOut 节点用于将设备（如深度相机）内部的数据通过 XLink 接口输出到主机（通常是运行程序的计算机）。
XLink 是 DepthAI 设备与主机之间的通信接口，XLinkOut 节点可以将各种类型的数据（如图像、深度信息等）
从设备传输到主机上的应用程序，以便进行进一步的处理或显示。
"""
xoutGrp = pipeline.create(dai.node.XLinkOut)

# Properties
# color.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
color.setCamera("color")
monoLeft.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
monoLeft.setCamera("left")
monoRight.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
monoRight.setCamera("right")
xoutGrp.setStreamName("xoutGrp")
# imu.enableIMUSensor([dai.IMUSensor.ACCELEROMETER_RAW, dai.IMUSensor.GYROSCOPE_RAW], 100)
"""
dai.IMUSensor.ROTATION_VECTOR：这是一个枚举值，表示要启用的 IMU 传感器的测量类型为旋转向量。
    旋转向量可以用于描述物体在三维空间中的旋转状态，常用于姿态估计等应用。
100：这个参数表示数据输出的频率，单位通常是赫兹（Hz）。
    在这里，设置为 100Hz 意味着 IMU 传感器将以每秒 100 次的频率输出旋转向量数据。
"""
imu.enableIMUSensor(dai.IMUSensor.ROTATION_VECTOR, 100)
imu.setBatchReportThreshold(1)  # 如果队列未被阻塞，则高于此数据包阈值的数据将被发送到主机
imu.setMaxBatchReports(10)  # 批处理报告中的最大 IMU 数据包数

config = stereo.initialConfig.get()
# 斑点噪声是一个具有巨大 相邻视差/深度像素之间的方差，散斑滤波器尝试过滤此区域。
# config.postProcessing.speckleFilter.enable = True
# config.postProcessing.speckleFilter.speckleRange = 50
# config.postProcessing.temporalFilter.enable = False
# config.postProcessing.spatialFilter.enable = True
# config.postProcessing.spatialFilter.holeFillingRadius = 2
# config.postProcessing.spatialFilter.numIterations = 1
config.postProcessing.thresholdFilter.minRange = 500
config.postProcessing.thresholdFilter.maxRange = 10000  # max 40000
# config.postProcessing.decimationFilter.decimationFactor = 1
stereo.initialConfig.set(config)
stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_ACCURACY)  # 选择高精度模式
# stereo.initialConfig.setMedianFilter(dai.MedianFilter.KERNEL_5x5)

stereo.setLeftRightCheck(lr_check)
stereo.setExtendedDisparity(extended_disparity)
stereo.setSubpixel(subpixel)

stereo.setSubpixelFractionalBits(5)
color.setIspScale(1, 3)
stereo.setDepthAlign(dai.CameraBoardSocket.CAM_A)  # 设置深度对齐color(360,640)

# Linking
monoLeft.out.link(stereo.left)
monoRight.out.link(stereo.right)
"""
isp 是 Image Signal Processor（图像信号处理器）的缩写。
color.isp 表示颜色相机的图像信号处理器的输出。
ISP 会对原始的图像数据进行一系列的处理，例如白平衡、色彩校正、降噪等，以提高图像的质量。
"""
color.isp.link(sync.inputs["color"])
stereo.depth.link(sync.inputs["depth"])
stereo.rectifiedRight.link(sync.inputs["rectifiedRight"])
stereo.rectifiedLeft.link(sync.inputs["rectifiedLeft"])
imu.out.link(sync.inputs["imu"])

sync.setSyncThreshold(timedelta(milliseconds=5))  # 同步时间戳的误差为100ms
sync.out.link(xoutGrp.input)

oak_device = dai.Device(pipeline)

# Print MxID, USB speed, and available cameras on the device
print('MxId:', oak_device.getDeviceInfo().getMxId())
print('USB speed:', oak_device.getUsbSpeed())
print('Connected cameras:', oak_device.getConnectedCameras())
print('Cameras Sensor:', oak_device.getCameraSensorNames())
print('Connected IMU:', oak_device.getConnectedIMU())
print('Device Info:', oak_device.getDeviceInfo())

# queue = oak_device.getOutputQueue("xoutGrp", 10, False)
# oak_device.setIrLaserDotProjectorIntensity(0.8)  # 1200