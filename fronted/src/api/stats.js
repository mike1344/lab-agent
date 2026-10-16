import request from '@/utils/request'

export function getSummaryApi() {
  return request.get('/api/stats/summary')
}
