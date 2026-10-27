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
      <el-checkbox v-model="favoriteOnly" @change="loadEquipmentList">只看收藏</el-checkbox>
      <el-button v-if="isAdmin" @click="exportEquipmentList">导出</el-button>
    </div>

    <el-table v-loading="loadingValue" :data="equipmentList" stripe>
      <el-table-column prop="code" label="设备编号" min-width="120" />
      <el-table-column prop="name" label="设备名称" min-width="150" />
      <el-table-column prop="lab_name" label="所属实验室" min-width="150" />
      <el-table-column prop="quantity" label="数量" width="90" />
      <el-table-column prop="description" label="设备说明" min-width="220" show-overflow-tooltip />
      <el-table-column label="操作说明" width="110">
        <template #default="scope">
          <el-button v-if="scope.row.usage_doc_url" link type="primary" @click="openDocDialog(scope.row)">查看说明</el-button>
          <span v-else style="color: #c0c4cc">未设置</span>
        </template>
      </el-table-column>
      <el-table-column label="收藏" width="76" align="center">
        <template #default="scope">
          <el-button
            link
            :type="isFavorited(scope.row.id) ? 'warning' : 'info'"
            :title="isFavorited(scope.row.id) ? '取消收藏' : '收藏'"
            @click="toggleFavorite(scope.row)"
          >
            <el-icon :size="16"><StarFilled v-if="isFavorited(scope.row.id)" /><Star v-else /></el-icon>
          </el-button>
        </template>
      </el-table-column>
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
        <el-form-item label="操作说明">
          <el-input v-model="equipmentForm.usage_doc_url" clearable placeholder="https://... 或 /uploads/xxx.pdf（选填）" />
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="savingValue" @click="saveEquipment">保存</el-button></template>
    </el-dialog>

    <!-- 设备操作说明预览：内嵌 iframe 展示 PDF/网页，禁止嵌入的站点用「在新窗口打开」兜底 -->
    <el-dialog v-model="docDialogVisible" :title="`设备操作说明 - ${docEquipment?.name || ''}`" width="760px">
      <iframe
        v-if="docEquipment?.usage_doc_url"
        :src="docEquipment.usage_doc_url"
        style="width: 100%; height: 460px; border: 1px solid #ebeef5; border-radius: 6px"
      />
      <p style="margin-top: 8px; font-size: 12px; color: #909399">
        如果内容无法内嵌显示（部分站点禁止嵌入），请点击「在新窗口打开」。
      </p>
      <template #footer>
        <el-button @click="docDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="openDocInNewTab">在新窗口打开</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute } from 'vue-router'
import { Star, StarFilled } from '@element-plus/icons-vue'
import { createEquipmentApi, deleteEquipmentApi, exportEquipmentApi, getEquipmentListApi, updateEquipmentApi } from '@/api/equipment'
import { addFavoriteApi, deleteFavoriteApi, getFavoritesApi } from '@/api/favorite'
import { promptSignature } from '@/utils/confirm'
import { downloadBlobResponse } from '@/utils/download'
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
// 收藏：favoriteMap 记录 target_id -> 收藏记录 id
const favoriteOnly = ref(false)
const favoriteMap = ref({})
const equipmentForm = reactive({ id: null, lab_id: null, name: '', code: '', quantity: 1, description: '', usage_doc_url: '', status: 1 })

// 操作说明预览弹窗
const docDialogVisible = ref(false)
const docEquipment = ref(null)

const openDocDialog = (equipment) => {
  docEquipment.value = equipment
  docDialogVisible.value = true
}

const openDocInNewTab = () => {
  if (docEquipment.value?.usage_doc_url) {
    window.open(docEquipment.value.usage_doc_url, '_blank', 'noopener')
  }
}

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
    const res = await getEquipmentListApi({
      lab_id: selectedLabId.value || undefined,
      keyword: keyword.value,
      only_available: !isAdmin.value,
      favorite_only: favoriteOnly.value || undefined
    })
    equipmentList.value = res.data
  } finally { loadingValue.value = false }
}

// ===== 收藏（设备）=====
const loadFavorites = async () => {
  try {
    const res = await getFavoritesApi({ target_type: 'equipment' })
    const map = {}
    for (const item of res.data || []) map[item.target_id] = item.id
    favoriteMap.value = map
  } catch {
    favoriteMap.value = {}
  }
}

const isFavorited = (equipmentId) => Boolean(favoriteMap.value[equipmentId])

const toggleFavorite = async (equipment) => {
  const favoriteId = favoriteMap.value[equipment.id]
  if (favoriteId) {
    await deleteFavoriteApi(favoriteId)
    ElMessage.success('已取消收藏')
  } else {
    await addFavoriteApi({ target_type: 'equipment', target_id: equipment.id })
    ElMessage.success('收藏成功')
  }
  await loadFavorites()
}

const openEquipmentDialog = (equipment = null) => {
  Object.assign(equipmentForm, equipment || { id: null, lab_id: selectedLabId.value || labList.value[0]?.id || null, name: '', code: '', quantity: 1, description: '', usage_doc_url: '', status: 1 })
  dialogVisible.value = true
}

const saveEquipment = async () => {
  const valid = await equipmentFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    const data = { lab_id: equipmentForm.lab_id, name: equipmentForm.name.trim(), code: equipmentForm.code.trim(), quantity: equipmentForm.quantity, description: equipmentForm.description || null, usage_doc_url: equipmentForm.usage_doc_url?.trim() || null, status: equipmentForm.status }
    if (equipmentForm.id) await updateEquipmentApi(equipmentForm.id, data)
    else await createEquipmentApi(data)
    ElMessage.success(equipmentForm.id ? '设备修改成功' : '设备新增成功')
    dialogVisible.value = false
    await loadEquipmentList()
  } finally { savingValue.value = false }
}

const removeEquipment = async (equipment) => {
  const password = await promptSignature(`确定删除设备“${equipment.name}”吗？此操作需要输入当前账号密码确认。`)
  if (password === null) return
  await deleteEquipmentApi(equipment.id, { signature_password: password })
  ElMessage.success('删除成功')
  await loadEquipmentList()
}

onMounted(async () => {
  await loadLabs()
  await loadEquipmentList()
  await loadFavorites()
})

const exportEquipmentList = async () => {
  const res = await exportEquipmentApi({
    lab_id: selectedLabId.value || undefined,
    keyword: keyword.value || undefined
  })
  downloadBlobResponse(res, '设备台账.xlsx')
}
</script>
