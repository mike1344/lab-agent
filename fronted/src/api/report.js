import request from '@/utils/request'

/** 机时报表：按实验室 / 用户两个维度汇总（教师/管理员） */
export function getUsageReportApi(params) {
  return request.get('/api/reports/usage', { params })
}

/** 导出机时报表 Excel（两个工作表） */
export function exportUsageReportApi(params) {
  return request.get('/api/reports/usage/export', { params, responseType: 'blob' })
}
