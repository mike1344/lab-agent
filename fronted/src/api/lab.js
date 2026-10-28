import request from '@/utils/request'

export function getLabListApi(params) {
  return request.get('/api/labs', { params })
}

export function createLabApi(data) {
  return request.post('/api/labs', data)
}

export function updateLabApi(labId, data) {
  return request.put(`/api/labs/${labId}`, data)
}

/** 删除实验室：危险操作需要 signature_password 二次确认 */
export function deleteLabApi(labId, params) {
  return request.delete(`/api/labs/${labId}`, { params })
}
