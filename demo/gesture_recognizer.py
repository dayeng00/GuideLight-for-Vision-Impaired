# -*- coding: utf-8 -*-

"""
使用 MediaPipe Tasks 进行手势识别
本脚本展示了如何使用 MediaPipe Tasks Python API 在图像中识别手势。
然后下载一个现成的模型。该模型可以识别 7 种手势：👍, 👎, ✌️, ☝️, ✊, 👋, 🤟
有关模型的更多详细信息，请查看 [MediaPipe 文档](https://developers.google.com/mediapipe/solutions/vision/gesture_recognizer#models)。
"""

"""
0 - Unrecognized gesture, label: Unknown
1 - Closed fist, label: Closed_Fist
2 - Open palm, label: Open_Palm
3 - Pointing up, label: Pointing_Up
4 - Thumbs down, label: Thumb_Down
5 - Thumbs up, label: Thumb_Up
6 - Victory, label: Victory
7 - Love, label: ILoveYou
"""

# 如果模型检测到手部但未识别出手势，手势识别器会返回“None”结果。如果模型未检测到手，手势识别器会返回空值。
# 手势识别模型详解网址:
# https://ai.google.dev/edge/mediapipe/solutions/vision/gesture_recognizer?hl=zh-cn

import math

# @markdown 我们实现了一些函数来可视化手势识别结果。运行以下单元格以激活这些函数。
from matplotlib import pyplot as plt
import mediapipe as mp
from mediapipe.framework.formats import landmark_pb2

plt.rcParams.update({
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.spines.left': False,
    'axes.spines.bottom': False,
    'xtick.labelbottom': False,
    'xtick.bottom': False,
    'ytick.labelleft': False,
    'ytick.left': False,
    'xtick.labeltop': False,
    'xtick.top': False,
    'ytick.labelright': False,
    'ytick.right': False
})

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles


def display_one_image(image, title, subplot, titlesize=16):
    """显示一张图像以及预测的类别名称和分数。"""
    plt.subplot(*subplot)
    plt.imshow(image)
    if len(title) > 0:
        plt.title(title, fontsize=int(titlesize), color='black', fontdict={'verticalalignment': 'center'},
                  pad=int(titlesize / 1.5))
    return (subplot[0], subplot[1], subplot[2] + 1)


def display_batch_of_images_with_gestures_and_hand_landmarks(images, results):
    """显示一批图像，包含手势类别及其分数以及手部关键点。"""
    # 图像和标签。
    images = [image.numpy_view() for image in images]
    gestures = [top_gesture for (top_gesture, _) in results]
    multi_hand_landmarks_list = [multi_hand_landmarks for (_, multi_hand_landmarks) in results]

    # 自动调整：这将丢弃不适合正方形或近似矩形的内容。
    rows = int(math.sqrt(len(images)))
    cols = len(images) // rows

    # 大小和间距。
    FIGSIZE = 13.0
    SPACING = 0.1
    subplot = (rows, cols, 1)
    if rows < cols:
        plt.figure(figsize=(FIGSIZE, FIGSIZE / cols * rows))
    else:
        plt.figure(figsize=(FIGSIZE / rows * cols, FIGSIZE))

    # 显示手势和手部关键点。
    for i, (image, gestures) in enumerate(zip(images[:rows * cols], gestures[:rows * cols])):
        title = f"{gestures.category_name} ({gestures.score:.2f})"
        dynamic_titlesize = FIGSIZE * SPACING / max(rows, cols) * 40 + 3
        annotated_image = image.copy()

        for hand_landmarks in multi_hand_landmarks_list[i]:
            hand_landmarks_proto = landmark_pb2.NormalizedLandmarkList()
            hand_landmarks_proto.landmark.extend([
                landmark_pb2.NormalizedLandmark(x=landmark.x, y=landmark.y, z=landmark.z) for landmark in hand_landmarks
            ])

            mp_drawing.draw_landmarks(
                annotated_image,
                hand_landmarks_proto,
                mp_hands.HAND_CONNECTIONS,
                mp_drawing_styles.get_default_hand_landmarks_style(),
                mp_drawing_styles.get_default_hand_connections_style())

        subplot = display_one_image(annotated_image, title, subplot, titlesize=dynamic_titlesize)

    # 布局。
    plt.tight_layout()
    plt.subplots_adjust(wspace=SPACING, hspace=SPACING)
    plt.show()


IMAGE_FILENAMES = ['./utils/gesture_recognizer/pointing_up.jpg',
                   './utils/gesture_recognizer/victory.jpg',
                   './utils/gesture_recognizer/thumbs_up.jpg',
                   './utils/gesture_recognizer/pointing_up.jpg']


"""
运行推理并可视化结果
以下是使用 MediaPipe 运行手势识别器的步骤。
有关此解决方案支持的配置选项的更多信息，请查看 [MediaPipe 文档](https://developers.google.com/mediapipe/solutions/vision/gesture_recognizer/python)。
注意：手势识别器还返回从图像中检测到的手部关键点，以及其他有用信息，例如检测到的手是左手还是右手。
"""

# 第一步：导入必要的模块。
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# 第二步：创建 GestureRecognizer 对象。
base_options = python.BaseOptions(model_asset_path='./utils/gesture_recognizer/gesture_recognizer.task')
options = vision.GestureRecognizerOptions(base_options=base_options)
recognizer = vision.GestureRecognizer.create_from_options(options)

images = []
results = []
for image_file_name in IMAGE_FILENAMES:
    # 第三步：加载输入图像。
    image = mp.Image.create_from_file(image_file_name)

    # 第四步：在输入图像中识别手势。
    recognition_result = recognizer.recognize(image)

    # 第五步：处理结果。在这种情况下，将其可视化。
    images.append(image)
    top_gesture = recognition_result.gestures[0][0]
    hand_landmarks = recognition_result.hand_landmarks
    results.append((top_gesture, hand_landmarks))

display_batch_of_images_with_gestures_and_hand_landmarks(images, results)