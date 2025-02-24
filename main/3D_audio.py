"""
这是一个示例代码 将一首歌曲的不同乐器发出的声音进行不同方位的模拟
使用时域卷积模拟声音的空间音频效果
由于没有相关音频文件 所以该代码不可以执行
"""
import numpy as np
import matplotlib.pyplot as plt

# Librosa是一个用于音频信号处理和音乐信息检索的Python库。
# 它提供了丰富的功能，包括音频加载、特征提取（如MFCC、谱图等）、节拍检测等，方便对音频数据进行分析和处理。
import librosa

# glob模块提供了一个简单的文件路径名模式匹配功能。
# 可以使用通配符（如*、?等）来查找符合特定模式的文件路径，常用于批量处理文件。
import glob

# SciPy是基于NumPy构建的一个用于科学和技术计算的Python库。
# 它包含了许多用于优化、积分、插值、信号处理、线性代数等方面的工具和算法，扩展了NumPy的功能。
import scipy

# signal模块提供了各种信号处理功能，如滤波、频谱分析、卷积等。
# 可以用于对音频、图像等信号进行处理和分析。
from scipy import signal

# IPython.display模块提供了在Jupyter Notebook等交互式环境中显示各种媒体类型的功能。
# Audio类可以用于在Notebook中直接播放音频文件，方便对音频数据进行试听和验证。
from IPython.display import Audio

audio_dir = None
hrir_f10 = r'./resource/HRTF/elev-10/*.wav'
hrir0_dir = r'./resource/HRTF/elev0/*.wav'
hrir10_dir = r'./resource/HRTF/elev10/*.wav'
hrir20_dir = r'./resource/HRTF/elev20/*.wav'
hrir40_dir = r'./resource/HRTF/elev40/*.wav'

# glob会返回一个列表
audio = glob.glob(audio_dir)
elef10 = glob.glob(hrir_f10)
ele0 = glob.glob(hrir0_dir)
ele10 = glob.glob(hrir10_dir)
ele20 = glob.glob(hrir20_dir)
ele40 = glob.glob(hrir40_dir)

# 读入音频
# sr:采样率48khz mono:是否将音频转换成单声道
accordion, accordion_sr = librosa.load(audio[0], sr=48000, mono=True)
bass, bass_sr = librosa.load(audio[1], sr=48000, mono=True)
cellos, cellos_sr = librosa.load(audio[2], sr=48000, mono=True)
gtr_1, gtr_1_sr = librosa.load(audio[5], sr=48000, mono=True)
gtr_2, gtr_2_sr = librosa.load(audio[6], sr=48000, mono=True)
kick, kick_sr = librosa.load(audio[7], sr=48000, mono=True)
rhythm, rhythm_sr = librosa.load(audio[8], sr=48000, mono=True)
string_L, _ = librosa.load(audio[9], sr=48000, mono=True)
string_R, _ = librosa.load(audio[10], sr=48000, mono=True)
cellos_L, _ = librosa.load(audio[2], sr=48000, mono=True)
cellos_R, _ = librosa.load(audio[3], sr=48000, mono=True)

# 读入音频相对应的HRTF数据HRIR
L_kick, _ = librosa.load(elef10[0], sr=48000)  # -10, 0, kick
R_kick, _ = librosa.load(elef10[72], sr=48000)
L_bass, _ = librosa.load(ele0[2], sr=48000)  # 0, 10, bass
R_bass, _ = librosa.load(ele0[74], sr=48000)
L_gtr1, _ = librosa.load(ele20[68], sr=48000)  # 20, 340, gtr1
R_gtr1, _ = librosa.load(ele20[134], sr=48000)
L_gtr2, _ = librosa.load(ele20[10], sr=48000)  # 20, 50, gtr2
R_gtr2, _ = librosa.load(ele20[85], sr=48000)
L_accordion, _ = librosa.load(ele0[38], sr=48000)  # 10, 190, accordion
R_accordion, _ = librosa.load(ele0[110], sr=48000)
L_rhythm, _ = librosa.load(ele40[36], sr=48000)  # 40, 180, ryth
R_rhythm, _ = librosa.load(ele40[108], sr=48000)

# padding 将左声道和右声道的不同音频整合到一起
LEN = np.max([len(kick), len(cellos), len(bass), len(gtr_1), len(gtr_2), len(rhythm), len(string_L), len(string_R)])

kick = np.pad(kick, (0, LEN - len(kick)), 'constant')
bass = np.pad(bass, (0, LEN - len(bass)), 'constant')
gtr_1 = np.pad(gtr_1, (0, LEN - len(gtr_1)), 'constant')
gtr_2 = np.pad(gtr_2, (0, LEN - len(gtr_2)), 'constant')
accordion = np.pad(accordion, (0, LEN - len(accordion)), 'constant')
rhythm = np.pad(rhythm, (0, LEN - len(rhythm)), 'constant')
cellos = np.pad(cellos, (0, LEN - len(cellos)), 'constant')

# def to_mono(a) :
#     if a.shape[1] > 1:
#         a = np.mean(a, axis = 1)
#         a = a
#         return a
#     else:
#         a = a
#         return a

# 时域卷积
kick_L = scipy.signal.convolve(kick, L_kick)
kick_R = scipy.signal.convolve(kick, R_kick)

bass_L = scipy.signal.convolve(bass, L_bass)
bass_R = scipy.signal.convolve(bass, R_bass)

gtr1_L = scipy.signal.convolve(gtr_1, L_gtr1)
gtr1_R = scipy.signal.convolve(gtr_1, R_gtr1)

gtr2_L = scipy.signal.convolve(gtr_2, L_gtr2)
gtr2_R = scipy.signal.convolve(gtr_2, R_gtr2)

accordion_L = scipy.signal.convolve(accordion, L_accordion)
accordion_R = scipy.signal.convolve(accordion, R_accordion)

rhythm_L = scipy.signal.convolve(rhythm, L_rhythm)
rhythm_R = scipy.signal.convolve(rhythm, R_rhythm)

string_L = np.pad(string_L, (0, 12689965 - len(string_L)), 'constant')
string_R = np.pad(string_R, (0, 12689965 - len(string_R)), 'constant')
cellos_L = np.pad(string_L, (0, 12689965 - len(string_L)), 'constant')
cellos_R = np.pad(string_R, (0, 12689965 - len(string_R)), 'constant')

# 渲染 render
# 类似于图形渲染中将多个元素组合成最终图像，音频渲染是把多个音频成分组合成最终音频输出。
# 在计算机编程和多媒体领域，“render” 常用来表示将数据（音频、图形等）处理并转换为最终可呈现或可播放的形式。
render_L = kick_L + bass_L + gtr1_L + gtr2_L + string_L + accordion_L + rhythm_L + cellos_L
render_R = kick_R + bass_R + gtr1_R + gtr2_R + string_R + accordion_R + rhythm_R + cellos_R
MIX = np.vstack([render_L, render_R])
