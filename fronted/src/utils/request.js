import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'
import { getRefreshToken, getToken, logout, setRefreshToken, setToken } from './auth'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
  timeout: 30000
})

// 无感刷新：同一时刻只允许一个 refresh 请求在飞，其余 401 请求排队复用结果
let refreshPromise = null

async function refreshAccessToken() {
  if (refreshPromise) return refreshPromise
  const stored = getRefreshToken()
  if (!stored) return null
  // 用裸 axios 调刷新接口，避免走本实例拦截器造成递归
  refreshPromise = axios
    .post(`${import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'}/api/auth/refresh`, {
      refresh_token: stored
    })
    .then((response) => {
      const payload = response.data || {}
      if (payload.code !== 200 || !payload.data?.token) return null
      setToken(payload.data.token)
      if (payload.data.refresh_token) setRefreshToken(payload.data.refresh_token)
      return payload.data.token
    })
    .catch(() => null)
    .finally(() => {
      refreshPromise = null
    })
  return refreshPromise
}

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
    // 文件下载（responseType: 'blob'）不走统一信封，直接返回原始响应
    if (response.config?.responseType === 'blob') return response

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
    const config = error.config || {}
    const url = config.url || ''
    const isAuthEndpoint =
      url.includes('/api/auth/login') || url.includes('/api/auth/refresh')
    // access token 过期（HTTP 401）：有 refresh token 时先尝试无感续期并重放请求
    if (status === 401 && !config._retried && !isAuthEndpoint && getRefreshToken()) {
      config._retried = true
      return refreshAccessToken().then((newToken) => {
        if (!newToken) {
          ElMessage.error('登录状态已失效，请重新登录')
          logout()
          router.replace({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
          return Promise.reject(error)
        }
        config.headers = config.headers || {}
        config.headers.Authorization = `Bearer ${newToken}`
        return request(config)
      })
    }

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
