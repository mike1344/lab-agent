<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">设备采购管理</h1>
      <el-button type="primary" @click="openDialog()">录入采购申请</el-button>
    </div>

    <div class="toolbar">
      <el-select v-model="filters.status" clearable placeholder="全部状态" style="width: 140px" @change="loadList">
        <el-option label="申请中" value="pending" />
        <el-option label="已到货" value="arrived" />
        <el-option label="已验收" value="accepted" />
      </el-select>
      <el-input
        v-model="filters.keyword"
        clearable
        placeholder="搜索物品名称"
        style="width: 220px"
        @keyup.enter="loadList"
        @clear="loadList"
      />
      <el-button @click="loadList">查询</el-button>
    </div>

    <el-table v-loading="loading" :data="list" stripe>
      <el-table-column prop="name" label="物品名称" min-width="150" />
      <el-table-column prop="quantity" label="数量" width="80" />
      <el-table-column prop="equipment_name" label="关联设备" min-width="140">
        <template #default="{ row }">{{ row.equipment_name || '未关联' }}</template>
      </el-table-column>
      <el-table-column prop="applicant_name" label="申请人" width="110" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ row.status_label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="140" show-overflow-tooltip />
      <el-table-column label="申请时间" width="160">
        <template #default="{ row }">{{ formatTime(row.create_time) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status === 'pending'" link type="warning" @click="advance(row, 'arrived')">标记到货</el-button>
          <el-button v-if="row.status === 'arrived'" link type="success" @click="advance(row, 'accepted')">验收入库</el-button>
          <el-button v-if="row.status !== 'accepted'" link type="danger" @click="removeItem(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" title="录入采购申请" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="物品名称" prop="name"><el-input v-model="form.name" maxlength="100" /></el-form-item>
        <el-form-item label="采购数量" prop="quantity">
          <el-input-number v-model="form.quantity" :min="1" :max="1000" />
        </el-form-item>
        <el-form-item label="关联设备">
          <el-select v-model="form.equipment_id" clearable placeholder="可先不选，验收前再关联" style="width: 100%">
            <el-option
              v-for="item in equipmentList"
              :key="item.id"
              :label="`${item.name}（${item.code}）`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="255" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createProcurementApi,
  deleteProcurementApi,
  getProcurementListApi,
  updateProcurementApi
} from '@/api/procurement'
import { getEquipmentListApi } from '@/api/equipment'

const loading = ref(false)
const saving = ref(false)
const list = ref([])
const equipmentList = ref([])
const dialogVisible = ref(false)
const formRef = ref(null)

const filters = reactive({ status: '', keyword: '' })
const form = reactive({ name: '', quantity: 1, equipment_id: null, remark: '' })

const rules = {
  name: [{ required: true, message: '请输入物品名称', trigger: 'blur' }]
}

const statusType = (status) => ({ pending: 'warning', arrived: 'primary', accepted: 'success' }[status] || 'info')
const formatTime = (value) => (value ? String(value).replace('T', ' ').slice(0, 16) : '--')

const loadList = async () => {
  loading.value = true
  try {
    const res = await getProcurementListApi({
      status: filters.status || undefined,
      keyword: filters.keyword || undefined
    })
    list.value = res.data || []
  } finally {
    loading.value = false
  }
}

const loadEquipmentOptions = async () => {
  const res = await getEquipmentListApi({})
  equipmentList.value = res.data || []
}

const openDialog = () => {
  Object.assign(form, { name: '', quantity: 1, equipment_id: null, remark: '' })
  dialogVisible.value = true
}

const save = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    await createProcurementApi({
      name: form.name.trim(),
      quantity: form.quantity,
      equipment_id: form.equipment_id || null,
      remark: form.remark?.trim() || null
    })
    ElMessage.success('采购申请已录入')
    dialogVisible.value = false
    await loadList()
  } finally {
    saving.value = false
  }
}

const advance = async (row, status) => {
  const label = status === 'arrived' ? '已到货' : '验收入库'
  const tip = status === 'accepted' ? '验收后采购数量将计入设备库存。' : ''
  try {
    await ElMessageBox.confirm(`确认将「${row.name}」标记为${label}？${tip}`, '操作确认', { type: 'warning' })
  } catch {
    return
  }
  await updateProcurementApi(row.id, { status })
  ElMessage.success(`已标记为${label}`)
  await loadList()
}

const removeItem = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除采购记录「${row.name}」吗？`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  await deleteProcurementApi(row.id)
  ElMessage.success('删除成功')
  await loadList()
}

onMounted(async () => {
  await loadList()
  await loadEquipmentOptions()
})
</script>
