<template>
    <el-container class="container">
      
  
      <el-main class="video-container">
        <!-- 摄像头 1 -->
        <el-card class="video-card">
          <img :src="camera1Url" class="video-stream" />
        </el-card>   
      </el-main>
  
      <el-footer class="footer">
        <el-button type="primary" @click="startStreaming">开启摄像头</el-button>
        <el-button type="danger" @click="stopStreaming">停止摄像头</el-button>
      </el-footer>
    </el-container>
  </template>
  
  <script setup>
  import { ref } from "vue";
  import axios from "axios";
//   import { useUserStore } from "../../store/userStore";
  // Flask 服务器地址（确保和 Flask 端口一致）
  const serverUrl = "http://127.0.0.1:5000";
  
  
  // 摄像头流地址
  const camera1Url = ref(`${serverUrl}/d_estimator/video_feed`);
  // 开启摄像头
  const startStreaming = () => {
    // TODO: 实现开启摄像头的逻辑
    // console.log("开启摄像头");
    camera1Url.value = `${serverUrl}/d_estimator/video_feed`;
    axios.post(`${serverUrl}/d_estimator/start_cameras`).then((response) => {
      console.log(response.data);
    })
    axios.post()
  };

  // 停止摄像头
  const stopStreaming = () => {
    // TODO: 实现停止摄像头的逻辑
    // console.log("停止摄像头");
    axios.post(`${serverUrl}/d_estimator/stop_cameras`).then((response) => {
      console.log(response.data);
    })
  };
  </script>
  
  <style scoped>
  /* 页面布局 */
  .container {
    height: 100vh;
    display: flex;
    flex-direction: column;
  }
  
  /* 头部 */
  .header {
    background-color: #409eff;
    color: white;
    text-align: center;
    font-size: 20px;
    padding: 10px;
  }
  
  /* 视频区域 */
  .video-container {
    display: flex;
    justify-content: center;
    gap: 20px;
    padding: 20px;
  }
  
  /* 每个摄像头的卡片 */
  .video-card {
    width: 45%;
    text-align: center;
  }
  
  /* 视频流样式 */
  .video-stream {
    width: 100%;
    height: auto;
    border-radius: 8px;
  }
  
  /* 底部 */
  .footer {
    text-align: center;
    padding: 10px;
    background-color: #f5f5f5;
  }
  </style>
  