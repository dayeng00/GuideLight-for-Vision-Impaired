<template>
    <div class="video-container">
      
      <div class="streams">
        <div v-for="stream in videoStreams" :key="stream.id" class="video-box">
          <h3>{{ stream.id === 1 ? '左摄像头' : '右摄像头' }}</h3>
          <img :src="stream.frame" :alt="'Camera ' + stream.id">
        </div>
      </div>
    </div>
  </template>
  
  <script setup>
  import { ref, onMounted } from 'vue';
  
  const videoStreams = ref([]);
  
  const socket = new WebSocket("ws://localhost:5173/socket.io/?EIO=4&transport=websocket");
  
  socket.onopen = () => {
    console.log("WebSocket 已连接");
  };
  
  socket.onmessage = (event) => {
    const rawData = event.data;
  
    if (rawData.startsWith('42')) {  // Socket.IO 消息格式，42 开头是 "message" 事件
      try {
        const data = JSON.parse(rawData.slice(2));  // 解析 JSON
        if (data[0] === "video_stream") {
          const { id, frame } = data[1];
  
          // 查找已有流
          const index = videoStreams.value.findIndex(v => v.id === id);
          if (index !== -1) {
            videoStreams.value[index].frame = `data:image/jpeg;base64,${frame}`;
          } else {
            videoStreams.value.push({ id, frame: `data:image/jpeg;base64,${frame}` });
          }
        }
      } catch (error) {
        console.error("WebSocket 数据解析失败", error);
      }
    }
  };
  
  socket.onerror = (error) => {
    console.error("WebSocket 连接错误:", error);
  };
  
  onMounted(() => {
    console.log("Vue 组件挂载，WebSocket 监听中...");
  });
  </script>
  
  <style scoped>
  .video-container {
    text-align: center;
  }
  .streams {
    display: flex;
    justify-content: center;
    gap: 20px;
  }
  .video-box {
    text-align: center;
  }
  img {
    width: 400px;
    height: auto;
    border: 2px solid black;
  }
  </style>
  