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

export function deleteLabApi(labId) {
  return request.delete(`/api/labs/${labId}`)
}
