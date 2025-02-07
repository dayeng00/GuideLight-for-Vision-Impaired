import cv2
import mediapipe as mp
import time

"""
cv2中坐标系的定义
原点 (0, 0)：位于图像的左上角
x 轴：水平向右为正方向
y 轴：垂直向下为正方向

图像的尺寸通常表示为 (height, width) 或 (rows, columns)。
height：图像的高度（行数，y 轴方向）
width：图像的宽度（列数，x 轴方向）

像素的访问是通过 img[y, x] 的方式进行
"""

cap = cv2.VideoCapture(0)
mpHands = mp.solutions.hands  # 使用手部检测模型

"""
Hands()的五个参数：
static_image_mode=False,       侦测的是否是静态的图片
max_num_hands=2,               侦测的最大手的数量
model_complexity=1,            模型的复杂度 只能设定成 0 或 1
min_detection_confidence=0.5,  最低侦测置信度 (0, 1)
min_tracking_confidence=0.5):  最低追踪置信度 (0, 1)
"""

hands = mpHands.Hands()
mpDraw = mp.solutions.drawing_utils
# 下面的参数 点的颜色BGR 点大小          红色
handLmsStyle = mpDraw.DrawingSpec(color=(0, 0, 255), thickness=5)
# 下面的参数 线的颜色BGR 线粗细          绿色
handConStyle = mpDraw.DrawingSpec(color=(0, 255, 0), thickness=4)
previousTime = 0
currentTime = 0

while True:
    ret, img = cap.read()
    if ret:
        # cv2里的图片通道默认顺序是BGR 所以需要先转换成RGB
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        result = hands.process(imgRGB)
        # print(result.multi_hand_landmarks)  # 打印手上的21个节点的坐标
        imgHeight, imgWidth = img.shape[:2]  # 存储目前帧的高和宽
        # 如果检测到手
        if result.multi_hand_landmarks:
            for hand_landmarks in result.multi_hand_landmarks:
                mpDraw.draw_landmarks(img, hand_landmarks, mpHands.HAND_CONNECTIONS, handLmsStyle, handConStyle)
                for i, lm in enumerate(hand_landmarks.landmark):
                    xPosition = int(lm.x * imgWidth)
                    yPosition = int(lm.y * imgHeight)
                    cv2.putText(img, str(i), (xPosition-25, yPosition+5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 2)
                    # print(i, xPosition, yPosition)  # 打印出来的是坐标的相对位置 需要再乘上窗口大小
                    # 放大某个点
                    if i == 0:
                        cv2.circle(img, (xPosition, yPosition), 10, (0, 0, 255), cv2.FILLED)
        # 打印FPS
        currentTime = time.time()
        fps = 1 / (currentTime - previousTime)
        previousTime = currentTime
        cv2.putText(img, f'FPS: {int(fps)}', (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 3)
        cv2.imshow('img', img)

    if cv2.waitKey(1) == ord('q'):  # 按下'q'键退出循环
        break
