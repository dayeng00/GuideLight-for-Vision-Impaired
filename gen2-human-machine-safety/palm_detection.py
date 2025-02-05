import numpy as np


class PalmDetection:
    def run_palm(self, frame, nn_data):
        """
        每个手掌检测结果是一个包含19个数字的张量：
            - ymin, xmin, ymax, xmax
            - 7个关键点的x、y坐标
            - 置信度得分
        :return: 经过非极大值抑制后的手掌检测框
        """
        # 如果神经网络数据为空，直接返回
        if nn_data is None:
            return
        # 定义输入图像的尺寸
        shape = (128, 128)
        # 定义关键点的数量
        num_keypoints = 7
        # 定义最小置信度阈值
        min_score_thresh = 0.7
        # 加载手掌检测的锚框
        anchors = np.load("anchors_palm.npy")

        # 运行神经网络，将数据转换为张量结果
        results = self.to_tensor_result(nn_data)

        # 对回归结果进行重塑，得到原始的边界框张量
        raw_box_tensor = results.get("regressors").reshape(-1, 896, 18)  # 回归
        # 对分类结果进行重塑，得到原始的得分张量
        raw_score_tensor = results.get("classificators").reshape(-1, 896, 1)  # 分类

        # 将原始的边界框和得分张量转换为检测结果
        detections = self.raw_to_detections(raw_box_tensor, raw_score_tensor, anchors, shape, num_keypoints)

        # 筛选出置信度高于阈值的手掌检测框，并将其坐标归一化到帧的尺寸
        palm_coords = [
            self.frame_norm(frame, *obj[:4])
            for det in detections
            for obj in det
            if obj[-1] > min_score_thresh
        ]

        # 筛选出置信度高于阈值的手掌检测框的置信度得分
        palm_confs = [
            obj[-1] for det in detections for obj in det if obj[-1] > min_score_thresh
        ]

        # 如果没有检测到符合条件的手掌，直接返回
        if len(palm_coords) == 0:
            return

        # 对筛选后的手掌检测框进行非极大值抑制，去除重叠的检测框
        return self.non_max_suppression(
            boxes=np.concatenate(palm_coords).reshape(-1, 4),
            probs=palm_confs,
            overlapThresh=0.1,
        )

    def sigmoid(self, x):
        """
        计算输入值的sigmoid函数值
        :param x: 输入值
        :return: sigmoid函数值
        """
        return (1.0 + np.tanh(0.5 * x)) * 0.5

    def decode_boxes(self, raw_boxes, anchors, shape, num_keypoints):
        """
        将预测结果转换为实际的坐标，使用锚框来处理整个批次的数据
        :param raw_boxes: 原始的边界框预测结果
        :param anchors: 锚框
        :param shape: 输入图像的尺寸
        :param num_keypoints: 关键点的数量
        :return: 解码后的边界框
        """
        # 创建一个与原始边界框相同形状的零数组
        boxes = np.zeros_like(raw_boxes)
        # 获取输入图像的宽度和高度
        x_scale, y_scale = shape

        # 计算边界框的中心点x坐标
        x_center = raw_boxes[..., 0] / x_scale * anchors[:, 2] + anchors[:, 0]
        # 计算边界框的中心点y坐标
        y_center = raw_boxes[..., 1] / y_scale * anchors[:, 3] + anchors[:, 1]

        # 计算边界框的宽度
        w = raw_boxes[..., 2] / x_scale * anchors[:, 2]
        # 计算边界框的高度
        h = raw_boxes[..., 3] / y_scale * anchors[:, 3]

        # 计算边界框的左上角x坐标
        boxes[..., 1] = y_center - h / 2.0  # xmin
        # 计算边界框的左上角y坐标
        boxes[..., 0] = x_center - w / 2.0  # ymin
        # 计算边界框的右下角x坐标
        boxes[..., 3] = y_center + h / 2.0  # xmax
        # 计算边界框的右下角y坐标
        boxes[..., 2] = x_center + w / 2.0  # ymax

        # 计算每个关键点的坐标
        for k in range(num_keypoints):
            offset = 4 + k * 2
            # 计算关键点的x坐标
            keypoint_x = raw_boxes[..., offset] / x_scale * anchors[:, 2] + anchors[:, 0]
            # 计算关键点的y坐标
            keypoint_y = (
                    raw_boxes[..., offset + 1] / y_scale * anchors[:, 3] + anchors[:, 1]
            )
            boxes[..., offset] = keypoint_x
            boxes[..., offset + 1] = keypoint_y

        return boxes

    def raw_to_detections(self, raw_box_tensor, raw_score_tensor, anchors_, shape, num_keypoints):
        """
        此函数将两个“原始”张量转换为合适的检测结果。
        返回一个列表，列表中的每个元素是一个(num_detections, 17)的张量，对应批次中的每张图像。

        此函数基于以下源代码：
        mediapipe/calculators/tflite/tflite_tensors_to_detections_calculator.cc
        mediapipe/calculators/tflite/tflite_tensors_to_detections_calculator.proto
        :param raw_box_tensor: 原始的边界框张量
        :param raw_score_tensor: 原始的得分张量
        :param anchors_: 锚框
        :param shape: 输入图像的尺寸
        :param num_keypoints: 关键点的数量
        :return: 转换后的检测结果列表
        """
        # 解码原始的边界框张量
        detection_boxes = self.decode_boxes(raw_box_tensor, anchors_, shape, num_keypoints)
        # 对原始的得分张量应用sigmoid函数，并去除最后一个维度
        detection_scores = self.sigmoid(raw_score_tensor).squeeze(-1)
        # 初始化输出检测结果列表
        output_detections = []
        # 遍历批次中的每张图像
        for i in range(raw_box_tensor.shape[0]):
            # 获取当前图像的边界框
            boxes = detection_boxes[i]
            # 获取当前图像的得分，并增加一个维度
            scores = np.expand_dims(detection_scores[i], -1)
            # 将边界框和得分拼接在一起，并添加到输出列表中
            output_detections.append(np.concatenate((boxes, scores), -1))
        return output_detections

    def non_max_suppression(self, boxes, probs=None, angles=None, overlapThresh=0.3):
        """
        非极大值抑制函数，用于去除重叠的检测框
        :param boxes: 检测框数组
        :param probs: 检测框的置信度得分
        :param angles: 检测框的角度（可选）
        :param overlapThresh: 重叠阈值
        :return: 经过非极大值抑制后的检测框和角度（如果提供了角度）
        """
        # 如果检测框数量为0，返回空列表
        if len(boxes) == 0:
            return [], []

        # 如果检测框的数据类型为整数，将其转换为浮点数
        if boxes.dtype.kind == "i":
            boxes = boxes.astype("float")

        # 初始化选择的检测框索引列表
        pick = []

        # 获取检测框的左上角x坐标
        x1 = boxes[:, 0]
        # 获取检测框的左上角y坐标
        y1 = boxes[:, 1]
        # 获取检测框的右下角x坐标
        x2 = boxes[:, 2]
        # 获取检测框的右下角y坐标
        y2 = boxes[:, 3]

        # 计算每个检测框的面积
        area = (x2 - x1 + 1) * (y2 - y1 + 1)
        # 初始化排序索引，默认为右下角y坐标
        idxs = y2

        # 如果提供了置信度得分，使用置信度得分进行排序
        if probs is not None:
            idxs = probs

        # 对索引进行排序
        idxs = np.argsort(idxs)

        # 循环处理排序后的索引
        while len(idxs) > 0:
            # 获取最后一个索引
            last = len(idxs) - 1
            # 获取当前选择的检测框索引
            i = idxs[last]
            # 将当前选择的检测框索引添加到选择列表中
            pick.append(i)

            # 计算当前选择的检测框与其他检测框的重叠区域的左上角x坐标
            xx1 = np.maximum(x1[i], x1[idxs[:last]])
            # 计算当前选择的检测框与其他检测框的重叠区域的左上角y坐标
            yy1 = np.maximum(y1[i], y1[idxs[:last]])
            # 计算当前选择的检测框与其他检测框的重叠区域的右下角x坐标
            xx2 = np.minimum(x2[i], x2[idxs[:last]])
            # 计算当前选择的检测框与其他检测框的重叠区域的右下角y坐标
            yy2 = np.minimum(y2[i], y2[idxs[:last]])

            # 计算重叠区域的宽度
            w = np.maximum(0, xx2 - xx1 + 1)
            # 计算重叠区域的高度
            h = np.maximum(0, yy2 - yy1 + 1)

            # 计算重叠区域的面积与其他检测框面积的比值
            overlap = (w * h) / area[idxs[:last]]

            # 删除当前选择的检测框索引和重叠度高于阈值的检测框索引
            idxs = np.delete(
                idxs, np.concatenate(([last], np.where(overlap > overlapThresh)[0]))
            )

        # 如果提供了角度，返回经过非极大值抑制后的检测框和角度
        if angles is not None:
            return boxes[pick].astype("int"), angles[pick]
        # 否则，返回经过非极大值抑制后的检测框
        return boxes[pick].astype("int")

    def to_tensor_result(self, packet):
        """
        将数据包中的数据转换为张量结果
        :param packet: 数据包
        :return: 张量结果字典
        """
        return {
            name: np.array(packet.getLayerFp16(name))
            for name in [tensor.name for tensor in packet.getRaw().tensors]
        }

    def frame_norm(self, frame, *xy_vals):
        """
        神经网络输出的边界框位置在<0..1>范围内，需要根据帧的宽度和高度进行归一化
        :param frame: 输入帧
        :param xy_vals: 边界框位置
        :return: 归一化后的边界框位置
        """
        return (
                np.clip(np.array(xy_vals), 0, 1)
                * np.array(frame.shape[:2] * (len(xy_vals) // 2))[::-1]
        ).astype(int)
