import request from '@/utils/request'

export function loginApi(data) {
  return request.post('/api/auth/login', data)
}

export function registerApi(data) {
  return request.post('/api/auth/register', data)
}
