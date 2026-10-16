import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { getToken, logout } from './auth'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
  timeout: 30000
})

// 每个业务请求自动携带 JWT，页面组件无需重复拼 Authorization。
request.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => {
    const data = response.data
    if (data.code === 200) return data

    ElMessage.error(data.message || '请求失败')
    if (data.code === 401) {
      logout()
      router.replace({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
    }
    return Promise.reject(data)
  },
  (error) => {
    const status = error.response?.status
    const message = error.response?.data?.message
    if (status === 401) {
      ElMessage.error(message || '登录状态已失效，请重新登录')
      logout()
      router.replace({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
    } else if (error.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请稍后重试')
    } else if (error.response) {
      ElMessage.error(message || '请求失败')
    } else {
      ElMessage.error('网络异常，请检查后端服务是否启动')
    }
    return Promise.reject(error)
  }
)

export default request
