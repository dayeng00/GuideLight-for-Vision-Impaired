"""
该脚本无法运行 只是显示了导出模型时常用的代码
"""
from ultralytics import YOLO

# Load a model
model = YOLO("yolo11n.pt")  # load an official model
model = YOLO("path/to/best.pt")  # load a custom trained model

# Export the model
model.export(format="onnx")

"""
本表详细介绍了可用于将YOLO 模型导出为不同格式的配置和选项。
这些设置对于优化导出模型的性能、大小以及在不同平台和环境中的兼容性至关重要。
正确的配置可确保模型以最佳效率部署到预定应用中。

参数	        类型	            默认值	        说明
format	    str	            'torchscript'	导出模型的目标格式，例如 'onnx', 'torchscript', 'tensorflow'或其他，定义与各种部署环境的兼容性。
imgsz	    int 或 tuple	640	            模型输入所需的图像尺寸。对于正方形图像，可以是一个整数，或者是一个元组 (height, width) 了解具体尺寸。
keras	    bool	        False	        可导出为 Keras 格式 TensorFlowSavedModel的 Keras 格式，提供与TensorFlow serving 和 API 的兼容性。
optimize	bool	        False	        在导出到TorchScript 时，应用针对移动设备的优化，可能会减小模型大小并提高性能。
half	    bool	        False	        启用 FP16（半精度）量化，在支持的硬件上减小模型大小并可能加快推理速度。
int8	    bool	        False	        激活 INT8 量化，进一步压缩模型并加快推理速度，同时将精度损失降至最低，主要用于边缘设备。
dynamic	    bool	        False	        允许为ONNX 、TensorRT 和OpenVINO 导出动态输入尺寸，提高了处理不同图像尺寸的灵活性。
simplify	bool	        True	        简化了ONNX 输出的模型图。 onnxslim这可能会提高性能和兼容性。
opset	    int	            None	        指定ONNX opset 版本，以便与不同的ONNX 解析器和运行时兼容。如果未设置，则使用最新的支持版本。
workspace	float 或 None	None	        为TensorRT 优化设置最大工作区大小（GiB），以平衡内存使用和性能；使用 None TensorRT 进行自动分配，最高可达设备最大值。
nms	        bool	        False	        在CoreML 导出中添加非最大值抑制 (NMS)，这对精确高效的检测后处理至关重要。
batch	    int	            1	            指定导出模型的批量推理大小，或导出模型将同时处理的图像的最大数量。 predict 模式。
device	    str	            None	        指定导出设备：GPU (device=0）、CPU (device=cpu)、MPS for Apple silicon (device=mps）或NVIDIA Jetson 的 DLA (device=dla:0 或 device=dla:1).
data	    str	            coco8.yaml	    数据集配置文件的路径（默认值： coco8.yaml)，对量化至关重要。
"""

"""
格式	        format参数	模型	                    元数据	参数
PyTorch	    -	        yolo11n.pt	            ✅	    -
TorchScript	torchscript	yolo11n.torchscript	    ✅	    imgsz, optimize, nms, batch
ONNX	    onnx	    yolo11n.onnx	        ✅	    imgsz, half, dynamic, simplify, opset, nms, batch
OpenVINO	openvino	yolo11n_openvino_model/	✅	    imgsz, half, dynamic, int8, nms, batch, data
TensorRT	engine	    yolo11n.engine	        ✅	    imgsz, half, dynamic, simplify, workspace, int8, nms, batch, data
"""