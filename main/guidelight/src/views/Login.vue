<!-- Login.vue -->
<template>
    <div class="login-container">
      <el-card class="login-box">
        <h2 class="login-title">用户登录</h2>
        <el-form 
          :model="loginForm" 
          :rules="loginRules" 
          ref="loginFormRef"
          @submit.prevent="handleLogin"
        >
          <el-form-item prop="username">
            <el-input
              v-model="loginForm.username"
              placeholder="请输入用户名"
              prefix-icon="User"
            />
          </el-form-item>
  
          <el-form-item prop="password">
            <el-input
              v-model="loginForm.password"
              type="password"
              placeholder="请输入密码"
              prefix-icon="Lock"
              show-password
            />
          </el-form-item>
  
          <el-form-item>
            <el-button 
              type="primary" 
              native-type="submit" 
              class="login-btn"
            >
              立即登录
            </el-button>
          </el-form-item>
  
          <div class="register-link">
            没有账号？
            <router-link to="/register">立即注册</router-link>
          </div>
        </el-form>
      </el-card>
    </div>
  </template>
  
  <script setup>
  import { ref } from 'vue'
  import { useRouter } from 'vue-router'
  import { ElMessage } from 'element-plus'
  import { getCurrentInstance } from 'vue'
  import axios from 'axios'
  import { useUserStore } from '../store/userStore'

  const { appContext } = getCurrentInstance()
  const axiosInstance = appContext.config.globalProperties.$axios
  const router = useRouter()
  const userStore = useUserStore() // 引入 store

  // 表单数据
  const loginForm = ref({
    username: '',
    password: ''
  })
  
  // 表单验证规则
  const loginRules = {
    username: [
      { required: true, message: '请输入用户名', trigger: 'blur' }
    ],
    password: [
      { required: true, message: '请输入密码', trigger: 'blur' }
    ]
  }
  
  // 登录处理
  const handleLogin = () => {
    // 发送登录请求，请求中包含用户名和密码
    axiosInstance.post('/login', loginForm.value)
      .then((response) => {
        // 登录成功后，跳转到主页
        // console.log(response.data)
        if (response.data.message === '登录成功') {
          ElMessage.success('登录成功')
          axios.post('http://localhost:5000/record', {
            username: loginForm.value.username
          }
          ).then((response) => {
            // console.log(response.data)
            userStore.setUser(response.data)
            // console.log(userStore.user)
          })
          router.push('/home')
        } else {
          console.log(response.data.message)
          ElMessage.error('用户名或密码错误')
        }
      })
  }
  </script>
  
  <style scoped>
  .login-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    background: #f0f2f5;
  }
  
  .login-box {
    width: 400px;
    padding: 30px;
    border-radius: 8px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.1);
  }
  
  .login-title {
    text-align: center;
    margin-bottom: 30px;
    color: #333;
  }
  
  .login-btn {
    width: 100%;
    margin-top: 10px;
  }
  
  .register-link {
    text-align: center;
    margin-top: 15px;
    color: #666;
  }
  
  .register-link a {
    color: #409eff;
    text-decoration: none;
  }
  
  .register-link a:hover {
    text-decoration: underline;
  }
  </style>