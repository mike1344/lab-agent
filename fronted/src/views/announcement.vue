<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ isAdmin ? '公告管理' : '系统公告' }}</h1>
      <el-button v-if="isAdmin" type="primary" @click="openDialog()">发布公告</el-button>
    </div>

    <div class="toolbar">
      <el-input v-model="keyword" clearable placeholder="搜索公告标题" style="width: 240px" @keyup.enter="loadList" @clear="loadList" />
      <el-button @click="loadList">查询</el-button>
    </div>

    <el-table v-loading="loadingValue" :data="list" stripe>
      <el-table-column label="置顶" width="70" align="center">
        <template #default="scope"><el-tag v-if="scope.row.is_pinned" type="danger" size="small">置顶</el-tag></template>
      </el-table-column>
      <el-table-column prop="title" label="公告标题" min-width="240" show-overflow-tooltip />
      <el-table-column prop="publisher_name" label="发布者" width="120" />
      <el-table-column label="发布时间" width="170">
        <template #default="scope">{{ formatTime(scope.row.create_time) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="scope">
          <el-button link type="primary" @click="viewDetail(scope.row)">查看</el-button>
          <template v-if="isAdmin">
            <el-button link type="primary" @click="openDialog(scope.row)">编辑</el-button>
            <el-button link type="danger" @click="removeItem(scope.row)">删除</el-button>
          </template>
        </template>
      </el-table-column>
    </el-table>

    <!-- 发布/编辑公告弹窗 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑公告' : '发布公告'" width="600px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="标题" prop="title"><el-input v-model="form.title" maxlength="200" show-word-limit /></el-form-item>
        <el-form-item label="内容" prop="content"><el-input v-model="form.content" type="textarea" :rows="8" maxlength="10000" show-word-limit /></el-form-item>
        <el-form-item label="置顶"><el-switch v-model="form.is_pinned" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="savingValue" @click="save">保存</el-button></template>
    </el-dialog>

    <!-- 公告详情弹窗 -->
    <el-dialog v-model="detailVisible" :title="detail.title" width="640px">
      <div class="detail-meta">
        <el-tag v-if="detail.is_pinned" type="danger" size="small">置顶</el-tag>
        <span>发布者：{{ detail.publisher_name }}</span>
        <span>发布时间：{{ formatTime(detail.create_time) }}</span>
      </div>
      <el-divider />
      <div class="detail-content">{{ detail.content }}</div>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createAnnouncementApi, deleteAnnouncementApi, getAnnouncementListApi, updateAnnouncementApi } from '@/api/announcement'
import { useUser } from '@/utils/user'

const { isAdmin } = useUser()
const loadingValue = ref(false)
const savingValue = ref(false)
const keyword = ref('')
const list = ref([])
const dialogVisible = ref(false)
const detailVisible = ref(false)
const formRef = ref(null)
const detail = ref({})
const form = reactive({ id: null, title: '', content: '', is_pinned: false })

const rules = {
  title: [{ required: true, message: '请输入公告标题', trigger: 'blur' }],
  content: [{ required: true, message: '请输入公告内容', trigger: 'blur' }]
}

const loadList = async () => {
  loadingValue.value = true
  try {
    const res = await getAnnouncementListApi({ keyword: keyword.value })
    list.value = res.data
  } finally {
    loadingValue.value = false
  }
}

const formatTime = (value) => value ? value.replace('T', ' ').slice(0, 16) : '--'

const openDialog = (row = null) => {
  Object.assign(form, row || { id: null, title: '', content: '', is_pinned: false })
  dialogVisible.value = true
}

const save = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    const data = { title: form.title.trim(), content: form.content.trim(), is_pinned: form.is_pinned }
    if (form.id) await updateAnnouncementApi(form.id, data)
    else await createAnnouncementApi(data)
    ElMessage.success(form.id ? '公告修改成功' : '公告发布成功')
    dialogVisible.value = false
    await loadList()
  } finally {
    savingValue.value = false
  }
}

const removeItem = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除公告“${row.title}”吗？`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  await deleteAnnouncementApi(row.id)
  ElMessage.success('删除成功')
  await loadList()
}

const viewDetail = (row) => {
  detail.value = row
  detailVisible.value = true
}

onMounted(loadList)
</script>

<style scoped>
.detail-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 13px;
  color: #909399;
}
.detail-content {
  font-size: 14px;
  line-height: 1.8;
  color: #303133;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
