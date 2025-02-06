"""
此代码的目的是计算从深度相机获取的深度数据在空间中的坐标，
提供一个用于从相机的深度图像中提取3D空间信息的工具。
通过设置合适的阈值和ROI，代码能够精确计算给定区域的空间位置。
"""
import math
import numpy as np
import depthai as dai

class HostSpatialsCalc:
    # 我们需要设备对象以获取标定数据
    def __init__(self, device):
        self.calibData = device.readCalibration()  # 读取设备的标定数据

        # 默认值
        self.DELTA = 5  # 用于深度ROI的偏移量
        self.THRESH_LOW = 200  # 低阈值，20厘米
        self.THRESH_HIGH = 30000  # 高阈值，30米

    # 设置低阈值
    def setLowerThreshold(self, threshold_low):
        self.THRESH_LOW = threshold_low

    # 设置高阈值
    def setUpperThreshold(self, threshold_low):
        self.THRESH_HIGH = threshold_low

    # 设置ROI偏移量
    def setDeltaRoi(self, delta):
        self.DELTA = delta

    # 检查输入的ROI是否为矩形区域或者是一个点。如果是点，转换为矩形区域
    def _check_input(self, roi, frame):
        if len(roi) == 4:  # 如果是4个元素，表示传入的是ROI（矩形区域）
            return roi
        if len(roi) != 2:  # 如果既不是ROI也不是点，抛出错误
            raise ValueError("You have to pass either ROI (4 values) or point (2 values)!")

        # 如果是点，转换为矩形ROI（以点为中心，大小为DELTA）
        self.DELTA = 5  # 取点周围10x10的深度像素进行深度平均
        x = min(max(roi[0], self.DELTA), frame.shape[1] - self.DELTA)  # 限制X坐标范围
        y = min(max(roi[1], self.DELTA), frame.shape[0] - self.DELTA)  # 限制Y坐标范围
        return (x - self.DELTA, y - self.DELTA, x + self.DELTA, y + self.DELTA)  # 返回转换后的ROI

    # 根据水平视场角（HFOV）计算偏移量的角度
    def _calc_angle(self, frame, offset, HFOV):
        return math.atan(math.tan(HFOV / 2.0) * offset / (frame.shape[1] / 2.0))  # 计算偏移角度

    # 计算空间坐标（深度、x、y坐标）
    def calc_spatials(self, depthData, roi, averaging_method=np.mean):
        # 获取深度帧
        depthFrame = depthData.getFrame()

        # 检查并处理输入ROI
        roi = self._check_input(roi, depthFrame)
        xmin, ymin, xmax, ymax = roi

        # 计算ROI区域内的平均深度
        depthROI = depthFrame[ymin:ymax, xmin:xmax]  # 截取ROI区域的深度图像
        inRange = (self.THRESH_LOW <= depthROI) & (depthROI <= self.THRESH_HIGH)  # 筛选深度值在阈值范围内的像素

        # 获取用于计算空间坐标的必要信息（HFOV）
        HFOV = np.deg2rad(self.calibData.getFov(dai.CameraBoardSocket(depthData.getInstanceNum()), useSpec=False))  # 水平视场角（转换为弧度）

        # 计算深度ROI中深度值的平均值（通过过滤掉不在阈值范围内的像素）
        averageDepth = averaging_method(depthROI[inRange])

        # 计算ROI的中心点（质心）
        centroid = {
            'x': int((xmax + xmin) / 2),  # ROI区域的X坐标中点
            'y': int((ymax + ymin) / 2)   # ROI区域的Y坐标中点
        }

        # 计算深度图的中心点
        midW = int(depthFrame.shape[1] / 2)  # 深度图宽度的中点
        midH = int(depthFrame.shape[0] / 2)  # 深度图高度的中点

        # 计算ROI质心相对于深度图中心的偏移
        bb_x_pos = centroid['x'] - midW
        bb_y_pos = centroid['y'] - midH

        # 计算相对于图像中心的偏移角度
        angle_x = self._calc_angle(depthFrame, bb_x_pos, HFOV)  # 计算X轴偏移的角度
        angle_y = self._calc_angle(depthFrame, bb_y_pos, HFOV)  # 计算Y轴偏移的角度

        # 返回空间坐标（X, Y, Z），其中Z是深度，X和Y是通过角度转换计算得到的
        spatials = {
            'z': averageDepth,  # Z坐标：深度值
            'x': averageDepth * math.tan(angle_x),  # X坐标：根据角度计算X位置
            'y': -averageDepth * math.tan(angle_y)  # Y坐标：根据角度计算Y位置（负号表示方向）
        }
        return spatials, centroid  # 返回空间坐标和ROI的质心
