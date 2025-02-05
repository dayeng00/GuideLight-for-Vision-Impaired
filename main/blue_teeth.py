"""
蓝牙耳机通常遵循 A2DP（Advanced Audio Distribution Profile）协议来接收音频流，
PyBluez 本身并不直接支持 A2DP 协议，它主要用于 RFCOMM 连接（用于串行数据传输），
因此此脚本已经废弃 无法正常运行
思路改为模拟3D音频的声音后使用电脑连接蓝牙耳机播放 从而进行蓝牙耳机3D音频效果的模拟
"""

import time
import bluetooth
from pydub import AudioSegment  # 音频处理库
import subprocess
import threading


class BluetoothAudioPlayer:
    def __init__(self, target_device_name, interrupt_playing=False, audio_format="mp3"):
        # 存储目标蓝牙设备的名称
        self.target_device_name = target_device_name
        # 标记当前是否正在播放音频，初始值为 False
        self.is_playing = False
        # 用于存储播放音频的线程对象，初始值为 None
        self.play_thread = None
        # 控制新音频播放时是否中断当前播放，默认为不中断
        self.interrupt_playing = interrupt_playing
        # 存储音频播放的格式，默认为 MP3
        self.audio_format = audio_format
        # 存储周围发现的蓝牙设备
        self.nearby_devices = None
        # 存储蓝牙连接的 Socket
        self.socket = None
        # 存储目标蓝牙设备的地址
        self.target_address = None

    def find_bluetooth_device(self):
        print("正在寻找附近可连接的蓝牙设备...")
        try:
            self.nearby_devices = bluetooth.discover_devices(duration=8, lookup_names=True,
                                                             flush_cache=True, lookup_class=False)
            print("发现{}个可连接的设备:".format(len(self.nearby_devices)))
            for addr, name in self.nearby_devices:
                try:
                    print("   {} - {}".format(addr, name))
                except UnicodeEncodeError:
                    print("   {} - {}".format(addr, name.encode("utf-8", "replace")))
        except bluetooth.btcommon.BluetoothError as err:
            print(f"搜索蓝牙设备时出错: {err}")

    def connect_to_bluetooth_device(self):
        # 用于存储目标蓝牙设备的地址，初始值为 None
        self.target_address = None
        # 搜索附近的蓝牙设备
        self.find_bluetooth_device()

        # 遍历搜索到的设备
        # bdaddr 是 “Bluetooth Device Address” 的缩写 即蓝牙设备地址
        for addr, name in self.nearby_devices:
            # 获取设备名称并与目标设备名称比较
            if name == self.target_device_name:
                # 找到目标设备，记录其地址
                self.target_address = addr
                break

        # 如果找到目标设备地址
        if self.target_address is not None:
            print(f"已找到设备: {self.target_device_name}，地址: {self.target_address}")
            try:
                print(f"正在尝试连接到 {self.target_device_name}...")
                # 创建蓝牙套接字
                self.socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
                # 连接到设备
                self.socket.connect((self.target_address, 1))  # 1 是 RFCOMM 端口号
                print(f"已成功连接到 {self.target_device_name}")
                return True
            except bluetooth.btcommon.BluetoothError as err:
                print(f"蓝牙连接错误: {err}")
        else:
            print(f"未找到设备: {self.target_device_name}")
        return False

    # 关闭蓝牙连接
    def close_bluetooth_device(self):
        if self.socket:
            try:
                self.socket.close()
                print("蓝牙连接已关闭。")
            except bluetooth.btcommon.BluetoothError as err:
                print(f"关闭蓝牙连接时出错: {err}")
        else:
            print("没有活动的蓝牙连接。")

    # 蓝牙耳机通常遵循 A2DP（Advanced Audio Distribution Profile）协议来接收音频流，
    # PyBluez 本身并不直接支持 A2DP 协议，它主要用于 RFCOMM 连接（用于串行数据传输），
    # 但我们可以借助一些其他库（如 bluez 的命令行工具）来模拟音频流的传输。
    def play_mp3_file(self, file_path):
        # 如果需要中断当前播放且正在播放音频
        if self.interrupt_playing and self.is_playing:
            # 停止当前播放
            self.is_playing = False
            if self.play_thread:
                # 等待播放线程结束
                self.play_thread.join()

        # 如果不需要中断当前播放且正在播放音频
        elif not self.interrupt_playing and self.is_playing:
            print("等待当前音频播放完成...")
            if self.play_thread:
                # 等待播放线程结束
                self.play_thread.join()

        try:
            print(f"正在播放文件: {file_path}")
            # 根据指定的音频格式加载音频文件
            if self.audio_format == "mp3":
                sound = AudioSegment.from_mp3(file_path)
            elif self.audio_format == "wav":
                sound = AudioSegment.from_wav(file_path)
            elif self.audio_format == "ogg":
                sound = AudioSegment.from_ogg(file_path)
            else:
                raise ValueError(f"不支持的音频格式: {self.audio_format}")

            # 将音频转换为 PCM 格式
            pcm_data = sound.raw_data

            def send_audio():
                self.is_playing = True
                try:
                    # 这里模拟将音频数据通过蓝牙套接字发送
                    # 实际中，需要使用支持 A2DP 的方式进行音频流传输
                    # 这里使用 bluez 的 pacat 命令结合蓝牙设备地址来模拟音频流传输
                    command = f'pacat --rate=44100 --channels=2 --format=s16le --device=bluez_sink.{self.target_address.replace(":", "_")}.a2dp_sink'
                    process = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE)
                    process.stdin.write(pcm_data)
                    process.stdin.close()
                    process.wait()
                except Exception as e:
                    print(f"发送音频数据时出错: {e}")
                finally:
                    self.is_playing = False
                    print("播放完成")

            self.play_thread = threading.Thread(target=send_audio)
            self.play_thread.start()
        except Exception as err:
            print(f"播放文件时出错: {err}")


if __name__ == "__main__":
    # 创建 BluetoothAudioPlayer 类的实例，设置中断播放为 True，音频格式为 mp3
    player = BluetoothAudioPlayer("NANK-OE Mix", interrupt_playing=True, audio_format="mp3")
    if player.connect_to_bluetooth_device():
        try:
            player.play_mp3_file(r"D:\bin\pycharm\GuideLight-for-Vision-Impaired\flowerAllOpened.mp3")
            time.sleep(10)
            player.play_mp3_file(r"../flowerAllOpened.mp3")
        except Exception as e:
            print(f"播放过程中出现错误: {e}")
        finally:
            # 确保在程序结束时关闭蓝牙连接
            player.close_bluetooth_device()
