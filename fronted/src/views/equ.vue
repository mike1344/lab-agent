<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ isAdmin ? '设备管理' : '实验室设备列表' }}</h1>
      <el-button v-if="isAdmin" type="primary" @click="openEquipmentDialog()">新增设备</el-button>
    </div>

    <div class="toolbar">
      <el-select v-model="selectedLabId" clearable placeholder="全部实验室" style="width: 200px" @change="loadEquipmentList">
        <el-option v-for="lab in labList" :key="lab.id" :label="lab.name" :value="lab.id" />
      </el-select>
      <el-input v-model="keyword" clearable placeholder="搜索设备名称" style="width: 220px" @keyup.enter="loadEquipmentList" @clear="loadEquipmentList" />
      <el-button @click="loadEquipmentList">查询</el-button>
    </div>

    <el-table v-loading="loadingValue" :data="equipmentList" stripe>
      <el-table-column prop="code" label="设备编号" min-width="120" />
      <el-table-column prop="name" label="设备名称" min-width="150" />
      <el-table-column prop="lab_name" label="所属实验室" min-width="150" />
      <el-table-column prop="quantity" label="数量" width="90" />
      <el-table-column prop="description" label="设备说明" min-width="220" show-overflow-tooltip />
      <el-table-column label="状态" width="100">
        <template #default="scope"><el-tag :type="scope.row.status === 1 ? 'success' : 'warning'">{{ scope.row.status === 1 ? '正常' : '维护中' }}</el-tag></template>
      </el-table-column>
      <el-table-column v-if="isAdmin" label="操作" width="150" fixed="right">
        <template #default="scope">
          <el-button link type="primary" @click="openEquipmentDialog(scope.row)">编辑</el-button>
          <el-button link type="danger" @click="removeEquipment(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="equipmentForm.id ? '编辑设备' : '新增设备'" width="540px">
      <el-form ref="equipmentFormRef" :model="equipmentForm" :rules="equipmentRules" label-width="100px">
        <el-form-item label="所属实验室" prop="lab_id">
          <el-select v-model="equipmentForm.lab_id" style="width: 100%"><el-option v-for="lab in labList" :key="lab.id" :label="lab.name" :value="lab.id" /></el-select>
        </el-form-item>
        <el-form-item label="设备名称" prop="name"><el-input v-model="equipmentForm.name" /></el-form-item>
        <el-form-item label="设备编号" prop="code"><el-input v-model="equipmentForm.code" /></el-form-item>
        <el-form-item label="设备数量" prop="quantity"><el-input-number v-model="equipmentForm.quantity" :min="0" :max="10000" /></el-form-item>
        <el-form-item label="设备状态"><el-switch v-model="equipmentForm.status" :active-value="1" :inactive-value="0" active-text="正常" inactive-text="维护" /></el-form-item>
        <el-form-item label="设备说明"><el-input v-model="equipmentForm.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="savingValue" @click="saveEquipment">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute } from 'vue-router'
import { createEquipmentApi, deleteEquipmentApi, getEquipmentListApi, updateEquipmentApi } from '@/api/equipment'
import { getLabListApi } from '@/api/lab'
import { useUser } from '@/utils/user'

const route = useRoute()
const { isAdmin } = useUser()
const loadingValue = ref(false)
const savingValue = ref(false)
const dialogVisible = ref(false)
const equipmentFormRef = ref(null)
const labList = ref([])
const equipmentList = ref([])
const keyword = ref('')
const selectedLabId = ref(route.query.lab_id ? Number(route.query.lab_id) : null)
const equipmentForm = reactive({ id: null, lab_id: null, name: '', code: '', quantity: 1, description: '', status: 1 })

const equipmentRules = {
  lab_id: [{ required: true, message: '请选择所属实验室', trigger: 'change' }],
  name: [{ required: true, message: '请输入设备名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入设备编号', trigger: 'blur' }]
}

const loadLabs = async () => {
  const res = await getLabListApi()
  labList.value = res.data
}

const loadEquipmentList = async () => {
  loadingValue.value = true
  try {
    const res = await getEquipmentListApi({ lab_id: selectedLabId.value || undefined, keyword: keyword.value, only_available: !isAdmin.value })
    equipmentList.value = res.data
  } finally { loadingValue.value = false }
}

const openEquipmentDialog = (equipment = null) => {
  Object.assign(equipmentForm, equipment || { id: null, lab_id: selectedLabId.value || labList.value[0]?.id || null, name: '', code: '', quantity: 1, description: '', status: 1 })
  dialogVisible.value = true
}

const saveEquipment = async () => {
  const valid = await equipmentFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    const data = { lab_id: equipmentForm.lab_id, name: equipmentForm.name.trim(), code: equipmentForm.code.trim(), quantity: equipmentForm.quantity, description: equipmentForm.description || null, status: equipmentForm.status }
    if (equipmentForm.id) await updateEquipmentApi(equipmentForm.id, data)
    else await createEquipmentApi(data)
    ElMessage.success(equipmentForm.id ? '设备修改成功' : '设备新增成功')
    dialogVisible.value = false
    await loadEquipmentList()
  } finally { savingValue.value = false }
}

const removeEquipment = async (equipment) => {
  try {
    await ElMessageBox.confirm(`确定删除设备“${equipment.name}”吗？`, '删除确认', { type: 'warning' })
  } catch {
    // 用户点击“取消”或关闭弹窗时，Element Plus 会 reject 这个 Promise。
    return
  }
  await deleteEquipmentApi(equipment.id)
  ElMessage.success('删除成功')
  await loadEquipmentList()
}

onMounted(async () => {
  await loadLabs()
  await loadEquipmentList()
})
</script>
