import request from '@/utils/request'

export function getSummaryApi() {
  return request.get('/api/stats/summary')
}

export function getDashboardApi(params) {
  return request.get('/api/stats/dashboard', { params })
}
