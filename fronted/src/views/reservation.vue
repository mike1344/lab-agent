<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ isStaff ? '预约审核' : '我的预约' }}</h1>
      <el-button v-if="!isStaff" type="primary" @click="$router.push('/lab')">发起预约</el-button>
    </div>

    <div class="toolbar">
      <el-select v-model="statusValue" clearable placeholder="全部状态" style="width: 160px" @change="loadReservationList">
        <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-select v-if="isStaff" v-model="selectedLabId" clearable placeholder="全部实验室" style="width: 190px" @change="loadReservationList">
        <el-option v-for="lab in labList" :key="lab.id" :label="lab.name" :value="lab.id" />
      </el-select>
      <el-button @click="loadReservationList">刷新</el-button>
      <el-button v-if="isStaff" type="success" plain @click="exportExcel">导出 Excel</el-button>
    </div>

    <el-table v-loading="loadingValue" :data="reservationList" stripe>
      <el-table-column v-if="isStaff" prop="user_name" label="预约人" min-width="110" />
      <el-table-column prop="lab_name" label="实验室" min-width="140" />
      <el-table-column prop="reservation_date" label="预约日期" width="120" />
      <el-table-column label="预约时间" width="150">
        <template #default="scope">{{ formatTime(scope.row.start_time) }} - {{ formatTime(scope.row.end_time) }}</template>
      </el-table-column>
      <el-table-column prop="purpose" label="用途" min-width="180" show-overflow-tooltip />
      <el-table-column label="状态" width="100">
        <template #default="scope"><el-tag :type="statusMap[scope.row.status]?.type">{{ statusMap[scope.row.status]?.label || scope.row.status }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="review_comment" label="审核意见" min-width="160" show-overflow-tooltip />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="scope">
          <template v-if="isStaff && scope.row.status === 'pending'">
            <el-button link type="success" @click="openReviewDialog(scope.row, 'approved')">通过</el-button>
            <el-button link type="danger" @click="openReviewDialog(scope.row, 'rejected')">拒绝</el-button>
          </template>
          <template v-else-if="!isStaff && scope.row.status === 'pending'">
            <el-button link type="primary" @click="openEditDialog(scope.row)">修改</el-button>
            <el-button link type="danger" @click="cancelReservation(scope.row)">取消</el-button>
          </template>
          <el-button v-else-if="!isStaff && scope.row.status === 'approved'" link type="danger" @click="cancelReservation(scope.row)">取消预约</el-button>
          <span v-else class="operation-finished">已处理</span>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="reviewDialogVisible" :title="reviewForm.status === 'approved' ? '通过预约' : '拒绝预约'" width="460px">
      <el-form label-position="top">
        <el-form-item label="审核意见">
          <el-input v-model="reviewForm.review_comment" type="textarea" :rows="4" :placeholder="reviewForm.status === 'rejected' ? '建议填写拒绝原因' : '可填写使用注意事项'" />
        </el-form-item>
        <el-form-item v-if="reviewForm.status === 'rejected'" label="二次验证">
          <el-input
            v-model="reviewForm.signature_password"
            type="password"
            show-password
            placeholder="请输入当前账号密码（5 分钟内已验证过可留空）"
          />
          <div class="signature-hint">拒绝属于危险操作，需要密码二次确认；验证有效期 5 分钟，期内重复危险操作免输。</div>
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="reviewDialogVisible = false">取消</el-button><el-button :type="reviewForm.status === 'approved' ? 'success' : 'danger'" :loading="savingValue" @click="saveReview">确认</el-button></template>
    </el-dialog>

    <!-- 修改预约弹窗 -->
    <el-dialog v-model="editDialogVisible" title="修改预约" width="460px">
      <el-form label-position="top">
        <el-form-item label="预约日期">
          <el-date-picker v-model="editForm.reservation_date" type="date" value-format="YYYY-MM-DD" :disabled-date="disablePastDate" placeholder="选择日期" style="width: 100%" />
        </el-form-item>
        <el-form-item label="开始时间">
          <el-time-picker v-model="editForm.start_time" value-format="HH:mm:ss" placeholder="选择时间" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-time-picker v-model="editForm.end_time" value-format="HH:mm:ss" placeholder="选择时间" style="width: 100%" />
        </el-form-item>
        <el-form-item label="用途">
          <el-input v-model="editForm.purpose" type="textarea" :rows="3" placeholder="请填写预约用途" />
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="editDialogVisible = false">取消</el-button><el-button type="primary" :loading="savingValue" @click="saveEdit">保存修改</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getLabListApi } from '@/api/lab'
import { cancelReservationApi, exportReservationsApi, getMyReservationListApi, getReservationListApi, reviewReservationApi, updateReservationApi } from '@/api/reservation'
import { useUser } from '@/utils/user'

const { isStaff } = useUser()
const loadingValue = ref(false)
const savingValue = ref(false)
const statusValue = ref('')
const selectedLabId = ref(null)
const labList = ref([])
const reservationList = ref([])
const reviewDialogVisible = ref(false)
const selectedReservation = ref(null)
const reviewForm = reactive({ status: 'approved', review_comment: '', signature_password: '' })
const editDialogVisible = ref(false)
const editForm = reactive({ reservation_date: '', start_time: '', end_time: '', purpose: '' })
const editingId = ref(null)
const disablePastDate = (date) => date.getTime() < new Date().setHours(0, 0, 0, 0)

const statusOptions = [
  { label: '待审核', value: 'pending' }, { label: '已通过', value: 'approved' },
  { label: '已拒绝', value: 'rejected' }, { label: '已取消', value: 'cancelled' },
  { label: '已过期', value: 'expired' }
]
const statusMap = {
  pending: { label: '待审核', type: 'warning' }, approved: { label: '已通过', type: 'success' },
  rejected: { label: '已拒绝', type: 'danger' }, cancelled: { label: '已取消', type: 'info' },
  expired: { label: '已过期', type: 'info' }
}

const loadReservationList = async () => {
  loadingValue.value = true
  try {
    const params = { status: statusValue.value, lab_id: selectedLabId.value || undefined }
    const res = isStaff.value ? await getReservationListApi(params) : await getMyReservationListApi(params)
    reservationList.value = res.data
  } finally { loadingValue.value = false }
}

const formatTime = (value) => value?.slice(0, 5) || '--:--'
const openReviewDialog = (reservation, status) => {
  selectedReservation.value = reservation
  Object.assign(reviewForm, { status, review_comment: '', signature_password: '' })
  reviewDialogVisible.value = true
}

const saveReview = async () => {
  savingValue.value = true
  try {
    // 拒绝属于危险操作：密码随查询参数提交；服务端 5 分钟有效期内的免密窗口生效时可留空
    const params =
      reviewForm.status === 'rejected' && reviewForm.signature_password
        ? { signature_password: reviewForm.signature_password }
        : undefined
    await reviewReservationApi(selectedReservation.value.id, reviewForm, params)
    ElMessage.success('预约审核完成')
    reviewDialogVisible.value = false
    await loadReservationList()
  } finally { savingValue.value = false }
}

const cancelReservation = async (reservation) => {
  try {
    await ElMessageBox.confirm('确定取消这条预约吗？', '取消确认', { type: 'warning' })
  } catch {
    return
  }
  await cancelReservationApi(reservation.id)
  ElMessage.success('预约已取消')
  await loadReservationList()
}

const openEditDialog = (reservation) => {
  editingId.value = reservation.id
  editForm.reservation_date = reservation.reservation_date
  editForm.start_time = reservation.start_time
  editForm.end_time = reservation.end_time
  editForm.purpose = reservation.purpose
  editDialogVisible.value = true
}

const saveEdit = async () => {
  savingValue.value = true
  try {
    await updateReservationApi(editingId.value, { ...editForm })
    ElMessage.success('预约已修改')
    editDialogVisible.value = false
    await loadReservationList()
  } finally { savingValue.value = false }
}

const exportExcel = async () => {
  try {
    const params = { status: statusValue.value, lab_id: selectedLabId.value || undefined }
    const res = await exportReservationsApi(params)
    const blob = new Blob([res], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `预约记录_${new Date().toISOString().slice(0, 10)}.xlsx`
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (_) {
    ElMessage.error('导出失败')
  }
}

onMounted(async () => {
  if (isStaff.value) {
    const res = await getLabListApi()
    labList.value = res.data
  }
  await loadReservationList()
})
</script>

<style scoped>
.operation-finished { color: #c0c4cc; font-size: 13px; }
.signature-hint { margin-top: 4px; font-size: 12px; line-height: 1.5; color: #909399; }
</style>
