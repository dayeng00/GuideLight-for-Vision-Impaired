import time

import bluetooth
from pydub import AudioSegment  # 音频处理库
from pydub.playback import play
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

    def find_bluetooth_device(self):
        print("正在寻找附近可连接的蓝牙设备...")
        self.nearby_devices = bluetooth.discover_devices(duration=8, lookup_names=True,
                                                    flush_cache=True, lookup_class=False)
        print("发现{}个可连接的设备:".format(len(self.nearby_devices)))
        for addr, name in self.nearby_devices:
            try:
                print("   {} - {}".format(addr, name))
            except UnicodeEncodeError:
                print("   {} - {}".format(addr, name.encode("utf-8", "replace")))

    def connect_to_bluetooth_device(self):
        # 用于存储目标蓝牙设备的地址，初始值为 None
        target_address = None
        # 搜索附近的蓝牙设备
        self.find_bluetooth_device()

        # 遍历搜索到的设备
        for bdaddr in self.nearby_devices:
            # 获取设备名称并与目标设备名称比较
            if self.target_device_name == bluetooth.lookup_name(bdaddr):
                # 找到目标设备，记录其地址
                target_address = bdaddr
                break

        # 如果找到目标设备地址
        if target_address is not None:
            print(f"已找到设备: {self.target_device_name}，地址: {target_address}")
            try:
                print(f"正在尝试连接到 {self.target_device_name}...")
                print(f"已成功连接到 {self.target_device_name}")
                return True
            except bluetooth.btcommon.BluetoothError as err:
                print(f"蓝牙连接错误: {err}")
        else:
            print(f"未找到设备: {self.target_device_name}")
        return False

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

            self.is_playing = True

            def play_audio():
                while self.is_playing:
                    for chunk in sound[::100]:
                        if not self.is_playing:
                            break
                        play(chunk)
                self.is_playing = False
                print("播放完成")

            self.play_thread = threading.Thread(target=play_audio)
            self.play_thread.start()
        except Exception as err:
            print(f"播放文件时出错: {err}")


if __name__ == "__main__":
    # 创建 BluetoothAudioPlayer 类的实例，设置中断播放为 True，音频格式为 wav
    player = BluetoothAudioPlayer("NANK-OE Mix", interrupt_playing=True, audio_format="mp3")
    if player.connect_to_bluetooth_device():
        player.find_bluetooth_device()
        player.play_mp3_file(r"D:\bin\pycharm\GuideLight-for-Vision-Impaired\flowerAllOpened.mp3")
        time.sleep(10)
        player.play_mp3_file(r"../flowerAllOpened.mp3")
