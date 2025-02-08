# Gen2 Human-Machine safety

This example demonstrates how to detect dangerous objects and calculates distance to a human hand (palm).
It uses mobilenet spatial detection netork node to get spatial coordinates of dangerous objects and palm
detection network to detect human palm. Script `palm_detection.py` handles decoding of the [palm detection network](https://google.github.io/mediapipe/solutions/hands#palm-detection-model) and returns the bounding box of a detected palm.
Instead of sending the bounding box of the detected palm back to device to the`SpatialLocationCalculator`, this example
uses function `def calc_spatials(self, bbox, depth):` to calculate spatial coordinates on the host (using bbox and depth map). After we have spatial coordiantes of both the dangerous object and the palm, we calculate the spatial distance of the two and if it's blow the threshold `WARNING_DIST`, it will output a warning.

本示例展示了如何检测危险物体并计算其与人类手部（手掌）之间的距离。
它使用 MobileNet 空间检测网络节点来获取危险物体的空间坐标，并使用手掌检测网络来检测人类手掌。脚本 palm_detection.py 负责对手掌检测网络的输出进行解码，并返回检测到的手掌的边界框。
与将检测到的手掌的边界框发送回设备上的 SpatialLocationCalculator 不同，本示例使用 def calc_spatials(self, bbox, depth): 函数在主机上（利用边界框和深度图）计算空间坐标。在获取了危险物体和手掌的空间坐标后，我们会计算两者之间的空间距离。如果该距离低于阈值 WARNING_DIST，则会输出一条警告信息。

## Demo:

[![Watch the demo](https://user-images.githubusercontent.com/18037362/121198687-a1202f00-c872-11eb-949a-df9f1167494f.gif)](https://www.youtube.com/watch?v=BcjZLaCYGi4)

## Pre-requisites

Install requirements:
```bash
python3 -m pip install -r requirements.txt
```

## Usage

```bash
   python3 main.py
```

> Press 'q' to exit the program.
