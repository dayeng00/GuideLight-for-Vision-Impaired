<template>
    <!-- 现在要实现 注册功能
        1.搞清楚表单在哪提交（什么URL）的，以什么形式提交的，在前端处理掉。
        2.加上若些验证不通过，则提示用户（dialog跳出提醒）
        3.注册成功后，跳转到登录页

        注册信息 -> 传到后端 -> 后端调用时间函数 标注时间 -> 存入数据库 -> 返回到历史记录（需要前端加一个监听）
        开启实时检测 -> 传到后端 -> 后端调用摄像头 -> 调用时间函数、标注时间 -> 存入数据库（注意存到对应用户的数据库） -> 返回到历史记录（需要前端加一个监听）
                                                -> 返回视频流到前端（但三个视频流在哪是个问题） -> 显示视频流
        
        -->
    <div class="register-container">
      <el-card class="register-box">
        <h2 class="register-title">用户注册</h2>
        <el-form 
          :model="registerForm" 
          :rules="registerRules" 
          ref="registerFormRef"
          @submit.prevent="handleRegister"
        >
          <el-form-item prop="username">
            <el-input
              v-model="registerForm.username"
              placeholder="请输入用户名"
              prefix-icon="User"
            />
          </el-form-item>
  
          <el-form-item prop="password">
            <el-input
              v-model="registerForm.password"
              type="password"
              placeholder="请输入密码"
              prefix-icon="Lock"
              show-password
            />
          </el-form-item>
  
          <el-form-item prop="confirmPassword">
            <el-input
              v-model="registerForm.confirmPassword"
              type="password"
              placeholder="请确认密码"
              prefix-icon="Lock"
              show-password
            />
          </el-form-item>
  
          <el-form-item>
            <el-button 
              type="primary" 
              native-type="submit" 
              class="register-btn"
            >
              立即注册
            </el-button>
          </el-form-item>
  
          <div class="login-link">
            已有账号？
            <router-link to="/login">立即登录</router-link>
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
import { defineEmits } from 'vue'
import axios from 'axios'
// 新增：声明表单ref
const { appContext } = getCurrentInstance()
const axiosInstance = appContext.config.globalProperties.$axios
const router = useRouter()
const emit = defineEmits(['registerSuccess'])
// 新增：声明表单ref
const registerFormRef = ref(null)

const registerForm = ref({
  username: '',
  password: '',
  confirmPassword: '',
  category: "register"
})

const validatePassword = (rule, value, callback) => {
  if (value !== registerForm.value.password) {
    callback(new Error('两次输入密码不一致'))
  } else {
    callback()
  }
}

const registerRules = {
  // 保持原有规则不变
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
    ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
     { min: 6, message: '密码长度不能小于6位', trigger: 'blur' }
     ],
     confirmPassword: [
     { required: true, message: '请确认密码', trigger: 'blur' },
     { validator: validatePassword, trigger: 'blur' }
     ],
}

const handleRegister = () => {
  // 修改：使用.value访问表单引用
  registerFormRef.value.validate((valid) => {
    if (valid) {
      axiosInstance.post('/register', registerForm.value)
        .then((response) => {
          // 注册成功后，跳转到登录页
          console.log(response.data)
          if (response.data.message === '注册成功') {
            ElMessage.success('注册成功')
            axios.post('http://localhost:5001/record', {
              username: registerForm.value.username
            }
            )
            router.push('/login')
          } else {
            console.log(response.data.message)
            ElMessage.error('用户名已存在')
          }
        })
    } else {
      ElMessage.error('请检查填写的字段')
    }
  })
}
</script>
  
  <style scoped>
  /* 样式与登录页类似，可根据需要调整 */
  .register-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    background: #f0f2f5;
  }
  
  .register-box {
    width: 400px;
    padding: 30px;
    border-radius: 8px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.1);
  }
  
  .register-title {
    text-align: center;
    margin-bottom: 30px;
    color: #333;
  }
  
  .register-btn {
    width: 100%;
    margin-top: 10px;
  }
  
  .login-link {
    text-align: center;
    margin-top: 15px;
    color: #666;
  }
  
  .login-link a {
    color: #409eff;
    text-decoration: none;
  }
  
  .login-link a:hover {
    text-decoration: underline;
  }
  </style>
  