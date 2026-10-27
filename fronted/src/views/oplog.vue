<template>
  <div class="page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div>
            <span class="title">操作日志</span>
            <span class="subtitle">所有写操作自动留痕：谁、何时、对哪个接口做了什么、结果如何</span>
          </div>
          <el-button size="small" @click="loadLogs">刷新</el-button>
        </div>
      </template>

      <div class="filter-bar">
        <el-input
          v-model="filters.username"
          placeholder="操作人用户名"
          clearable
          style="width: 180px"
          @keyup.enter="handleSearch"
        />
        <el-select v-model="filters.method" placeholder="请求方法" clearable style="width: 140px">
          <el-option label="全部方法" value="" />
          <el-option label="POST 新增" value="POST" />
          <el-option label="PUT 修改" value="PUT" />
          <el-option label="PATCH 修改" value="PATCH" />
          <el-option label="DELETE 删除" value="DELETE" />
        </el-select>
        <el-select v-model="filters.success" placeholder="结果" clearable style="width: 120px">
          <el-option label="全部结果" value="" />
          <el-option label="成功" value="true" />
          <el-option label="失败" value="false" />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 260px"
        />
        <el-button type="primary" @click="handleSearch">查询</el-button>
        <el-button @click="handleReset">重置</el-button>
        <el-button type="success" @click="exportLogs">导出审计报告</el-button>
      </div>

      <el-table v-loading="loading" :data="logs" stripe>
        <el-table-column label="时间" width="170">
          <template #default="{ row }">{{ formatTime(row.create_time) }}</template>
        </el-table-column>
        <el-table-column prop="username" label="操作人" width="120" />
        <el-table-column label="角色" width="92">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_superuser ? 'danger' : 'info'">
              {{ row.is_superuser ? '管理员' : '用户' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="method" label="方法" width="82" />
        <el-table-column prop="summary" label="操作说明" min-width="190" show-overflow-tooltip />
        <el-table-column prop="path" label="接口路径" min-width="190" show-overflow-tooltip />
        <el-table-column label="结果" width="82">
          <template #default="{ row }">
            <el-tag size="small" :type="row.success ? 'success' : 'danger'">
              {{ row.success ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="http_status" label="状态码" width="82" />
        <el-table-column prop="message" label="结果信息" min-width="150" show-overflow-tooltip />
        <el-table-column prop="ip" label="IP" width="120" />
        <el-table-column label="耗时" width="90">
          <template #default="{ row }">{{ row.duration_ms }} ms</template>
        </el-table-column>
        <template #empty>
          <div class="empty-text">暂无操作日志</div>
        </template>
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @current-change="loadLogs"
          @size-change="handleSizeChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { exportOperationLogsApi, getOperationLogsApi } from '@/api/operationLog'
import { downloadBlobResponse } from '@/utils/download'

const loading = ref(false)
const logs = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const dateRange = ref([])

const filters = reactive({
  username: '',
  method: '',
  success: ''
})

// 后端返回 ISO 时间（2026-10-21T11:22:33），去掉 T 只留到秒，便于阅读
const formatTime = (value) => (value ? String(value).replace('T', ' ').slice(0, 19) : '')

const buildParams = () => {
  const params = { page: page.value, page_size: pageSize.value }
  if (filters.username.trim()) params.username = filters.username.trim()
  if (filters.method) params.method = filters.method
  if (filters.success) params.success = filters.success
  return params
}

const loadLogs = async () => {
  loading.value = true
  try {
    const res = await getOperationLogsApi(buildParams())
    logs.value = res.data?.list || []
    total.value = res.data?.total || 0
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  page.value = 1
  loadLogs()
}

const handleReset = () => {
  filters.username = ''
  filters.method = ''
  filters.success = ''
  dateRange.value = []
  page.value = 1
  loadLogs()
}

// 导出审计报告：按操作人与时间范围过滤，返回 xlsx 文件流
const exportLogs = async () => {
  const params = {}
  if (filters.username.trim()) params.username = filters.username.trim()
  if (dateRange.value?.length === 2) {
    params.start_date = dateRange.value[0]
    params.end_date = dateRange.value[1]
  }
  const res = await exportOperationLogsApi(params)
  downloadBlobResponse(res, '操作审计.xlsx')
}

// 切换每页条数后回到第一页，避免停留在超出范围的页码上
const handleSizeChange = () => {
  page.value = 1
  loadLogs()
}

onMounted(loadLogs)
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.card-header .title {
  font-size: 17px;
  font-weight: 600;
  color: #1f2d3d;
}

.card-header .subtitle {
  margin-left: 10px;
  font-size: 13px;
  color: #909399;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.empty-text {
  padding: 24px 0;
  color: #909399;
}
</style>
