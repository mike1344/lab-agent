import request from '@/utils/request'

export function getEquipmentListApi(params) {
  return request.get('/api/equipment', { params })
}

export function createEquipmentApi(data) {
  return request.post('/api/equipment', data)
}

export function updateEquipmentApi(equipmentId, data) {
  return request.put(`/api/equipment/${equipmentId}`, data)
}

export function deleteEquipmentApi(equipmentId) {
  return request.delete(`/api/equipment/${equipmentId}`)
}
