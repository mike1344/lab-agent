<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">审批流配置</h1>
      <el-button @click="loadData">刷新</el-button>
    </div>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="为实验室配置多级审批：预约提交后按节点逐级流转，全部节点通过才正式生效；未配置流程的实验室保持原来的单级审核。"
      class="page-tip"
    />

    <el-table v-loading="loading" :data="rows" stripe>
      <el-table-column prop="lab_name" label="实验室" min-width="170" />
      <el-table-column label="审批流" min-width="170">
        <template #default="{ row }">
          <template v-if="row.flow">
            <div class="flow-name">{{ row.flow.name }}</div>
            <div class="flow-desc">{{ row.flow.description || '未填写说明' }}</div>
          </template>
          <span v-else class="muted">未配置（单级审核）</span>
        </template>
      </el-table-column>
      <el-table-column label="审批节点" min-width="260">
        <template #default="{ row }">
          <div v-if="row.flow?.steps?.length" class="flow-steps">
            <el-tag v-for="step in row.flow.steps" :key="step.id || step.step_order" size="small" effect="plain">
              {{ step.step_order }}. {{ step.label }}（{{ step.approver_name }}）
            </el-tag>
          </div>
          <span v-else class="muted">--</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag v-if="row.flow" :type="row.flow.enabled ? 'success' : 'info'">
            {{ row.flow.enabled ? '启用' : '停用' }}
          </el-tag>
          <span v-else class="muted">--</span>
        </template>
      </el-table-column>
      <el-table-column label="进行中" width="80" align="center">
        <template #default="{ row }">{{ row.flow?.pending_count ?? '--' }}</template>
      </el-table-column>
      <el-table-column label="历史预约" width="90" align="center">
        <template #default="{ row }">{{ row.flow?.used_count ?? '--' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openDialog(row)">{{ row.flow ? '编辑' : '配置' }}</el-button>
          <el-button v-if="row.flow && row.flow.used_count === 0" link type="danger" @click="removeFlow(row)">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="editingFlowId ? '编辑审批流' : '配置审批流'" width="720px" destroy-on-close>
      <el-form label-width="90px">
        <el-form-item label="实验室">
          <el-select v-model="form.lab_id" :disabled="Boolean(editingFlowId)" style="width: 100%" @change="handleLabChange">
            <el-option v-for="lab in labs" :key="lab.id" :label="lab.name" :value="lab.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="流程名称">
          <el-input v-model="form.name" maxlength="100" placeholder="如：重点实验室预约审批流" />
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="form.enabled" active-text="启用" inactive-text="停用" />
          <span class="field-hint">停用后新预约不再进入本流程，已经提交的预约仍需走完</span>
        </el-form-item>
        <el-form-item label="流程说明">
          <el-input v-model="form.description" type="textarea" :rows="2" maxlength="500" placeholder="说明审批规则与注意事项（可选）" />
        </el-form-item>
      </el-form>

      <el-alert
        v-if="stepsLocked"
        type="warning"
        :closable="false"
        show-icon
        title="该流程已经被预约使用，审批节点不可再调整；可以修改名称、说明或停用。"
        class="steps-lock-tip"
      />

      <div class="steps-head">
        <span class="steps-title">审批节点（按顺序流转）</span>
        <el-button size="small" :disabled="stepsLocked || form.steps.length >= 8" @click="addStep">添加节点</el-button>
      </div>

      <div v-for="(step, index) in form.steps" :key="index" class="step-card">
        <div class="step-card-head">
          <span class="step-order">第 {{ index + 1 }} 步</span>
          <el-button
            link
            type="danger"
            :disabled="stepsLocked || form.steps.length <= 1"
            @click="removeStep(index)"
          >
            删除
          </el-button>
        </div>
        <el-form label-width="90px">
          <el-form-item label="节点名称">
            <el-input v-model="step.name" maxlength="100" :disabled="stepsLocked" placeholder="可选，如：导师初审" />
          </el-form-item>
          <el-form-item label="审批方式">
            <el-radio-group v-model="step.approver_type" :disabled="stepsLocked" @change="handleApproverTypeChange(step)">
              <el-radio value="role">按角色</el-radio>
              <el-radio value="user">指定人员</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="step.approver_type === 'role'" label="审批角色">
            <el-select v-model="step.approver_role" :disabled="stepsLocked" style="width: 240px">
              <el-option label="管理员（所有管理员）" value="admin" />
              <el-option label="教师（所有教师）" value="teacher" />
            </el-select>
          </el-form-item>
          <el-form-item v-else label="审批人">
            <el-select v-model="step.approver_id" :disabled="stepsLocked" filterable style="width: 300px" placeholder="选择教师或管理员">
              <el-option
                v-for="user in staffOptions"
                :key="user.id"
                :label="`${user.full_name || user.username}（${user.username}）`"
                :value="user.id"
              />
            </el-select>
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveFlow">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  deleteApprovalFlowApi,
  getApprovalFlowsApi,
  saveApprovalFlowApi
} from '@/api/approval'
import { getLabListApi } from '@/api/lab'
import { getUserListApi } from '@/api/user'

const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const editingFlowId = ref(null)
const editingUsedCount = ref(0)
const labs = ref([])
const flows = ref([])
const staffOptions = ref([])
const form = reactive({
  lab_id: null,
  name: '',
  description: '',
  enabled: true,
  steps: []
})

const rows = computed(() => {
  const flowMap = new Map(flows.value.map((flow) => [flow.lab_id, flow]))
  return labs.value.map((lab) => ({ lab_id: lab.id, lab_name: lab.name, flow: flowMap.get(lab.id) || null }))
})
const stepsLocked = computed(() => Boolean(editingFlowId.value) && editingUsedCount.value > 0)

function defaultAdminStep() {
  return { name: '', approver_type: 'role', approver_role: 'admin', approver_id: null }
}

function handleLabChange(labId) {
  if (editingFlowId.value) return
  const lab = labs.value.find((item) => item.id === labId)
  if (lab) form.name = `${lab.name}审批流`
}

function handleApproverTypeChange(step) {
  if (step.approver_type === 'role') {
    step.approver_role = step.approver_role || 'admin'
    step.approver_id = null
  } else {
    step.approver_id = step.approver_id || null
    step.approver_role = null
  }
}

function addStep() {
  form.steps.push({ name: '', approver_type: 'role', approver_role: 'teacher', approver_id: null })
}

function removeStep(index) {
  form.steps.splice(index, 1)
}

function openDialog(row) {
  editingFlowId.value = row.flow?.id || null
  editingUsedCount.value = row.flow?.used_count || 0
  form.lab_id = row.lab_id
  form.name = row.flow?.name || `${row.lab_name}审批流`
  form.description = row.flow?.description || ''
  form.enabled = row.flow?.enabled ?? true
  form.steps = row.flow?.steps?.length
    ? row.flow.steps.map((step) => ({
        name: step.name || '',
        approver_type: step.approver_type,
        approver_role: step.approver_role,
        approver_id: step.approver_id
      }))
    : [defaultAdminStep()]
  dialogVisible.value = true
}

function buildPayload() {
  const name = form.name.trim()
  if (name.length < 2) {
    ElMessage.warning('流程名称至少需要 2 个字符')
    return null
  }
  if (!form.steps.length) {
    ElMessage.warning('至少需要一个审批节点')
    return null
  }
  const steps = []
  for (let index = 0; index < form.steps.length; index += 1) {
    const step = form.steps[index]
    if (step.approver_type === 'role' && !step.approver_role) {
      ElMessage.warning(`第 ${index + 1} 步请选择审批角色`)
      return null
    }
    if (step.approver_type === 'user' && !step.approver_id) {
      ElMessage.warning(`第 ${index + 1} 步请选择审批人`)
      return null
    }
    steps.push({
      name: step.name?.trim() || null,
      approver_type: step.approver_type,
      approver_role: step.approver_type === 'role' ? step.approver_role : null,
      approver_id: step.approver_type === 'user' ? step.approver_id : null
    })
  }
  return { name, description: form.description.trim() || null, enabled: form.enabled, steps }
}

async function saveFlow() {
  if (!form.lab_id) {
    ElMessage.warning('请选择实验室')
    return
  }
  const payload = buildPayload()
  if (!payload) return
  saving.value = true
  try {
    const res = await saveApprovalFlowApi(form.lab_id, payload)
    ElMessage.success(res.message || '审批流保存成功')
    dialogVisible.value = false
    await loadData()
  } finally {
    saving.value = false
  }
}

async function removeFlow(row) {
  try {
    await ElMessageBox.confirm(`确定删除「${row.flow.name}」吗？`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  await deleteApprovalFlowApi(row.flow.id)
  ElMessage.success('审批流已删除')
  await loadData()
}

async function loadData() {
  loading.value = true
  try {
    const [labRes, flowRes, userRes] = await Promise.all([
      getLabListApi(),
      getApprovalFlowsApi(),
      getUserListApi({ page: 1, page_size: 100 })
    ])
    labs.value = labRes.data || []
    flows.value = flowRes.data || []
    staffOptions.value = (userRes.data?.list || []).filter(
      (user) => user.is_active && (user.is_superuser || user.is_teacher)
    )
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.page-tip {
  margin-bottom: 16px;
}

.flow-name {
  font-weight: 600;
  color: #303133;
}

.flow-desc {
  margin-top: 2px;
  font-size: 12px;
  color: #909399;
}

.flow-steps {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.muted {
  color: #c0c4cc;
  font-size: 13px;
}

.field-hint {
  margin-left: 10px;
  font-size: 12px;
  color: #909399;
}

.steps-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 16px 0 10px;
}

.steps-title {
  font-weight: 600;
  color: #303133;
}

.steps-lock-tip {
  margin-bottom: 10px;
}

.step-card {
  margin-bottom: 12px;
  padding: 12px 14px 0;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  background: #fafafa;
}

.step-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.step-order {
  font-weight: 600;
  color: #409eff;
}
</style>
