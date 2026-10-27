<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ isStaff ? '实验课程' : '课程表' }}</h1>
      <el-button v-if="isStaff" type="primary" @click="openDialog()">新增课程</el-button>
    </div>

    <div class="toolbar">
      <el-select v-model="filters.lab_id" clearable placeholder="全部实验室" style="width: 200px" @change="loadList">
        <el-option v-for="lab in labList" :key="lab.id" :label="lab.name" :value="lab.id" />
      </el-select>
      <el-input
        v-model="filters.keyword"
        clearable
        placeholder="搜索课程名称"
        style="width: 220px"
        @keyup.enter="loadList"
        @clear="loadList"
      />
      <el-checkbox v-model="filters.mine" @change="loadList">我的课程</el-checkbox>
      <el-button @click="loadList">查询</el-button>
    </div>

    <el-table v-loading="loading" :data="list" stripe>
      <el-table-column prop="name" label="课程名称" min-width="150" />
      <el-table-column prop="lab_name" label="实验室" min-width="140" />
      <el-table-column prop="teacher_name" label="授课教师" width="120" />
      <el-table-column prop="weekday_label" label="星期" width="80" />
      <el-table-column label="上课时间" width="130">
        <template #default="{ row }">{{ (row.start_time || '').slice(0, 5) }} - {{ (row.end_time || '').slice(0, 5) }}</template>
      </el-table-column>
      <el-table-column label="学期" width="210">
        <template #default="{ row }">{{ row.start_date }} ~ {{ row.end_date }}</template>
      </el-table-column>
      <el-table-column prop="enrolled_count" label="选课人数" width="90" />
      <el-table-column prop="description" label="说明" min-width="160" show-overflow-tooltip />
      <el-table-column v-if="isStaff" label="操作" width="240" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="openRoster(row)">选课名单</el-button>
          <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
          <el-button link type="danger" @click="removeItem(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 建课 / 编辑 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑课程' : '新增课程'" width="560px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="课程名称" prop="name"><el-input v-model="form.name" maxlength="100" /></el-form-item>
        <el-form-item label="实验室" prop="lab_id">
          <el-select v-model="form.lab_id" style="width: 100%">
            <el-option v-for="lab in labList" :key="lab.id" :label="lab.name" :value="lab.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="上课星期" prop="weekday">
          <el-select v-model="form.weekday" style="width: 100%">
            <el-option v-for="day in weekdays" :key="day.value" :label="day.label" :value="day.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="上课时间" prop="timeRange">
          <el-time-picker
            v-model="form.timeRange"
            is-range
            value-format="HH:mm:ss"
            range-separator="至"
            start-placeholder="开始"
            end-placeholder="结束"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="学期区间" prop="dateRange">
          <el-date-picker
            v-model="form.dateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="课程说明">
          <el-input v-model="form.description" type="textarea" :rows="2" maxlength="500" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 选课名单 -->
    <el-dialog v-model="rosterVisible" :title="`选课名单：${rosterCourse?.name || ''}`" width="620px">
      <div class="roster-actions">
        <el-select
          v-model="selectedStudents"
          multiple
          filterable
          placeholder="选择学生加入名单"
          style="flex: 1"
        >
          <el-option
            v-for="student in candidates"
            :key="student.id"
            :label="`${student.full_name || student.username}（${student.username}）`"
            :value="student.id"
          />
        </el-select>
        <el-button type="primary" @click="addStudents">加入</el-button>
      </div>
      <el-table :data="roster" size="small" max-height="320">
        <el-table-column label="学生" min-width="140">
          <template #default="{ row }">{{ row.full_name || row.username }}</template>
        </el-table-column>
        <el-table-column prop="username" label="账号" width="120" />
        <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button link type="danger" @click="removeStudent(row)">移出</el-button>
          </template>
        </el-table-column>
        <template #empty><div class="empty-text">还没有学生选课</div></template>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  addCourseStudentsApi,
  createCourseApi,
  deleteCourseApi,
  getAvailableStudentsApi,
  getCourseListApi,
  getCourseRosterApi,
  removeCourseStudentApi,
  updateCourseApi
} from '@/api/course'
import { getLabListApi } from '@/api/lab'
import { useUser } from '@/utils/user'

const { isStaff } = useUser()
const weekdays = [
  { value: 1, label: '周一' },
  { value: 2, label: '周二' },
  { value: 3, label: '周三' },
  { value: 4, label: '周四' },
  { value: 5, label: '周五' },
  { value: 6, label: '周六' },
  { value: 7, label: '周日' }
]

const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const rosterVisible = ref(false)
const formRef = ref(null)
const list = ref([])
const labList = ref([])
const selectedStudents = ref([])
const candidates = ref([])
const roster = ref([])
const rosterCourse = ref(null)

const filters = reactive({ lab_id: null, keyword: '', mine: false })
const form = reactive({ id: null, name: '', lab_id: null, weekday: 1, timeRange: [], dateRange: [], description: '' })

const rules = {
  name: [{ required: true, message: '请输入课程名称', trigger: 'blur' }],
  lab_id: [{ required: true, message: '请选择实验室', trigger: 'change' }],
  weekday: [{ required: true, message: '请选择上课星期', trigger: 'change' }],
  timeRange: [{ required: true, message: '请选择上课时间', trigger: 'change' }],
  dateRange: [{ required: true, message: '请选择学期区间', trigger: 'change' }]
}

const loadList = async () => {
  loading.value = true
  try {
    const res = await getCourseListApi({
      keyword: filters.keyword || undefined,
      lab_id: filters.lab_id || undefined,
      mine: filters.mine || undefined
    })
    list.value = res.data || []
  } finally {
    loading.value = false
  }
}

const loadLabs = async () => {
  const res = await getLabListApi()
  labList.value = res.data || []
}

const openDialog = (row = null) => {
  if (row) {
    Object.assign(form, {
      id: row.id,
      name: row.name,
      lab_id: row.lab_id,
      weekday: row.weekday,
      timeRange: [row.start_time, row.end_time],
      dateRange: [row.start_date, row.end_date],
      description: row.description || ''
    })
  } else {
    Object.assign(form, {
      id: null,
      name: '',
      lab_id: filters.lab_id || labList.value[0]?.id || null,
      weekday: 1,
      timeRange: [],
      dateRange: [],
      description: ''
    })
  }
  dialogVisible.value = true
}

const save = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const data = {
      name: form.name.trim(),
      lab_id: form.lab_id,
      weekday: form.weekday,
      start_time: form.timeRange[0],
      end_time: form.timeRange[1],
      start_date: form.dateRange[0],
      end_date: form.dateRange[1],
      description: form.description?.trim() || null
    }
    if (form.id) await updateCourseApi(form.id, data)
    else await createCourseApi(data)
    ElMessage.success(form.id ? '课程修改成功' : '课程创建成功')
    dialogVisible.value = false
    await loadList()
  } finally {
    saving.value = false
  }
}

const removeItem = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除课程「${row.name}」吗？选课名单会一并清除。`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  await deleteCourseApi(row.id)
  ElMessage.success('课程删除成功')
  await loadList()
}

const openRoster = async (row) => {
  rosterCourse.value = row
  selectedStudents.value = []
  rosterVisible.value = true
  const [rosterRes, candidateRes] = await Promise.all([getCourseRosterApi(row.id), getAvailableStudentsApi()])
  roster.value = rosterRes.data || []
  candidates.value = candidateRes.data || []
}

const addStudents = async () => {
  if (!selectedStudents.value.length) {
    ElMessage.warning('请先选择要加入的学生')
    return
  }
  const res = await addCourseStudentsApi(rosterCourse.value.id, { student_ids: selectedStudents.value })
  ElMessage.success(`已添加 ${res.data?.added ?? 0} 名学生`)
  selectedStudents.value = []
  const rosterRes = await getCourseRosterApi(rosterCourse.value.id)
  roster.value = rosterRes.data || []
  await loadList()
}

const removeStudent = async (row) => {
  await removeCourseStudentApi(rosterCourse.value.id, row.student_id)
  ElMessage.success('已移出选课名单')
  const rosterRes = await getCourseRosterApi(rosterCourse.value.id)
  roster.value = rosterRes.data || []
  await loadList()
}

onMounted(async () => {
  await loadLabs()
  await loadList()
})
</script>

<style scoped>
.roster-actions {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}

.empty-text {
  padding: 20px 0;
  text-align: center;
  color: #909399;
}
</style>
