import request from '@/utils/request'

/** 操作日志分页查询（管理员）：params 支持 page/page_size/username/method/success */
export function getOperationLogsApi(params) {
  return request.get('/api/operation-logs', { params })
}

/** 导出审计报告 Excel（管理员，可按操作人/时间范围过滤） */
export function exportOperationLogsApi(params) {
  return request.get('/api/operation-logs/export', { params, responseType: 'blob' })
}
