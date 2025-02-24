"""
验证训练集
"""

from ultralytics import YOLO


def main():
    """
    YOLO11 模型会自动记住它们的训练设置，因此您可以在相同的图像尺寸和原始数据集上轻松验证模型，
    只需 yolo val model=yolo11n.pt 或 model('yolo11n.pt').val()
    """

    """
    使用示例
    验证训练有素的YOLO11n模型精确度在COCO8 数据集上使用。
    无需参数，因为model保留其培训data和参数作为模型属性。
    有关验证参数的完整列表，请参阅下面的 "参数 "部分。
    """

    # 加载模型
    # model = YOLO("yolo11n.pt")  # 加载官方模型
    model = YOLO("elevator_button_best.pt")  # 加载自定义模型

    # 验证模型
    metrics = model.val()  # 无需参数，数据集和设置已记住
    """
    mAP50（IoU 阈值为 0.5 时的平均精度平均值）
    mAP75（在 IoU 临界值为 0.75 时的平均平均精度）
    mAP50-95（从 0.5 到 0.95 的多个 IoU 阈值的平均精度平均值）
    """
    # metrics.box.map  # map50-95
    # metrics.box.map50  # map50
    # metrics.box.map75  # map75
    # metrics.box.maps  # 包含每个类别的map50-95的列表
    print(metrics.box.maps)  # list of mAP50-95 for each category

    """
    YOLO模型验证的论据
    在验证YOLO模型时，可以对几个参数进行微调，以优化评估过程。
    这些参数可控制输入图像大小、批处理和性能阈值等方面。
    以下是每个参数的详细说明，可帮助您有效地自定义验证设置。
    
    论据	        类型	        默认值	    说明
    data	    str	        None	    指定数据集配置文件的路径（如 coco8.yaml).该文件包括指向 验证数据类名和类数。
    imgsz	    int	        640	        定义输入图像的尺寸。所有图像在处理前都会调整到这一尺寸。
    batch	    int	        16	        设置每批图像的数量。使用 -1 的自动批处理功能，它会根据GPU 内存可用性自动调整。
    save_json	bool	    False	    如果 True此外，还可将结果保存到 JSON 文件中，以便进一步分析或与其他工具集成。
    save_hybrid	bool	    False	    如果 True，保存混合版本的标签，将原始注释与额外的模型预测相结合。
    conf	    float	    0.001	    设置检测的最小置信度阈值。置信度低于此阈值的检测将被丢弃。
    iou	        float	    0.6	        设置非最大抑制 (NMS) 的交叉重叠(IoU) 阈值。有助于减少重复检测。
    max_det	    int	        300	        限制每幅图像的最大检测次数。在密度较高的场景中非常有用，可以防止检测次数过多。
    half	    bool	    True	    可进行半精度（FP16）计算，减少内存使用量，在提高速度的同时，将对精度的影响降至最低。
    device	    str	        None	    指定验证设备 (cpu, cuda:0等）。可灵活利用CPU 或GPU 资源。
    dnn	        bool	    False	    如果 True使用 OpenCV 用于ONNX 模型推理的 DNN 模块，为 PyTorch 推理方法。
    plots	    bool	    False	    当设置为 True此外，它还能生成并保存预测结果与地面实况的对比图，以便对模型的性能进行可视化评估。
    rect	    bool	    True	    如果 True该软件使用矩形推理进行批处理，减少了填充，可能会提高速度和效率。
    split	    str	        val	        确定用于验证的数据集分割 (val, test或 train).可灵活选择数据段进行性能评估。
    project	    str	        None	    保存验证输出的项目目录名称。
    name	    str	        None	    验证运行的名称。用于在项目文件夹内创建一个子目录，用于存储验证日志和输出结果。
    """


if __name__ == '__main__':
    main()
