import whisper
from opencc import OpenCC

# 加载模型
model = whisper.load_model("base")

result = model.transcribe("../test_audio.wav")

# 创建 OpenCC 对象，指定从繁体到简体的转换
cc = OpenCC('t2s')
simplified_text = cc.convert(result["text"])

# 打印识别结果（简体中文）
print("识别结果（简体中文）：", simplified_text)