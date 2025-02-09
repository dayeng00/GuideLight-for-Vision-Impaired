<template>
  <el-container>
    <!-- 顶部导航 -->
    <el-header>
      <el-dropdown @command="handleCommand">
        <el-button type="primary">
          选择页面 <el-icon><arrow-down /></el-icon>
        </el-button>
        <template #dropdown style="">
          <el-dropdown-menu>
<!--            <el-dropdown-item command="base">基本影像</el-dropdown-item>-->
            <el-dropdown-item command="disparity">视差估计</el-dropdown-item>
<!--            <el-dropdown-item command="detetor">特征检测</el-dropdown-item>-->
<!--            <el-dropdown-item command="tracker">特征点追踪</el-dropdown-item>-->
            <el-dropdown-item command="g_recognition">手势关键点检测</el-dropdown-item>
            <el-dropdown-item command="g_recognizer">手势识别</el-dropdown-item>
            <el-dropdown-item command="m_detector">目标检测</el-dropdown-item>
<!--            <el-dropdown-item command="p_tracker_V">人像追踪</el-dropdown-item>-->
            <el-dropdown-item command="tracker_RGB">RGB</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </el-header>

    <!-- 主内容，嵌套路由在这里切换 -->
    <el-main>
      <router-view style="width: 100%; height: 100%;"></router-view>
    </el-main>
  </el-container>
</template>

<script>
import { useRouter } from "vue-router";
import { ArrowDown } from "@element-plus/icons-vue";
import { el } from "element-plus/es/locales.mjs";
import axios from "axios";
export default {
  components: {
    ArrowDown,
  },
  setup() {
    const router = useRouter();
    // router.push("scan/base_Video")
    const handleCommand = (command) => {
      if (command === "base") {
        router.push("/scan/base_Video"); 
        axios.post(
          "http://localhost:5000/b_video/stop_camera",
        ) // ✅ 绝对路径
      } else if (command === "disparity") {
        router.push("/scan/disparity_estimator");
      } else if (command === "detetor") {
        router.push("/scan/feature_detector");
      } else if (command === "tracker") {
        router.push("/scan/feature_tracker");
      } else if (command === "g_recognition") {
        router.push("/scan/gesture_point_recognition");
      } else if (command === "g_recognizer") {
        router.push("/scan/gesture_recognizer");
      } else if (command === "m_detector") {
        router.push("/scan/moblie_net_SSD_detector");
      } else if (command === "p_tracker_V") {
        router.push("/scan/person_detection_tracker_on_video");
      } else if (command === "tracker_RGB") {
        router.push("/scan/spatial_object_tracker_on_RGB");
      }

    };

    return {
      handleCommand,
    };
  },
};
</script>

<style scoped>
.el-header {
  background-color: #ffffff;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 60px;
}

.el-main {
  padding: 20px;
}
</style>
