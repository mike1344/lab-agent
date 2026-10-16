import request from '@/utils/request'

export function getMyNotificationsApi() {
  return request.get('/api/notifications/mine')
}

export function getUnreadCountApi() {
  return request.get('/api/notifications/unread-count')
}

export function markAsReadApi(id) {
  return request.put(`/api/notifications/${id}/read`)
}

export function markAllAsReadApi() {
  return request.put('/api/notifications/read-all')
}
