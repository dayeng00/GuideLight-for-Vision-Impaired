# coding=utf-8
import math
import time

import blobconverter
import cv2
import depthai as dai
import numpy as np

from video_show import VideoShow
from palm_detection import PalmDetection

# 深度阈值上限（单位：毫米）
DEPTH_THRESH_HIGH = 3000
# 深度阈值下限（单位：毫米）
DEPTH_THRESH_LOW = 500
# 危险警告距离阈值（单位：毫米）
WARNING_DIST = 300

nnYoloPath = "../resources/yolo11n/yolo11n_openvino_2022.1_6shave.blob"
nnMobilenetPath = blobconverter.from_zoo(name='mobilenet-ssd', shaves=6)
# 如果危险物体与手掌距离过近，将显示警告信息

# 定义危险物体列表
DANGEROUS_OBJECTS = ["bottle"]

# MobilenetSSD 标签文本
MobilenetSSDLabelMap = ["background", "aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair", "cow",
                        "diningtable", "dog", "horse", "motorbike", "person", "pottedplant", "sheep", "sofa", "train", "tvmonitor"]

Yolov11nLabelMap = [
    "person",         "bicycle",    "car",           "motorbike",     "aeroplane",   "bus",           "train",
    "truck",          "boat",       "traffic light", "fire hydrant",  "stop sign",   "parking meter", "bench",
    "bird",           "cat",        "dog",           "horse",         "sheep",       "cow",           "elephant",
    "bear",           "zebra",      "giraffe",       "backpack",      "umbrella",    "handbag",       "tie",
    "suitcase",       "frisbee",    "skis",          "snowboard",     "sports ball", "kite",          "baseball bat",
    "baseball glove", "skateboard", "surfboard",     "tennis racket", "bottle",      "wine glass",    "cup",
    "fork",           "knife",      "spoon",         "bowl",          "banana",      "apple",         "sandwich",
    "orange",         "broccoli",   "carrot",        "hot dog",       "pizza",       "donut",         "cake",
    "chair",          "sofa",       "pottedplant",   "bed",           "diningtable", "toilet",        "tvmonitor",
    "laptop",         "mouse",      "remote",        "keyboard",      "cell phone",  "microwave",     "oven",
    "toaster",        "sink",       "refrigerator",  "book",          "clock",       "vase",          "scissors",
    "teddy bear",     "hair drier", "toothbrush"
]


# 将图像裁剪为正方形
def crop_to_rect(frame):
    # 获取图像的高度
    height = frame.shape[0]
    # 获取图像的宽度
    width = frame.shape[1]
    # 计算需要裁剪的宽度差值的一半
    delta = int((width - height) / 2)
    # 打印高度、宽度和裁剪差值
    # print(height, width, delta)
    # 返回裁剪后的图像
    return frame[0:height, delta:width - delta]


# 创建一个用于在图像上添加文本注释的函数
def annotate_fun(img, color, fontFace=cv2.FONT_HERSHEY_TRIPLEX, fontScale=0.5, **kwargs):
    def fun(text, pos):
        # 在图像上绘制文本
        cv2.putText(img, text, pos, fontFace, fontScale, color, **kwargs)

    return fun


class HumanMachineSafety(VideoShow):
    def __init__(self, model="mobilenet", nnPath=nnMobilenetPath, nnConfidence=0.5,
                 show_depth_frame=False):
        """

        :param model(String): "yolo" or "mobilenet"
        :param nnPath(String):
        :param nnConfidence(int): the confidence of model
        """
        super().__init__()
        print("正在加载管道...")

        self.model = model
        self.nnPath = nnPath
        self.nnConfidence = nnConfidence
        self.show_depth_frame = show_depth_frame

        if model == "yolo":
            self.labelMap = Yolov11nLabelMap
        elif model == "mobilenet":
            self.labelMap = MobilenetSSDLabelMap
        else:
            raise ValueError(f"unknown model: {model}")

        # 初始化手掌检测类
        self.palmDetection = PalmDetection()

        # 初始化手掌与危险物体之间的距离
        self.distance = None

        # 在主机上计算空间坐标所需的信息
        # 单目相机的水平视场角（弧度）
        self.monoHFOV = np.deg2rad(73.5)
        # 深度图像的宽度
        self.depthWidth = 1080.0

    # 根据深度图和边界框（感兴趣区域）计算空间坐标
    def calc_spatials(self, bbox, depth, averaging_method=np.mean):
        # 获取边界框的坐标
        xmin, ymin, xmax, ymax = bbox
        # 将边界框缩小为原来的 1/3
        deltaX = int((xmax - xmin) * 0.33)
        deltaY = int((ymax - ymin) * 0.33)
        xmin += deltaX
        ymin += deltaY
        xmax -= deltaX
        ymax -= deltaY
        if xmin > xmax:  # 如果边界框翻转
            xmin, xmax = xmax, xmin
        if ymin > ymax:  # 如果边界框翻转
            ymin, ymax = ymax, ymin

        if xmin == xmax or ymin == ymax:  # 边界框大小为零
            return None

        # 计算感兴趣区域内的平均深度
        depthROI = depth[ymin:ymax, xmin:xmax]
        # 筛选出在深度阈值范围内的像素
        inThreshRange = (DEPTH_THRESH_LOW < depthROI) & (depthROI < DEPTH_THRESH_HIGH)

        # 计算平均深度
        averageDepth = averaging_method(depthROI[inThreshRange])
        # 打印平均深度
        # print(f"Average depth: {averageDepth}")

        # 手掌检测的质心坐标
        centroidX = int((xmax - xmin) / 2) + xmin
        centroidY = int((ymax - ymin) / 2) + ymin

        # 深度图像的中心位置
        mid = int(depth.shape[0] / 2)
        # 边界框质心相对于图像中心的 x 偏移量
        bb_x_pos = centroidX - mid
        # 边界框质心相对于图像中心的 y 偏移量
        bb_y_pos = centroidY - mid

        # 计算 x 和 y 方向的角度
        angle_x = self.calc_angle(bb_x_pos)
        angle_y = self.calc_angle(bb_y_pos)

        # 深度值
        z = averageDepth
        # 计算 x 坐标
        x = z * math.tan(angle_x)
        # 计算 y 坐标
        y = -z * math.tan(angle_y)

        # 打印空间坐标
        # print(f"X: {x}mm, Y: {y} mm, Z: {z} mm")
        return (x, y, z, centroidX, centroidY)

    # 计算手掌与危险物体之间的空间距离，并在图像上绘制相关信息
    def calc_spatial_distance(self, spatialCoords, frame, detections):
        # 解包手掌的空间坐标和质心坐标
        x, y, z, centroidX, centroidY = spatialCoords
        # 创建一个用于在图像上添加注释的函数
        annotate = annotate_fun(frame, (0, 0, 25), fontScale=1.7)

        if not detections:
            print('No detections found')

        for det in detections:
            # 忽略非危险物体的检测结果
            print('find' + self.labelMap[det.label])
            if self.labelMap[det.label] not in DANGEROUS_OBJECTS: continue

            # 计算手掌与危险物体之间的空间距离
            self.distance = math.sqrt((det.spatialCoordinates.x - x) ** 2 + (det.spatialCoordinates.y - y) ** 2 + (
                    det.spatialCoordinates.z - z) ** 2)

            # 获取图像的高度
            height = frame.shape[0]
            # 计算危险物体边界框的坐标
            x1 = int(det.xmin * height)
            x2 = int(det.xmax * height)
            y1 = int(det.ymin * height)
            y2 = int(det.ymax * height)
            # if not x1 or x2 or y1 or y2: continue
            # 计算危险物体的中心坐标
            objectCenterX = int((x1 + x2) / 2)
            objectCenterY = int((y1 + y2) / 2)
            # 在图像上绘制从手掌质心到危险物体中心的直线
            cv2.line(frame, (centroidX, centroidY), (objectCenterX, objectCenterY), (50, 220, 100), 4)

            if self.distance < WARNING_DIST:
                # 如果距离小于警告阈值，将危险物体标记为红色
                sub_img = frame[y1:y2, x1:x2]
                red_rect = np.ones(sub_img.shape, dtype=np.uint8) * 255
                # 将蓝色和绿色通道设置为 0
                red_rect[:, :, 0] = 0
                red_rect[:, :, 1] = 0
                # 混合原始图像和红色矩形
                res = cv2.addWeighted(sub_img, 0.5, red_rect, 0.5, 1.0)
                # 将处理后的图像放回原位置
                frame[y1:y2, x1:x2] = res
                # 在图像上添加“Danger”警告信息（打印两次以显示加粗效果）
                annotate("Drink Water!", (100, int(height / 3)))
                annotate("Drink Water!", (101, int(height / 3)))
        # 显示彩色图像
        cv2.imshow("color", frame)

    # 在图像上绘制边界框
    def draw_bbox(self, bbox, color):
        def draw(img):
            # 在图像上绘制矩形边界框
            cv2.rectangle(
                img=img,
                pt1=(bbox[0], bbox[1]),
                pt2=(bbox[2], bbox[3]),
                color=color,
                thickness=2,
            )

        # 在调试图像上绘制边界框
        draw(self.debug_frame)
        # 在深度彩色图像上绘制边界框
        draw(self.depthFrameColor)

    # 在图像上绘制检测结果
    def draw_detections(self, frame, detections):
        # 定义边界框颜色
        color = (250, 0, 0)
        # 创建一个用于在图像上添加注释的函数
        annotate = annotate_fun(frame, (0, 0, 25))

        for detection in detections:

            # print(self.labelMap[detection.label])
            # 忽略非危险物体的检测结果
            if self.labelMap[detection.label] not in DANGEROUS_OBJECTS: continue
            # 获取图像的高度
            height = frame.shape[0]
            # 获取图像的宽度
            width = frame.shape[1]
            # 将归一化的边界框坐标转换为实际像素坐标
            x1 = int(detection.xmin * width)
            x2 = int(detection.xmax * width)
            y1 = int(detection.ymin * height)
            y2 = int(detection.ymax * height)
            # 定义注释的偏移量
            offsetX = x1 + 10
            # 在图像上添加检测置信度信息
            annotate("{:.2f}".format(detection.confidence * 100), (offsetX, y1 + 35))
            # 在图像上添加危险物体的 x 坐标信息
            annotate(f"X: {int(detection.spatialCoordinates.x)} mm", (offsetX, y1 + 50))
            # 在图像上添加危险物体的 y 坐标信息
            annotate(f"Y: {int(detection.spatialCoordinates.y)} mm", (offsetX, y1 + 65))
            # 在图像上添加危险物体的 z 坐标信息
            annotate(f"Z: {int(detection.spatialCoordinates.z)} mm", (offsetX, y1 + 80))
            # 在图像上绘制边界框
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, cv2.FONT_HERSHEY_SIMPLEX)
            try:
                # 获取检测物体的标签
                label = self.labelMap[detection.label]
            except:
                label = detection.label

            # 在图像上添加检测物体的标签信息
            annotate(str(label), (offsetX, y1 + 20))

    # 计算偏移量对应的角度
    def calc_angle(self, offset):
        return math.atan(math.tan(self.monoHFOV / 2.0) * offset / (self.depthWidth / 2.0))

    # 在图像上绘制手掌检测结果，并计算手掌的空间坐标
    def draw_palm_detection(self, palm_coords, depth):
        if palm_coords is None:
            return None

        # 定义手掌边界框的颜色
        color = (10, 245, 10)
        # 创建一个用于在图像上添加注释的函数
        annotate = annotate_fun(self.debug_frame, color)

        for bbox in palm_coords:
            # 计算手掌的空间坐标
            spatialCoords = self.calc_spatials(bbox, depth)
            if spatialCoords is None:  # 边界框大小为 0
                continue
            # 在图像上绘制手掌的边界框
            self.draw_bbox(bbox, color)
            # 解包手掌的空间坐标和质心坐标
            x, y, z, cx, cy = spatialCoords

            if math.isnan(x) or math.isnan(y) or math.isnan(z):
                continue

            # 在图像上添加手掌的 x 坐标信息
            annotate(f"X: {int(x)} mm", (bbox[0], bbox[1]))
            # 在图像上添加手掌的 y 坐标信息
            annotate(f"Y: {int(y)} mm", (bbox[0], bbox[1] + 15))
            # 在图像上添加手掌的 z 坐标信息
            annotate(f"Z: {int(z)} mm", (bbox[0], bbox[1] + 30))
            return spatialCoords

    # 解析手掌检测结果、物体检测结果，并在图像上绘制相关信息
    def parse(self, in_palm_detections, detections, frame, depth, depthColored):
        # 复制彩色图像用于调试
        self.debug_frame = frame.copy()
        # 存储深度彩色图像
        self.depthFrameColor = depthColored
        # 创建一个用于在图像上添加注释的函数
        annotate = annotate_fun(self.debug_frame, (50, 220, 110), fontScale=1.4)

        # 解析手掌检测输出
        palm_coords = self.palmDetection.run_palm(
            self.debug_frame,
            in_palm_detections)
        # 计算并绘制手掌的空间坐标
        spatialCoords = self.draw_palm_detection(palm_coords, depth)
        # 计算手掌与危险物体之间的距离，并显示警告信息
        if spatialCoords is not None:
            self.calc_spatial_distance(spatialCoords, self.debug_frame, detections)

        # 绘制目标检测结果
        self.draw_detections(self.debug_frame, detections)
        # 在图像上添加手掌与危险物体之间的距离信息（打印三次以显示加粗效果）
        if self.distance:
            annotate(f"Distance: {int(self.distance)} mm", (50, 700))
            annotate(f"Distance: {int(self.distance)} mm", (51, 700))
            annotate(f"Distance: {int(self.distance)} mm", (52, 700))
        # 显示调试图像
        self.debug_frame = self.show_fps(self.debug_frame)
        cv2.imshow("color", self.debug_frame)

        if self.depthFrameColor is not None:
            if self.show_depth_frame:
                # 在深度彩色图像上绘制检测结果
                self.draw_detections(self.depthFrameColor, detections)
                # 显示深度彩色图像
                cv2.imshow("depth", self.depthFrameColor)

        cv2.waitKey(1)

        if not self.continue_running:
            # 关闭所有 OpenCV 窗口
            cv2.destroyAllWindows()
            # 抛出停止迭代异常，退出循环
            raise StopIteration()

    def run(self):
        print("正在创建管道...")
        # 创建一个新的 DepthAI 管道
        pipeline = dai.Pipeline()

        # 创建一个彩色相机节点
        cam = pipeline.create(dai.node.ColorCamera)
        # 设置彩色相机的分辨率为 1080P
        cam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
        # 设置 ISP 缩放比例，以匹配 720P 单目相机
        cam.setIspScale(2, 3)
        # 设置彩色相机的板载插槽为 RGB
        cam.setBoardSocket(dai.CameraBoardSocket.CAM_A)
        # 设置彩色相机的手动对焦值
        cam.initialControl.setManualFocus(130)
        # 为 MobileNet 神经网络设置颜色顺序为 BGR
        cam.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)

        # 设置彩色相机的预览尺寸为 300x300
        if self.model == "yolo":
            cam.setPreviewSize(640, 640)
        elif self.model == "mobilenet":
            cam.setPreviewSize(300, 300)
        else:
            raise ValueError("unknown model: " + self.model)

        # 设置彩色相机的图像不交错
        cam.setInterleaved(False)

        # 创建一个 XLinkOut 节点，用于将彩色相机的 ISP 输出发送到主机
        isp_xout = pipeline.create(dai.node.XLinkOut)
        # 设置输出流的名称为 "cam"
        isp_xout.setStreamName("cam")
        # 将彩色相机的 ISP 输出链接到 XLinkOut 节点的输入
        cam.isp.link(isp_xout.input)

        print(f"正在创建手掌检测神经网络...")
        # 创建一个神经网络节点，用于手掌检测
        model_nn = pipeline.create(dai.node.NeuralNetwork)
        # 设置手掌检测神经网络的模型路径，从 DepthAI 模型库中下载
        model_nn.setBlobPath(blobconverter.from_zoo(name="palm_detection_128x128", zoo_type="depthai", shaves=6))
        # 设置神经网络输入不阻塞
        model_nn.input.setBlocking(False)

        # 创建一个图像操作节点，用于调整图像大小
        manip = pipeline.create(dai.node.ImageManip)
        # 初始配置为将图像调整为 128x128
        manip.initialConfig.setResize(128, 128)
        # 将彩色相机的预览输出链接到图像操作节点的输入
        cam.preview.link(manip.inputImage)
        # 将图像操作节点的输出链接到神经网络节点的输入
        manip.out.link(model_nn.input)

        # 创建一个 XLinkOut 节点，用于将手掌检测神经网络的输出发送到主机
        model_nn_xout = pipeline.create(dai.node.XLinkOut)
        # 设置输出流的名称为 "palm_nn"
        model_nn_xout.setStreamName("palm_nn")
        # 将神经网络节点的输出链接到 XLinkOut 节点的输入
        model_nn.out.link(model_nn_xout.input)

        # 创建左单目相机节点
        left = pipeline.create(dai.node.MonoCamera)
        # 设置左单目相机的分辨率为 720P
        left.setResolution(dai.MonoCameraProperties.SensorResolution.THE_720_P)
        # 设置左单目相机的板载插槽为 LEFT
        left.setBoardSocket(dai.CameraBoardSocket.CAM_B)

        # 创建右单目相机节点
        right = pipeline.create(dai.node.MonoCamera)
        # 设置右单目相机的分辨率为 720P
        right.setResolution(dai.MonoCameraProperties.SensorResolution.THE_720_P)
        # 设置右单目相机的板载插槽为 RIGHT
        right.setBoardSocket(dai.CameraBoardSocket.CAM_C)

        # 创建一个立体深度节点，用于生成深度图
        stereo = pipeline.create(dai.node.StereoDepth)
        # 设置立体深度计算的置信度阈值
        stereo.initialConfig.setConfidenceThreshold(245)
        # 设置中值滤波的内核大小为 7x7
        stereo.initialConfig.setMedianFilter(dai.StereoDepthProperties.MedianFilter.KERNEL_7x7)
        # 启用左右一致性检查
        stereo.setLeftRightCheck(True)
        # 将深度图对齐到 RGB 相机
        stereo.setDepthAlign(dai.CameraBoardSocket.CAM_A)
        # 将左单目相机的输出链接到立体深度节点的左输入
        left.out.link(stereo.left)
        # 将右单目相机的输出链接到立体深度节点的右输入
        right.out.link(stereo.right)

        # 创建一个空间检测网络节点
        if self.model == "yolo":
            net = pipeline.create(dai.node.YoloSpatialDetectionNetwork)
        elif self.model == "mobilenet":
            net = pipeline.create(dai.node.MobileNetSpatialDetectionNetwork)
        else:
            raise ValueError(f"Unknown model: {self.model}")

        # 设置空间检测网络的模型路径，从 DepthAI 模型库中下载
        net.setBlobPath(self.nnPath)
        # 设置检测的置信度阈值
        net.setConfidenceThreshold(self.nnConfidence)
        if self.model == "yolo":
            net.setNumClasses(len(self.labelMap))
        # 设置输入不阻塞
        net.input.setBlocking(False)
        # 设置边界框的缩放因子
        net.setBoundingBoxScaleFactor(0.2)
        # 设置深度的下限阈值
        net.setDepthLowerThreshold(DEPTH_THRESH_LOW)
        # 设置深度的上限阈值
        net.setDepthUpperThreshold(DEPTH_THRESH_HIGH)

        # 将彩色相机的预览输出链接到 MobileNet 空间检测网络节点的输入
        cam.preview.link(net.input)
        # 将立体深度节点的深度输出链接到 MobileNet 空间检测网络节点的深度输入
        stereo.depth.link(net.inputDepth)

        # 创建一个 XLinkOut 节点，用于将 MobileNet 空间检测网络的输出发送到主机
        net_out = pipeline.create(dai.node.XLinkOut)
        # 设置输出流的名称为 "det"
        net_out.setStreamName("det")
        # 将 MobileNet 空间检测网络节点的输出链接到 XLinkOut 节点的输入
        net.out.link(net_out.input)

        # 创建一个 XLinkOut 节点，用于将深度图输出发送到主机
        depth_out = pipeline.create(dai.node.XLinkOut)
        # 设置输出流的名称为 "depth"
        depth_out.setStreamName("depth")
        # 将 MobileNet 空间检测网络节点的深度直通输出链接到 XLinkOut 节点的输入
        net.passthroughDepth.link(depth_out.input)

        print("管道创建完成。")

        # 打开 DepthAI 设备
        with dai.Device() as device:
            # 获取连接到设备的相机列表
            cams = device.getConnectedCameras()
            # 检查设备是否连接了左右单目相机，以确定是否支持深度功能
            depth_enabled = dai.CameraBoardSocket.CAM_B in cams and dai.CameraBoardSocket.CAM_C in cams
            if not depth_enabled:
                # 如果设备不支持深度功能，抛出运行时错误
                raise RuntimeError("无法在不具备深度功能的设备上运行此实验！（可用相机：{}）".format(cams))
            # 启动管道
            device.startPipeline(pipeline)
            # 创建输出队列
            # 创建彩色相机输出队列
            vidQ = device.getOutputQueue(name="cam", maxSize=4, blocking=False)
            # 创建空间检测网络输出队列
            detQ = device.getOutputQueue(name="det", maxSize=4, blocking=False)
            # 创建深度图输出队列
            depthQ = device.getOutputQueue(name="depth", maxSize=4, blocking=False)
            # 创建手掌检测神经网络输出队列
            palmQ = device.getOutputQueue(name="palm_nn", maxSize=4, blocking=False)

            # 初始化检测结果列表
            detections = []
            # 初始化深度图
            depthFrame = None
            # 初始化彩色深度图
            depthFrameColor = None
            # 初始化彩色图像帧
            frame = None

            # 进入主循环
            while True:
                # 尝试从彩色相机输出队列获取帧
                in_rgb = vidQ.tryGet()
                if in_rgb is not None:
                    # 如果获取到帧，将其裁剪为正方形
                    frame = crop_to_rect(in_rgb.getCvFrame())

                # 检查空间检测网络输出队列
                in_det = detQ.tryGet()
                if in_det is not None:
                    # print('detection: {}'.format(self.labelMap[det.label] for det in in_det.detections))
                    # 如果获取到检测结果，更新检测结果列表
                    detections = in_det.detections
                    print(f"获取到 {len(detections)} 个检测结果")
                else:
                    print("未获取到检测结果")

                # 尝试从深度图输出队列获取深度帧
                in_depth = depthQ.tryGet()
                if in_depth is not None:
                    # 如果获取到深度帧，将其裁剪为正方形
                    depthFrame = crop_to_rect(in_depth.getFrame())
                    # 对深度图进行归一化处理
                    depthFrameColor = cv2.normalize(depthFrame, None, 255, 0, cv2.NORM_INF, cv2.CV_8UC1)
                    # 对归一化后的深度图进行直方图均衡化处理
                    depthFrameColor = cv2.equalizeHist(depthFrameColor)
                    # 为深度图应用热图颜色映射
                    depthFrameColor = cv2.applyColorMap(depthFrameColor, cv2.COLORMAP_JET)

                # 尝试从手掌检测神经网络输出队列获取手掌检测结果
                palm_in = palmQ.tryGet()
                if palm_in is not None and frame is not None and depthFrame is not None:
                    try:
                        # 解析手掌检测结果、物体检测结果，并在图像上绘制相关信息
                        self.parse(
                            palm_in,
                            detections,
                            frame,
                            depthFrame,
                            depthFrameColor)
                    except StopIteration:
                        # 如果捕获到停止迭代异常，退出循环
                        break


if __name__ == "__main__":
    human_machine_safety = HumanMachineSafety(nnConfidence=0.5, model='mobilenet', nnPath=nnMobilenetPath)
    human_machine_safety.start()  # 创建了一个新线程
    time.sleep(100)
    human_machine_safety.close()
    human_machine_safety.join()
    print("Done")
