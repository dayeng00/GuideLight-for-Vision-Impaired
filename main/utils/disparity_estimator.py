"""
视差估计
"""
#!/usr/bin/env python3

import cv2
import time
import depthai as dai
import numpy as np
#
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
                try:
                    inDisparity = q.get()  # 从队列中获取视差图数据
                    if inDisparity is None:
                        time.sleep(0.01)
                        continue
                        
                    frame = inDisparity.getFrame()  # 获取视差图的帧数据
                    if frame is None or frame.size == 0:
                        print("收到空视差帧，跳过处理")
                        time.sleep(0.01)
                        continue
                    
                    # 安全地处理视差图，避免除零
                    max_disparity = self.depth.initialConfig.getMaxDisparity()
                    if max_disparity > 0:
                        frame = (frame * (255 / max_disparity)).astype(np.uint8)
                    else:
                        # 如果最大视差为零，使用默认值
                        frame = frame.astype(np.uint8)
                        print("警告：最大视差为零，使用原始视差图")

                    try:
                        # 使用颜色映射增强视差图的可视化效果
                        frame = cv2.applyColorMap(frame, cv2.COLORMAP_JET)

                        # 显示帧率
                        frame = self.show_fps(frame)

                        # 安全调整图像大小
                        # 避免使用相对尺寸计算，防止除零错误
                        if self.camera_size > 0:
                            new_width = int(self.camera_size * 1280 / 720)
                            new_height = int(self.camera_size)
                        else:
                            # 如果camera_size无效，使用默认值
                            new_width = 1280
                            new_height = 720
                            
                        frame = cv2.resize(frame, (new_width, new_height))

                        if __name__ == "__main__":
                            cv2.imshow("color_disparity", frame)
                            cv2.waitKey(1)
                        else:
                            # 编码为JPEG
                            _, buffer = cv2.imencode('.jpg', frame)
                            frame_bytes = buffer.tobytes()

                            # 以 MJPEG 格式返回
                            yield (b'--frame\r\n'
                                b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')  # 显示带有颜色映射的视差图
                    except Exception as e:
                        print(f"处理视差图时出错: {str(e)}")
                        time.sleep(0.1)
                        continue
                    
                except Exception as e:
                    print(f"视差估计器运行时出错: {str(e)}")
                    time.sleep(0.1)
                    
                # 添加短暂休眠以避免过度占用CPU
                time.sleep(0.01)
                
                if not self.continue_running:
                    break
            
            print("视差估计器线程已停止")

    def shutdown(self):
        """安全关闭设备"""
        try:
            if self.device is not None:
                self.device.close()
                print("视差估计器设备已安全关闭")
        except Exception as e:
            print(f"关闭视差估计器设备时出错: {str(e)}")


# 一个视频流
if __name__ == "__main__":
    # 创建StereoDepthEstimator实例并运行
    disparity_estimator = DisparityEstimator(camera_size=720)
    disparity_estimator.start()  # 创建了一个新线程
    time.sleep(20)
    disparity_estimator.close()
    disparity_estimator.join()
    print("Done")
