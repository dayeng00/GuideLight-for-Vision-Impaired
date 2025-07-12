"""
HRTF 3D音频处理器
移植自HFUT-MVNS-main/System_V1的3D音频功能
"""

import numpy as np
import librosa
import sounddevice as sd
import threading
import time
import logging
from scipy.signal import fftconvolve
import base64
import io
import wave
import json
import os

# 尝试导入SOFA文件处理库
try:
    from pysofaconventions import SOFAFile
    SOFA_AVAILABLE = True
except ImportError:
    SOFA_AVAILABLE = False
    logging.warning("pysofaconventions not available, using fallback HRTF")

logger = logging.getLogger(__name__)

class HRTFProcessor:
    """Head-Related Transfer Function (HRTF) 处理器"""
    
    def __init__(self, sofa_path='main/resources/HRTF/hrtf_nh94.sofa'):
        """
        初始化HRTF处理器
        
        Args:
            sofa_path: SOFA文件路径
        """
        self.sofa_path = sofa_path
        self.sofa = None
        self.positions = None
        self.sample_rate = 44100
        self.is_loaded = False
        
        # 加载HRTF数据
        self._load_hrtf()
        
        # 预定义的音频波形
        self.frequencies = [220, 330, 440, 660, 880]  # A3, E4, A4, E5, A5
        
    def _load_hrtf(self):
        """加载HRTF数据"""
        if not SOFA_AVAILABLE:
            logger.warning("SOFA库不可用，使用简化的HRTF实现")
            self._create_fallback_hrtf()
            return
            
        try:
            if os.path.exists(self.sofa_path):
                self.sofa = SOFAFile(self.sofa_path, 'r')
                self.positions = self.sofa.getVariableValue('SourcePosition')
                self.is_loaded = True
                logger.info(f"HRTF数据加载成功: {self.sofa_path}")
            else:
                logger.warning(f"SOFA文件不存在: {self.sofa_path}，使用简化HRTF")
                self._create_fallback_hrtf()
        except Exception as e:
            logger.error(f"加载HRTF数据失败: {e}")
            self._create_fallback_hrtf()
    
    def _create_fallback_hrtf(self):
        """创建简化的HRTF实现"""
        # 创建简化的位置数据 (方位角, 俯仰角, 距离)
        azimuths = np.arange(0, 360, 15)  # 每15度一个方位角
        elevations = np.arange(-40, 90, 10)  # 俯仰角范围
        
        self.positions = []
        for az in azimuths:
            for el in elevations:
                self.positions.append([az, el, 1.0])
        
        self.positions = np.array(self.positions)
        self.is_loaded = True
        logger.info("使用简化HRTF实现")
    
    def get_lr_hrtf(self, pitch_angle, azimuth_angle):
        """
        获取左右耳的HRTF
        
        Args:
            pitch_angle: 俯仰角
            azimuth_angle: 方位角
            
        Returns:
            (hrtf_left, hrtf_right): 左右耳的HRTF
        """
        if not self.is_loaded:
            return self._fallback_hrtf(pitch_angle, azimuth_angle)
            
        if self.sofa is None:
            return self._fallback_hrtf(pitch_angle, azimuth_angle)
        
        try:
            # 找到最接近的HRTF位置
            distances = np.sqrt(
                (self.positions[:, 0] - azimuth_angle)**2 + 
                (self.positions[:, 1] - pitch_angle)**2
            )
            closest_index = np.argmin(distances)
            
            # 获取HRTF数据
            hrtf_left = self.sofa.getDataIR()[closest_index, 0, :]
            hrtf_right = self.sofa.getDataIR()[closest_index, 1, :]
            
            return hrtf_left, hrtf_right
            
        except Exception as e:
            logger.error(f"获取HRTF失败: {e}")
            return self._fallback_hrtf(pitch_angle, azimuth_angle)
    
    def _fallback_hrtf(self, pitch_angle, azimuth_angle):
        """简化的HRTF实现"""
        # 生成简单的延迟和增益差异
        delay_samples = int(abs(azimuth_angle) / 180 * 10)  # 最大10采样点延迟
        gain_left = 1.0 - abs(azimuth_angle) / 360
        gain_right = 1.0 - abs(azimuth_angle - 180) / 360
        
        # 创建简单的脉冲响应
        hrtf_length = 128
        hrtf_left = np.zeros(hrtf_length)
        hrtf_right = np.zeros(hrtf_length)
        
        hrtf_left[delay_samples] = gain_left
        hrtf_right[0] = gain_right
        
        return hrtf_left, hrtf_right


class Audio3DProcessor:
    """3D音频处理器"""
    
    def __init__(self, hrtf_path='main/resources/HRTF/hrtf_nh94.sofa'):
        """
        初始化3D音频处理器
        
        Args:
            hrtf_path: HRTF文件路径
        """
        self.hrtf_processor = HRTFProcessor(hrtf_path)
        self.sample_rate = 44100
        self.is_playing = False
        self.audio_thread = None
        self.audio_queue = []
        self.queue_lock = threading.Lock()
        
        # 加载预设音频文件
        self._load_audio_samples()
        
        # 初始化音频流
        self.stream = None
        self._init_audio_stream()
    
    def _load_audio_samples(self):
        """加载音频样本"""
        self.audio_samples = {}
        
        # 尝试加载音频文件
        audio_files = {
            'beep': 'main/resources/sounds/beep2.wav',
            'alert': 'main/resources/sounds/alert.wav',
            'notification': 'main/resources/sounds/notification.wav'
        }
        
        for name, path in audio_files.items():
            try:
                if os.path.exists(path):
                    wave_data, sr = librosa.load(path, sr=self.sample_rate, mono=False)
                    self.audio_samples[name] = wave_data
                    logger.info(f"加载音频文件: {name}")
                else:
                    # 生成默认音频
                    self.audio_samples[name] = self._generate_default_audio(name)
                    logger.info(f"生成默认音频: {name}")
            except Exception as e:
                logger.error(f"加载音频文件失败 {name}: {e}")
                self.audio_samples[name] = self._generate_default_audio(name)
    
    def _generate_default_audio(self, audio_type):
        """生成默认音频"""
        duration = 0.5  # 0.5秒
        t = np.linspace(0, duration, int(self.sample_rate * duration), endpoint=False)
        
        if audio_type == 'beep':
            frequency = 440  # A4
            wave = np.sin(2 * np.pi * frequency * t)
        elif audio_type == 'alert':
            frequency = 880  # A5
            wave = np.sin(2 * np.pi * frequency * t) * np.sin(2 * np.pi * 10 * t)
        else:
            frequency = 220  # A3
            wave = np.sin(2 * np.pi * frequency * t)
        
        # 创建立体声
        if wave.ndim == 1:
            stereo_wave = np.vstack([wave, wave])
        else:
            stereo_wave = wave
            
        return stereo_wave
    
    def _init_audio_stream(self):
        """初始化音频流"""
        try:
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=2,
                callback=self._audio_callback,
                blocksize=1024
            )
            self.stream.start()
            logger.info("音频流初始化成功")
        except Exception as e:
            logger.error(f"音频流初始化失败: {e}")
            self.stream = None
    
    def _audio_callback(self, outdata, frames, time, status):
        """音频回调函数"""
        if status:
            logger.warning(f"音频流状态: {status}")
        
        with self.queue_lock:
            if self.audio_queue:
                # 播放队列中的音频
                audio_data = self.audio_queue.pop(0)
                if len(audio_data) >= frames:
                    outdata[:] = audio_data[:frames].T
                else:
                    outdata[:len(audio_data)] = audio_data.T
                    outdata[len(audio_data):] = 0
            else:
                # 静音
                outdata[:] = 0
    
    def process_3d_audio(self, azimuth_pitch_data, audio_type='beep'):
        """
        处理3D音频
        
        Args:
            azimuth_pitch_data: 方位角和俯仰角数据列表
            audio_type: 音频类型
            
        Returns:
            处理后的音频数据
        """
        if not azimuth_pitch_data:
            return None
        
        # 限制同时播放的音频数量
        if len(azimuth_pitch_data) > 3:
            # 按距离排序，取最近的3个
            azimuth_pitch_data.sort(key=lambda x: x[3] if len(x) > 3 else 0)
            azimuth_pitch_data = azimuth_pitch_data[:3]
        
        processed_audio = []
        
        for i, ap_data in enumerate(azimuth_pitch_data):
            if len(ap_data) >= 4:
                name, azimuth_angle, pitch_angle, distance = ap_data
                
                # 获取HRTF
                hrtf_left, hrtf_right = self.hrtf_processor.get_lr_hrtf(
                    pitch_angle, azimuth_angle
                )
                
                # 获取音频样本
                if audio_type in self.audio_samples:
                    wave = self.audio_samples[audio_type]
                else:
                    wave = self.audio_samples['beep']
                
                # 应用距离衰减
                distance_factor = max(0.1, 1.0 / ((distance / 100) ** 2))
                
                # 卷积处理
                if wave.ndim == 1:
                    convolved_left = fftconvolve(wave, hrtf_left, mode='same') * distance_factor
                    convolved_right = fftconvolve(wave, hrtf_right, mode='same') * distance_factor
                else:
                    convolved_left = fftconvolve(wave[0, :], hrtf_left, mode='same') * distance_factor
                    convolved_right = fftconvolve(wave[1, :], hrtf_right, mode='same') * distance_factor
                
                # 创建立体声信号
                stereo_signal = np.vstack([convolved_left, convolved_right])
                processed_audio.append({
                    'name': name,
                    'azimuth': azimuth_angle,
                    'pitch': pitch_angle,
                    'distance': distance,
                    'audio_data': stereo_signal,
                    'delay': i * 0.1  # 延迟播放
                })
        
        return processed_audio
    
    def play_3d_audio(self, azimuth_pitch_data, audio_type='beep'):
        """
        播放3D音频
        
        Args:
            azimuth_pitch_data: 方位角和俯仰角数据
            audio_type: 音频类型
        """
        if not self.stream:
            logger.error("音频流未初始化")
            return
        
        processed_audio = self.process_3d_audio(azimuth_pitch_data, audio_type)
        
        if processed_audio:
            with self.queue_lock:
                for audio_item in processed_audio:
                    # 添加到播放队列
                    self.audio_queue.append(audio_item['audio_data'])
    
    def generate_audio_visualization(self, audio_data):
        """
        生成音频可视化数据
        
        Args:
            audio_data: 音频数据
            
        Returns:
            可视化数据
        """
        if audio_data is None:
            return None
        
        # 计算频谱
        if audio_data.ndim == 2:
            left_channel = audio_data[0, :]
            right_channel = audio_data[1, :]
        else:
            left_channel = right_channel = audio_data
        
        # FFT分析
        fft_left = np.fft.fft(left_channel)
        fft_right = np.fft.fft(right_channel)
        
        # 计算幅度谱
        magnitude_left = np.abs(fft_left)[:len(fft_left)//2]
        magnitude_right = np.abs(fft_right)[:len(fft_right)//2]
        
        # 频率轴
        freqs = np.fft.fftfreq(len(left_channel), 1/self.sample_rate)[:len(left_channel)//2]
        
        return {
            'left_channel': left_channel.tolist(),
            'right_channel': right_channel.tolist(),
            'magnitude_left': magnitude_left.tolist(),
            'magnitude_right': magnitude_right.tolist(),
            'frequencies': freqs.tolist(),
            'sample_rate': self.sample_rate
        }
    
    def create_audio_response(self, audio_data, format='wav'):
        """
        创建音频响应数据
        
        Args:
            audio_data: 音频数据
            format: 音频格式
            
        Returns:
            Base64编码的音频数据
        """
        if audio_data is None:
            return None
        
        try:
            # 转换为16位整数
            if audio_data.ndim == 2:
                audio_int16 = (audio_data.T * 32767).astype(np.int16)
            else:
                audio_int16 = (audio_data * 32767).astype(np.int16)
            
            # 创建WAV文件
            buffer = io.BytesIO()
            with wave.open(buffer, 'wb') as wav_file:
                wav_file.setnchannels(2 if audio_data.ndim == 2 else 1)
                wav_file.setsampwidth(2)  # 16位
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_int16.tobytes())
            
            # Base64编码
            audio_bytes = buffer.getvalue()
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            return {
                'audio_data': audio_base64,
                'format': format,
                'sample_rate': self.sample_rate,
                'channels': 2 if audio_data.ndim == 2 else 1
            }
            
        except Exception as e:
            logger.error(f"创建音频响应失败: {e}")
            return None
    
    def stop_audio(self):
        """停止音频播放"""
        with self.queue_lock:
            self.audio_queue.clear()
        
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
                logger.info("音频流已停止")
            except Exception as e:
                logger.error(f"停止音频流失败: {e}")
    
    def get_status(self):
        """获取音频处理器状态"""
        return {
            'hrtf_loaded': self.hrtf_processor.is_loaded,
            'stream_active': self.stream is not None and self.stream.active,
            'queue_size': len(self.audio_queue),
            'audio_samples': list(self.audio_samples.keys())
        }


class AudioManager:
    """音频管理器"""
    
    def __init__(self):
        self.audio_processor = Audio3DProcessor()
        self.is_active = False
        self.processing_thread = None
        self.audio_data_queue = []
        self.queue_lock = threading.Lock()
        
    def start(self):
        """启动音频管理器"""
        if not self.is_active:
            self.is_active = True
            self.processing_thread = threading.Thread(target=self._processing_loop)
            self.processing_thread.daemon = True
            self.processing_thread.start()
            logger.info("音频管理器已启动")
    
    def stop(self):
        """停止音频管理器"""
        self.is_active = False
        if self.processing_thread:
            self.processing_thread.join(timeout=1)
        
        self.audio_processor.stop_audio()
        logger.info("音频管理器已停止")
    
    def _processing_loop(self):
        """音频处理循环"""
        while self.is_active:
            try:
                with self.queue_lock:
                    if self.audio_data_queue:
                        audio_data = self.audio_data_queue.pop(0)
                        self.audio_processor.play_3d_audio(
                            audio_data['azimuth_pitch_data'],
                            audio_data.get('audio_type', 'beep')
                        )
                
                time.sleep(0.1)  # 100ms间隔
                
            except Exception as e:
                logger.error(f"音频处理循环错误: {e}")
                time.sleep(0.5)
    
    def add_audio_data(self, azimuth_pitch_data, audio_type='beep'):
        """添加音频数据到处理队列"""
        with self.queue_lock:
            self.audio_data_queue.append({
                'azimuth_pitch_data': azimuth_pitch_data,
                'audio_type': audio_type,
                'timestamp': time.time()
            })
    
    def get_audio_visualization(self, azimuth_pitch_data, audio_type='beep'):
        """获取音频可视化数据"""
        processed_audio = self.audio_processor.process_3d_audio(azimuth_pitch_data, audio_type)
        
        if processed_audio:
            # 合并所有音频数据进行可视化
            combined_audio = np.zeros((2, 0))
            for audio_item in processed_audio:
                combined_audio = np.concatenate([combined_audio, audio_item['audio_data']], axis=1)
            
            return self.audio_processor.generate_audio_visualization(combined_audio)
        
        return None
    
    def get_status(self):
        """获取管理器状态"""
        return {
            'active': self.is_active,
            'queue_size': len(self.audio_data_queue),
            'processor_status': self.audio_processor.get_status()
        } 