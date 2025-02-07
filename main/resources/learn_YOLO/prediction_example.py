"""
该代码无法运行 只是提供了一些常用预测时的示例
"""
from ultralytics import YOLO
from PIL import Image

# 加载模型
model = YOLO("yolo11n.pt")  # 预训练的 YOLO11n 模型

# 对一组图像进行批量推理
results = model(["image1.jpg", "image2.jpg"])  # 返回一个 Results 对象列表

# 处理结果列表
for result in results:
    boxes = result.boxes  # Boxes 对象，用于边界框输出
    masks = result.masks  # Masks 对象，用于分割掩码输出
    keypoints = result.keypoints  # Keypoints 对象，用于姿态输出
    probs = result.probs  # Probs 对象，用于分类输出
    obb = result.obb  # Oriented boxes 对象，用于 OBB 输出
    result.show()  # 显示结果到屏幕
    result.save(filename="result.jpg")  # 保存结果到磁盘

"""
使用 stream=True 用于处理长视频或大型数据集，以有效管理内存。
当 stream=False在这种情况下，所有帧或数据点的结果都会存储在内存中，
这可能会迅速累加，并导致大量输入出现内存不足错误。
与此形成鲜明对比的是 stream=True 利用生成器，只将当前帧或数据点的结果保存在内存中，
从而大大减少了内存消耗，并防止出现内存不足的问题。
"""

"""
资料来源	    示例	                                        类型	            说明
图像	        'image.jpg'	                                str 或 Path	    单个图像文件。
网址	        'https://ultralytics.com/images/bus.jpg'	str	            图片的 URL。
截图	        'screen'	                                str	            截图
PIL	        Image.open('image.jpg')	                    PIL.Image	    具有 RGB 通道的 HWC 格式。
OpenCV	    cv2.imread('image.jpg')	                    np.ndarray	    带有 BGR 频道的 HWC 格式 uint8 (0-255).
numpy	    np.zeros((640,1280,3))	                    np.ndarray	    带有 BGR 频道的 HWC 格式 uint8 (0-255).
torch	    torch.zeros(16,3,320,640)	                torch.Tensor	带 RGB 通道的 BCHW 格式 float32 (0.0-1.0).
CSV	        'sources.csv'	                            str 或 Path	    包含图像、视频或目录路径的 CSV 文件。
视频 ✅	    'video.mp4'	                                str 或 Path	    MP4 和 AVI 等格式的视频文件
目录 ✅	    'path/'	                                    str 或 Path	    包含图像或视频的目录路径。
球体 ✅	    'path/*.jpg'	                            str	            全局模式来匹配多个文件。使用 * 字符作为通配符。
YouTube ✅	'https://youtu.be/LNwODJXcvt4'	            str	            YouTube 视频的 URL。
流 ✅	    'rtsp://example.com/media.mp4'	            str	            流媒体协议（如 RTSP、RTMP、TCP）的 URL 或 IP 地址。
多流 ✅	    'list.streams'	                            str 或 Path	    *.streams 文本文件，每行一个流 URL，即 8 个流将以 8 的批处理大小运行。
网络摄像头 ✅	0	                                        int	            要进行推理的已连接摄像机设备的索引。
"""

# 以下是处理视频的示例
# Define path to video file
source = "path/to/video.mp4"

# Run inference on the source
results = model(source, stream=True)  # generator of Results objects

"""
model.predict() 接受多个参数，这些参数可以在推理时传递，以覆盖默认值：
"""
# Run inference on 'bus.jpg' with arguments
model.predict("bus.jpg", save=True, imgsz=320, conf=0.5)

"""
推理参数：
参数	            类型	            默认值	                说明
source	        str	            'ultralytics/assets'	指定推理的数据源。可以是图像路径、视频文件、目录、URL 或用于实时馈送的设备 ID。支持多种格式和来源，可灵活应用于不同类型的输入。
conf	        float	        0.25	                设置检测的最小置信度阈值。如果检测到的对象置信度低于此阈值，则将不予考虑。调整该值有助于减少误报。
iou	            float	        0.7	                    非最大抑制 (NMS) 的交叉重叠(IoU) 阈值。较低的数值可以消除重叠的方框，从而减少检测次数，这对减少重复检测非常有用。
imgsz	        int 或 tuple	640	                    定义用于推理的图像大小。可以是一个整数 640 或一个（高度、宽度）元组。适当调整大小可以提高检测效率 精确度 和处理速度。
half	        bool	        False	                启用半精度（FP16）推理，可加快支持的 GPU 上的模型推理速度，同时将对精度的影响降至最低。
device	        str	            None	                指定用于推理的设备（例如：......）、 cpu, cuda:0 或 0).允许用户选择CPU 、特定GPU 或其他计算设备执行模型。
batch	        int	            1	                    指定推理的批量大小（仅当来源为 目录、视频文件或 .txt 文件).更大的批次规模可以提供更高的吞吐量，缩短推理所需的总时间。
max_det	        int	            300	                    每幅图像允许的最大检测次数。限制模型在单次推理中可以检测到的物体总数，防止在密集场景中产生过多的输出。
vid_stride	    int	            1	                    视频输入的帧间距。允许跳过视频中的帧，以加快处理速度，但会牺牲时间分辨率。数值为 1 时会处理每一帧，数值越大越跳帧。
stream_buffer	bool	        False	                决定是否对接收到的视频流帧进行排队。如果 False，旧帧会被丢弃，以容纳新帧（针对实时应用进行了优化）。如果为 "真"，则在缓冲区中排队等待新帧，确保不会跳过任何帧，但如果推理的 FPS 低于流的 FPS，则会导致延迟。
visualize	    bool	        False	                在推理过程中激活模型特征的可视化，从而深入了解模型 "看到 "了什么。这对调试和模型解释非常有用。
augment	        bool	        False	                可对预测进行测试时间增强（TTA），从而在牺牲推理速度的情况下提高检测的鲁棒性。
agnostic_nms	bool	        False	                启用与类别无关的非最大抑制 (NMS)，可合并不同类别的重叠方框。这在多类检测场景中非常有用，因为在这种场景中，类的重叠很常见。
classes	        list[int]	    None	                根据一组类别 ID 过滤预测结果。只有属于指定类别的检测结果才会返回。这对于在多类检测任务中集中检测相关对象非常有用。
retina_masks	bool	        False	                返回高分辨率分割掩码。返回的掩码 (masks.data) 如果启用，将与原始图像大小相匹配。如果禁用，它们将与推理过程中使用的图像大小一致。
embed	        list[int]	    None	                指定从中提取特征向量或嵌入的层。这对聚类或相似性搜索等下游任务非常有用。
project	        str	            None	                保存预测结果的项目目录名称，如果 save 已启用。
name	        str	            None	                预测运行的名称。用于在项目文件夹内创建一个子目录，在下列情况下存储预测输出结果 save 已启用。

可视化参数：
参数	        类型	        默认值	        说明
show	    bool	    False	        如果 True在一个窗口中显示注释的图像或视频。有助于在开发或测试过程中提供即时视觉反馈。
save	    bool	    False或True	    可将注释的图像或视频保存到文件中。这对记录、进一步分析或共享结果非常有用。使用CLI 时默认为 True，在Python 中使用时默认为 False。
save_frames	bool	    False	        处理视频时，将单个帧保存为图像。可用于提取特定帧或进行详细的逐帧分析。
save_txt	bool	    False	        将检测结果保存在文本文件中，格式如下 [class] [x_center] [y_center] [width] [height] [confidence].有助于与其他分析工具集成。
save_conf	bool	    False	        在保存的文本文件中包含置信度分数。增强了后期处理和分析的细节。
save_crop	bool	    False	        保存经过裁剪的检测图像。可用于数据集扩充、分析或创建特定物体的重点数据集。
show_labels	bool	    True	        在可视输出中显示每次检测的标签。让用户立即了解检测到的物体。
show_conf	bool	    True	        在标签旁显示每次检测的置信度得分。让人了解模型对每次检测的确定性。
show_boxes	bool	    True	        在检测到的物体周围绘制边框。对于图像或视频帧中物体的视觉识别和定位至关重要。
line_width	None或int	None	        指定边界框的线宽。如果 None根据图像大小自动调整线宽。提供可视化定制，使图像更加清晰。
"""

# 对一张图片进行推理
results = model("bus.jpg")  # 结果列表

# 查看结果
for r in results:
    print(r.boxes)  # 打印包含检测边界框的 Boxes 对象

"""
下面是一张表格 Boxes 类方法和属性，包括名称、类型和说明：
名称	    类型	                说明
cpu()	方法	                将对象移至CPU 内存。
numpy()	方法	                将对象转换为 numpy 数组。
cuda()	方法	                将对象移至CUDA 内存。
to()	方法	                将对象移动到指定设备。
xyxy	财产 (torch.Tensor)	以 xyxy 格式返回方框。
conf	财产 (torch.Tensor)	返回方框的置信度值。
cls	    财产 (torch.Tensor)	返回方框的类值。
id	    财产 (torch.Tensor)	返回盒子的轨道 ID（如果有）。
xywh	财产 (torch.Tensor)	以 xywh 格式返回方框。
xyxyn	财产 (torch.Tensor)	以 xyxy 格式返回按原始图像大小归一化的方框。
xywhn	财产 (torch.Tensor)	以 xywh 格式返回按原始图像大小归一化的方框。
"""


# 对 'bus.jpg' 和 'zidane.jpg' 进行推理
results = model(["bus.jpg", "zidane.jpg"])  # 结果列表

# 可视化结果
for i, r in enumerate(results):
    # 绘制结果图像
    im_bgr = r.plot()  # BGR 顺序的 numpy 数组
    im_rgb = Image.fromarray(im_bgr[..., ::-1])  # RGB 顺序的 PIL 图像

    # 在支持的环境中显示结果到屏幕
    r.show()

    # 将结果保存到磁盘
    r.save(filename=f"results{i}.jpg")
"""
plot() 方法参数
参数	        类型	            说明	                                                默认值
conf	    bool	        包括检测置信度分数。	                                True
line_width	float	        边界框的线宽。根据图像大小缩放，如果 None.	            None
font_size	float	        文字字体大小。与图像大小一致，如果 None.	                None
font	    str	            文本注释的字体名称。	                                'Arial.ttf'
pil	        bool	        将图像作为 PIL 图像对象返回。	                        False
img	        numpy.ndarray	用于绘图的替代图像。如果出现以下情况，则使用原始图像 None.	None
im_gpu	    torch.Tensor	GPU-加速图像，用于更快地绘制掩膜图。形状:（1，3，640，640）	None
kpt_radius	int	            绘制关键点的半径。	                                    5
kpt_line	bool	        用线条连接关键点。	                                    True
labels	    bool	        在注释中包含类标签。	                                True
boxes	    bool	        在图像上叠加边界框。	                                True
masks	    bool	        在图像上叠加蒙版	                                    True
probs	    bool	        包括分类概率。	                                    True
show	    bool	        使用默认图像查看器直接显示注释图像。	                    False
save	    bool	        将注释图像保存到由 filename.	                        False
filename	str	            保存注释图像的文件路径和名称（如果有）。 save 是 True.	    None
color_mode	str	            指定颜色模式，如 "实例 "或 "类"。	                    'class'
"""

"""
Python 下面是一个使用 OpenCV (cv2)和YOLO 对视频帧进行推理的完整脚本
本脚本假定您已经安装了必要的软件包 (opencv-python 和 ultralytics).
"""

import cv2
from ultralytics import YOLO

# 加载 YOLO 模型
model = YOLO("yolo11n.pt")

# 打开视频文件
video_path = "path/to/your/video/file.mp4"
cap = cv2.VideoCapture(video_path)

# 遍历视频帧
while cap.isOpened():
    # 从视频中读取一帧
    success, frame = cap.read()

    if success:
        # 对当前帧运行 YOLO 推理
        results = model(frame)

        # 在当前帧上可视化结果
        annotated_frame = results[0].plot()

        # 显示带注释的帧
        cv2.imshow("YOLO Inference", annotated_frame)

        # 如果按下 'q' 键，则退出循环
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    else:
        # 如果视频结束，则退出循环
        break

# 释放视频捕获对象并关闭显示窗口
cap.release()
cv2.destroyAllWindows()