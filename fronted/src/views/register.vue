<template>
  <div class="register-container">
    <div class="register-box">
      <h2 class="register-title">注册账号</h2>

      <el-form
        ref="registerFormRef"
        :model="registerForm"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleRegister"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="registerForm.username" :prefix-icon="User" placeholder="3～20 个字符" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="registerForm.email" :prefix-icon="Message" placeholder="用于账号识别" />
        </el-form-item>
        <el-form-item label="姓名" prop="full_name">
          <el-input v-model="registerForm.full_name" :prefix-icon="Postcard" placeholder="选填" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="registerForm.password"
            :prefix-icon="Lock"
            type="password"
            placeholder="8～64 个字符"
            autocomplete="new-password"
            show-password
            @change="revalidateConfirmPassword"
          />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="registerForm.confirmPassword"
            :prefix-icon="Lock"
            type="password"
            placeholder="请再次输入密码"
            autocomplete="new-password"
            show-password
          />
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          native-type="submit"
          :loading="loadingValue"
          class="submit-button"
        >
          注册
        </el-button>

        <div class="login-link">
          已有账号？
          <router-link to="/login">返回登录</router-link>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { User, Lock, Message, Postcard } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { registerApi } from '@/api/auth'

const router = useRouter()
const registerFormRef = ref(null)
const loadingValue = ref(false)

const registerForm = reactive({
  username: '',
  email: '',
  full_name: '',
  password: '',
  confirmPassword: ''
})

const validateConfirmPassword = (rule, value, callback) => {
  if (!value) callback(new Error('请再次输入密码'))
  else if (value !== registerForm.password) callback(new Error('两次输入的密码不一致'))
  else callback()
}

const rules = {
  username: [
    { required: true, whitespace: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度为 3～20 个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, max: 64, message: '密码长度为 8～64 个字符', trigger: 'blur' }
  ],
  confirmPassword: [{ validator: validateConfirmPassword, trigger: 'blur' }]
}

const revalidateConfirmPassword = () => {
  if (registerForm.confirmPassword) {
    registerFormRef.value?.validateField('confirmPassword').catch(() => {})
  }
}

const handleRegister = async () => {
  const valid = await registerFormRef.value?.validate().catch(() => false)
  if (!valid || loadingValue.value) return

  loadingValue.value = true
  try {
    await registerApi({
      username: registerForm.username.trim(),
      email: registerForm.email.trim(),
      full_name: registerForm.full_name.trim() || null,
      password: registerForm.password
    })
    ElMessage.success('注册成功，请使用新账号登录')
    await router.replace('/login')
  } finally {
    loadingValue.value = false
  }
}
</script>

<style scoped>
.register-container {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background: linear-gradient(135deg, #ecf5ff, #f7f9fc);
}

.register-box {
  width: 440px;
  max-width: 100%;
  padding: 32px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 18px 50px rgba(31, 45, 61, 0.12);
}

.register-title {
  margin-bottom: 24px;
  text-align: center;
}

.submit-button {
  width: 100%;
}

.login-link {
  margin-top: 20px;
  text-align: right;
  color: #606266;
}

.login-link a {
  color: #409eff;
}
</style>
