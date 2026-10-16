<template>
  <div class="auth-container">
    <div class="auth-card">
      <div class="brand-block">
        <img :src="logo" alt="系统 Logo" />
        <div>
          <h1>智能实验室预约系统</h1>
          <p>登录后管理实验室、设备与预约</p>
        </div>
      </div>

      <el-form ref="loginFormRef" :model="form" :rules="rules" @submit.prevent="login">
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            :prefix-icon="User"
            size="large"
            placeholder="请输入用户名"
            autocomplete="username"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            :prefix-icon="Lock"
            type="password"
            size="large"
            placeholder="请输入密码"
            autocomplete="current-password"
            show-password
            @keyup.enter="login"
          />
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          native-type="submit"
          :loading="loadingValue"
          class="submit-button"
        >
          登录
        </el-button>

        <div class="auth-link">
          还没有账号？
          <router-link to="/register">立即注册</router-link>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { loginApi } from '@/api/auth'
import { useUser } from '@/utils/user'
import logo from '@/assets/css/images/logo.png'

const route = useRoute()
const router = useRouter()
const { saveLoginData } = useUser()
const loginFormRef = ref(null)
const loadingValue = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, whitespace: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const login = async () => {
  const valid = await loginFormRef.value?.validate().catch(() => false)
  if (!valid || loadingValue.value) return

  loadingValue.value = true
  try {
    const res = await loginApi({
      username: form.username.trim(),
      password: form.password
    })
    saveLoginData(res.data)
    ElMessage.success('登录成功')

    // 如果用户是被路由守卫拦下的，登录后回到原页面，否则进入首页。
    const redirectPath = typeof route.query.redirect === 'string' ? route.query.redirect : '/home'
    await router.replace(redirectPath)
  } finally {
    loadingValue.value = false
  }
}
</script>

<style scoped>
.auth-container {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background: linear-gradient(135deg, #ecf5ff 0%, #f7f9fc 50%, #f0f9eb 100%);
}

.auth-card {
  width: 420px;
  max-width: 100%;
  padding: 36px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid #e4e7ed;
  border-radius: 16px;
  box-shadow: 0 18px 50px rgba(31, 45, 61, 0.12);
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 30px;
}

.brand-block img {
  width: 52px;
  height: 52px;
  object-fit: contain;
}

.brand-block h1 {
  font-size: 22px;
  color: #1f2d3d;
}

.brand-block p {
  margin-top: 6px;
  color: #909399;
}

.submit-button {
  width: 100%;
}

.auth-link {
  margin-top: 20px;
  text-align: right;
  color: #606266;
}

.auth-link a {
  color: #409eff;
}
</style>
