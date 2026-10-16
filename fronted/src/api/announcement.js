import request from '@/utils/request'

export function getAnnouncementListApi(params) {
  return request.get('/api/announcements', { params })
}

export function getAnnouncementDetailApi(id) {
  return request.get(`/api/announcements/${id}`)
}

export function createAnnouncementApi(data) {
  return request.post('/api/announcements', data)
}

export function updateAnnouncementApi(id, data) {
  return request.put(`/api/announcements/${id}`, data)
}

export function deleteAnnouncementApi(id) {
  return request.delete(`/api/announcements/${id}`)
}
