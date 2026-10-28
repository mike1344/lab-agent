import request from '@/utils/request'

export function loginApi(data) {
  return request.post('/api/auth/login', data)
}

/** 获取图形验证码：后端开启时返回 { enabled, captcha_id, image }，关闭时 enabled=false */
export function getCaptchaApi() {
  return request.get('/api/auth/captcha')
}

export function registerApi(data) {
  return request.post('/api/auth/register', data)
}
