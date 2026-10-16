import request from '@/utils/request'

export function getUserInfoApi() {
  return request.get('/api/user/info')
}

export function updateProfileApi(data) {
  return request.put('/api/user/profile', data)
}

export function updatePasswordApi(data) {
  return request.put('/api/user/password', data)
}

export function getUserListApi(params) {
  return request.get('/api/user', { params })
}

export function createUserApi(data) {
  return request.post('/api/user', data)
}

export function updateUserApi(userId, data) {
  return request.put(`/api/user/${userId}`, data)
}

export function deleteUserApi(userId) {
  return request.delete(`/api/user/${userId}`)
}

export function adminResetPasswordApi(userId, data) {
  return request.put(`/api/user/${userId}/reset-password`, data)
}

export function uploadImageApi(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/api/upload/image', formData)
}
