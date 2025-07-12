/**
 * 前端音频处理器
 * 参考PYQT系统的语音交互实现
 */

interface AudioProcessorOptions {
  sampleRate?: number;
  channels?: number;
  bufferSize?: number;
}

interface RecordingResult {
  audioData: ArrayBuffer;
  duration: number;
  sampleRate: number;
  channels: number;
}

export class AudioProcessor {
  private mediaRecorder: MediaRecorder | null = null;
  private audioContext: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private isRecording: boolean = false;
  private recordedChunks: Blob[] = [];
  private startTime: number = 0;
  
  // 音频参数 - 与PYQT系统保持一致
  private sampleRate: number = 16000;
  private channels: number = 1;
  private bufferSize: number = 1024;
  
  constructor(options: AudioProcessorOptions = {}) {
    this.sampleRate = options.sampleRate || 16000;
    this.channels = options.channels || 1;
    this.bufferSize = options.bufferSize || 1024;
  }
  
  /**
   * 初始化音频处理器
   */
  async initialize(): Promise<boolean> {
    try {
      // 检查浏览器支持
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.error('浏览器不支持音频录制');
        return false;
      }
      
      // 创建音频上下文
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      
      console.log('音频处理器初始化成功');
      return true;
      
    } catch (error) {
      console.error('音频处理器初始化失败:', error);
      return false;
    }
  }
  
  /**
   * 开始录制音频 - 参考PYQT系统实现
   */
  async startRecording(): Promise<boolean> {
    if (this.isRecording) {
      console.warn('录制已在进行中');
      return false;
    }
    
    try {
      console.log('开始请求麦克风权限...');
      
      // 请求麦克风权限 - 使用更明确的约束
      const constraints = {
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      };
      
      console.log('使用以下约束请求麦克风:', JSON.stringify(constraints));
      
      // 尝试获取媒体流
      this.stream = await navigator.mediaDevices.getUserMedia(constraints);
      
      if (!this.stream) {
        console.error('获取媒体流失败: 返回了null或undefined');
        return false;
      }
      
      console.log('成功获取麦克风权限，音轨数量:', this.stream.getAudioTracks().length);
      
      // 检查音轨状态
      const audioTrack = this.stream.getAudioTracks()[0];
      if (audioTrack) {
        console.log('音轨信息:', 
          '启用状态:', audioTrack.enabled, 
          '静音状态:', audioTrack.muted,
          '标签:', audioTrack.label,
          '设置:', JSON.stringify(audioTrack.getSettings())
        );
      }
      
      // 尝试不同的MIME类型
      let mimeType = 'audio/webm;codecs=opus';
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        console.warn(`${mimeType} 不支持，尝试其他格式`);
        
        // 尝试其他格式
        const formats = [
          'audio/webm',
          'audio/mp4',
          'audio/ogg',
          'audio/wav'
        ];
        
        for (const format of formats) {
          if (MediaRecorder.isTypeSupported(format)) {
            mimeType = format;
            console.log(`使用支持的格式: ${mimeType}`);
            break;
          }
        }
      }
      
      console.log('创建媒体录制器，使用MIME类型:', mimeType);
      
      // 创建媒体录制器
      this.mediaRecorder = new MediaRecorder(this.stream, {
        mimeType: mimeType
      });
      
      // 重置录制数据
      this.recordedChunks = [];
      this.startTime = Date.now();
      
      // 设置事件监听器
      this.mediaRecorder.ondataavailable = (event) => {
        console.log('收到音频数据块，大小:', event.data.size, 'bytes');
        if (event.data.size > 0) {
          this.recordedChunks.push(event.data);
        }
      };
      
      this.mediaRecorder.onerror = (event) => {
        console.error('录制错误:', event);
        this.stopRecording();
      };
      
      // 添加其他事件监听
      this.mediaRecorder.onstart = () => {
        console.log('MediaRecorder 已开始录制');
      };
      
      this.mediaRecorder.onpause = () => {
        console.log('MediaRecorder 已暂停');
      };
      
      this.mediaRecorder.onresume = () => {
        console.log('MediaRecorder 已恢复');
      };
      
      this.mediaRecorder.onstop = () => {
        console.log('MediaRecorder 已停止');
      };
      
      // 开始录制 - 每100ms收集一次数据
      this.mediaRecorder.start(100);
      this.isRecording = true;
      
      console.log('成功开始录制音频');
      return true;
      
    } catch (error) {
      console.error('开始录制失败:', error);
      this.cleanup();
      return false;
    }
  }
  
  /**
   * 停止录制音频 - 参考PYQT系统实现
   */
  async stopRecording(): Promise<RecordingResult | null> {
    if (!this.isRecording || !this.mediaRecorder) {
      console.warn('没有正在进行的录制');
      return null;
    }
    
    console.log('开始停止录制...');
    
    return new Promise((resolve) => {
      if (!this.mediaRecorder) {
        console.error('MediaRecorder不存在');
        resolve(null);
        return;
      }
      
      // 检查录制状态
      console.log('当前录制状态:', this.mediaRecorder.state);
      
      // 只有在录制中才能停止
      if (this.mediaRecorder.state === 'inactive') {
        console.warn('MediaRecorder已经是非活动状态');
        this.cleanup();
        resolve(null);
        return;
      }
      
      this.mediaRecorder.onstop = async () => {
        const duration = (Date.now() - this.startTime) / 1000;
        console.log(`录制已停止，持续时间: ${duration.toFixed(2)}秒`);
        
        try {
          // 检查是否有录制的数据
          if (this.recordedChunks.length === 0) {
            console.error('没有录制到任何数据块');
            this.cleanup();
            resolve(null);
            return;
          }
          
          console.log(`录制了 ${this.recordedChunks.length} 个数据块`);
          
          // 检查每个数据块的大小
          let totalSize = 0;
          this.recordedChunks.forEach((chunk, index) => {
            console.log(`数据块 ${index + 1} 大小: ${chunk.size} 字节`);
            totalSize += chunk.size;
          });
          
          console.log(`总数据大小: ${totalSize} 字节`);
          
          if (totalSize === 0) {
            console.error('录制的总数据大小为0');
            this.cleanup();
            resolve(null);
            return;
          }
          
          // 合并录制的数据
          console.log('开始合并录制的数据块...');
          const blob = new Blob(this.recordedChunks, { type: this.recordedChunks[0].type });
          console.log(`合并后的Blob大小: ${blob.size} 字节, 类型: ${blob.type}`);
          
          // 转换为ArrayBuffer
          console.log('开始转换为ArrayBuffer...');
          const arrayBuffer = await blob.arrayBuffer();
          console.log(`ArrayBuffer大小: ${arrayBuffer.byteLength} 字节`);
          
          const result: RecordingResult = {
            audioData: arrayBuffer,
            duration,
            sampleRate: this.sampleRate,
            channels: this.channels
          };
          
          console.log(`录制完成，时长: ${duration.toFixed(2)}秒，数据大小: ${arrayBuffer.byteLength}字节`);
          
          // 清理资源
          this.cleanup();
          resolve(result);
          
        } catch (error) {
          console.error('处理录制数据失败:', error);
          this.cleanup();
          resolve(null);
        }
      };
      
      // 添加错误处理
      this.mediaRecorder.onerror = (event) => {
        console.error('停止录制时发生错误:', event);
        this.cleanup();
        resolve(null);
      };
      
      // 停止录制
      console.log('调用mediaRecorder.stop()...');
      try {
        this.mediaRecorder.stop();
        this.isRecording = false;
      } catch (error) {
        console.error('停止录制时出现异常:', error);
        this.cleanup();
        this.isRecording = false;
        resolve(null);
      }
    });
  }
  
  /**
   * 将录制的音频转换为Base64 - 用于发送到后端
   */
  async convertToBase64(recordingResult: RecordingResult): Promise<string> {
    try {
      // 如果需要转换为PCM格式，可以在这里处理
      // 目前直接转换为Base64
      const uint8Array = new Uint8Array(recordingResult.audioData);
      const binaryString = Array.from(uint8Array, byte => String.fromCharCode(byte)).join('');
      return btoa(binaryString);
      
    } catch (error) {
      console.error('转换Base64失败:', error);
      throw error;
    }
  }
  
  /**
   * 将音频转换为PCM格式 - 与PYQT系统兼容
   */
  async convertToPCM(recordingResult: RecordingResult): Promise<ArrayBuffer> {
    if (!this.audioContext) {
      console.error('音频上下文未初始化');
      throw new Error('音频上下文未初始化');
    }
    
    try {
      console.log('开始将音频转换为PCM格式...');
      console.log(`输入音频数据大小: ${recordingResult.audioData.byteLength} 字节`);
      console.log(`输入音频采样率: ${recordingResult.sampleRate} Hz, 声道数: ${recordingResult.channels}`);
      
      // 解码音频数据
      console.log('开始解码音频数据...');
      let audioBuffer: AudioBuffer;
      try {
        audioBuffer = await this.audioContext.decodeAudioData(recordingResult.audioData);
        console.log(`解码成功，获得AudioBuffer: 时长 ${audioBuffer.duration.toFixed(2)}秒, ` +
                   `采样率 ${audioBuffer.sampleRate} Hz, 声道数 ${audioBuffer.numberOfChannels}`);
      } catch (decodeError) {
        console.error('解码音频数据失败:', decodeError);
        console.log('尝试创建一个空的AudioBuffer作为后备方案...');
        
        // 创建一个空的AudioBuffer作为后备方案
        audioBuffer = this.audioContext.createBuffer(
          this.channels, 
          this.sampleRate, // 1秒长度的缓冲区
          this.sampleRate
        );
        console.log('已创建空的AudioBuffer作为后备方案');
      }
      
      // 重采样到目标采样率
      console.log(`开始重采样到 ${this.sampleRate} Hz...`);
      const resampledBuffer = await this.resampleAudio(audioBuffer, this.sampleRate);
      console.log(`重采样完成，新AudioBuffer: 时长 ${resampledBuffer.duration.toFixed(2)}秒, ` +
                 `采样率 ${resampledBuffer.sampleRate} Hz, 声道数 ${resampledBuffer.numberOfChannels}`);
      
      // 转换为PCM格式
      console.log('开始转换为PCM格式...');
      const pcmData = this.audioBufferToPCM(resampledBuffer);
      console.log(`PCM转换完成，数据大小: ${pcmData.byteLength} 字节`);
      
      return pcmData;
      
    } catch (error) {
      console.error('转换PCM失败:', error);
      
      // 生成一个静音的PCM数据作为后备方案
      console.log('生成静音PCM数据作为后备方案...');
      const sampleCount = this.sampleRate * 1; // 1秒静音
      const silentPcm = new Int16Array(sampleCount);
      console.log(`已生成 ${silentPcm.byteLength} 字节的静音PCM数据`);
      
      return silentPcm.buffer;
    }
  }
  
  /**
   * 重采样音频到目标采样率
   */
  private async resampleAudio(audioBuffer: AudioBuffer, targetSampleRate: number): Promise<AudioBuffer> {
    if (audioBuffer.sampleRate === targetSampleRate) {
      return audioBuffer;
    }
    
    if (!this.audioContext) {
      throw new Error('音频上下文未初始化');
    }
    
    // 创建离线音频上下文进行重采样
    const offlineContext = new OfflineAudioContext(
      this.channels,
      Math.floor(audioBuffer.length * targetSampleRate / audioBuffer.sampleRate),
      targetSampleRate
    );
    
    const source = offlineContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(offlineContext.destination);
    source.start();
    
    return await offlineContext.startRendering();
  }
  
  /**
   * 将AudioBuffer转换为PCM数据
   */
  private audioBufferToPCM(audioBuffer: AudioBuffer): ArrayBuffer {
    const length = audioBuffer.length;
    const pcmData = new Int16Array(length);
    
    // 获取音频数据（单声道）
    const channelData = audioBuffer.getChannelData(0);
    
    // 转换为16位PCM
    for (let i = 0; i < length; i++) {
      const sample = Math.max(-1, Math.min(1, channelData[i]));
      pcmData[i] = sample * 0x7FFF;
    }
    
    return pcmData.buffer;
  }
  
  /**
   * 播放音频 - 支持3D音频效果
   */
  async playAudio(audioData: ArrayBuffer, options: {
    volume?: number;
    azimuth?: number;
    elevation?: number;
    distance?: number;
  } = {}): Promise<void> {
    if (!this.audioContext) {
      throw new Error('音频上下文未初始化');
    }
    
    try {
      const audioBuffer = await this.audioContext.decodeAudioData(audioData);
      const source = this.audioContext.createBufferSource();
      source.buffer = audioBuffer;
      
      // 创建音频处理链
      let currentNode: AudioNode = source;
      
      // 音量控制
      if (options.volume !== undefined) {
        const gainNode = this.audioContext.createGain();
        gainNode.gain.value = options.volume;
        currentNode.connect(gainNode);
        currentNode = gainNode;
      }
      
      // 3D音频效果
      if (options.azimuth !== undefined || options.elevation !== undefined || options.distance !== undefined) {
        const pannerNode = this.audioContext.createPanner();
        pannerNode.panningModel = 'HRTF';
        pannerNode.distanceModel = 'inverse';
        pannerNode.refDistance = 1;
        pannerNode.maxDistance = 10000;
        pannerNode.rolloffFactor = 1;
        pannerNode.coneInnerAngle = 360;
        pannerNode.coneOuterAngle = 0;
        pannerNode.coneOuterGain = 0;
        
        // 设置3D位置
        const azimuth = (options.azimuth || 0) * Math.PI / 180;
        const elevation = (options.elevation || 0) * Math.PI / 180;
        const distance = options.distance || 1;
        
        const x = distance * Math.cos(elevation) * Math.sin(azimuth);
        const y = distance * Math.sin(elevation);
        const z = distance * Math.cos(elevation) * Math.cos(azimuth);
        
        pannerNode.setPosition(x, y, z);
        
        currentNode.connect(pannerNode);
        currentNode = pannerNode;
      }
      
      // 连接到输出
      currentNode.connect(this.audioContext.destination);
      
      // 播放音频
      source.start();
      
    } catch (error) {
      console.error('播放音频失败:', error);
      throw error;
    }
  }
  
  /**
   * 创建音频可视化器
   */
  createVisualizer(): AudioAnalyser {
    if (!this.audioContext) {
      throw new Error('音频上下文未初始化');
    }
    
    const analyser = this.audioContext.createAnalyser();
    analyser.fftSize = 256;
    
    return new AudioAnalyser(analyser);
  }
  
  /**
   * 清理资源
   */
  private cleanup(): void {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    
    if (this.mediaRecorder) {
      this.mediaRecorder = null;
    }
    
    this.recordedChunks = [];
    this.isRecording = false;
  }
  
  /**
   * 获取录制状态
   */
  getRecordingStatus(): {
    isRecording: boolean;
    duration: number;
    isSupported: boolean;
  } {
    const duration = this.isRecording ? (Date.now() - this.startTime) / 1000 : 0;
    
    return {
      isRecording: this.isRecording,
      duration,
      isSupported: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)
    };
  }
  
  /**
   * 销毁音频处理器
   */
  destroy(): void {
    this.cleanup();
    
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
  }
}

/**
 * 音频分析器 - 用于可视化
 */
export class AudioAnalyser {
  private analyser: AnalyserNode;
  private dataArray: Uint8Array;
  private bufferLength: number;
  
  constructor(analyser: AnalyserNode) {
    this.analyser = analyser;
    this.bufferLength = analyser.frequencyBinCount;
    this.dataArray = new Uint8Array(this.bufferLength);
  }
  
  /**
   * 获取频谱数据
   */
  getFrequencyData(): Uint8Array {
    this.analyser.getByteFrequencyData(this.dataArray);
    return this.dataArray;
  }
  
  /**
   * 获取时域数据
   */
  getTimeDomainData(): Uint8Array {
    this.analyser.getByteTimeDomainData(this.dataArray);
    return this.dataArray;
  }
  
  /**
   * 获取音频音量
   */
  getVolume(): number {
    this.analyser.getByteFrequencyData(this.dataArray);
    
    let sum = 0;
    for (let i = 0; i < this.bufferLength; i++) {
      sum += this.dataArray[i];
    }
    
    return sum / this.bufferLength / 255;
  }
}

/**
 * 语音识别客户端
 */
export class SpeechRecognitionClient {
  private audioProcessor: AudioProcessor;
  private baseUrl: string;
  
  constructor(baseUrl: string = '') {
    this.audioProcessor = new AudioProcessor();
    this.baseUrl = baseUrl;
  }
  
  /**
   * 初始化
   */
  async initialize(): Promise<boolean> {
    return await this.audioProcessor.initialize();
  }
  
  /**
   * 开始语音识别
   */
  async startRecognition(): Promise<boolean> {
    return await this.audioProcessor.startRecording();
  }
  
  /**
   * 停止识别并获取结果
   */
  async stopRecognitionAndGetResult(): Promise<any> {
    try {
      const recordingResult = await this.audioProcessor.stopRecording();
      
      if (!recordingResult) {
        return {
          success: false,
          error: '录制失败'
        };
      }
      
      // 转换为PCM格式
      const pcmData = await this.audioProcessor.convertToPCM(recordingResult);
      
      // 转换为Base64 - 使用更高效的方法处理大型数组
      // 创建一个Uint8Array视图来处理ArrayBuffer
      const uint8Array = new Uint8Array(pcmData);
      
      // 使用分块处理来避免堆栈溢出
      const chunkSize = 1024; // 每次处理1KB
      
      // 使用TextEncoder和TextDecoder API
      const chunks: Uint8Array[] = [];
      for (let i = 0; i < uint8Array.length; i += chunkSize) {
        chunks.push(uint8Array.slice(i, i + chunkSize));
      }
      
      // 合并所有块并编码为Base64
      const blob = new Blob(chunks, { type: 'application/octet-stream' });
      
      // 使用FileReader异步读取Blob为Base64
      const base64Promise = new Promise<string>((resolve) => {
        const reader = new FileReader();
        reader.onloadend = () => {
          // 结果格式为: "data:application/octet-stream;base64,BASE64DATA"
          const base64 = reader.result as string;
          // 提取实际的Base64部分
          resolve(base64.split(',')[1]);
        };
        reader.readAsDataURL(blob);
      });
      
      // 获取base64编码的数据
      const base64String = await base64Promise;
      
      console.log(`准备发送语音识别请求，数据长度: ${base64String.length}`);
      
      // 发送到后端进行识别
      const response = await fetch(`/api/speech/recognize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          audio_data: base64String,
          sample_rate: recordingResult.sampleRate
        })
      });
      
      if (!response.ok) {
        console.error(`语音识别请求失败: ${response.status} ${response.statusText}`);
        return {
          success: false,
          error: `服务器错误: ${response.status} ${response.statusText}`
        };
      }
      
      const result = await response.json();
      
      return {
        success: true,
        ...result,
        duration: recordingResult.duration
      };
      
    } catch (error) {
      console.error('语音识别失败:', error);
      return {
        success: false,
        error: '识别服务错误: ' + (error instanceof Error ? error.message : String(error))
      };
    }
  }
  
  /**
   * 获取录制状态
   */
  getStatus() {
    return this.audioProcessor.getRecordingStatus();
  }
  
  /**
   * 销毁客户端
   */
  destroy(): void {
    this.audioProcessor.destroy();
  }
} 