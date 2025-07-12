# Vosk 离线语音识别模型

Vosk 是一个基于 Kaldi 的轻量级离线语音识别工具包，特别适合在没有网络连接的情况下进行语音识别。

## 特点

- 完全离线工作，不需要网络连接
- 支持多种语言，包括中文
- 提供不同大小的模型，适应不同的硬件环境
- 识别准确度高，特别适合口令和短语识别
- 资源占用低，可在嵌入式设备上运行

## 安装 Vosk

在使用 Vosk 之前，需要先安装 Vosk 库：

```bash
pip install vosk
```

## 下载中文模型

Vosk 需要语言模型才能工作。为方便使用，本目录提供了一个脚本来下载中文语音识别模型。

### 自动下载

运行 `download_model.py` 脚本来下载中文模型：

```bash
python download_model.py
```

脚本会提示你选择要下载的模型类型：

- **small**: 小型模型 (~38MB)，适合在资源受限的设备上使用
- **standard**: 标准模型 (~1.1GB)，识别准确度更高

### 手动下载

如果自动下载失败，你可以从以下链接手动下载：

- 小型模型: [vosk-model-small-cn-0.22](https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip)
- 标准模型: [vosk-model-cn-0.22](https://alphacephei.com/vosk/models/vosk-model-cn-0.22.zip)

下载后，将模型文件解压到本目录（`main/resources/vosk_model`）。

## 目录结构

下载并解压模型后，该目录应包含以下文件：

```
vosk_model/
  ├── README.md
  ├── download_model.py
  ├── am/
  ├── conf/
  ├── graph/
  ├── ivector/
  ├── phones/
  ├── model
  └── ...其他模型文件
```

## 故障排除

如果语音识别不能正常工作，请检查：

1. Vosk 库是否成功安装
2. 模型文件是否已正确下载并解压
3. 音频输入格式是否正确（16kHz，16位，单声道）
4. 系统日志中是否有与 Vosk 相关的错误信息

## 更多信息

- Vosk 官方网站: https://alphacephei.com/vosk/
- Vosk GitHub: https://github.com/alphacep/vosk-api
- 更多 Vosk 模型: https://alphacephei.com/vosk/models 