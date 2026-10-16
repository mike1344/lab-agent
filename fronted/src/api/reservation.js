import request from '@/utils/request'

export function createReservationApi(data) {
  return request.post('/api/reservations', data)
}

export function getReservationSlotsApi(params) {
  return request.get('/api/reservations/slots', { params })
}

export function getMyReservationListApi(params) {
  return request.get('/api/reservations/mine', { params })
}

export function cancelReservationApi(reservationId) {
  return request.put(`/api/reservations/${reservationId}/cancel`)
}

export function getReservationListApi(params) {
  return request.get('/api/reservations', { params })
}

export function reviewReservationApi(reservationId, data) {
  return request.put(`/api/reservations/${reservationId}/review`, data)
}

export function updateReservationApi(reservationId, data) {
  return request.put(`/api/reservations/${reservationId}`, data)
}

export function exportReservationsApi(params) {
  return request.get('/api/reservations/export', { params, responseType: 'blob' })
}
