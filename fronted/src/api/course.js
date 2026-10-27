import request from '@/utils/request'

export function getCourseListApi(params) {
  return request.get('/api/courses', { params })
}

export function createCourseApi(data) {
  return request.post('/api/courses', data)
}

export function updateCourseApi(id, data) {
  return request.put(`/api/courses/${id}`, data)
}

export function deleteCourseApi(id) {
  return request.delete(`/api/courses/${id}`)
}

/** 选课弹窗的学生候选名单（教师/管理员） */
export function getAvailableStudentsApi() {
  return request.get('/api/courses/available-students')
}

export function getCourseRosterApi(id) {
  return request.get(`/api/courses/${id}/students`)
}

export function addCourseStudentsApi(id, data) {
  return request.post(`/api/courses/${id}/students`, data)
}

export function removeCourseStudentApi(id, studentId) {
  return request.delete(`/api/courses/${id}/students/${studentId}`)
}
