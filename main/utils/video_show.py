"""
此脚本定义了一些类 是其他可以可视化演示的父类，定义了一些常见的函数和用法
"""
import cv2
from threading import Thread
import depthai as dai
import time


class VideoShow(Thread):
    def __init__(self, camera_size=720, is_show_fps=True):
        """
        参数:
        camera_size (int): 演示图像的大小：400 480 720 800 默认为720
        is_show_fps (bool): 是否显示帧率 默认为True
        """
        super().__init__()
        self.camera_size = camera_size
        self.is_show_fps = is_show_fps
        self.continue_running = True

        # 用于显示帧率
        self.previous_time = time.time()
        self.current_time = time.time()
        self.old_time = time.time()
        self.fps = 0

    def show_fps(self, img):
        if self.is_show_fps:
            # 计算FPS
            self.current_time = time.time()
            # 防止除以零错误
            time_diff = self.current_time - self.previous_time
            if time_diff > 0:
                fps = 1 / time_diff
            else:
                fps = self.fps or 30  # 使用上一帧FPS或默认值30
            self.previous_time = self.current_time

            # 获取帧的高度和宽度
            height, width, _ = img.shape
            # 根据帧的高度按比例计算字体大小，这里以高度的 1/200 为基准
            font_scale = height / 800
            # 根据字体大小按比例计算字体厚度
            thickness = int(2 * font_scale)
            # 计算文本显示的位置，距离帧左上角一定比例的位置
            x = int(width * 0.02)
            y = int(height * 0.07)

            if self.current_time - self.old_time >= 0.3:
                # 在图像上绘制 FPS 信息
                cv2.putText(img, f'FPS: {int(fps)}', (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (235, 206, 135), thickness)
                self.old_time = self.current_time
                self.fps = fps
            else:
                cv2.putText(img, f'FPS: {int(self.fps)}', (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (235, 206, 135), thickness)

        return img

    def close(self):
        """
        关闭视频流和窗口，释放资源。
        """
        self.continue_running = False
        # 等待一段时间，确保线程有足够的时间退出循环
        time.sleep(0.5)
        # 销毁所有OpenCV窗口
        cv2.destroyAllWindows()


class VideoShowOAK(VideoShow):
    def __init__(self, camera_size=720, is_show_fps=True):
        super().__init__(camera_size=camera_size, is_show_fps=is_show_fps)

        # 创建DepthAI的管道（Pipeline）
        self.pipeline = dai.Pipeline()
        # 定义单目摄像头节点
        self.monoLeft = self.pipeline.create(dai.node.MonoCamera)
        self.monoRight = self.pipeline.create(dai.node.MonoCamera)

        # 配置左、右单目摄像头的属性
        if self.camera_size == 400:
            self.monoLeft.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
            self.monoRight.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
        elif self.camera_size == 480:
            self.monoLeft.setResolution(dai.MonoCameraProperties.SensorResolution.THE_480_P)
            self.monoRight.setResolution(dai.MonoCameraProperties.SensorResolution.THE_480_P)
        elif self.camera_size == 720:
            self.monoLeft.setResolution(dai.MonoCameraProperties.SensorResolution.THE_720_P)
            self.monoRight.setResolution(dai.MonoCameraProperties.SensorResolution.THE_720_P)
        elif self.camera_size == 800:
            self.monoLeft.setResolution(dai.MonoCameraProperties.SensorResolution.THE_800_P)
            self.monoRight.setResolution(dai.MonoCameraProperties.SensorResolution.THE_800_P)

        self.monoLeft.setBoardSocket(dai.CameraBoardSocket.CAM_B)
        self.monoRight.setBoardSocket(dai.CameraBoardSocket.CAM_C)
