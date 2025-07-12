"""
Vosk离线语音识别示例
这个示例演示如何使用Vosk进行离线语音识别
"""

import os
import sys
import json
import wave
import pyaudio
import logging
from typing import Optional

# 添加父目录到路径，以便导入speech_processor
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 尝试导入Vosk
try:
    from vosk import Model, KaldiRecognizer
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    print("Vosk库不可用，请安装: pip install vosk")
    sys.exit(1)

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VoskDemo:
    """Vosk语音识别演示"""
    
    def __init__(self, model_path: Optional[str] = None):
        """
        初始化Vosk演示
        
        Args:
            model_path: Vosk模型路径，如果为None则自动查找
        """
        # 寻找模型路径
        if model_path is None:
            model_path = self._find_model_path()
            
        if not os.path.exists(model_path):
            logger.error(f"找不到Vosk模型: {model_path}")
            logger.info("请运行 resources/vosk_model/download_model.py 下载模型")
            sys.exit(1)
            
        logger.info(f"加载Vosk模型: {model_path}")
        self.model = Model(model_path)
        logger.info("Vosk模型加载成功")
    
    def _find_model_path(self) -> str:
        """查找Vosk模型路径"""
        # 尝试在以下位置查找模型
        possible_paths = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resources', 'vosk_model'),
            os.path.join(os.getcwd(), 'resources', 'vosk_model'),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'resources', 'vosk_model'),
            os.path.join(os.path.expanduser('~'), 'vosk_model')
        ]
        
        for path in possible_paths:
            if os.path.exists(path) and any(os.listdir(path)):
                logger.info(f"找到Vosk模型目录: {path}")
                return path
        
        # 如果找不到，返回默认路径
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resources', 'vosk_model')
    
    def recognize_from_file(self, audio_path: str) -> Optional[str]:
        """
        从音频文件识别文本
        
        Args:
            audio_path: 音频文件路径（WAV格式）
            
        Returns:
            识别的文本，如果失败则返回None
        """
        try:
            if not os.path.exists(audio_path):
                logger.error(f"找不到音频文件: {audio_path}")
                return None
            
            logger.info(f"打开音频文件: {audio_path}")
            
            # 打开音频文件
            wf = wave.open(audio_path, "rb")
            
            # 检查格式
            if wf.getnchannels() != 1:
                logger.warning(f"音频不是单声道，可能会影响识别质量: {wf.getnchannels()} 声道")
            
            if wf.getsampwidth() != 2:
                logger.warning(f"音频不是16位采样，可能会影响识别质量: {wf.getsampwidth() * 8} 位")
                
            if wf.getframerate() != 16000:
                logger.warning(f"音频采样率不是16kHz，可能会影响识别质量: {wf.getframerate()} Hz")
            
            # 创建识别器
            rec = KaldiRecognizer(self.model, wf.getframerate())
            rec.SetWords(True)
            
            # 处理音频数据
            logger.info("开始处理音频文件...")
            
            result = None
            while True:
                data = wf.readframes(4000)  # 每次读取4000帧
                if len(data) == 0:
                    break
                
                if rec.AcceptWaveform(data):
                    # 获取完整识别结果
                    result_json = rec.Result()
                    result_dict = json.loads(result_json)
                    result = result_dict.get("text", "")
                    if result:
                        logger.info(f"识别结果: {result}")
            
            # 获取最终结果
            if not result:
                final_json = rec.FinalResult()
                final_dict = json.loads(final_json)
                result = final_dict.get("text", "")
                logger.info(f"最终识别结果: {result}")
                
            return result
            
        except Exception as e:
            logger.error(f"识别音频文件时出错: {e}")
            return None
    
    def recognize_from_microphone(self, duration: int = 5) -> Optional[str]:
        """
        从麦克风录制并识别文本
        
        Args:
            duration: 录制时长（秒）
            
        Returns:
            识别的文本，如果失败则返回None
        """
        try:
            if not VOSK_AVAILABLE:
                logger.error("Vosk不可用")
                return None
            
            # 初始化PyAudio
            p = pyaudio.PyAudio()
            
            # 打开音频流
            logger.info("打开麦克风...")
            stream = p.open(format=pyaudio.paInt16,
                            channels=1,
                            rate=16000,
                            input=True,
                            frames_per_buffer=8000)
            
            # 创建识别器
            rec = KaldiRecognizer(self.model, 16000)
            rec.SetWords(True)
            
            # 处理音频数据
            logger.info(f"开始录制，持续 {duration} 秒...")
            
            frames = []
            partial_results = []
            start_time = os.times()[4]  # 获取当前时间
            
            print("请开始说话...")
            while os.times()[4] < start_time + duration:
                data = stream.read(4000)  # 每次读取4000帧
                frames.append(data)
                
                if rec.AcceptWaveform(data):
                    # 获取完整识别结果
                    result_json = rec.Result()
                    result_dict = json.loads(result_json)
                    result = result_dict.get("text", "")
                    if result:
                        partial_results.append(result)
                        print(f"部分识别结果: {result}")
                else:
                    # 获取部分识别结果
                    partial_json = rec.PartialResult()
                    partial_dict = json.loads(partial_json)
                    partial = partial_dict.get("partial", "")
                    if partial:
                        print(f"\r正在识别: {partial}", end="")
            
            print("\n录制结束")
            
            # 关闭流
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            # 获取最终结果
            final_json = rec.FinalResult()
            final_dict = json.loads(final_json)
            final_result = final_dict.get("text", "")
            
            # 合并所有结果
            all_results = " ".join(partial_results + [final_result]).strip()
            logger.info(f"最终识别结果: {all_results}")
            
            # 保存音频文件（可选）
            self._save_audio_file(frames)
            
            return all_results if all_results else None
            
        except Exception as e:
            logger.error(f"从麦克风识别时出错: {e}")
            return None
    
    def _save_audio_file(self, frames):
        """保存录制的音频到文件"""
        try:
            filename = "vosk_recording.wav"
            logger.info(f"保存录制音频到: {filename}")
            
            wf = wave.open(filename, 'wb')
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b''.join(frames))
            wf.close()
            
            logger.info(f"音频已保存到: {filename}")
        except Exception as e:
            logger.error(f"保存音频文件时出错: {e}")

def main():
    """主函数"""
    print("Vosk离线语音识别示例")
    print("=================")
    
    # 创建Vosk演示实例
    demo = VoskDemo()
    
    while True:
        print("\n选择一个选项:")
        print("1. 从麦克风录制并识别")
        print("2. 从WAV文件识别")
        print("3. 退出")
        
        choice = input("请输入选择 [1-3]: ").strip()
        
        if choice == '1':
            duration = input("录制时长(秒) [默认5]: ").strip()
            try:
                duration = int(duration) if duration else 5
            except:
                duration = 5
                
            result = demo.recognize_from_microphone(duration)
            
            if result:
                print(f"\n识别结果: {result}")
            else:
                print("\n未能识别语音")
                
        elif choice == '2':
            file_path = input("请输入WAV文件路径: ").strip()
            
            if os.path.exists(file_path):
                result = demo.recognize_from_file(file_path)
                
                if result:
                    print(f"\n识别结果: {result}")
                else:
                    print("\n未能识别语音")
            else:
                print(f"文件不存在: {file_path}")
                
        elif choice == '3':
            print("退出程序")
            break
            
        else:
            print("无效选择，请重试")

if __name__ == "__main__":
    main() 