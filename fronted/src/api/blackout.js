import request from '@/utils/request'

export function getBlackoutsApi(params) {
  return request.get('/api/blackouts', { params })
}

export function createBlackoutApi(data) {
  return request.post('/api/blackouts', data)
}

export function deleteBlackoutApi(id) {
  return request.delete(`/api/blackouts/${id}`)
}
