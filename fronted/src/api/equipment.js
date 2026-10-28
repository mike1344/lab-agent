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

/** 删除设备：危险操作需要 signature_password 二次确认 */
export function deleteEquipmentApi(equipmentId, params) {
  return request.delete(`/api/equipment/${equipmentId}`, { params })
}

/** 导出设备台账 Excel（blob 响应，经 downloadBlobResponse 触发下载） */
export function exportEquipmentApi(params) {
  return request.get('/api/equipment/export', { params, responseType: 'blob' })
}
