<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

// 创建API客户端
const apiClient = axios.create({
  baseURL: '/',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

const router = useRouter()

const loginForm = reactive({
  username: '',
  password: ''
})

const registerVisible = ref(false)
const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  category: 'family' // 默认为家属端用户
})

const loginLoading = ref(false)
const registerLoading = ref(false)
const loginRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' }
  ]
}

const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度应为3-20个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule: any, value: string, callback: any) => {
        if (value !== registerForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const loginFormRef = ref()
const registerFormRef = ref()

// 处理登录
const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  await loginFormRef.value.validate(async (valid: boolean) => {
    if (valid) {
      loginLoading.value = true
      try {
        const response = await apiClient.post('/login', {
          username: loginForm.username,
          password: loginForm.password
        })
        
        if (response.data.message === '登录成功') {
          ElMessage.success('登录成功')
          // 存储登录状态
          localStorage.setItem('user', JSON.stringify({
            username: loginForm.username,
            isLoggedIn: true
          }))
          // 跳转到控制面板
          router.push('/dashboard')
        } else {
          ElMessage.error(response.data.message || '登录失败')
        }
      } catch (error) {
        console.error('登录请求失败:', error)
        ElMessage.error('登录失败，请检查网络连接')
      } finally {
        loginLoading.value = false
      }
    }
  })
}

// 处理注册
const handleRegister = async () => {
  if (!registerFormRef.value) return
  
  await registerFormRef.value.validate(async (valid: boolean) => {
    if (valid) {
      registerLoading.value = true
      try {
        const response = await apiClient.post('/register', {
          username: registerForm.username,
          password: registerForm.password,
          category: registerForm.category
        })
        
        if (response.data.message === '注册成功') {
          ElMessage.success('注册成功，请登录')
          registerVisible.value = false
          // 自动填充登录表单
          loginForm.username = registerForm.username
          loginForm.password = ''
        } else {
          ElMessage.error(response.data.message || '注册失败')
        }
      } catch (error) {
        console.error('注册请求失败:', error)
        ElMessage.error('注册失败，请检查网络连接')
      } finally {
        registerLoading.value = false
      }
    }
  })
}

// 显示注册表单
const showRegister = () => {
  registerVisible.value = true
}

// 取消注册，返回登录
const cancelRegister = () => {
  registerVisible.value = false
}
</script>

<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-title">
        <h2>盲人安全实时检测系统</h2>
        <p>家人视角登录</p>
      </div>
      
      <!-- 登录表单 -->
      <el-form
        v-if="!registerVisible"
        ref="loginFormRef"
        :model="loginForm"
        :rules="loginRules"
        label-position="top"
        class="login-form"
      >
        <el-form-item label="用户名" prop="username">
          <el-input 
            v-model="loginForm.username" 
            placeholder="请输入用户名"
            prefix-icon="User"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        
        <el-form-item label="密码" prop="password">
          <el-input 
            v-model="loginForm.password" 
            type="password" 
            placeholder="请输入密码"
            prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button 
            type="primary" 
            :loading="loginLoading" 
            @click="handleLogin" 
            class="login-button"
          >
            登录
          </el-button>
        </el-form-item>
        
        <div class="form-footer">
          <span>还没有账号？</span>
          <el-button type="text" @click="showRegister">立即注册</el-button>
        </div>
      </el-form>
      
      <!-- 注册表单 -->
      <el-form
        v-else
        ref="registerFormRef"
        :model="registerForm"
        :rules="registerRules"
        label-position="top"
        class="register-form"
      >
        <el-form-item label="用户名" prop="username">
          <el-input 
            v-model="registerForm.username" 
            placeholder="请输入用户名"
            prefix-icon="User"
          />
        </el-form-item>
        
        <el-form-item label="密码" prop="password">
          <el-input 
            v-model="registerForm.password" 
            type="password" 
            placeholder="请输入密码"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input 
            v-model="registerForm.confirmPassword" 
            type="password" 
            placeholder="请再次输入密码"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        
        <el-form-item label="用户类型">
          <el-radio-group v-model="registerForm.category">
            <el-radio label="family">家属</el-radio>
            <el-radio label="blind">盲人用户</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item>
          <el-button 
            type="primary" 
            :loading="registerLoading" 
            @click="handleRegister" 
            class="register-button"
          >
            注册
          </el-button>
          <el-button @click="cancelRegister">返回登录</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f5f7fa;
}

.login-box {
  width: 400px;
  padding: 30px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.login-title {
  text-align: center;
  margin-bottom: 30px;
}

.login-title h2 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.login-title p {
  margin: 10px 0 0;
  font-size: 14px;
  color: #606266;
}

.login-form,
.register-form {
  margin-top: 20px;
}

.login-button,
.register-button {
  width: 100%;
}

.form-footer {
  margin-top: 15px;
  text-align: center;
  font-size: 14px;
  color: #606266;
}
</style> 