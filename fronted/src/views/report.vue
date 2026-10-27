<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">报表中心</h1>
      <el-button type="success" @click="exportReport">导出报表</el-button>
    </div>

    <div class="toolbar">
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        value-format="YYYY-MM-DD"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        style="width: 260px"
      />
      <el-select v-model="labId" clearable placeholder="全部实验室" style="width: 200px">
        <el-option v-for="lab in labs" :key="lab.id" :label="lab.name" :value="lab.id" />
      </el-select>
      <el-button @click="loadReport">查询</el-button>
    </div>

    <el-row :gutter="16" class="stat-row">
      <el-col :span="6">
        <el-card shadow="never">
          <div class="stat-label">总机时（小时）</div>
          <div class="stat-value">{{ report.totals.hours }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never">
          <div class="stat-label">已通过预约</div>
          <div class="stat-value">{{ report.totals.approved }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never">
          <div class="stat-label">使用人数</div>
          <div class="stat-value">{{ report.totals.users }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never">
          <div class="stat-label">预估费用（元）</div>
          <div class="stat-value">{{ report.totals.estimated_cost }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="table-card">
      <template #header>
        <span>按实验室（课程机时 {{ report.totals.course_hours }} 小时，单价 {{ report.hour_rate }} 元/小时）</span>
      </template>
      <el-table v-loading="loading" :data="report.by_lab" stripe>
        <el-table-column prop="lab_name" label="实验室" min-width="160" />
        <el-table-column prop="reservations" label="预约次数" width="100" />
        <el-table-column prop="approved" label="已通过" width="100" />
        <el-table-column prop="hours" label="机时(小时)" width="110" />
        <el-table-column prop="course_hours" label="课程机时" width="110" />
        <el-table-column prop="users" label="使用人数" width="100" />
        <el-table-column prop="estimated_cost" label="预估费用(元)" width="130" />
        <template #empty><div class="empty-text">该时间范围内没有预约数据</div></template>
      </el-table>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header>按用户</template>
      <el-table :data="report.by_user" stripe>
        <el-table-column prop="username" label="用户" min-width="160" />
        <el-table-column prop="reservations" label="预约次数" width="110" />
        <el-table-column prop="approved" label="已通过" width="100" />
        <el-table-column prop="hours" label="机时(小时)" width="110" />
        <el-table-column prop="estimated_cost" label="预估费用(元)" width="130" />
        <template #empty><div class="empty-text">暂无数据</div></template>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { exportUsageReportApi, getUsageReportApi } from '@/api/report'
import { getLabListApi } from '@/api/lab'
import { downloadBlobResponse } from '@/utils/download'

const loading = ref(false)
const labs = ref([])
const labId = ref(null)
const dateRange = ref([])

// 默认展示最近 30 天，与后端默认口径一致
const pad = (value) => String(value).padStart(2, '0')
const toDateString = (value) =>
  `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`
const end = new Date()
const start = new Date(end.getTime() - 29 * 24 * 3600 * 1000)
dateRange.value = [toDateString(start), toDateString(end)]

const report = reactive({
  totals: { reservations: 0, approved: 0, hours: 0, users: 0, course_hours: 0, estimated_cost: 0 },
  hour_rate: 0,
  by_lab: [],
  by_user: []
})

const buildParams = () => {
  const params = {}
  if (dateRange.value?.length === 2) {
    params.start_date = dateRange.value[0]
    params.end_date = dateRange.value[1]
  }
  if (labId.value) params.lab_id = labId.value
  return params
}

const loadReport = async () => {
  loading.value = true
  try {
    const res = await getUsageReportApi(buildParams())
    report.totals = res.data?.totals || report.totals
    report.hour_rate = res.data?.hour_rate || 0
    report.by_lab = res.data?.by_lab || []
    report.by_user = res.data?.by_user || []
  } finally {
    loading.value = false
  }
}

const exportReport = async () => {
  const res = await exportUsageReportApi(buildParams())
  downloadBlobResponse(res, '机时报表.xlsx')
}

onMounted(async () => {
  const labRes = await getLabListApi()
  labs.value = labRes.data || []
  await loadReport()
})
</script>

<style scoped>
.stat-row {
  margin-bottom: 16px;
}

.stat-label {
  font-size: 13px;
  color: #909399;
}

.stat-value {
  margin-top: 6px;
  font-size: 24px;
  font-weight: 600;
  color: #1f2d3d;
}

.table-card {
  margin-bottom: 16px;
}

.empty-text {
  padding: 20px 0;
  text-align: center;
  color: #909399;
}
</style>
