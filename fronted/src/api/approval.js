import request from '@/utils/request'

/** 审批流列表（管理员）：包含每个实验室的节点、启用状态与进行中数量 */
export function getApprovalFlowsApi() {
  return request.get('/api/approval-flows')
}

/** 读取单个实验室的审批流；未配置时 data 为 null */
export function getLabApprovalFlowApi(labId) {
  return request.get(`/api/approval-flows/${labId}`)
}

/** 新建或整体更新某个实验室的审批流 */
export function saveApprovalFlowApi(labId, data) {
  return request.put(`/api/approval-flows/${labId}`, data)
}

/** 删除未被任何预约使用的审批流 */
export function deleteApprovalFlowApi(flowId) {
  return request.delete(`/api/approval-flows/${flowId}`)
}
