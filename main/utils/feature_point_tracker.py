"""
特征点追踪
"""
import cv2
import time
import depthai as dai
from collections import deque
from utils.video_show import VideoShowOAK


class FeaturePointTrackerDrawer:
    lineColor = (200, 0, 200)
    pointColor = (0, 0, 255)
    circleRadius = 2
    maxTrackedFeaturesPathLength = 30
    trackedFeaturesPathLength = 10

    def __init__(self, trackbarName, windowName):

        self.trackbarName = trackbarName
        self.windowName = windowName
        cv2.namedWindow(windowName)
        cv2.createTrackbar(trackbarName, windowName, self.trackedFeaturesPathLength, self.maxTrackedFeaturesPathLength,
                           self.onTrackBar)
        self.trackedIDs = set()
        self.trackedFeaturesPath = dict()

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
        cv2.setTrackbarPos(self.trackbarName, self.windowName, self.trackedFeaturesPathLength)
        for featurePath in self.trackedFeaturesPath.values():
            path = featurePath
            for j in range(len(path) - 1):
                src = (int(path[j].x), int(path[j].y))
                dst = (int(path[j + 1].x), int(path[j + 1].y))
                cv2.line(img, src, dst, self.lineColor, 1, cv2.LINE_AA, 0)
            j = len(path) - 1
            cv2.circle(img, (int(path[j].x), int(path[j].y)), self.circleRadius, self.pointColor, -1, cv2.LINE_AA, 0)


class FeaturePointTracker(VideoShowOAK):
    def __init__(self, camera_size=720, is_show_fps=True, motion_estimation="hardware_accelerated"):
        """

        :param camera_size:
        :param is_show_fps:
        :param motion_estimation: 运动估算方法：  "hardware_accelerated" 硬件加速法
                                               "lucas_kanade_optical_flow" 光流法 默认硬件加速法
        """
        super().__init__(camera_size=camera_size, is_show_fps=is_show_fps)

        # 2025/3/27 NEW：左右视频流
        self.rightFrame = None
        self.leftFrame = None

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

    def run(self):
        with dai.Device(self.pipeline) as self.device:
            passthroughImageLeftQueue = self.device.getOutputQueue("passthroughFrameLeft", 8, False)
            outputFeaturesLeftQueue = self.device.getOutputQueue("trackedFeaturesLeft", 8, False)
            passthroughImageRightQueue = self.device.getOutputQueue("passthroughFrameRight", 8, False)
            outputFeaturesRightQueue = self.device.getOutputQueue("trackedFeaturesRight", 8, False)
            inputFeatureTrackerConfigQueue = self.device.getInputQueue("trackedFeaturesConfig")

            leftWindowName = "left"
            leftFeatureDrawer = FeaturePointTrackerDrawer("Feature tracking duration (frames)", leftWindowName)

            rightWindowName = "right"
            rightFeatureDrawer = FeaturePointTrackerDrawer("Feature tracking duration (frames)", rightWindowName)

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

            while True:
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

                leftFrame = self.show_fps(leftFrame)

                # 调整图像大小
                leftFrame = cv2.resize(leftFrame, (int(self.camera_size * 1280 / 720), int(self.camera_size)))
                rightFrame = cv2.resize(rightFrame, (int(self.camera_size * 1280 / 720), int(self.camera_size)))

                self.leftFrame = leftFrame
                self.rightFrame = rightFrame
                
                
                # cv2.imshow(leftWindowName, leftFrame)
                # cv2.imshow(rightWindowName, rightFrame)

                key = cv2.waitKey(1)

                if not self.continue_running:
                    break
    # 2025/3/27 NEW: 左视频流
    def show_left(self):
        # FIXME tobytes函数检验
        leftFrame = self.leftFrame
        if leftFrame:
            _, buffer = cv2.imencode('jpg',leftFrame)
            frame_bytes = buffer.tobytes()

            # 以 MJPEG 格式返回
            yield (b'--frame\r\n'
                            b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    # 2025/3/27 NEW: 右视频流
    def show_right(self):
        # FIXME tobytes函数检验
        rightFrame = self.rightFrame
        if rightFrame:
            _, buffer = cv2.imencode('jpg', rightFrame)
            frame_bytes = buffer.tobytes()

            yield(b'--frame\r\n'
                            b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            
    # TODO 补充shutdown函数关闭停止摄像头调用
    def shut_down(self):
        self.device.close()



if __name__ == "__main__":
    if __name__ == "__main__":
        feature_point_tracker = FeaturePointTracker(camera_size=720, motion_estimation="hardware_accelerated")
        feature_point_tracker.start()  # 创建了一个新线程
        time.sleep(20)
        feature_point_tracker.close()
        feature_point_tracker.join()
        print("Done")
