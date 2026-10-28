import request from '@/utils/request'

/** 我的收藏列表：target_type 可选 lab / equipment */
export function getFavoritesApi(params) {
  return request.get('/api/favorites', { params })
}

/** 收藏实验室或设备（幂等） */
export function addFavoriteApi(data) {
  return request.post('/api/favorites', data)
}

export function deleteFavoriteApi(id) {
  return request.delete(`/api/favorites/${id}`)
}
