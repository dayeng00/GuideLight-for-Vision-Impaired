import cv2
import depthai as dai
from ultralytics import YOLO

# 初始化 OAK 设备
pipeline = dai.Pipeline()

# 创建 RGB 摄像头节点
cam_rgb = pipeline.create(dai.node.ColorCamera)
cam_rgb.setPreviewSize(640, 640)
cam_rgb.setInterleaved(False)
cam_rgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)

# 创建输出节点
xout_rgb = pipeline.create(dai.node.XLinkOut)
xout_rgb.setStreamName("rgb")
cam_rgb.preview.link(xout_rgb.input)

# 加载 YOLOv8 模型
model = YOLO('elevator_button_best.pt')  # 可以根据需要选择不同的预训练模型，如 yolov8s.pt, yolov8m.pt 等

# 连接到 OAK 设备
with dai.Device(pipeline) as device:
    q_rgb = device.getOutputQueue(name="rgb", maxSize=4, blocking=False)

    while True:
        # 获取 RGB 图像
        in_rgb = q_rgb.get()
        frame = in_rgb.getCvFrame()

        # 使用 YOLOv8 模型进行目标检测
        results = model(frame)

        # 获取检测结果并绘制在图像上
        annotated_frame = results[0].plot()

        # 显示图像
        cv2.imshow("Elevator Button", annotated_frame)

        # 按 'q' 键退出循环
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

# 释放资源
cv2.destroyAllWindows()