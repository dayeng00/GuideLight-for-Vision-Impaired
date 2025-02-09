<script setup>
import { ElContainer, ElAside, ElMain, ElHeader, ElFooter } from 'element-plus'
import sider from './components/sider.vue'
import Header from './components/header.vue';// 引入头部组件，注意header是固定组件，需要与其不同。
import router from './router';
import { useUserStore } from "./store/userStore";
import { onMounted, watch } from "vue";

const userStore = useUserStore();
console.log(router)
// 在组件挂载时执行
onMounted(() => {
  // 加载用户信息
  userStore.loadUser();
  // 打印用户信息
  console.log(userStore.user)
});
const changeRouter = (path) => {
  console.log(path);
  if(path === 'login') {
    router.push("/login")
  } else if(path === 'scan') {
    router.push('/scan')
  }else if(path === 'demonstrate'){
    router.push('/demonstrate')
  }else if(path === 'record'){
    router.push('/record')
  }else if(path === 'home'){
    router.push('/home')
  }else if(path === 'about'){
    router.push('/about')
  }else if(path === 'register'){
    router.push('/register')
  }
}

watch(
  () => router.currentRoute.value.path,
  (newPath) => {
    userStore.loadUser();
    // console.log('路由切换至:', newPath, '用户状态:', userStore.user);
  }
);
</script>

<template>
  <div class="common-layout">
    <el-container style="height: 100vh; flex-direction: column;">
      <el-header>
        <Header @home="changeRouter" @about="changeRouter"></Header>
      </el-header>
      <el-container style="flex: 1; overflow: hidden;">
        <el-aside style="overflow: auto">
          <sider @login="changeRouter" @scan="changeRouter" @demonstrate="changeRouter" @record="changeRouter"></sider>
        </el-aside>
        <el-container direction="vertical">
          <el-main style="overflow: auto">
            <router-view style="width: 100%; height: 100%"></router-view>
          </el-main>
          <el-footer>
            <div class="footer-content">
              <p>© 2025 项目名称 | 所有权归项目团队所有</p>
            </div>
          </el-footer>
        </el-container>
      </el-container>
    </el-container>
  </div>
</template>

<style scoped>
/* 移除所有手动高度计算 */
.common-layout {
  position: absolute;
  inset: 0; /* 等同于 top:0; right:0; bottom:0; left:0 */
  display: flex;
}

.el-container {
  /* Element Plus 容器默认已经是 flex 布局 */
  min-height: 0; /* 修复 flex 容器的最小尺寸问题 */
}

.el-aside {
  width: 15%; /* 改用固定宽度 */
  background-color: #ffffff;
  height: 100%; /* 继承父容器高度 */
}

.el-main {
  padding: 20px;
}

/* 确保根元素高度正确 */
html, body, #app {
  height: 100%;
  margin: 0;
  padding: 0;
}
</style>