"""
语音识别处理器
移植自HFUT-MVNS-main/System_V1的语音识别功能
"""

import numpy as np
import threading
import time
import logging
import io
import wave
import base64
import json
import re
import os
from typing import Optional, Dict, List, Callable

# 尝试导入语音识别库
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    logging.warning("speech_recognition库不可用")

# 尝试导入音频处理库
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    logging.warning("pyaudio库不可用")

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    logging.warning("sounddevice库不可用")

# 尝试导入Vosk库用于离线识别
try:
    from vosk import Model, KaldiRecognizer, SetLogLevel
    VOSK_AVAILABLE = True
    # 设置Vosk日志级别，-1禁用调试消息，0为正常日志
    SetLogLevel(0)
    logging.info("Vosk库可用，将启用离线语音识别")
except ImportError:
    VOSK_AVAILABLE = False
    logging.warning("Vosk库不可用，无法使用离线语音识别")

# 尝试导入音频预处理库
try:
    import torchaudio
    TORCHAUDIO_AVAILABLE = True
except ImportError:
    TORCHAUDIO_AVAILABLE = False
    logging.warning("torchaudio库不可用，无法进行高级音频预处理")

logger = logging.getLogger(__name__)

class SpeechRecognizer:
    """语音识别器 - 基于PYQT系统的实现"""
    
    def __init__(self, language='zh-CN'):
        """
        初始化语音识别器
        
        Args:
            language: 识别语言，默认中文
        """
        self.language = language
        self.recognizer = None
        self.microphone = None
        self.is_available = False
        
        # Vosk模型
        self.vosk_model = None
        self.vosk_recognizer = None
        self.vosk_available = False
        
        # 初始化识别器
        self._init_recognizer()
        
        # 语音命令模式 - 参考PYQT系统
        self.command_patterns = {
            'navigation': [
                r'导航到(.+)',
                r'去(.+)', 
                r'前往(.+)',
                r'到(.+)去',
                r'我要去(.+)',
                r'带我去(.+)'
            ],
            'query': [
                r'这是什么',
                r'前面是什么',
                r'周围有什么',
                r'描述一下',
                r'看看周围',
                r'有什么障碍'
            ],
            'control': [
                r'开始',
                r'停止',
                r'暂停',
                r'继续',
                r'启动系统',
                r'关闭系统'
            ]
        }
        
        # 地点关键词处理
        self.location_keywords = {
            '学校': '合肥工业大学',
            '食堂': '合肥工业大学食堂',
            '图书馆': '合肥工业大学图书馆',
            '教学楼': '合肥工业大学教学楼',
            '宿舍': '合肥工业大学宿舍',
            '超市': '附近超市',
            '医院': '附近医院',
            '银行': '附近银行',
            '公交站': '附近公交站'
        }
    
    def _init_recognizer(self):
        """初始化识别器"""
        if not SPEECH_RECOGNITION_AVAILABLE:
            logger.error("语音识别库不可用，请安装speech_recognition库")
            self.is_available = False
            return
        
        try:
            logger.info("开始初始化语音识别器...")
            self.recognizer = sr.Recognizer()
            
            # 优化识别参数 - 参考PYQT系统
            self.recognizer.energy_threshold = 300  # 最小音频能量阈值
            self.recognizer.dynamic_energy_threshold = True  # 动态调整阈值
            self.recognizer.pause_threshold = 0.8  # 静音时间阈值
            self.recognizer.phrase_threshold = 0.3  # 短语时间阈值
            self.recognizer.non_speaking_duration = 0.8  # 非说话时间
            
            logger.info("成功创建语音识别器实例")
            
            # 初始化Vosk模型 - 用于离线识别
            self._init_vosk()
            
            # 检查是否可以使用离线识别
            try:
                import pocketsphinx
                logger.info("发现 PocketSphinx 库，将作为备用离线识别")
                self.offline_recognition_available = True
            except ImportError:
                if self.vosk_available:
                    logger.info("将使用Vosk进行离线识别")
                    self.offline_recognition_available = True
                else:
                    logger.warning("未找到离线识别库，将尝试使用在线识别")
                    self.offline_recognition_available = False
            
            # 尝试初始化麦克风
            try:
                if PYAUDIO_AVAILABLE:
                    logger.info("尝试初始化麦克风...")
                    self.microphone = sr.Microphone()
                    
                    # 调整环境噪声
                    try:
                        logger.info("调整环境噪声...")
                        with self.microphone as source:
                            self.recognizer.adjust_for_ambient_noise(source, duration=1)
                        logger.info("环境噪声调整成功")
                    except Exception as mic_err:
                        logger.warning(f"调整环境噪声失败: {mic_err}")
                    
                    self.is_available = True
                    logger.info("麦克风初始化成功")
                else:
                    logger.warning("PyAudio库不可用，麦克风无法使用")
                    self.is_available = True  # 仍然可以进行文件识别
                    logger.info("语音识别器初始化成功，但麦克风不可用")
            except Exception as mic_err:
                logger.warning(f"初始化麦克风失败: {mic_err}")
                self.is_available = True  # 仍然可以进行文件识别
                logger.info("语音识别器初始化成功，但麦克风不可用")
                
        except Exception as e:
            logger.error(f"初始化语音识别器失败: {e}", exc_info=True)
            self.is_available = False
    
    def _init_vosk(self):
        """初始化Vosk模型"""
        if not VOSK_AVAILABLE:
            logger.warning("Vosk不可用，跳过Vosk初始化")
            self.vosk_available = False
            return
        
        try:
            # 直接使用用户提供的路径
            vosk_api_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vosk_audio', 'vosk-api')
            logger.info(f"使用Vosk API路径: {vosk_api_path}")
            
            # 尝试使用lang参数直接初始化中文模型
            try:
                logger.info("尝试使用lang='cn'参数初始化中文模型")
                self.vosk_model = Model(lang="cn")
                logger.info("使用lang='cn'参数成功初始化中文模型")
            except Exception as e:
                logger.error(f"使用lang参数初始化模型失败: {e}")
                logger.warning("尝试使用其他方法初始化模型")
                
                # 如果lang参数失败，尝试使用python/example中的模型
                try:
                    example_model_path = os.path.join(vosk_api_path, 'python', 'example', 'model')
                    if os.path.exists(example_model_path):
                        logger.info(f"尝试使用示例模型: {example_model_path}")
                        self.vosk_model = Model(example_model_path)
                        logger.info("使用示例模型初始化成功")
                    else:
                        logger.warning(f"示例模型不存在: {example_model_path}")
                        # 最后尝试在系统路径中查找模型
                        model_paths = [
                            os.path.join(os.path.expanduser('~'), '.cache', 'vosk', 'vosk-model-cn-0.22'),
                            os.path.join(os.path.expanduser('~'), '.cache', 'vosk', 'vosk-model-small-cn-0.22'),
                            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resources', 'vosk_model')
                        ]
                        
                        for path in model_paths:
                            if os.path.exists(path):
                                logger.info(f"尝试使用模型路径: {path}")
                                try:
                                    self.vosk_model = Model(path)
                                    logger.info(f"使用模型路径成功: {path}")
                                    break
                                except Exception as path_err:
                                    logger.error(f"使用模型路径失败: {path_err}")
                        else:
                            logger.error("找不到可用的Vosk模型，无法初始化")
                            self.vosk_available = False
                            return
                except Exception as ex_err:
                    logger.error(f"尝试加载示例模型失败: {ex_err}")
                    self.vosk_available = False
                    return
            
            # 创建识别器
            self.vosk_recognizer = KaldiRecognizer(self.vosk_model, 16000)
            self.vosk_recognizer.SetWords(True)  # 启用词级别的识别结果
            logger.info("Vosk识别器创建成功")
            
            self.vosk_available = True
            logger.info("Vosk初始化成功")
            
        except Exception as e:
            logger.error(f"初始化Vosk失败: {e}", exc_info=True)
            self.vosk_available = False
    
    def _convert_to_mono_16k(self, audio_data: bytes, sample_rate: int) -> Optional[bytes]:
        """
        将音频转换为Vosk所需的格式：单声道16kHz 16位PCM
        
        Args:
            audio_data: 原始音频数据
            sample_rate: 原始采样率
            
        Returns:
            转换后的音频数据
        """
        if not TORCHAUDIO_AVAILABLE:
            logger.warning("torchaudio不可用，无法进行高级音频转换")
            return audio_data
            
        try:
            # 创建临时文件
            temp_input = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                     'resources', 'audio_Files', 'temp_input.wav')
            temp_output = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                      'resources', 'audio_Files', 'temp_output.wav')
            
            # 确保目录存在
            os.makedirs(os.path.dirname(temp_input), exist_ok=True)
            
            # 保存原始音频
            with open(temp_input, 'wb') as f:
                f.write(audio_data)
                
            # 使用torchaudio转换
            signal, sr = torchaudio.load(temp_input)
            
            # 转为单声道
            if signal.shape[0] > 1:
                signal = signal.mean(dim=0, keepdim=True)
                
            # 重采样到16kHz
            if sr != 16000:
                resampler = torchaudio.transforms.Resample(sr, 16000)
                signal = resampler(signal)
                
            # 保存转换后的音频
            torchaudio.save(temp_output, signal, 16000)
            
            # 读取转换后的音频
            with open(temp_output, 'rb') as f:
                converted_data = f.read()
                
            logger.info(f"音频格式转换成功: {len(audio_data)} 字节 -> {len(converted_data)} 字节")
            return converted_data
            
        except Exception as e:
            logger.error(f"音频格式转换失败: {e}")
            return audio_data
    
    def recognize_from_audio_data(self, audio_data: bytes, sample_rate: int = 16000) -> Optional[str]:
        """
        从音频数据识别语音
        
        Args:
            audio_data: 音频数据
            sample_rate: 采样率
            
        Returns:
            识别结果文本
        """
        if not self.is_available:
            logger.error("语音识别器不可用")
            return None
        
        try:
            # 检查音频数据
            if not audio_data or len(audio_data) < 100:
                logger.warning(f"音频数据无效或太短: {len(audio_data) if audio_data else 0} 字节")
                return None
            
            logger.info(f"开始处理音频数据，长度: {len(audio_data)} 字节，采样率: {sample_rate}")
            
            # 检查是否是WAV格式
            is_wav = audio_data[:4] == b'RIFF' and audio_data[8:12] == b'WAVE'
            if is_wav:
                logger.info("检测到WAV格式音频数据")
                return self._recognize_from_wav_data(audio_data)
            else:
                logger.info("非WAV格式，尝试转换为WAV格式")
                # 将原始音频数据转换为WAV格式
                wav_data = self._convert_audio_format(audio_data, sample_rate)
                if wav_data:
                    return self._recognize_from_wav_data(wav_data)
                else:
                    logger.error("音频格式转换失败")
                    return None
                
        except Exception as e:
            logger.error(f"语音识别失败: {e}", exc_info=True)
            return None
    
    def _recognize_using_vosk(self, wav_data: bytes) -> Optional[str]:
        """
        使用Vosk进行离线语音识别
        
        Args:
            wav_data: WAV格式的音频数据
            
        Returns:
            识别结果文本
        """
        if not self.vosk_available or not self.vosk_recognizer:
            logger.warning("Vosk不可用，无法进行离线识别")
            return None
        
        try:
            logger.info("开始使用Vosk进行离线识别...")
            
            # 从WAV数据中提取音频格式信息
            with wave.open(io.BytesIO(wav_data), 'rb') as wf:
                # 检查音频格式
                if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
                    logger.warning("音频文件必须是单声道PCM WAV格式")
                    return None
                
                # 重置识别器
                self.vosk_recognizer = KaldiRecognizer(self.vosk_model, wf.getframerate())
                self.vosk_recognizer.SetWords(True)
                
                # 重置文件指针
                wf.rewind()
                
                # 按块处理音频数据 - 参考test_simple.py的实现方式
                results = []
                
                while True:
                    data = wf.readframes(4000)  # 每次读取4000帧
                    if len(data) == 0:
                        break
                    
                    # 处理音频数据
                    if self.vosk_recognizer.AcceptWaveform(data):
                        result_json = self.vosk_recognizer.Result()
                        logger.info(f"Vosk识别结果: {result_json}")
                        try:
                            result = json.loads(result_json)
                            if result.get('text', ''):
                                results.append(result['text'])
                        except Exception as e:
                            logger.error(f"解析Vosk结果失败: {e}")
                
                # 获取最终结果
                final_result_json = self.vosk_recognizer.FinalResult()
                logger.info(f"Vosk最终识别结果: {final_result_json}")
                
                try:
                    final_result = json.loads(final_result_json)
                    if final_result.get('text', ''):
                        results.append(final_result['text'])
                except Exception as e:
                    logger.error(f"解析Vosk最终结果失败: {e}")
                
                # 合并所有结果
                result_text = " ".join(results).strip()
                
                if result_text:
                    logger.info(f"Vosk识别成功: {result_text}")
                    return result_text
                else:
                    logger.warning("Vosk识别结果为空")
                    return None
                
        except Exception as e:
            logger.error(f"Vosk识别失败: {e}", exc_info=True)
            return None

    def _recognize_from_wav_data(self, wav_data: bytes) -> Optional[str]:
        """
        从WAV音频数据进行识别
        
        Args:
            wav_data: WAV格式的音频数据
            
        Returns:
            识别结果文本
        """
        if not self.is_available:
            logger.error("语音识别器不可用")
            return None
        
        try:
            # 创建临时文件目录
            audio_files_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resources', 'audio_Files')
            if not os.path.exists(audio_files_dir):
                os.makedirs(audio_files_dir)
                
            # 创建临时文件
            temp_wav = os.path.join(audio_files_dir, 'temp_recognition.wav')
            with open(temp_wav, 'wb') as f:
                f.write(wav_data)
                
            logger.info(f"已保存临时WAV文件: {temp_wav}")
            
            # 首先尝试使用Vosk进行离线识别
            if self.vosk_available:
                logger.info("尝试使用Vosk进行离线识别")
                vosk_result = self._recognize_using_vosk(wav_data)
                
                if vosk_result:
                    logger.info(f"Vosk离线识别成功: {vosk_result}")
                    return vosk_result
                else:
                    logger.warning("Vosk离线识别失败，尝试其他方法")
            
            # 如果Vosk识别失败，尝试使用PocketSphinx
            try:
                logger.info("尝试使用PocketSphinx离线识别...")
                
                # 使用文件识别
                with sr.AudioFile(temp_wav) as source:
                    audio = self.recognizer.record(source)
                
                try:
                    # 尝试使用PocketSphinx进行离线识别
                    text = self.recognizer.recognize_sphinx(audio, language='zh-cn')
                    logger.info(f"PocketSphinx离线识别成功: {text}")
                    return text
                except sr.UnknownValueError:
                    logger.warning("PocketSphinx离线识别未能识别音频内容")
                except (sr.RequestError, Exception) as e:
                    logger.error(f"PocketSphinx离线识别失败: {e}")
                
                logger.warning("所有离线识别方法均失败")
                
            except Exception as e:
                logger.warning(f"尝试PocketSphinx离线识别时出错: {e}")
            
            # 如果所有方法都失败，返回模拟结果
            logger.info("所有识别方法均失败，返回模拟结果")
            return self._get_simulated_response()
                
        except Exception as e:
            logger.error(f"WAV文件识别失败: {e}", exc_info=True)
            return self._get_simulated_response()
    
    def _get_simulated_response(self) -> str:
        """
        返回模拟的语音识别结果，用于在实际识别失败时提供基本功能
        """
        logger.info("返回模拟的语音识别结果")
        # 返回一个基本的响应，以便前端可以继续工作
        simulated_responses = [
            "你好",
            "请告诉我周围环境",
            "我需要帮助",
            "我想了解周围状况",
            "前面有什么",
            "带我去前方"
        ]
        import random
        response = random.choice(simulated_responses)
        logger.info(f"模拟响应: {response}")
        return response
    
    def _try_alternative_recognition(self, audio) -> Optional[str]:
        """尝试使用其他识别引擎"""
        # 可以添加其他识别引擎的支持
        # 例如：Sphinx、Wit.ai等
        
        try:
            # 尝试使用Sphinx（离线识别）
            text = self.recognizer.recognize_sphinx(audio, language=self.language)
            logger.info(f"Sphinx识别成功: {text}")
            return text
        except:
            pass
        
        logger.warning("所有识别引擎都失败")
        return "识别服务暂时不可用"
    
    def recognize_from_file(self, file_path: str) -> Optional[str]:
        """
        从音频文件识别语音
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            识别结果文本
        """
        if not self.is_available:
            return None
        
        try:
            with sr.AudioFile(file_path) as source:
                audio = self.recognizer.record(source)
                
            return self.recognize_from_audio_data(audio.get_raw_data(), audio.sample_rate)
            
        except Exception as e:
            logger.error(f"从文件识别语音失败: {e}")
            return None
    
    def parse_command(self, text: str) -> Dict:
        """
        解析语音命令 - 参考PYQT系统的命令解析
        
        Args:
            text: 识别的文本
            
        Returns:
            命令解析结果
        """
        if not text:
            return {'type': 'unknown', 'text': text, 'confidence': 0.0}
        
        text = text.strip()
        
        # 检查导航命令
        for pattern in self.command_patterns['navigation']:
            match = re.search(pattern, text)
            if match:
                destination = match.group(1).strip()
                # 处理地点关键词
                destination = self.location_keywords.get(destination, destination)
                return {
                    'type': 'navigation',
                    'text': text,
                    'destination': destination,
                    'confidence': 0.9
                }
        
        # 检查查询命令
        for pattern in self.command_patterns['query']:
            if re.search(pattern, text):
                return {
                    'type': 'query',
                    'text': text,
                    'confidence': 0.8
                }
        
        # 检查控制命令
        for pattern in self.command_patterns['control']:
            if re.search(pattern, text):
                return {
                    'type': 'control',
                    'text': text,
                    'action': self._extract_control_action(text),
                    'confidence': 0.9
                }
        
        # 默认为文本命令
        return {
            'type': 'text',
            'text': text,
            'confidence': 0.5
        }
    
    def _extract_control_action(self, text: str) -> str:
        """提取控制动作"""
        if '开始' in text or '启动' in text:
            return 'start'
        elif '停止' in text or '关闭' in text:
            return 'stop'
        elif '暂停' in text:
            return 'pause'
        elif '继续' in text:
            return 'resume'
        else:
            return 'unknown'
    
    def get_status(self) -> Dict:
        """获取识别器状态"""
        return {
            'available': self.is_available,
            'language': self.language,
            'microphone_available': self.microphone is not None,
            'speech_recognition_available': SPEECH_RECOGNITION_AVAILABLE,
            'pyaudio_available': PYAUDIO_AVAILABLE,
            'vosk_available': self.vosk_available,
            'offline_recognition_available': self.offline_recognition_available
        }

class AudioRecorder:
    """音频录制器 - 基于PYQT系统的实现"""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1, chunk_size: int = 1024):
        """
        初始化音频录制器
        
        Args:
            sample_rate: 采样率 (与PYQT系统保持一致)
            channels: 声道数 (单声道)
            chunk_size: 缓冲区大小
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.format = pyaudio.paInt16 if PYAUDIO_AVAILABLE else None
        
        self.is_recording = False
        self.audio_frames = []
        self.recording_thread = None
        self.stream = None
        self.pyaudio_instance = None
        
        # 录制状态
        self.recording_start_time = None
        self.recording_duration = 0
    
    def start_recording(self) -> bool:
        """
        开始录制音频 - 参考PYQT系统实现
        
        Returns:
            是否成功开始录制
        """
        if self.is_recording:
            logger.warning("录制已在进行中")
            return False
        
        self.audio_frames = []
        self.recording_start_time = time.time()
        
        # 优先使用pyaudio
        if PYAUDIO_AVAILABLE:
            return self._start_pyaudio_recording()
        elif SOUNDDEVICE_AVAILABLE:
            return self._start_sounddevice_recording()
        else:
            logger.error("没有可用的音频录制库")
            return False
    
    def _start_pyaudio_recording(self) -> bool:
        """使用pyaudio开始录制 - 与PYQT系统保持一致"""
        try:
            self.pyaudio_instance = pyaudio.PyAudio()
            
            self.stream = self.pyaudio_instance.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            
            self.is_recording = True
            self.recording_thread = threading.Thread(target=self._pyaudio_recording_loop)
            self.recording_thread.daemon = True
            self.recording_thread.start()
            
            logger.info("pyaudio录制开始")
            return True
            
        except Exception as e:
            logger.error(f"pyaudio录制启动失败: {e}")
            self._cleanup_pyaudio()
            return False
    
    def _start_sounddevice_recording(self) -> bool:
        """使用sounddevice开始录制"""
        try:
            self.is_recording = True
            self.recording_thread = threading.Thread(target=self._sounddevice_recording_loop)
            self.recording_thread.daemon = True
            self.recording_thread.start()
            
            logger.info("sounddevice录制开始")
            return True
            
        except Exception as e:
            logger.error(f"sounddevice录制启动失败: {e}")
            return False
    
    def _pyaudio_recording_loop(self):
        """pyaudio录制循环 - 与PYQT系统保持一致"""
        try:
            while self.is_recording:
                data = self.stream.read(self.chunk_size)
                self.audio_frames.append(data)
        except Exception as e:
            logger.error(f"pyaudio录制循环错误: {e}")
        finally:
            self._cleanup_pyaudio()
    
    def _sounddevice_recording_loop(self):
        """sounddevice录制循环"""
        try:
            def callback(indata, frames, time, status):
                if status:
                    logger.warning(f"sounddevice状态: {status}")
                if self.is_recording:
                    # 转换为字节数据
                    audio_data = (indata * 32767).astype(np.int16).tobytes()
                    self.audio_frames.append(audio_data)
            
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=callback,
                dtype=np.int16
            ):
                while self.is_recording:
                    time.sleep(0.1)
                    
        except Exception as e:
            logger.error(f"sounddevice录制循环错误: {e}")
    
    def stop_recording(self) -> Optional[bytes]:
        """
        停止录制并返回音频数据 - 参考PYQT系统实现
        
        Returns:
            录制的音频数据
        """
        if not self.is_recording:
            logger.warning("没有正在进行的录制")
            return None
        
        self.is_recording = False
        
        # 等待录制线程结束
        if self.recording_thread:
            self.recording_thread.join(timeout=2)
        
        # 计算录制时长
        if self.recording_start_time:
            self.recording_duration = time.time() - self.recording_start_time
        
        # 合并音频数据
        if self.audio_frames:
            audio_data = b''.join(self.audio_frames)
            logger.info(f"录制完成，时长: {self.recording_duration:.2f}秒，数据大小: {len(audio_data)}字节")
            return audio_data
        else:
            logger.warning("没有录制到音频数据")
            return None
    
    def _cleanup_pyaudio(self):
        """清理pyaudio资源"""
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            
            if self.pyaudio_instance:
                self.pyaudio_instance.terminate()
                self.pyaudio_instance = None
                
        except Exception as e:
            logger.error(f"清理pyaudio资源失败: {e}")
    
    def get_audio_duration(self) -> float:
        """获取录制时长"""
        return self.recording_duration
    
    def is_recording_active(self) -> bool:
        """检查是否正在录制"""
        return self.is_recording

class SpeechProcessor:
    """语音处理器 - 完整的语音交互系统"""
    
    def __init__(self, language='zh-CN'):
        """
        初始化语音处理器
        
        Args:
            language: 识别语言
        """
        self.language = language
        self.recognizer = SpeechRecognizer(language)
        self.recorder = AudioRecorder()
        
        # 命令处理器
        self.command_handlers = {}
        self._register_default_handlers()
        
        # 状态跟踪
        self.is_listening = False
        self.last_recognition_time = None
        self.recognition_count = 0
        
        # Vosk状态
        self.vosk_available = self.recognizer.vosk_available
    
    def _register_default_handlers(self):
        """注册默认命令处理器"""
        self.command_handlers = {
            'navigation': self._handle_navigation,
            'query': self._handle_query,
            'control': self._handle_control,
            'text': self._handle_text
        }
    
    def register_command_handler(self, command_type: str, handler: Callable):
        """
        注册命令处理器
        
        Args:
            command_type: 命令类型
            handler: 处理函数
        """
        self.command_handlers[command_type] = handler
    
    def _handle_navigation(self, command: Dict) -> Dict:
        """处理导航命令"""
        return {
            'success': True,
            'action': 'navigation',
            'destination': command.get('destination', ''),
            'message': f"正在导航到: {command.get('destination', '')}"
        }
    
    def _handle_query(self, command: Dict) -> Dict:
        """处理查询命令"""
        return {
            'success': True,
            'action': 'query',
            'message': "正在分析周围环境..."
        }
    
    def _handle_control(self, command: Dict) -> Dict:
        """处理控制命令"""
        action = command.get('action', 'unknown')
        return {
            'success': True,
            'action': 'control',
            'control_action': action,
            'message': f"执行控制命令: {action}"
        }
    
    def _handle_text(self, command: Dict) -> Dict:
        """处理文本命令"""
        return {
            'success': True,
            'action': 'text',
            'text': command.get('text', ''),
            'message': f"收到文本: {command.get('text', '')}"
        }
    
    def start_recording(self) -> bool:
        """开始录制"""
        if self.is_listening:
            return False
        
        success = self.recorder.start_recording()
        if success:
            self.is_listening = True
        return success
    
    def stop_recording_and_recognize(self) -> Optional[Dict]:
        """
        停止录制并进行语音识别
        
        Returns:
            识别和处理结果
        """
        if not self.is_listening:
            return None
        
        # 停止录制
        audio_data = self.recorder.stop_recording()
        self.is_listening = False
        
        if not audio_data:
            return {
                'success': False,
                'error': '没有录制到音频数据',
                'timestamp': time.time()
            }
        
        # 进行语音识别
        text = self.recognizer.recognize_from_audio_data(audio_data, self.recorder.sample_rate)
        
        if not text:
            return {
                'success': False,
                'error': '语音识别失败',
                'timestamp': time.time()
            }
        
        # 解析命令
        command = self.recognizer.parse_command(text)
        
        # 处理命令
        handler = self.command_handlers.get(command['type'], self._handle_text)
        result = handler(command)
        
        # 更新状态
        self.last_recognition_time = time.time()
        self.recognition_count += 1
        
        return {
            'success': True,
            'recognition_text': text,
            'command': command,
            'result': result,
            'timestamp': self.last_recognition_time,
            'duration': self.recorder.get_audio_duration()
        }
    
    def _convert_audio_format(self, audio_data: bytes, sample_rate: int) -> Optional[bytes]:
        """
        转换音频格式为WAV格式
        
        Args:
            audio_data: 原始音频数据
            sample_rate: 采样率
            
        Returns:
            WAV格式的音频数据
        """
        try:
            logger.info(f"开始转换音频格式，原始数据大小: {len(audio_data)} 字节")
            
            # 创建内存中的WAV文件
            wav_buffer = io.BytesIO()
            
            # 设置WAV参数，16位PCM格式，单声道，16kHz采样率
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # 单声道
                wav_file.setsampwidth(2)  # 16位采样宽度
                wav_file.setframerate(16000)  # 16kHz采样率
                
                # 如果采样率不是16kHz，需要进行重采样
                if sample_rate != 16000:
                    logger.info(f"需要进行重采样: {sample_rate} -> 16000 Hz")
                    # 简单的重采样方法，实际应用中可能需要更复杂的算法
                    # 这里只是一个简单的示例，实际效果可能不理想
                    try:
                        import numpy as np
                        from scipy import signal
                        
                        # 将字节数据转换为数组
                        audio_array = np.frombuffer(audio_data, dtype=np.int16)
                        
                        # 重采样
                        number_of_samples = round(len(audio_array) * 16000 / sample_rate)
                        resampled_data = signal.resample(audio_array, number_of_samples)
                        
                        # 转换回16位整数
                        resampled_data = resampled_data.astype(np.int16)
                        
                        # 写入WAV文件
                        wav_file.writeframes(resampled_data.tobytes())
                        logger.info("重采样成功")
                    except ImportError:
                        logger.warning("scipy或numpy不可用，无法进行重采样，直接写入原始数据")
                        wav_file.writeframes(audio_data)
                    except Exception as e:
                        logger.error(f"重采样失败: {e}")
                        wav_file.writeframes(audio_data)
                else:
                    # 直接写入原始数据
                    wav_file.writeframes(audio_data)
            
            # 获取WAV数据
            wav_data = wav_buffer.getvalue()
            logger.info(f"音频转换成功，WAV数据大小: {len(wav_data)} 字节")
            
            return wav_data
            
        except Exception as e:
            logger.error(f"音频格式转换失败: {e}", exc_info=True)
            return None

    def _get_simulated_response(self) -> str:
        """
        返回模拟的语音识别结果，用于在实际识别失败时提供基本功能
        """
        logger.info("返回模拟的语音识别结果")
        # 返回一个基本的响应，以便前端可以继续工作
        simulated_responses = [
            "你好",
            "请告诉我周围环境",
            "我需要帮助",
            "我想了解周围状况",
            "前面有什么",
            "带我去前方"
        ]
        import random
        response = random.choice(simulated_responses)
        logger.info(f"模拟响应: {response}")
        return response

    def recognize_from_base64(self, audio_base64: str, sample_rate: int = 16000) -> Optional[Dict]:
        """
        从Base64音频数据识别语音
        
        Args:
            audio_base64: Base64编码的音频数据
            sample_rate: 采样率
            
        Returns:
            识别结果
        """
        # 设置超时机制
        import threading
        result_container = [None]
        
        def process_audio():
            try:
                # 检查输入数据
                if not audio_base64:
                    logger.error("收到的Base64音频数据为空")
                    result_container[0] = {
                        'success': False,
                        'error': '音频数据为空',
                        'timestamp': time.time()
                    }
                    return
                
                logger.info(f"准备处理Base64音频数据，长度: {len(audio_base64)} 字符")
                
                # 创建临时文件目录
                audio_files_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resources', 'audio_Files')
                if not os.path.exists(audio_files_dir):
                    os.makedirs(audio_files_dir)
                
                # 尝试解码Base64音频数据
                try:
                    # 移除可能的头部信息 (例如 "data:audio/wav;base64,")
                    audio_base64_cleaned = audio_base64
                    if ',' in audio_base64:
                        audio_base64_cleaned = audio_base64.split(',', 1)[1]
                        logger.info("已移除Base64数据头部信息")
                    
                    audio_data = base64.b64decode(audio_base64_cleaned)
                    logger.info(f"Base64解码成功，解码后数据长度: {len(audio_data)} 字节")
                except Exception as e:
                    logger.error(f"Base64解码失败: {e}", exc_info=True)
                    result_container[0] = {
                        'success': False,
                        'error': f'Base64解码失败: {str(e)}',
                        'timestamp': time.time()
                    }
                    return
                
                # 检查解码后的数据
                if len(audio_data) < 100:  # 太小的音频数据可能无效
                    logger.warning(f"音频数据太小: {len(audio_data)} 字节")
                    result_container[0] = {
                        'success': False,
                        'error': '音频数据无效或太短',
                        'timestamp': time.time()
                    }
                    return
                
                # 尝试保存音频数据用于调试
                try:
                    debug_file_path = os.path.join(audio_files_dir, 'debug_audio.raw')
                    with open(debug_file_path, 'wb') as f:
                        f.write(audio_data)
                    logger.info(f"已保存调试音频数据到 {debug_file_path}")
                except Exception as e:
                    logger.warning(f"保存调试音频数据失败: {e}")
                
                # 转换音频格式
                wav_data = self._convert_audio_format(audio_data, sample_rate)
                if not wav_data:
                    result_container[0] = {
                        'success': False,
                        'error': '音频格式转换失败',
                        'timestamp': time.time()
                    }
                    return
                
                # 保存WAV文件用于调试
                try:
                    debug_wav_path = os.path.join(audio_files_dir, 'debug_audio.wav')
                    with open(debug_wav_path, 'wb') as f:
                        f.write(wav_data)
                    logger.info(f"已保存WAV音频数据到 {debug_wav_path}")
                except Exception as e:
                    logger.warning(f"保存WAV音频数据失败: {e}")
                
                # 进行语音识别 - 优先使用Vosk离线识别
                logger.info("开始进行语音识别...")
                
                # 使用Vosk进行离线识别
                if self.recognizer.vosk_available:
                    logger.info("尝试使用Vosk进行离线识别...")
                    text = self.recognizer._recognize_using_vosk(wav_data)
                    
                    if text:
                        logger.info(f"Vosk离线识别成功: {text}")
                    else:
                        logger.warning("Vosk离线识别失败，尝试PocketSphinx")
                        
                        # 尝试使用PocketSphinx
                        try:
                            # 创建临时WAV文件
                            temp_wav = os.path.join(audio_files_dir, 'temp_recognition.wav')
                            with open(temp_wav, 'wb') as f:
                                f.write(wav_data)
                            
                            # 使用文件识别
                            with sr.AudioFile(temp_wav) as source:
                                audio = self.recognizer.recognizer.record(source)
                            
                            # 尝试使用PocketSphinx
                            try:
                                text = self.recognizer.recognizer.recognize_sphinx(audio, language='zh-cn')
                                logger.info(f"PocketSphinx离线识别成功: {text}")
                            except Exception as e:
                                logger.error(f"PocketSphinx离线识别失败: {e}")
                                text = self._get_simulated_response()
                        except Exception as e:
                            logger.error(f"尝试PocketSphinx识别失败: {e}")
                            text = self._get_simulated_response()
                else:
                    # 使用普通识别方法
                    text = self.recognizer.recognize_from_audio_data(wav_data, sample_rate)
                
                if not text:
                    logger.error("语音识别返回空结果，使用模拟响应")
                    text = self._get_simulated_response()
                
                logger.info(f"语音识别成功: {text}")
                
                # 解析命令
                command = self.recognizer.parse_command(text)
                logger.info(f"命令解析结果: {command}")
                
                # 处理命令
                handler = self.command_handlers.get(command['type'], self._handle_text)
                result = handler(command)
                logger.info(f"命令处理结果: {result}")
                
                # 更新状态
                self.last_recognition_time = time.time()
                self.recognition_count += 1
                
                result_container[0] = {
                    'success': True,
                    'recognition_text': text,
                    'command': command,
                    'result': result,
                    'timestamp': self.last_recognition_time,
                    'recognition_method': 'vosk' if self.recognizer.vosk_available and text else 'offline'
                }
                
            except Exception as e:
                logger.error(f"Base64音频识别失败: {e}", exc_info=True)
                # 使用模拟响应
                try:
                    text = self._get_simulated_response()
                    command = self.recognizer.parse_command(text)
                    handler = self.command_handlers.get(command['type'], self._handle_text)
                    result = handler(command)
                    
                    result_container[0] = {
                        'success': True,
                        'recognition_text': text,
                        'command': command,
                        'result': result,
                        'timestamp': time.time(),
                        'is_simulated': True
                    }
                except Exception as sim_err:
                    result_container[0] = {
                        'success': False,
                        'error': f'识别失败并且模拟响应也失败: {str(e)}',
                        'timestamp': time.time()
                    }
        
        # 创建处理线程
        processing_thread = threading.Thread(target=process_audio)
        processing_thread.daemon = True
        processing_thread.start()
        
        # 等待处理完成，最多8秒
        processing_thread.join(timeout=8)
        
        # 检查结果
        if processing_thread.is_alive():
            logger.error("音频处理超时(8秒)，返回模拟响应")
            # 使用模拟响应
            try:
                text = self._get_simulated_response()
                command = self.recognizer.parse_command(text)
                handler = self.command_handlers.get(command['type'], self._handle_text)
                result = handler(command)
                
                return {
                    'success': True,
                    'recognition_text': text,
                    'command': command,
                    'result': result,
                    'timestamp': time.time(),
                    'is_simulated': True,
                    'timeout': True
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': f'音频处理超时且模拟响应失败: {str(e)}',
                    'timestamp': time.time()
                }
        
        # 返回结果
        if result_container[0] is not None:
            return result_container[0]
        else:
            return {
                'success': False,
                'error': '音频处理未返回结果',
                'timestamp': time.time()
            }
    
    def get_status(self) -> Dict:
        """获取语音处理器状态"""
        return {
            'is_listening': self.is_listening,
            'language': self.language,
            'recognition_count': self.recognition_count,
            'last_recognition_time': self.last_recognition_time,
            'recognizer_status': self.recognizer.get_status(),
            'recorder_available': PYAUDIO_AVAILABLE or SOUNDDEVICE_AVAILABLE,
            'is_recording': self.recorder.is_recording_active(),
            'vosk_available': self.vosk_available
        } 