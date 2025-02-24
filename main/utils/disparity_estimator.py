"""
视差估计
"""
#!/usr/bin/env python3

import cv2
import time
import depthai as dai
import numpy as np
if __name__ == "__main__":
    from video_show import VideoShowOAK
else:
    from utils.video_show import VideoShowOAK


class DisparityEstimator(VideoShowOAK):
    def __init__(self, extended_disparity=False, subpixel=False, lr_check=True,
                 camera_size=720, is_show_fps=True):
        """
        初始化StereoDepthEstimator类。

        参数:
        extended_disparity (bool): 是否启用扩展视差范围，默认为False
        subpixel (bool): 是否启用子像素精度，默认为False
        lr_check (bool): 是否启用左右视差检查，默认为True
        """
        super().__init__(camera_size, is_show_fps)
        self.extended_disparity = extended_disparity
        self.subpixel = subpixel
        self.lr_check = lr_check

        # 定义深度图节点
        self.depth = self.pipeline.create(dai.node.StereoDepth)
        self.xout = self.pipeline.create(dai.node.XLinkOut)

        self.xout.setStreamName("disparity")

        # 配置深度图节点的属性
        self.depth.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.DEFAULT)
        self.depth.initialConfig.setMedianFilter(dai.MedianFilter.KERNEL_7x7)
        self.depth.setLeftRightCheck(self.lr_check)
        self.depth.setExtendedDisparity(self.extended_disparity)
        self.depth.setSubpixel(self.subpixel)

        # 连接节点
        self.monoLeft.out.link(self.depth.left)
        self.monoRight.out.link(self.depth.right)
        self.depth.disparity.link(self.xout.input)
        self.device = None

    def run(self):
        """
        启动深度估计并显示视差图。
        """
        with dai.Device(self.pipeline) as self.device:
            # 获取输出队列
            q = self.device.getOutputQueue(name="disparity", maxSize=4, blocking=False)

            while True:
                inDisparity = q.get()  # 从队列中获取视差图数据
                frame = inDisparity.getFrame()  # 获取视差图的帧数据
                frame = (frame * (255 / self.depth.initialConfig.getMaxDisparity())).astype(np.uint8)

                # cv2.imshow("disparity", frame)  # 显示原始的视差图

                # 使用颜色映射增强视差图的可视化效果
                frame = cv2.applyColorMap(frame, cv2.COLORMAP_JET)

                # 显示帧率
                frame = self.show_fps(frame)

                # 调整图像大小
                frame = cv2.resize(frame, (int(self.camera_size * 1280 / 720), int(self.camera_size)))

                if __name__ == "__main__":
                    cv2.imshow("color_disparity", frame)
                    cv2.waitKey(1)
                """
                else:
                    _, buffer = cv2.imencode('.jpg', frame)
                    frame_bytes = buffer.tobytes()

                    # 以 MJPEG 格式返回
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')  # 显示带有颜色映射的视差图
                """
                if not self.continue_running:
                    break

    def shutdown(self):
        self.device.close()


# 一个视频流
if __name__ == "__main__":
    # 创建StereoDepthEstimator实例并运行
    disparity_estimator = DisparityEstimator(camera_size=720)
    disparity_estimator.start()  # 创建了一个新线程
    time.sleep(20)
    disparity_estimator.close()
    disparity_estimator.join()
    print("Done")
