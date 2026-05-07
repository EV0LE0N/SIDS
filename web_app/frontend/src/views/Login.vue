<template>
  <div class="login-container">
    <div class="login-box">
      <div class="logo-container">
        <h2>SIDS</h2>
        <p>网络攻击检测与态势感知平台</p>
      </div>
      
      <el-form :model="loginForm" :rules="rules" ref="loginFormRef" class="login-form" @submit.prevent>
        <el-form-item prop="username">
          <el-input 
            v-model="loginForm.username" 
            placeholder="管理员账号"
            prefix-icon="User"
            size="large"
            @keyup.enter="handleLogin"
          ></el-input>
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input 
            v-model="loginForm.password" 
            type="password" 
            placeholder="安全密码"
            prefix-icon="Lock"
            size="large"
            show-password
            @keyup.enter="handleLogin"
          ></el-input>
        </el-form-item>
        
        <el-form-item>
          <el-button 
            type="primary" 
            class="login-btn" 
            @click="handleLogin" 
            :loading="loading"
            size="large"
          >
            系统登入
          </el-button>
        </el-form-item>
        
        <div class="hint">
          <p>温馨提示：系统不开放注册，请使用预置管理员账号登入</p>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { User, Lock } from '@element-plus/icons-vue'

const router = useRouter()
const loginFormRef = ref(null)
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入管理员账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const handleLogin = () => {
  loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        const response = await axios.post('/api/auth/login', loginForm)
        if (response.data.token) {
          localStorage.setItem('sids_token', response.data.token)
          localStorage.setItem('sids_user', response.data.username)
          ElMessage.success('登入成功，欢迎进入系统')
          router.push('/sop')
        }
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || '登入失败，请检查网络或联系维护人员')
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  width: 100vw;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #0b1120;
  background-image: 
    radial-gradient(circle at 15% 50%, rgba(43, 124, 233, 0.15), transparent 25%),
    radial-gradient(circle at 85% 30%, rgba(103, 194, 58, 0.1), transparent 25%);
}

.login-box {
  width: 420px;
  background: rgba(13, 27, 42, 0.8);
  border: 1px solid rgba(43, 124, 233, 0.3);
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5), inset 0 0 15px rgba(43, 124, 233, 0.1);
  backdrop-filter: blur(10px);
}

.logo-container {
  text-align: center;
  margin-bottom: 35px;
}

.logo-container h2 {
  color: #fff;
  font-size: 32px;
  margin: 0 0 10px 0;
  letter-spacing: 2px;
  text-shadow: 0 0 10px rgba(43, 124, 233, 0.5);
}

.logo-container p {
  color: #a3b8d0;
  font-size: 14px;
  margin: 0;
}

.login-form {
  margin-top: 20px;
}

.login-btn {
  width: 100%;
  font-size: 16px;
  letter-spacing: 4px;
  background: linear-gradient(90deg, #2b7ce9, #1b5bb5);
  border: none;
  box-shadow: 0 4px 15px rgba(43, 124, 233, 0.4);
  transition: all 0.3s;
}

.login-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(43, 124, 233, 0.6);
}

.hint {
  text-align: center;
  margin-top: 20px;
}

.hint p {
  color: #6c849e;
  font-size: 12px;
  margin: 0;
}

/* 覆盖 Element UI 默认样式以匹配深色主题 */
:deep(.el-input__wrapper) {
  background-color: rgba(0, 0, 0, 0.2) !important;
  border: 1px solid #1a3a5f !important;
  box-shadow: none !important;
}

:deep(.el-input__inner) {
  color: #e8edf4 !important;
}

:deep(.el-input__wrapper.is-focus) {
  border-color: #2b7ce9 !important;
  box-shadow: 0 0 0 1px #2b7ce9 inset !important;
}
</style>
