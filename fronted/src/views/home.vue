<template>
  <div class="home-page">
    <section class="welcome-card">
      <div>
        <p class="welcome-label">WELCOME</p>
        <h1>{{ greeting }}，{{ displayName }}</h1>
        <p>在这里查看实验室、设备和预约进度，也可以让 AI 助手帮你查询与预约。</p>
      </div>
      <el-button type="primary" @click="$router.push('/chat')">咨询 AI 助手</el-button>
    </section>

    <section v-loading="loadingValue" class="stats-grid">
      <article v-for="item in statItems" :key="item.key" class="stat-card" :class="{ clickable: item.path }" @click="goTo(item.path)">
        <div class="stat-icon" :style="{ background: item.color }">
          <el-icon><component :is="item.icon" /></el-icon>
        </div>
        <div>
          <p>{{ item.label }}</p>
          <strong>{{ summary[item.key] ?? 0 }}</strong>
        </div>
        <el-icon v-if="item.path" class="stat-arrow"><ArrowRight /></el-icon>
      </article>
    </section>

    <section v-loading="chartsLoading" class="charts-grid">
      <article class="chart-card chart-wide">
        <div class="chart-head">
          <h2>{{ isAdmin ? '全部预约趋势' : '我的预约趋势' }}</h2>
          <el-radio-group v-model="trendDays" size="small" @change="loadDashboard">
            <el-radio-button :value="7">近 7 天</el-radio-button>
            <el-radio-button :value="30">近 30 天</el-radio-button>
          </el-radio-group>
        </div>
        <div ref="trendRef" class="chart-body"></div>
        <div v-if="trendTotal === 0" class="chart-empty">近期暂无预约数据</div>
      </article>
      <article class="chart-card">
        <h2>实验室使用排行</h2>
        <div ref="usageRef" class="chart-body"></div>
        <div v-if="!dashboard.lab_usage.length" class="chart-empty">暂无使用数据</div>
      </article>
      <article class="chart-card">
        <h2>报修状态分布</h2>
        <div ref="repairRef" class="chart-body"></div>
        <div v-if="!dashboard.repair_status.length" class="chart-empty">暂无报修数据</div>
      </article>
    </section>

    <section class="guide-card">
      <h2>预约流程</h2>
      <el-steps :active="1" align-center>
        <el-step title="选择实验室" description="查看开放状态与设备" />
        <el-step title="提交预约" description="填写日期、时间与用途" />
        <el-step title="等待审核" description="管理员处理预约申请" />
        <el-step title="按时使用" description="审核通过后前往实验室" />
      </el-steps>
    </section>
  </div>
</template>

<script setup>
import { computed, markRaw, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, Calendar, Collection, Monitor, User } from '@element-plus/icons-vue'
import * as echarts from 'echarts/core'
import { BarChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { getDashboardApi, getSummaryApi } from '@/api/stats'
import { useUser } from '@/utils/user'

// 按需注册：只引入本项目用到的图表类型与组件，避免整包引入 echarts（约 1MB）。
echarts.use([BarChart, PieChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

const RESERVATION_STATUS_META = [
  { key: 'pending', label: '待审核', color: '#e6a23c' },
  { key: 'approved', label: '已通过', color: '#67c23a' },
  { key: 'rejected', label: '已拒绝', color: '#f56c6c' },
  { key: 'cancelled', label: '已取消', color: '#909399' },
  { key: 'expired', label: '已过期', color: '#c0c4cc' }
]
const REPAIR_STATUS_META = {
  pending: { label: '待处理', color: '#e6a23c' },
  processing: { label: '处理中', color: '#409eff' },
  resolved: { label: '已解决', color: '#67c23a' }
}

const router = useRouter()
const { userInfo, isAdmin } = useUser()
const loadingValue = ref(false)
const summary = reactive({})
const displayName = computed(() => userInfo.value?.full_name || userInfo.value?.username || '同学')

const chartsLoading = ref(false)
const trendDays = ref(7)
const dashboard = reactive({ reservation_trend: [], lab_usage: [], repair_status: [] })
const trendRef = ref(null)
const usageRef = ref(null)
const repairRef = ref(null)
let trendChart = null
let usageChart = null
let repairChart = null

const trendTotal = computed(() =>
  dashboard.reservation_trend.reduce((sum, day) => sum + day.pending + day.approved + day.rejected + day.cancelled, 0)
)

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return '上午好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

const statItems = computed(() => {
  const items = [
    { key: 'lab_count', label: '开放实验室', icon: markRaw(Collection), color: '#ecf5ff', path: '/lab' },
    { key: 'equipment_count', label: '可用设备数量', icon: markRaw(Monitor), color: '#f0f9eb', path: '/equ' },
    { key: 'reservation_count', label: isAdmin.value ? '全部预约' : '我的预约', icon: markRaw(Calendar), color: '#fdf6ec', path: '/reservation' },
    { key: 'pending_count', label: '待审核预约', icon: markRaw(Calendar), color: '#fef0f0', path: '/reservation' }
  ]
  if (isAdmin.value) items.push({ key: 'user_count', label: '系统用户', icon: markRaw(User), color: '#f4f4f5', path: '/user' })
  return items
})

const goTo = (path) => {
  if (path) router.push(path)
}

const loadDashboard = async () => {
  chartsLoading.value = true
  try {
    const res = await getDashboardApi({ days: trendDays.value })
    dashboard.reservation_trend = res.data.reservation_trend || []
    dashboard.lab_usage = res.data.lab_usage || []
    dashboard.repair_status = res.data.repair_status || []
    renderCharts()
  } finally {
    chartsLoading.value = false
  }
}

// 三个图共用一次请求的数据；div 始终挂在 DOM 上（不用 v-show），保证 echarts.init 拿得到尺寸。
const renderCharts = () => {
  if (!trendRef.value || !usageRef.value || !repairRef.value) return

  trendChart = trendChart || echarts.init(trendRef.value)
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0, itemWidth: 12, itemHeight: 8 },
    grid: { left: 8, right: 8, top: 24, bottom: 34, containLabel: true },
    xAxis: { type: 'category', data: dashboard.reservation_trend.map((day) => day.date.slice(5)) },
    yAxis: { type: 'value', minInterval: 1 },
    series: RESERVATION_STATUS_META.map((meta) => ({
      name: meta.label,
      type: 'bar',
      stack: 'total',
      barMaxWidth: 26,
      itemStyle: { color: meta.color },
      data: dashboard.reservation_trend.map((day) => day[meta.key])
    }))
  })

  usageChart = usageChart || echarts.init(usageRef.value)
  // 横向条形图自下而上绘制，先反转让次数最多的实验室显示在最上面。
  const usage = [...dashboard.lab_usage].reverse()
  usageChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 8, right: 28, top: 8, bottom: 8, containLabel: true },
    xAxis: { type: 'value', minInterval: 1 },
    yAxis: { type: 'category', data: usage.map((item) => item.lab_name), axisLabel: { width: 96, overflow: 'truncate' } },
    series: [{
      type: 'bar',
      barMaxWidth: 18,
      itemStyle: { color: '#409eff', borderRadius: [0, 6, 6, 0] },
      data: usage.map((item) => item.count)
    }]
  })

  repairChart = repairChart || echarts.init(repairRef.value)
  repairChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}：{c} 条（{d}%）' },
    legend: { bottom: 0, itemWidth: 12, itemHeight: 8 },
    series: [{
      type: 'pie',
      radius: ['42%', '66%'],
      center: ['50%', '44%'],
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { formatter: '{b}\n{c} 条' },
      data: dashboard.repair_status.map((item) => ({
        name: REPAIR_STATUS_META[item.status]?.label || item.status,
        value: item.count,
        itemStyle: { color: REPAIR_STATUS_META[item.status]?.color }
      }))
    }]
  })
}

const handleResize = () => {
  trendChart?.resize()
  usageChart?.resize()
  repairChart?.resize()
}

onMounted(async () => {
  loadingValue.value = true
  try {
    const res = await getSummaryApi()
    Object.assign(summary, res.data)
  } finally {
    loadingValue.value = false
  }
  window.addEventListener('resize', handleResize)
  await loadDashboard()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  trendChart?.dispose()
  usageChart?.dispose()
  repairChart?.dispose()
})
</script>

<style scoped>
.home-page { display: grid; gap: 22px; }
.welcome-card, .guide-card { padding: 28px; background: #fff; border-radius: 12px; box-shadow: 0 2px 12px rgba(31, 45, 61, 0.05); }
.welcome-card { display: flex; align-items: center; justify-content: space-between; gap: 20px; background: linear-gradient(120deg, #fff 20%, #ecf5ff 100%); }
.welcome-label { color: #409eff; font-size: 12px; letter-spacing: 3px; }
.welcome-card h1 { margin: 8px 0; font-size: 26px; }
.welcome-card p:last-child, .stat-card p { color: #909399; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 18px; }
.stat-card { display: flex; align-items: center; gap: 16px; padding: 22px; background: #fff; border-radius: 12px; box-shadow: 0 2px 12px rgba(31, 45, 61, 0.05); position: relative; }
.stat-card.clickable { cursor: pointer; transition: transform 0.15s ease, box-shadow 0.15s ease; }
.stat-card.clickable:hover { transform: translateY(-3px); box-shadow: 0 6px 20px rgba(31, 45, 61, 0.1); }
.stat-arrow { position: absolute; right: 18px; top: 50%; transform: translateY(-50%); color: #c0c4cc; font-size: 18px; }
.stat-icon { display: grid; width: 50px; height: 50px; place-items: center; border-radius: 12px; color: #409eff; font-size: 24px; }
.stat-card strong { display: block; margin-top: 5px; font-size: 28px; }
.guide-card h2 { margin-bottom: 28px; font-size: 18px; }

/* —— 首页统计图表 —— */
.charts-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.chart-wide { grid-column: 1 / -1; }
.chart-card {
  position: relative;
  padding: 20px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(31, 45, 61, 0.05);
}
.chart-card h2 { font-size: 16px; }
.chart-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.chart-body { height: 300px; }
.chart-empty {
  position: absolute;
  left: 0; right: 0; top: 60px; bottom: 0;
  display: grid; place-items: center;
  color: #909399; font-size: 13px;
  background: rgba(255, 255, 255, 0.65);
  border-radius: 0 0 12px 12px;
}
@media (max-width: 900px) {
  .charts-grid { grid-template-columns: 1fr; }
}
</style>
