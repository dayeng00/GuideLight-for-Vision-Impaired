import cv2
import time
import depthai as dai
from collections import deque
from video_show import VideoShowOAK


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
    def __init__(self, camera_size=720, is_show_fps=True):
        super().__init__(camera_size=camera_size, is_show_fps=is_show_fps)

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
        print("Press 's' to switch between Lucas-Kanade optical flow and hardware accelerated motion estimation!")

    def run(self):
        with dai.Device(self.pipeline) as device:
            passthroughImageLeftQueue = device.getOutputQueue("passthroughFrameLeft", 8, False)
            outputFeaturesLeftQueue = device.getOutputQueue("trackedFeaturesLeft", 8, False)
            passthroughImageRightQueue = device.getOutputQueue("passthroughFrameRight", 8, False)
            outputFeaturesRightQueue = device.getOutputQueue("trackedFeaturesRight", 8, False)
            inputFeatureTrackerConfigQueue = device.getInputQueue("trackedFeaturesConfig")

            leftWindowName = "left"
            leftFeatureDrawer = FeaturePointTrackerDrawer("Feature tracking duration (frames)", leftWindowName)

            rightWindowName = "right"
            rightFeatureDrawer = FeaturePointTrackerDrawer("Feature tracking duration (frames)", rightWindowName)

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

                cv2.imshow(leftWindowName, leftFrame)
                cv2.imshow(rightWindowName, rightFrame)

                key = cv2.waitKey(1)

                if key == ord('s'):
                    if self.featureTrackerConfig.motionEstimator.type == dai.FeatureTrackerConfig.MotionEstimator.Type.LUCAS_KANADE_OPTICAL_FLOW:
                        self.featureTrackerConfig.motionEstimator.type = dai.FeatureTrackerConfig.MotionEstimator.Type.HW_MOTION_ESTIMATION
                        print("Switching to hardware accelerated motion estimation")
                    else:
                        self.featureTrackerConfig.motionEstimator.type = dai.FeatureTrackerConfig.MotionEstimator.Type.LUCAS_KANADE_OPTICAL_FLOW
                        print("Switching to Lucas-Kanade optical flow")

                    cfg = dai.FeatureTrackerConfig()
                    cfg.set(self.featureTrackerConfig)
                    inputFeatureTrackerConfigQueue.send(cfg)

                if not self.continue_running:
                    break


if __name__ == "__main__":
    if __name__ == "__main__":
        feature_point_tracker = FeaturePointTracker(camera_size=720)
        feature_point_tracker.start()  # 创建了一个新线程
        time.sleep(20)
        feature_point_tracker.close()
        feature_point_tracker.join()
        print("Done")