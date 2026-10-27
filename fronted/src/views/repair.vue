<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ isAdmin ? '报修管理' : '我的报修' }}</h1>
      <el-button v-if="!isAdmin" type="primary" @click="openCreateDialog">提交报修</el-button>
    </div>

    <div class="toolbar">
      <el-select v-model="statusValue" clearable placeholder="全部状态" style="width: 140px" @change="loadList">
        <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-select v-if="isAdmin" v-model="selectedLabId" clearable placeholder="全部实验室" style="width: 180px" @change="loadList">
        <el-option v-for="lab in labList" :key="lab.id" :label="lab.name" :value="lab.id" />
      </el-select>
      <el-button @click="loadList">刷新</el-button>
      <el-button v-if="isAdmin" @click="exportRepairs">导出</el-button>
    </div>

    <el-table v-loading="loadingValue" :data="list" stripe>
      <el-table-column prop="title" label="报修标题" min-width="180" show-overflow-tooltip />
      <el-table-column v-if="isAdmin" prop="reporter_name" label="报修人" width="110" />
      <el-table-column label="关联实验室" width="140">
        <template #default="scope">{{ scope.row.lab_name || '-' }}</template>
      </el-table-column>
      <el-table-column label="关联设备" width="140">
        <template #default="scope">{{ scope.row.equipment_name || '-' }}</template>
      </el-table-column>
      <el-table-column prop="description" label="故障描述" min-width="200" show-overflow-tooltip />
      <el-table-column label="状态" width="100">
        <template #default="scope"><el-tag :type="statusMap[scope.row.status]?.type">{{ statusMap[scope.row.status]?.label || scope.row.status }}</el-tag></template>
      </el-table-column>
      <el-table-column label="提交时间" width="160">
        <template #default="scope">{{ formatTime(scope.row.create_time) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="scope">
          <el-button link type="primary" @click="viewDetail(scope.row)">详情</el-button>
          <el-button v-if="isAdmin && scope.row.status !== 'resolved'" link type="success" @click="openHandleDialog(scope.row)">处理</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 提交报修弹窗 -->
    <el-dialog v-model="createVisible" title="提交报修" width="560px">
      <el-form ref="createFormRef" :model="createForm" :rules="createRules" label-width="90px">
        <el-form-item label="报修标题" prop="title"><el-input v-model="createForm.title" maxlength="200" show-word-limit /></el-form-item>
        <el-form-item label="关联实验室">
          <el-select v-model="createForm.lab_id" clearable placeholder="可选" style="width: 100%">
            <el-option v-for="lab in labList" :key="lab.id" :label="lab.name" :value="lab.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联设备">
          <el-select v-model="createForm.equipment_id" clearable placeholder="可选" style="width: 100%">
            <el-option v-for="eq in equipmentList" :key="eq.id" :label="eq.name" :value="eq.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="故障描述" prop="description"><el-input v-model="createForm.description" type="textarea" :rows="4" maxlength="2000" show-word-limit /></el-form-item>
      </el-form>
      <template #footer><el-button @click="createVisible = false">取消</el-button><el-button type="primary" :loading="savingValue" @click="submitCreate">提交</el-button></template>
    </el-dialog>

    <!-- 处理报修弹窗 -->
    <el-dialog v-model="handleVisible" title="处理报修" width="500px">
      <el-form label-width="90px">
        <el-form-item label="报修标题"><span>{{ selectedRow?.title }}</span></el-form-item>
        <el-form-item label="处理状态">
          <el-radio-group v-model="handleForm.status">
            <el-radio value="processing">处理中</el-radio>
            <el-radio value="resolved">已解决</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="处理备注"><el-input v-model="handleForm.handle_comment" type="textarea" :rows="3" maxlength="500" show-word-limit /></el-form-item>
      </el-form>
      <template #footer><el-button @click="handleVisible = false">取消</el-button><el-button type="primary" :loading="savingValue" @click="submitHandle">确认</el-button></template>
    </el-dialog>

    <!-- 报修详情弹窗 -->
    <el-dialog v-model="detailVisible" title="报修详情" width="600px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="报修标题" :span="2">{{ detail.title }}</el-descriptions-item>
        <el-descriptions-item label="报修人">{{ detail.reporter_name }}</el-descriptions-item>
        <el-descriptions-item label="提交时间">{{ formatTime(detail.create_time) }}</el-descriptions-item>
        <el-descriptions-item label="关联实验室">{{ detail.lab_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="关联设备">{{ detail.equipment_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态"><el-tag :type="statusMap[detail.status]?.type">{{ statusMap[detail.status]?.label }}</el-tag></el-descriptions-item>
        <el-descriptions-item label="处理人">{{ detail.handler_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="故障描述" :span="2">{{ detail.description }}</el-descriptions-item>
        <el-descriptions-item label="处理备注" :span="2">{{ detail.handle_comment || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getLabListApi } from '@/api/lab'
import { getEquipmentListApi } from '@/api/equipment'
import { createRepairApi, exportRepairsApi, getMyRepairListApi, getRepairListApi, handleRepairApi } from '@/api/repair'
import { downloadBlobResponse } from '@/utils/download'
import { useUser } from '@/utils/user'

const { isAdmin } = useUser()
const loadingValue = ref(false)
const savingValue = ref(false)
const statusValue = ref('')
const selectedLabId = ref(null)
const list = ref([])
const labList = ref([])
const equipmentList = ref([])
const createVisible = ref(false)
const handleVisible = ref(false)
const detailVisible = ref(false)
const createFormRef = ref(null)
const selectedRow = ref(null)
const detail = ref({})

const createForm = reactive({ title: '', description: '', lab_id: null, equipment_id: null })
const handleForm = reactive({ status: 'processing', handle_comment: '' })

const createRules = {
  title: [{ required: true, message: '请输入报修标题', trigger: 'blur' }],
  description: [{ required: true, message: '请描述故障情况', trigger: 'blur' }]
}

const statusOptions = [
  { label: '待处理', value: 'pending' },
  { label: '处理中', value: 'processing' },
  { label: '已解决', value: 'resolved' }
]
const statusMap = {
  pending: { label: '待处理', type: 'warning' },
  processing: { label: '处理中', type: 'primary' },
  resolved: { label: '已解决', type: 'success' }
}

const loadList = async () => {
  loadingValue.value = true
  try {
    const params = { status: statusValue.value, lab_id: selectedLabId.value || undefined }
    const res = isAdmin.value ? await getRepairListApi(params) : await getMyRepairListApi({ status: statusValue.value })
    list.value = res.data
  } finally {
    loadingValue.value = false
  }
}

const formatTime = (value) => value ? value.replace('T', ' ').slice(0, 16) : '--'

const openCreateDialog = async () => {
  Object.assign(createForm, { title: '', description: '', lab_id: null, equipment_id: null })
  if (!labList.value.length) {
    const res = await getLabListApi({ only_open: true })
    labList.value = res.data
  }
  if (!equipmentList.value.length) {
    const res = await getEquipmentListApi()
    equipmentList.value = res.data
  }
  createVisible.value = true
}

const submitCreate = async () => {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    await createRepairApi({
      title: createForm.title.trim(),
      description: createForm.description.trim(),
      lab_id: createForm.lab_id || undefined,
      equipment_id: createForm.equipment_id || undefined
    })
    ElMessage.success('报修提交成功')
    createVisible.value = false
    await loadList()
  } finally {
    savingValue.value = false
  }
}

const openHandleDialog = (row) => {
  selectedRow.value = row
  Object.assign(handleForm, { status: row.status === 'pending' ? 'processing' : 'resolved', handle_comment: row.handle_comment || '' })
  handleVisible.value = true
}

const submitHandle = async () => {
  savingValue.value = true
  try {
    await handleRepairApi(selectedRow.value.id, handleForm)
    ElMessage.success('报修处理完成')
    handleVisible.value = false
    await loadList()
  } finally {
    savingValue.value = false
  }
}

const viewDetail = (row) => {
  detail.value = row
  detailVisible.value = true
}

const exportRepairs = async () => {
  const res = await exportRepairsApi({
    status: statusValue.value || undefined,
    lab_id: selectedLabId.value || undefined
  })
  downloadBlobResponse(res, '报修记录.xlsx')
}

onMounted(async () => {
  if (isAdmin.value) {
    const res = await getLabListApi()
    labList.value = res.data
  }
  await loadList()
})
</script>
