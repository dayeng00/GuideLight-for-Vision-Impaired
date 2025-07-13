"""
视差估计
"""
#!/usr/bin/env python3

import cv2
import time
import depthai as dai
import numpy as np
#
if __name__ == "__main__":
    from video_show import VideoShowOAK
    from device_manager import device_manager
else:
    from utils.video_show import VideoShowOAK
    from utils.device_manager import device_manager
    from .global_frame_cache import get_global_frame_cache


class DisparityEstimator(VideoShowOAK):
    def __init__(self, extended_disparity=False, subpixel=False, lr_check=True,
                 camera_size=720, is_show_fps=True):
        """
        初始化StereoDepthEstimator类。

        参数:
        extended_disparity (bool): 是否启用扩展视差范围，默认为False
        subpixel (bool): 是否启用子像素精度，默认为False
        lr_check (bool): 是否启用左右视差检查，默认为True
        """
        super().__init__(camera_size, is_show_fps)
        self.extended_disparity = extended_disparity
        self.subpixel = subpixel
        self.lr_check = lr_check
        
        # 获取全局帧缓存
        self.global_cache = get_global_frame_cache()
        
        # 获取设备管理器
        self.device_manager = device_manager
        
        # 当前帧数据
        self.current_depth_frame = None
        self.last_processed_frame = None
        
        # 运行状态
        self.continue_running = True

        # 定义深度图节点（保留原有配置用于兼容性）
        self.depth = self.pipeline.create(dai.node.StereoDepth)
        self.xout = self.pipeline.create(dai.node.XLinkOut)

        self.xout.setStreamName("disparity")

        # 配置深度图节点的属性
        self.depth.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.DEFAULT)
        self.depth.initialConfig.setMedianFilter(dai.MedianFilter.KERNEL_7x7)
        self.depth.setLeftRightCheck(self.lr_check)
        self.depth.setExtendedDisparity(self.extended_disparity)
        self.depth.setSubpixel(self.subpixel)

        # 连接节点
        self.monoLeft.out.link(self.depth.left)
        self.monoRight.out.link(self.depth.right)
        self.depth.disparity.link(self.xout.input)
        self.device = None
        
        print("✅ 视差估计器初始化完成，使用全局帧缓存")

    def run(self):
        """
        启动深度估计并显示视差图 - 使用全局帧缓存
        """
        print("🎥 开始视差估计视频流生成...")
        
        # 确保设备管理器正在运行
        if not self.device_manager.is_running():
            print("⚠️ 设备管理器未运行，尝试启动...")
            try:
                self.device_manager.start()
                time.sleep(2)  # 等待设备启动
            except Exception as e:
                print(f"❌ 启动设备管理器失败: {e}")
                return

        while self.continue_running:
            try:
                # 从全局帧缓存获取深度数据
                current_frames = self.global_cache.get_current_frames(['depth'])
                
                if 'depth' not in current_frames or current_frames['depth'] is None:
                    # 如果没有深度数据，等待一下
                    time.sleep(0.05)
                    continue
                
                depth_frame = current_frames['depth']
                
                # 检查帧是否有效
                if depth_frame is None or depth_frame.size == 0:
                    print("收到空深度帧，跳过处理")
                    time.sleep(0.01)
                    continue
                
                # 处理深度帧为视差图
                processed_frame = self._process_depth_to_disparity(depth_frame)
                
                if processed_frame is not None:
                    # 编码为JPEG
                    _, buffer = cv2.imencode('.jpg', processed_frame)
                    frame_bytes = buffer.tobytes()

                    # 以 MJPEG 格式返回
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                else:
                    # 如果处理失败，使用上一帧或生成占位符
                    if self.last_processed_frame is not None:
                        _, buffer = cv2.imencode('.jpg', self.last_processed_frame)
                        frame_bytes = buffer.tobytes()
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    else:
                        # 生成占位符帧
                        placeholder_frame = self._generate_placeholder_frame()
                        _, buffer = cv2.imencode('.jpg', placeholder_frame)
                        frame_bytes = buffer.tobytes()
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
                # 短暂休眠以控制帧率
                time.sleep(0.03)  # ~30fps
                
            except Exception as e:
                print(f"⚠️ 视差估计器处理错误: {e}")
                time.sleep(0.1)
        
        print("🎥 视差估计视频流生成已停止")

    def _process_depth_to_disparity(self, depth_frame):
        """将深度帧转换为视差图"""
        try:
            # 深度帧通常是毫米单位，需要转换为视差表示
            # 视差 = 基线 * 焦距 / 深度
            # 这里我们使用简化的转换方法
            
            # 将深度值转换为视差值（反比关系）
            # 避免除零错误
            depth_frame_safe = np.where(depth_frame > 0, depth_frame, 1)
            
            # 计算视差（使用简化公式）
            # 假设基线*焦距 = 7.5 * 882 = 6615（这是OAK-D的典型值）
            baseline_focal = 6615
            disparity = baseline_focal / depth_frame_safe
            
            # 将视差值标准化到0-255范围
            disparity_normalized = np.clip(disparity, 0, 255).astype(np.uint8)
            
            # 应用颜色映射增强可视化效果
            disparity_colored = cv2.applyColorMap(disparity_normalized, cv2.COLORMAP_JET)
            
            # 显示帧率
            disparity_with_fps = self.show_fps(disparity_colored)
            
            # 调整图像大小
            if self.camera_size > 0:
                new_width = int(self.camera_size * 1280 / 720)
                new_height = int(self.camera_size)
            else:
                new_width = 1280
                new_height = 720
            
            final_frame = cv2.resize(disparity_with_fps, (new_width, new_height))
            
            # 保存处理后的帧
            self.last_processed_frame = final_frame.copy()
            
            return final_frame
            
        except Exception as e:
            print(f"❌ 深度到视差转换失败: {e}")
            return None

    def _generate_placeholder_frame(self):
        """生成占位符帧"""
        try:
            # 创建占位符图像
            if self.camera_size > 0:
                width = int(self.camera_size * 1280 / 720)
                height = int(self.camera_size)
            else:
                width = 1280
                height = 720
            
            placeholder = np.zeros((height, width, 3), dtype=np.uint8)
            
            # 添加文本
            text = "Waiting for depth data..."
            text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
            text_x = (width - text_size[0]) // 2
            text_y = (height + text_size[1]) // 2
            
            cv2.putText(placeholder, text, (text_x, text_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            return placeholder
            
        except Exception as e:
            print(f"❌ 生成占位符帧失败: {e}")
            return np.zeros((720, 1280, 3), dtype=np.uint8)

    def shutdown(self):
        """安全关闭设备"""
        try:
            self.continue_running = False
            print("✅ 视差估计器已安全关闭")
        except Exception as e:
            print(f"❌ 关闭视差估计器时出错: {e}")


# 一个视频流
if __name__ == "__main__":
    # 创建StereoDepthEstimator实例并运行
    disparity_estimator = DisparityEstimator(camera_size=720)
    disparity_estimator.start()  # 创建了一个新线程
    time.sleep(20)
    disparity_estimator.close()
    disparity_estimator.join()
    print("Done")
