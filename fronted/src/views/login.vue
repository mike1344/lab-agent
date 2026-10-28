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

        <!-- 图形验证码：后端关闭验证码时整行隐藏 -->
        <el-form-item v-if="captcha.enabled" prop="captcha_code">
          <div class="captcha-row">
            <el-input
              v-model="form.captcha_code"
              :prefix-icon="Key"
              size="large"
              placeholder="请输入验证码"
              maxlength="4"
              autocomplete="off"
              @keyup.enter="login"
            />
            <img
              v-if="captcha.image"
              :src="captcha.image"
              alt="验证码"
              title="看不清？点击刷新"
              class="captcha-image"
              @click="refreshCaptcha"
            />
          </div>
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
import { onMounted, reactive, ref } from 'vue'
import { Key, Lock, User } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { getCaptchaApi, loginApi } from '@/api/auth'
import { useUser } from '@/utils/user'
import logo from '@/assets/css/images/logo.png'

const route = useRoute()
const router = useRouter()
const { saveLoginData } = useUser()
const loginFormRef = ref(null)
const loadingValue = ref(false)

const form = reactive({
  username: '',
  password: '',
  captcha_code: ''
})

// 验证码凭据：enabled=false 时后端没开验证码，不展示也不校验
const captcha = reactive({
  enabled: false,
  captcha_id: '',
  image: ''
})

const rules = {
  username: [{ required: true, whitespace: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  captcha_code: [
    {
      // 自定义校验：只在验证码开启时要求填写
      validator: (_, value, callback) => {
        if (captcha.enabled && !String(value || '').trim()) {
          callback(new Error('请输入验证码'))
          return
        }
        callback()
      },
      trigger: 'blur'
    }
  ]
}

// 拉取（或刷新）一张新验证码，同时清空已输入的内容
const refreshCaptcha = async () => {
  try {
    const res = await getCaptchaApi()
    captcha.enabled = Boolean(res.data?.enabled)
    captcha.captcha_id = res.data?.captcha_id || ''
    captcha.image = res.data?.image || ''
  } catch {
    // 验证码接口异常时不阻断登录表单（后端若开启验证码会明确拒绝登录）
    captcha.enabled = false
  }
  form.captcha_code = ''
}

onMounted(refreshCaptcha)

const login = async () => {
  const valid = await loginFormRef.value?.validate().catch(() => false)
  if (!valid || loadingValue.value) return

  loadingValue.value = true
  try {
    const res = await loginApi({
      username: form.username.trim(),
      password: form.password,
      captcha_id: captcha.enabled ? captcha.captcha_id : '',
      captcha_code: captcha.enabled ? form.captcha_code.trim() : ''
    })
    saveLoginData(res.data)
    ElMessage.success('登录成功')

    // 如果用户是被路由守卫拦下的，登录后回到原页面，否则进入首页。
    const redirectPath = typeof route.query.redirect === 'string' ? route.query.redirect : '/home'
    await router.replace(redirectPath)
  } catch {
    // 登录失败（密码错误/验证码错误/账号锁定）：验证码已一次性消费，立刻换一张
    await refreshCaptcha()
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

/* 验证码行：输入框占满剩余宽度，图片固定高度可点击刷新 */
.captcha-row {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}

.captcha-image {
  height: 40px;
  padding: 0 4px;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  cursor: pointer;
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
