"""
代码的主要功能：改代码通过电脑摄像头捕获图象，然后使用asyncio库实现异步网络通信，将RGB图象和深度图象传给服务器，
然后接收服务器通过yolo目标检测和道路分割后的数据标记在图像上然后进行显示

主要内容：
摄像头捕获：通过OpenCV捕获摄像头图像。
图像处理：对捕获的图像进行裁剪和压缩。
网络通信：将处理后的图像数据发送到服务器，并接收服务器返回的处理结果。
结果展示：在图像上绘制检测结果（如检测框、道路标记等），并显示处理后的图像。
异步编程：使用asyncio库实现异步网络通信，提高程序的响应速度。

代码的关键点：
图像压缩：使用cv2.imencode将图像压缩为JPEG格式，减少网络传输的数据量。
数据序列化：使用pickle库将数据序列化为字节流，便于网络传输。
异步通信：使用asyncio库实现异步网络通信，避免阻塞主线程。
结果展示：在图像上绘制检测结果，并显示处理时间。
这段代码适用于需要实时处理摄像头图像并显示处理结果的场景，如自动驾驶、智能监控等。
"""

import socket  # 导入socket库，用于网络通信
import pickle  # 导入pickle库，用于序列化和反序列化Python对象
import time  # 导入time库，用于时间相关的操作
import cv2  # 导入OpenCV库，用于图像处理
import numpy as np  # 导入numpy库，用于数值计算
import random  # 导入random库，用于生成随机数
import threading  # 导入threading库，用于多线程操作
import asyncio  # 导入asyncio库，用于异步编程

# 设置客户端参数
HOST = '127.0.0.1'  # 服务器的主机地址
PORT = 65432  # 服务器的端口号

# 创建一个套接字
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 创建一个TCP套接字
# socket.AF_INET：这是地址族（Address Family）的一种表示，AF_INET 表示使用 IPv4 地址族，意味着该套接字将使用 IPv4 地址进行通信。
# socket.SOCK_STREAM：表示使用面向连接的 TCP（传输控制协议）套接字。TCP 提供可靠的、基于字节流的通信，确保数据在传输过程中不会丢失、乱序。
client_socket.connect((HOST, PORT))  # 连接到指定的服务器地址和端口


def generate_random_color(seed=None):
    """生成并返回一个随机颜色"""
    random.seed(seed)  # 设置随机数种子
    red = random.randint(0, 255)  # 生成0到255之间的随机红色值
    green = random.randint(0, 255)  # 生成0到255之间的随机绿色值
    blue = random.randint(0, 255)  # 生成0到255之间的随机蓝色值
    return red, green, blue  # 返回生成的RGB颜色值


async def send_images(rgb_image, depth_image):
    # 压缩RGB图像
    _, rgb_image_compressed = cv2.imencode('.jpg', rgb_image, [cv2.IMWRITE_JPEG_QUALITY, 80])  # 将RGB图像压缩为JPEG格式，质量为80
    rgb_image_compressed = rgb_image_compressed.tobytes()  # 将压缩后的图像转换为字节流

    # 构建数据包
    # data = {'rgb': rgb_image_compressed, 'depth': depth_image}  # 原始数据包，包含RGB和深度图像
    data = {'rgb': rgb_image_compressed}  # 只包含压缩后的RGB图像
    serialized_data = pickle.dumps(data)  # 将数据包序列化为字节流
    serialized_data += b'$END#'  # 添加结束标记，用于标识数据包的结束

    loop = asyncio.get_event_loop()  # 获取当前事件循环
    await loop.sock_sendall(client_socket, serialized_data)  # 异步发送序列化后的数据包到服务器
    # loop.sock_sendall 事件循环对象的一个方法，用于异步地将数据发送到指定的套接字

    # 接收结果
    received_data = b''  # 初始化接收数据的字节流
    while True:
        packet = await loop.sock_recv(client_socket, 4096)  # 异步接收数据包，每次最多接收4096字节
        if packet.endswith(b'#END$'):  # 如果接收到结束标记
            received_data += packet[:-5]  # 将数据包（去掉结束标记）添加到接收数据中
            break  # 结束接收循环
        received_data += packet  # 将接收到的数据包添加到接收数据中

    # 反序列化结果
    result = pickle.loads(received_data)  # 将接收到的字节流反序列化为Python对象
    return result  # 返回反序列化后的结果


async def capture_and_send():
    try:
        # 打开摄像头（0表示默认摄像头）
        cap = cv2.VideoCapture(0)  # 打开默认摄像头

        if not cap.isOpened():  # 检查摄像头是否成功打开
            print("Cannot open camera")  # 如果未成功打开，打印错误信息
            return

        while True:
            t0 = time.time()  # 记录当前时间
            # 从摄像头读取一帧
            ret, frame = cap.read()  # 读取一帧图像 ret类型:Bool

            if not ret:  # 如果读取失败
                print("Can't receive frame (stream end?). Exiting ...")  # 打印错误信息
                break  # 退出循环

            start_row = (480 - 360) // 2  # 计算裁剪的起始行
            frame = frame[start_row:start_row + 360, 0:640]  # 裁剪图像，使其大小为640x360

            # 假设深度图像是一个全零数组（需要实际深度摄像头来获取真实数据）
            depth_image = np.zeros((frame.shape[0], frame.shape[1]))  # 创建一个与RGB图像大小相同的全零数组作为深度图像

            # 发送图像并接收结果
            received_data = await send_images(frame, depth_image)  # 异步发送图像并接收处理结果
            yolo_result = received_data['yolo']  # 获取YOLO检测结果
            road_result = received_data['road']  # 获取道路检测结果
            frame[road_result == 1] = (233, 233, 233)  # 将道路检测结果在图像上标记为灰色
            for i in range(len(yolo_result)):  # 遍历YOLO检测结果
                box = yolo_result.boxes[i]  # 获取检测框
                mask = yolo_result.masks[i].data[0][12: -12, :].int().cpu()  # 获取检测框的掩码
                bbox = box.xyxy.cpu().round().int().tolist()[0]  # 获取检测框的坐标
                name = yolo_result.names[box.cls.cpu().round().int().tolist()[0]]  # 获取检测框的类别名称
                color = generate_random_color(int(box.cls.cpu()))  # 根据类别生成随机颜色
                cv2.rectangle(frame, bbox[:2], bbox[2:], color, 2)  # 在图像上绘制检测框
            cv2.putText(frame, f"{int((time.time() - t0) * 1000)}ms", (0, 30), cv2.FONT_HERSHEY_TRIPLEX, 0.8,
                        (0, 0, 255))  # 在图像上绘制处理时间
            # 显示捕获的图像
            cv2.imshow('frame', frame)  # 显示处理后的图像

            if cv2.waitKey(1) == ord('q'):  # 如果按下'q'键
                break  # 退出循环

    except KeyboardInterrupt:  # 捕获键盘中断异常
        print("Client stopped.")  # 打印客户端停止信息

    finally:
        # 释放摄像头并关闭窗口
        cap.release()  # 释放摄像头资源
        cv2.destroyAllWindows()  # 关闭所有OpenCV窗口
        client_socket.close()  # 关闭客户端套接字


# 启动捕获和发送任务
asyncio.run(capture_and_send())  # 运行异步任务，启动摄像头捕获和图像发送
