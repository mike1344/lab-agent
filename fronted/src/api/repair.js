import request from '@/utils/request'

export function createRepairApi(data) {
  return request.post('/api/repairs', data)
}

export function getMyRepairListApi(params) {
  return request.get('/api/repairs/mine', { params })
}

export function getRepairListApi(params) {
  return request.get('/api/repairs', { params })
}

export function getRepairDetailApi(id) {
  return request.get(`/api/repairs/${id}`)
}

export function handleRepairApi(id, data) {
  return request.put(`/api/repairs/${id}/handle`, data)
}
