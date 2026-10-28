import request from '@/utils/request'

export function getProcurementListApi(params) {
  return request.get('/api/procurements', { params })
}

export function createProcurementApi(data) {
  return request.post('/api/procurements', data)
}

/** 状态流转：arrived 到货 / accepted 验收入库 */
export function updateProcurementApi(id, data) {
  return request.put(`/api/procurements/${id}`, data)
}

export function deleteProcurementApi(id) {
  return request.delete(`/api/procurements/${id}`)
}
