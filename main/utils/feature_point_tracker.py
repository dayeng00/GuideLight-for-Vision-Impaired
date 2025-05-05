"""
特征点追踪
"""
import cv2
import time
import depthai as dai
from collections import deque
from utils.video_show import VideoShowOAK
import threading


class FeaturePointTrackerDrawer:
    lineColor = (200, 0, 200)
    pointColor = (0, 0, 255)
    circleRadius = 2
    maxTrackedFeaturesPathLength = 30
    trackedFeaturesPathLength = 10

    def __init__(self, trackbarName, windowName, headless=False):
        """
        初始化跟踪器绘制器
        
        Args:
            trackbarName: 滑动条名称
            windowName: 窗口名称
            headless: 是否不创建窗口，在服务器模式下设为True
        """
        self.trackbarName = trackbarName
        self.windowName = windowName
        self.headless = headless
        self.trackedIDs = set()
        self.trackedFeaturesPath = dict()
        
        # 只有在非无头模式下才创建窗口和滑动条
        if not headless:
            cv2.namedWindow(windowName)
            cv2.createTrackbar(trackbarName, windowName, self.trackedFeaturesPathLength, self.maxTrackedFeaturesPathLength,
                           self.onTrackBar)

    def onTrackBar(self, val):
        self.trackedFeaturesPathLength = val

    def trackFeaturePath(self, features):
        newTrackedIDs = set()
        for currentFeature in features:
            currentID = currentFeature.id
            newTrackedIDs.add(currentID)

            if currentID not in self.trackedFeaturesPath:
                self.trackedFeaturesPath[currentID] = deque()

            path = self.trackedFeaturesPath[currentID]
            path.append(currentFeature.position)
            while len(path) > max(1, self.trackedFeaturesPathLength):
                path.popleft()

            self.trackedFeaturesPath[currentID] = path

        featuresToRemove = set()
        for oldId in self.trackedIDs:
            if oldId not in newTrackedIDs:
                featuresToRemove.add(oldId)

        for id in featuresToRemove:
            self.trackedFeaturesPath.pop(id)

        self.trackedIDs = newTrackedIDs

    def drawFeatures(self, img):
        # 只有在非无头模式下才设置滑动条位置
        if not self.headless:
            try:
                cv2.setTrackbarPos(self.trackbarName, self.windowName, self.trackedFeaturesPathLength)
            except Exception as e:
                # 如果设置滑动条失败，忽略错误继续执行
                pass
                
        for featurePath in self.trackedFeaturesPath.values():
            path = featurePath
            for j in range(len(path) - 1):
                src = (int(path[j].x), int(path[j].y))
                dst = (int(path[j + 1].x), int(path[j + 1].y))
                cv2.line(img, src, dst, self.lineColor, 1, cv2.LINE_AA, 0)
            j = len(path) - 1
            cv2.circle(img, (int(path[j].x), int(path[j].y)), self.circleRadius, self.pointColor, -1, cv2.LINE_AA, 0)


class FeaturePointTracker(VideoShowOAK):
    def __init__(self, camera_size=720, is_show_fps=True, motion_estimation="hardware_accelerated", headless=True):
        """
        初始化特征点跟踪器
        
        Args:
            camera_size: 相机图像大小
            is_show_fps: 是否显示帧率
            motion_estimation: 运动估算方法
            headless: 是否以无头模式运行（不显示OpenCV窗口）
        """
        super().__init__(camera_size=camera_size, is_show_fps=is_show_fps)

        self.headless = headless  # 添加headless标志
        # 2025/3/27 NEW：左右视频流
        self.rightFrame = None
        self.leftFrame = None
        
        # 添加线程控制
        self.thread = None
        self.continue_running = False

        self.featureTrackerLeft = self.pipeline.create(dai.node.FeatureTracker)
        self.featureTrackerRight = self.pipeline.create(dai.node.FeatureTracker)

        self.xoutPassthroughFrameLeft = self.pipeline.create(dai.node.XLinkOut)
        self.xoutTrackedFeaturesLeft = self.pipeline.create(dai.node.XLinkOut)
        self.xoutPassthroughFrameRight = self.pipeline.create(dai.node.XLinkOut)
        self.xoutTrackedFeaturesRight = self.pipeline.create(dai.node.XLinkOut)
        self.xinTrackedFeaturesConfig = self.pipeline.create(dai.node.XLinkIn)

        self.xoutPassthroughFrameLeft.setStreamName("passthroughFrameLeft")
        self.xoutTrackedFeaturesLeft.setStreamName("trackedFeaturesLeft")
        self.xoutPassthroughFrameRight.setStreamName("passthroughFrameRight")
        self.xoutTrackedFeaturesRight.setStreamName("trackedFeaturesRight")
        self.xinTrackedFeaturesConfig.setStreamName("trackedFeaturesConfig")

        self.monoLeft.out.link(self.featureTrackerLeft.inputImage)
        self.featureTrackerLeft.passthroughInputImage.link(self.xoutPassthroughFrameLeft.input)
        self.featureTrackerLeft.outputFeatures.link(self.xoutTrackedFeaturesLeft.input)
        self.xinTrackedFeaturesConfig.out.link(self.featureTrackerLeft.inputConfig)

        self.monoRight.out.link(self.featureTrackerRight.inputImage)
        self.featureTrackerRight.passthroughInputImage.link(self.xoutPassthroughFrameRight.input)
        self.featureTrackerRight.outputFeatures.link(self.xoutTrackedFeaturesRight.input)
        self.xinTrackedFeaturesConfig.out.link(self.featureTrackerRight.inputConfig)

        numShaves = 2
        numMemorySlices = 2
        self.featureTrackerLeft.setHardwareResources(numShaves, numMemorySlices)
        self.featureTrackerRight.setHardwareResources(numShaves, numMemorySlices)

        self.featureTrackerConfig = self.featureTrackerRight.initialConfig.get()

        self.motion_estimation = motion_estimation

        self.device = None
        
    def start(self):
        """启动视频处理线程"""
        try:
            if self.thread is None or not self.thread.is_alive():
                self.continue_running = True
                self.thread = threading.Thread(target=self.run)
                self.thread.daemon = True  # 设置为守护线程，当主线程退出时，该线程也会退出
                self.thread.start()
                print("特征点追踪器线程已启动")
                # 等待线程初始化，确保视频流已开始
                time.sleep(1.0)  # 增加等待时间，以便捕获初始化错误
                return True
            return False
        except Exception as e:
            self.continue_running = False
            print(f"启动特征点追踪器线程失败: {str(e)}")
            raise RuntimeError(f"无法启动摄像头: {str(e)}")
            
    def close(self):
        """安全停止视频处理线程"""
        self.continue_running = False
        if self.thread is not None and self.thread.is_alive():
            try:
                self.thread.join(timeout=5.0)  # 等待线程最多5秒钟
                print("特征点追踪器线程已关闭")
            except Exception as e:
                print(f"关闭线程失败: {str(e)}")
        return True

    def run(self):
        with dai.Device(self.pipeline) as self.device:
            passthroughImageLeftQueue = self.device.getOutputQueue("passthroughFrameLeft", 8, False)
            outputFeaturesLeftQueue = self.device.getOutputQueue("trackedFeaturesLeft", 8, False)
            passthroughImageRightQueue = self.device.getOutputQueue("passthroughFrameRight", 8, False)
            outputFeaturesRightQueue = self.device.getOutputQueue("trackedFeaturesRight", 8, False)
            inputFeatureTrackerConfigQueue = self.device.getInputQueue("trackedFeaturesConfig")

            leftWindowName = "left"
            leftFeatureDrawer = FeaturePointTrackerDrawer("Feature tracking duration (frames)", leftWindowName, self.headless)

            rightWindowName = "right"
            rightFeatureDrawer = FeaturePointTrackerDrawer("Feature tracking duration (frames)", rightWindowName, self.headless)

            # 设置运动估算方法
            if self.motion_estimation == "hardware_accelerated":
                self.featureTrackerConfig.motionEstimator.type = dai.FeatureTrackerConfig.MotionEstimator.Type.HW_MOTION_ESTIMATION
                print("Using hardware accelerated motion estimation")
            elif self.motion_estimation == "lucas_kanade_optical_flow":
                self.featureTrackerConfig.motionEstimator.type = dai.FeatureTrackerConfig.MotionEstimator.Type.LUCAS_KANADE_OPTICAL_FLOW
                print("Switching to Lucas-Kanade optical flow")
            else:
                raise ValueError("Unknown motion estimation!")
                return

            cfg = dai.FeatureTrackerConfig()
            cfg.set(self.featureTrackerConfig)
            inputFeatureTrackerConfigQueue.send(cfg)
            
            # 确保camera_size非零，防止除零错误
            if self.camera_size <= 0:
                self.camera_size = 720  # 设置默认值
                print(f"警告: 相机尺寸无效，已设置为默认值 {self.camera_size}")

            # 使用self.continue_running来控制循环
            self.continue_running = True
            while self.continue_running:
                try:
                    # 从队列中获取帧
                    inPassthroughFrameLeft = passthroughImageLeftQueue.get()
                    passthroughFrameLeft = inPassthroughFrameLeft.getFrame()
                    leftFrame = cv2.cvtColor(passthroughFrameLeft, cv2.COLOR_GRAY2BGR)

                    inPassthroughFrameRight = passthroughImageRightQueue.get()
                    passthroughFrameRight = inPassthroughFrameRight.getFrame()
                    rightFrame = cv2.cvtColor(passthroughFrameRight, cv2.COLOR_GRAY2BGR)

                    trackedFeaturesLeft = outputFeaturesLeftQueue.get().trackedFeatures
                    leftFeatureDrawer.trackFeaturePath(trackedFeaturesLeft)
                    leftFeatureDrawer.drawFeatures(leftFrame)

                    trackedFeaturesRight = outputFeaturesRightQueue.get().trackedFeatures
                    rightFeatureDrawer.trackFeaturePath(trackedFeaturesRight)
                    rightFeatureDrawer.drawFeatures(rightFrame)

                    # 显示FPS
                    try:
                        leftFrame = self.show_fps(leftFrame)
                        
                        # 安全地调整图像大小，避免除零错误
                        if self.camera_size > 0 and leftFrame is not None and rightFrame is not None:
                            # 计算图像比例，确保数值有效
                            ratio = max(0.1, 1280 / 720)  # 使用固定比例以避免除零
                            new_width = int(self.camera_size * ratio)
                            new_height = int(self.camera_size)
                            
                            left_frame = cv2.resize(leftFrame, (new_width, new_height))
                            right_frame = cv2.resize(rightFrame, (new_width, new_height))
                            
                            self.leftFrame = left_frame
                            self.rightFrame = right_frame
                    except Exception as resize_error:
                        print(f"调整图像大小时出错: {str(resize_error)}")
                        # 如果调整失败，继续使用原始图像
                        self.leftFrame = leftFrame
                        self.rightFrame = rightFrame
                    
                    # 添加短暂休眠以避免过度占用CPU
                    time.sleep(0.01)

                    if not self.continue_running:
                        break
                except Exception as frame_error:
                    print(f"处理一帧图像时出错: {str(frame_error)}")
                    time.sleep(0.1)  # 发生错误时稍等片刻
                    
            print("特征点追踪线程已停止")
            # 确保不再创建或使用OpenCV窗口
            if not self.headless:
                cv2.destroyAllWindows()

    # 2025/3/27 NEW: 左视频流
    def show_left(self):
        """为前端提供左侧摄像头的MJPEG流"""
        # 不使用无限循环，而是让Flask负责多次调用生成器
        while self.continue_running:  # 保留检查，但不是主循环
            try:
                leftFrame = self.leftFrame
                if leftFrame is not None:
                    # 将图像编码为JPEG格式
                    _, buffer = cv2.imencode('.jpg', leftFrame)
                    frame_bytes = buffer.tobytes()

                    # 以 MJPEG 格式返回单帧
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    
                    # 让出CPU，避免过度占用资源
                    time.sleep(0.03)  # 约30fps
                else:
                    # 如果图像不可用，等待一会再尝试
                    time.sleep(0.1)
                    # 返回一个空帧或错误消息
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + b'' + b'\r\n')
            except Exception as e:
                print(f"左摄像头流处理错误: {str(e)}")
                # 出错时返回空帧
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + b'' + b'\r\n')
                time.sleep(0.1)

    # 2025/3/27 NEW: 右视频流
    def show_right(self):
        """为前端提供右侧摄像头的MJPEG流"""
        # 不使用无限循环，而是让Flask负责多次调用生成器
        while self.continue_running:  # 保留检查，但不是主循环
            try:
                rightFrame = self.rightFrame
                if rightFrame is not None:
                    # 将图像编码为JPEG格式
                    _, buffer = cv2.imencode('.jpg', rightFrame)
                    frame_bytes = buffer.tobytes()

                    # 以 MJPEG 格式返回单帧
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    
                    # 让出CPU，避免过度占用资源
                    time.sleep(0.03)  # 约30fps
                else:
                    # 如果图像不可用，等待一会再尝试
                    time.sleep(0.1)
                    # 返回一个空帧或错误消息
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + b'' + b'\r\n')
            except Exception as e:
                print(f"右摄像头流处理错误: {str(e)}")
                # 出错时返回空帧
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + b'' + b'\r\n')
                time.sleep(0.1)

    # TODO 补充shutdown函数关闭停止摄像头调用
    def shutdown(self):
        """关闭设备并释放资源"""
        self.continue_running = False
        print("正在关闭设备...")
        try:
            if self.device is not None:
                self.device.close()
                print("设备已关闭")
        except Exception as e:
            print(f"关闭设备失败: {str(e)}")



if __name__ == "__main__":
    if __name__ == "__main__":
        feature_point_tracker = FeaturePointTracker(camera_size=720, motion_estimation="hardware_accelerated")
        feature_point_tracker.start()  # 创建了一个新线程
        time.sleep(20)
        feature_point_tracker.close()
        feature_point_tracker.join()
        print("Done")
