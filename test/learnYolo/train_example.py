"""
该代码无法运行 只是提供了一些常用训练时的示例
"""
import comet_ml
from ultralytics import YOLO

# 加载模型
model = YOLO("yolo11n.yaml")  # 从YAML构建一个新的模型
model = YOLO("yolo11n.pt")  # 加载一个预训练的模型（推荐用于训练）
model = YOLO("yolo11n.yaml").load("yolo11n.pt")  # 从YAML构建模型并转移权重

# 训练模型
# 使用coco8.yaml数据集训练模型，训练100个周期，图像尺寸为640
results = model.train(data="coco8.yaml", epochs=100, imgsz=640)

# Train the model with 2 GPUs
results = model.train(data="coco8.yaml", epochs=100, imgsz=640, device=[0, 1])

"""
在使用 Ultralytics YOLO 进行深度学习模型训练时，恢复中断的训练是一个非常有用的功能。
在这个示例中，resume=True 参数告诉 train 函数从 "path/to/last.pt" 文件中加载模型的状态，
包括权重、优化器状态、学习率调度器和历时编号。这样，训练过程会从中断的地方继续。
"""
# 加载部分训练的模型
model = YOLO("path/to/last.pt")  # 加载一个部分训练的模型
# 恢复训练
results = model.train(resume=True)

"""
最常见的训练时配置的参数：
参数	        默认值	    说明
model	    None	    用于训练的模型文件的路径。
data	    None	    数据集配置文件的路径（例如 coco8.yaml).
epochs	    100	        训练历元总数。
batch	    16	        批量大小，可调整为整数或自动模式。
imgsz	    640	        用于训练的目标图像大小。
device	    None	    用于训练的计算设备，如 cpu, 0, 0,1或 mps.
save	    True	    可保存训练检查点和最终模型权重。
"""

"""
以下是训练时可以配置的参数：
参数	            类型	            默认值	        说明
model	        str	            None	        指定用于训练的模型文件。接受指向 .pt 预训练模型或 .yaml 配置文件。对于定义模型结构或初始化权重至关重要。
data	        str	            None	        数据集配置文件的路径（例如 coco8.yaml).该文件包含特定于数据集的参数，包括训练和 验证数据类名和类数。
epochs	        int	            100	            训练历元总数。每个历元代表对整个数据集进行一次完整的训练。调整该值会影响训练时间和模型性能。
time	        float	        None	        最长训练时间（小时）。如果设置了该值，则会覆盖 epochs 参数，允许训练在指定的持续时间后自动停止。对于时间有限的训练场景非常有用。
patience	    int	            100	            在验证指标没有改善的情况下，提前停止训练所需的历元数。当性能趋于平稳时停止训练，有助于防止过度拟合。
batch	        int	            16	            批量大小有三种模式： 设置为整数（如 batch=16）、自动模式，内存利用率为 60%GPU (batch=-1），或指定利用率的自动模式 (batch=0.70).
imgsz	        int 或 list	    640	            用于训练的目标图像尺寸。所有图像在输入模型前都会被调整到这一尺寸。影响模型精度和计算复杂度。
save	        bool	        True	        可保存训练检查点和最终模型权重。这对恢复训练或模型部署非常有用。
save_period	    int	            -1	            保存模型检查点的频率，以 epochs 为单位。值为-1 时将禁用此功能。该功能适用于在长时间训练过程中保存临时模型。
cache	        bool	        False	        在内存中缓存数据集图像 (True/ram）、磁盘 (disk），或禁用它 (False).通过减少磁盘 I/O，提高训练速度，但代价是增加内存使用量。
device	        int或str或list	None	        指定用于训练的计算设备：单个GPU (device=0）、多个 GPU (device=0,1）、CPU (device=cpu) 或MPS for Apple silicon (device=mps).
workers	        int	            8	            加载数据的工作线程数（每 RANK 如果多GPU 训练）。影响数据预处理和输入模型的速度，尤其适用于多GPU 设置。
project	        str	            None	        保存训练结果的项目目录名称。允许有组织地存储不同的实验。
name	        str	            None	        训练运行的名称。用于在项目文件夹内创建一个子目录，用于存储训练日志和输出结果。
exist_ok	    bool	        False	        如果为 True，则允许覆盖现有的项目/名称目录。这对迭代实验非常有用，无需手动清除之前的输出。
pretrained	    bool	        True	        决定是否从预处理模型开始训练。可以是布尔值，也可以是加载权重的特定模型的字符串路径。提高训练效率和模型性能。
optimizer	    str	            'auto'	        为培训选择优化器。选项包括 SGD, Adam, AdamW, NAdam, RAdam, RMSProp 等，或 auto 用于根据模型配置进行自动选择。影响收敛速度和稳定性
seed	        int	            0	            为训练设置随机种子，确保在相同配置下运行的结果具有可重复性。
deterministic	bool	        True	        强制使用确定性算法，确保可重复性，但由于对非确定性算法的限制，可能会影响性能和速度。
single_cls	    bool	        False	        在训练过程中将多类数据集中的所有类别视为单一类别。适用于二元分类任务，或侧重于对象的存在而非分类。
classes	        list[int]	    None	        指定要训练的类 ID 列表。有助于在训练过程中筛选出特定的类并将其作为训练重点。
rect	        bool	        False	        可进行矩形训练，优化批次组成以减少填充。这可以提高效率和速度，但可能会影响模型的准确性。
multi_scale	    bool	        False	        通过增加/减少 imgsz 的系数 0.5 在训练过程中通过多次训练，使模型更加准确。 imgsz 在推理过程中
cos_lr	        bool	        False	        利用余弦学习率调度器，根据历时的余弦曲线调整学习率。这有助于管理学习率，实现更好的收敛。
close_mosaic	int	            10	            在训练完成前禁用最后 N 个历元的马赛克数据增强以稳定训练。设置为 0 则禁用此功能。
resume	        bool	        False	        从上次保存的检查点恢复训练。自动加载模型权重、优化器状态和历时计数，无缝继续训练。
amp	            bool	        True	        启用自动混合精度(AMP) 训练，可减少内存使用量并加快训练速度，同时将对精度的影响降至最低。
fraction	    float	        1.0         	指定用于训练的数据集的部分。允许在完整数据集的子集上进行训练，这对实验或资源有限的情况非常有用。
profile	        bool	        False       	在训练过程中，可对ONNX 和TensorRT 速度进行剖析，有助于优化模型部署。
freeze	        int 或 list	    None	        冻结模型的前 N 层或按索引指定的层，从而减少可训练参数的数量。这对微调或迁移学习非常有用。
lr0	            float	        0.01	        初始学习率（即 SGD=1E-2, Adam=1E-3) .调整这个值对优化过程至关重要，会影响模型权重的更新速度。
lrf	            float	        0.01	        最终学习率占初始学习率的百分比 = (lr0 * lrf)，与调度程序结合使用，随着时间的推移调整学习率。
momentum	    float	        0.937	        用于 SGD 的动量因子，或用于Adam 优化器的 beta1，用于将过去的梯度纳入当前更新。
weight_decay	float	        0.0005	        L2正则化项，对大权重进行惩罚，以防止过度拟合。
warmup_epochs	float	        3.0	            学习率预热的历元数，学习率从低值逐渐增加到初始学习率，以在早期稳定训练。
warmup_momentum	float	        0.8	            热身阶段的初始动力，在热身期间逐渐调整到设定动力。
warmup_bias_lr	float	        0.1	            热身阶段的偏置参数学习率，有助于稳定初始历元的模型训练。
box	            float	        7.5	            损失函数中边框损失部分的权重，影响对准确预测边框坐标的重视程度。
cls	            float	        0.5	            分类损失在总损失函数中的权重，影响正确分类预测相对于其他部分的重要性。
dfl	            float	        1.5	            分布焦点损失权重，在某些YOLO 版本中用于精细分类。
pose	        float	        12.0	        姿态损失在姿态估计模型中的权重，影响着准确预测姿态关键点的重点。
kobj	        float	        2.0	            姿态估计模型中关键点对象性损失的权重，平衡检测可信度与姿态精度。
nbs	            int	            64	            用于损耗正常化的标称批量大小。
overlap_mask	bool	        True	        决定是将对象遮罩合并为一个遮罩进行训练，还是将每个对象的遮罩分开。在重叠的情况下，较小的掩码会在合并时覆盖在较大的掩码之上。
mask_ratio	    int	            4	            分割掩码的下采样率，影响训练时使用的掩码分辨率。
dropout	        float	        0.0	            分类任务中正则化的丢弃率，通过在训练过程中随机省略单元来防止过拟合。
val	            bool	        True	        可在训练过程中进行验证，以便在单独的数据集上对模型性能进行定期评估。
plots	        bool	        False	        生成并保存训练和验证指标图以及预测示例图，以便直观了解模型性能和学习进度。
"""

"""
以下是数据增强的参数设置：
参数	            类型	        默认值	    范围	        说明
hsv_h	        float	    0.015	    0.0 - 1.0	通过色轮的一部分来调整图像的色调，从而引入色彩的可变性。帮助模型在不同的光照条件下通用。
hsv_s	        float	    0.7	        0.0 - 1.0	改变图像饱和度的一部分，影响色彩的强度。可用于模拟不同的环境条件。
hsv_v	        float	    0.4	        0.0 - 1.0	将图像的数值（亮度）修改一部分，帮助模型在不同的光照条件下表现良好。
degrees	        float	    0.0	        -180 - +180	在指定的度数范围内随机旋转图像，提高模型识别不同方向物体的能力。
translate	    float	    0.1	        0.0 - 1.0	将图像进行水平和垂直平移，平移幅度为图像大小的一小部分，有助于学习检测部分可见的物体。
scale	        float	    0.5	        >=0.0	    通过增益因子缩放图像，模拟物体与摄像机的不同距离。
shear	        float	    0.0	        -180 - +180	按指定角度剪切图像，模拟从不同角度观察物体的效果。
perspective 	float	    0.0	        0.0 - 0.001	对图像进行随机透视变换，增强模型理解三维空间中物体的能力。
flipud	        float	    0.0	        0.0 - 1.0	以指定的概率将图像翻转过来，在不影响物体特征的情况下增加数据的可变性。
fliplr	        float	    0.5	        0.0 - 1.0	以指定概率从左到右翻转图像，这对学习对称物体和增加数据集多样性很有用。
bgr	            float	    0.0	        0.0 - 1.0	以指定的概率将图像通道从 RGB 翻转到 BGR，用于提高对错误通道排序的稳健性。
mosaic	        float	    1.0	        0.0 - 1.0	将四幅训练图像合成一幅，模拟不同的场景构成和物体互动。对复杂场景的理解非常有效。
mixup	        float	    0.0	        0.0 - 1.0	混合两幅图像及其标签，创建合成图像。通过引入标签噪声和视觉变化，增强模型的泛化能力。
copy_paste	    float	    0.0	        0.0 - 1.0	在图像中复制和粘贴对象，有助于增加对象实例和学习对象遮挡。需要分割标签。
copy_paste_mode	str	        flip	    -	        在 ( )选项中选择复制-粘贴增强方法。"flip", "mixup").
auto_augment	str	        randaugment	-	        自动应用预定义的增强策略 (randaugment, autoaugment, augmix)，通过丰富视觉特征来优化分类任务。
erasing	        float	    0.4	        0.0 - 0.9	在分类训练中随机擦除部分图像，鼓励模型将识别重点放在不明显的特征上。
crop_fraction	float	    1.0	        0.1 - 1.0	将分类图像裁剪为其大小的一小部分，以突出中心特征并适应对象比例，减少背景干扰。
"""

"""
以下是一个使用Comet日志记录器的示例
"""
# 初始化 Comet
# Comet API key PrTNljI3CgerouhlK8pIVeS1j
comet_ml.init(api_key="YOUR_COMET_API_KEY")

# 训练模型并启用 Comet 日志记录
results = model.train(
    data="coco128.yaml",
    epochs=100,
    imgsz=640,
    batch=16,
    project="my-yolo-project",
    name="yolov8-comet-experiment",
    logger="comet"
)


# 在验证集上评估模型的性能
results = model.val()

# 使用该模型对图像进行目标检测
results = model("https://ultralytics.com/images/bus.jpg")

# 将模型导出为ONNX格式
success = model.export(format="onnx")
