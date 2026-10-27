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

/** 删除公告：危险操作需要 signature_password 二次确认 */
export function deleteAnnouncementApi(id, params) {
  return request.delete(`/api/announcements/${id}`, { params })
}

/** 公告评论列表（含一级回复，前端按 parent_id 组装） */
export function getAnnouncementCommentsApi(id) {
  return request.get(`/api/announcements/${id}/comments`)
}

/** 发表评论或回复：parent_id 为空表示顶级评论 */
export function createAnnouncementCommentApi(id, data) {
  return request.post(`/api/announcements/${id}/comments`, data)
}

export function deleteAnnouncementCommentApi(commentId) {
  return request.delete(`/api/announcements/comments/${commentId}`)
}

/** 标记已读（幂等），返回最新已读人数 */
export function markAnnouncementReadApi(id) {
  return request.post(`/api/announcements/${id}/read`)
}

/** 管理员查看已读回执：已读人数 / 在册人数 / 已读名单 */
export function getAnnouncementReadReceiptsApi(id) {
  return request.get(`/api/announcements/${id}/read-receipts`)
}
