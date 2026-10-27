<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">{{ isAdmin ? '实验室管理' : '可预约实验室' }}</h1>
      <el-button v-if="isAdmin" type="primary" @click="openLabDialog()">新增实验室</el-button>
    </div>
    <div class="toolbar">
      <el-input v-model="keyword" clearable placeholder="搜索实验室名称" style="width: 240px" @keyup.enter="loadLabList" @clear="loadLabList" />
      <el-button @click="loadLabList">查询</el-button>
      <el-checkbox v-model="favoriteOnly" @change="loadLabList">只看收藏</el-checkbox>
    </div>

    <el-table v-loading="loadingValue" :data="labList" stripe>
      <el-table-column prop="name" label="实验室名称" min-width="150" />
      <el-table-column prop="location" label="位置" min-width="160" />
      <el-table-column prop="capacity" label="容纳人数" width="100" />
      <el-table-column prop="description" label="说明" min-width="220" show-overflow-tooltip />
      <el-table-column label="状态" width="100">
        <template #default="scope"><el-tag :type="scope.row.status === 1 ? 'success' : 'info'">{{ scope.row.status === 1 ? '开放' : '暂停' }}</el-tag></template>
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
      <el-table-column label="操作" :width="isAdmin ? 320 : 240" fixed="right">
        <template #default="scope">
          <el-button link type="warning" @click="openCalendarDialog(scope.row)">查看周历</el-button>
          <el-button link type="primary" @click="showEquipment(scope.row)">查看设备</el-button>
          <template v-if="isAdmin">
            <el-button link type="primary" @click="openLabDialog(scope.row)">编辑</el-button>
            <el-button link type="warning" @click="openBlackoutDialog(scope.row)">维护设置</el-button>
            <el-button link type="danger" @click="removeLab(scope.row)">删除</el-button>
          </template>
          <el-button v-else link type="success" @click="openReservationDialog(scope.row)">立即预约</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="labDialogVisible" :title="labForm.id ? '编辑实验室' : '新增实验室'" width="520px">
      <el-form ref="labFormRef" :model="labForm" :rules="labRules" label-width="90px">
        <el-form-item label="名称" prop="name"><el-input v-model="labForm.name" /></el-form-item>
        <el-form-item label="位置" prop="location"><el-input v-model="labForm.location" /></el-form-item>
        <el-form-item label="容纳人数" prop="capacity"><el-input-number v-model="labForm.capacity" :min="1" :max="1000" /></el-form-item>
        <el-form-item label="状态"><el-switch v-model="labForm.status" :active-value="1" :inactive-value="0" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="labForm.description" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="labDialogVisible = false">取消</el-button><el-button type="primary" :loading="savingValue" @click="saveLab">保存</el-button></template>
    </el-dialog>

    <!-- 维护设置弹窗 -->
    <el-dialog v-model="blackoutDialogVisible" title="不可约时段设置" width="620px">
      <el-alert :title="`实验室：${blackoutLab?.name || ''}`" type="warning" :closable="false" style="margin-bottom: 12px" />
      <el-form :inline="true" label-width="80px">
        <el-form-item label="日期">
          <el-date-picker v-model="blackoutForm.blackout_date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" />
        </el-form-item>
        <el-form-item label="时间">
          <el-time-picker v-model="blackoutForm.timeRange" is-range value-format="HH:mm:ss" range-separator="至" start-placeholder="开始" end-placeholder="结束" />
        </el-form-item>
        <el-form-item label="原因">
          <el-input v-model="blackoutForm.reason" placeholder="如：维护/考试/节假日" style="width: 160px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="addBlackout">添加</el-button>
        </el-form-item>
      </el-form>
      <el-table :data="blackoutList" size="small" border>
        <el-table-column prop="blackout_date" label="日期" width="110" />
        <el-table-column label="时间" width="140">
          <template #default="scope">{{ scope.row.start_time.slice(0,5) }} - {{ scope.row.end_time.slice(0,5) }}</template>
        </el-table-column>
        <el-table-column prop="reason" label="原因" />
        <el-table-column label="操作" width="80">
          <template #default="scope"><el-button link type="danger" @click="removeBlackout(scope.row)">删除</el-button></template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <el-dialog v-model="reservationDialogVisible" title="提交实验室预约" width="680px">
      <el-alert :title="`正在预约：${selectedLab?.name || ''}`" type="info" :closable="false" />
      <el-form ref="reservationFormRef" :model="reservationForm" :rules="reservationRules" label-width="90px" class="dialog-form">
        <el-form-item label="预约日期" prop="reservation_date"><el-date-picker v-model="reservationForm.reservation_date" type="date" value-format="YYYY-MM-DD" :disabled-date="disablePastDate" style="width: 100%" @change="onDateChange" /></el-form-item>
        <el-form-item label="预约时间" prop="timeRange"><el-time-picker v-model="reservationForm.timeRange" is-range value-format="HH:mm:ss" range-separator="至" start-placeholder="开始时间" end-placeholder="结束时间" style="width: 100%" @change="onTimeChange" /></el-form-item>
        <el-form-item label="时段占用">
          <div class="slot-panel">
            <div class="slot-panel-head">
              <span class="slot-panel-title">当日可视化时段（每格 30 分钟）</span>
              <div class="slot-legend">
                <span class="legend-item"><i class="legend-dot free" />空闲</span>
                <span class="legend-item"><i class="legend-dot occupied" />已被预约</span>
                <span class="legend-item"><i class="legend-dot blackout" />不可约</span>
                <span class="legend-item"><i class="legend-dot selected" />本次选择</span>
              </div>
            </div>
            <div v-loading="slotsLoading" class="slot-cells">
              <div v-for="slot in timeSlots" :key="slot.startMin" :class="cellClass(slot)" :title="slotTooltip(slot)" @click="onCellClick(slot)">{{ slot.startLabel }}</div>
            </div>
            <div v-if="selectionConflict" class="slot-conflict">所选时间与已有预约冲突，请重新选择。</div>
            <div v-else-if="selectedRange" class="slot-ok">已选择 {{ selectedRangeLabel }}，该时段空闲，可提交。</div>
            <div v-else class="slot-hint">点击空闲格子选择时间段：先点起点，再点更晚的空闲格子作为结束。</div>
          </div>
        </el-form-item>
        <el-form-item label="预约用途" prop="purpose"><el-input v-model="reservationForm.purpose" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="重复预约">
          <el-radio-group v-model="reservationForm.repeat_weeks">
            <el-radio :value="1">只约一次</el-radio>
            <el-radio :value="2">每周重复2周</el-radio>
            <el-radio :value="3">每周重复3周</el-radio>
            <el-radio :value="4">每周重复4周</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer><el-button @click="reservationDialogVisible = false">取消</el-button><el-button type="primary" :loading="savingValue" :disabled="!!selectionConflict" @click="saveReservation">提交申请</el-button></template>
    </el-dialog>
    <!-- 周/日视图预约日历弹窗 -->
    <el-dialog v-model="calendarDialogVisible" :title="`预约日历：${calendarLab?.name || ''}`" width="980px" top="6vh">
      <div class="cal-toolbar">
        <el-button-group>
          <el-button @click="calNav(-1)">上一{{ calendarView === 'week' ? '周' : '天' }}</el-button>
          <el-button @click="calJumpToday">今天</el-button>
          <el-button @click="calNav(1)">下一{{ calendarView === 'week' ? '周' : '天' }}</el-button>
        </el-button-group>
        <span class="cal-range">{{ calendarRangeLabel }}</span>
        <el-radio-group v-model="calendarView" @change="loadCalendar">
          <el-radio-button value="week">周视图</el-radio-button>
          <el-radio-button value="day">日视图</el-radio-button>
        </el-radio-group>
      </div>
      <div class="cal-legend">
        <span class="legend-item"><i class="cal-dot approved" />已通过</span>
        <span class="legend-item"><i class="cal-dot pending" />待审核</span>
        <span class="legend-item"><i class="cal-dot blackout" />不可约</span>
        <span class="legend-hint">点击空白时段可直接发起预约</span>
      </div>
      <div v-loading="calendarLoading" class="cal-frame">
        <div class="cal-head-row">
          <div class="cal-gutter"></div>
          <div v-for="day in displayDays" :key="day" class="cal-day-head" :class="{ today: day === calToday }">
            {{ weekdayLabel(day) }}<br />{{ day.slice(5) }}
          </div>
        </div>
        <div class="cal-body-row">
          <div class="cal-gutter">
            <div v-for="tick in hourTicks" :key="tick" class="cal-hour-label" :style="tickStyle(tick)">{{ minToLabel(tick) }}</div>
          </div>
          <div v-for="day in displayDays" :key="day" class="cal-day" @click="onEmptyClick($event, day)">
            <div v-for="tick in hourTicks" :key="tick" class="cal-hour-line" :style="tickStyle(tick)"></div>
            <div v-if="nowPercent !== null" class="cal-nowline" :style="{ top: nowPercent + '%' }"></div>
            <div
              v-for="block in dayBlocks(day)"
              :key="block.key"
              class="cal-block"
              :class="block.kind"
              :style="blockStyle(block)"
              :title="blockTitle(block)"
              @click.stop="onBlockClick(block)"
            >
              <div class="cal-block-time">{{ minToLabel(block.startMin) }} - {{ minToLabel(block.endMin) }}</div>
              <div v-if="block.kind !== 'blackout'" class="cal-block-user">{{ block.info.user_name }}</div>
              <div class="cal-block-purpose">{{ block.kind === 'blackout' ? block.info.reason : block.info.purpose }}</div>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { Star, StarFilled } from '@element-plus/icons-vue'
import { createLabApi, deleteLabApi, getLabListApi, updateLabApi } from '@/api/lab'
import { addFavoriteApi, deleteFavoriteApi, getFavoritesApi } from '@/api/favorite'
import { createReservationApi, getReservationCalendarApi, getReservationSlotsApi } from '@/api/reservation'
import { createBlackoutApi, deleteBlackoutApi, getBlackoutsApi } from '@/api/blackout'
import { promptSignature } from '@/utils/confirm'
import { useUser } from '@/utils/user'

const router = useRouter()
const { isAdmin } = useUser()
const loadingValue = ref(false)
const savingValue = ref(false)
const keyword = ref('')
const labList = ref([])
// 收藏：favoriteMap 记录 target_id -> 收藏记录 id，用于切换收藏/取消收藏
const favoriteOnly = ref(false)
const favoriteMap = ref({})
const labDialogVisible = ref(false)
const reservationDialogVisible = ref(false)
const labFormRef = ref(null)
const reservationFormRef = ref(null)
const selectedLab = ref(null)
const labForm = reactive({ id: null, name: '', location: '', capacity: 1, description: '', status: 1 })
const reservationForm = reactive({ reservation_date: '', timeRange: [], purpose: '', repeat_weeks: 1 })

// —— 维护设置 ——
const blackoutDialogVisible = ref(false)
const blackoutLab = ref(null)
const blackoutList = ref([])
const blackoutForm = reactive({ blackout_date: '', timeRange: [], reason: '' })

// —— 预约时段可视化 ——
const slotsLoading = ref(false)
const occupiedSlots = ref([])
const blackoutSlots = ref([])
const gridStartIndex = ref(null)
const DAY_START = 8 * 60 // 可视化默认从 08:00 开始
const DAY_END = 22 * 60 // 到 22:00 结束，遇到更早/更晚的占用会自动扩展
const STEP = 30

const toMin = (t) => {
  const [h, m] = t.split(':').map(Number)
  return h * 60 + m
}
const minToLabel = (m) => `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`
const minToTime = (m) => `${minToLabel(m)}:00`

const occupiedIntervals = computed(() =>
  occupiedSlots.value.map((s) => ({
    startMin: toMin(s.start_time.slice(0, 5)),
    endMin: toMin(s.end_time.slice(0, 5)),
    info: s
  }))
)

const blackoutIntervals = computed(() =>
  blackoutSlots.value.map((b) => ({
    startMin: toMin(b.start_time.slice(0, 5)),
    endMin: toMin(b.end_time.slice(0, 5)),
    info: b
  }))
)

// 把一天切成 30 分钟一格的时间轴，命中占用区间（半开区间）的格子标为 occupied。
const timeSlots = computed(() => {
  const occ = [...occupiedIntervals.value, ...blackoutIntervals.value]
  let ws = DAY_START
  let we = DAY_END
  for (const o of occ) {
    if (o.startMin < ws) ws = o.startMin
    if (o.endMin > we) we = o.endMin
  }
  const cells = []
  for (let m = ws; m < we; m += STEP) {
    const hit = occupiedIntervals.value.find((o) => o.startMin < m + STEP && o.endMin > m)
    const blackoutHit = blackoutIntervals.value.find((o) => o.startMin < m + STEP && o.endMin > m)
    cells.push({
      startMin: m,
      endMin: m + STEP,
      startLabel: minToLabel(m),
      state: hit ? 'occupied' : (blackoutHit ? 'blackout' : 'free'),
      info: hit ? hit.info : (blackoutHit ? blackoutHit.info : null)
    })
  }
  return cells
})

const selectedRange = computed(() => {
  const r = reservationForm.timeRange
  if (!r || r.length !== 2 || !r[0] || !r[1]) return null
  return { startMin: toMin(r[0].slice(0, 5)), endMin: toMin(r[1].slice(0, 5)) }
})
const selectedRangeLabel = computed(() => {
  const s = selectedRange.value
  return s ? `${minToLabel(s.startMin)} - ${minToLabel(s.endMin)}` : ''
})

// 与后端一致：两个半开区间相交的充要条件是 旧开始 < 新结束 且 旧结束 > 新开始。
const selectionConflict = computed(() => {
  const s = selectedRange.value
  if (!s) return false
  return [...occupiedIntervals.value, ...blackoutIntervals.value].some((o) => o.startMin < s.endMin && o.endMin > s.startMin)
})

const cellClass = (slot) => {
  if (slot.state === 'occupied') return 'slot-cell occupied'
  if (slot.state === 'blackout') return 'slot-cell blackout'
  const s = selectedRange.value
  if (s && slot.startMin >= s.startMin && slot.startMin < s.endMin) return 'slot-cell selected'
  return 'slot-cell free'
}
const slotTooltip = (slot) => {
  if (slot.state === 'blackout') return `不可约：${slot.info.reason}`
  if (!slot.info) return '空闲，点击开始选择'
  const st = slot.info.status === 'approved' ? '已通过' : '待审核'
  return `${slot.info.user_name}｜${st}｜${minToLabel(slot.startMin)}-${minToLabel(slot.endMin)}\n用途：${slot.info.purpose || '-'}`
}

const onCellClick = (slot) => {
  if (slot.state === 'occupied') {
    gridStartIndex.value = null
    ElMessage.warning(`该时段已被预约：${slot.info.user_name} ${minToLabel(slot.startMin)}-${minToLabel(slot.endMin)}`)
    return
  }
  if (slot.state === 'blackout') {
    gridStartIndex.value = null
    ElMessage.warning(`该时段不可约：${slot.info.reason}`)
    return
  }
  if (gridStartIndex.value === null) {
    gridStartIndex.value = slot.startMin
    ElMessage.info(`已选起点 ${minToLabel(slot.startMin)}，请再点一个更晚的空闲格子作为结束时间`)
    return
  }
  const startMin = Math.min(gridStartIndex.value, slot.startMin)
  const endMin = Math.max(gridStartIndex.value, slot.startMin) + STEP
  gridStartIndex.value = null
  reservationForm.timeRange = [minToTime(startMin), minToTime(endMin)]
}

const onDateChange = () => {
  gridStartIndex.value = null
  reservationForm.timeRange = []
  loadOccupiedSlots()
}
const onTimeChange = () => {
  gridStartIndex.value = null
}

const loadOccupiedSlots = async () => {
  if (!selectedLab.value || !reservationForm.reservation_date) {
    occupiedSlots.value = []
    blackoutSlots.value = []
    return
  }
  slotsLoading.value = true
  try {
    const res = await getReservationSlotsApi({ lab_id: selectedLab.value.id, reservation_date: reservationForm.reservation_date })
    occupiedSlots.value = res.data.occupied || []
    blackoutSlots.value = res.data.blackouts || []
  } catch {
    occupiedSlots.value = []
    blackoutSlots.value = []
  } finally {
    slotsLoading.value = false
  }
}

// —— 周/日视图预约日历 ——
// 日期工具：ISO 字符串（YYYY-MM-DD）可直接比较大小，跨天加减用 Date 换算。
const formatDate = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
const addDays = (dateStr, n) => {
  const d = new Date(`${dateStr}T00:00:00`)
  d.setDate(d.getDate() + n)
  return formatDate(d)
}
// getDay() 周日=0；(getDay()+6)%7 把周一换算成 0，即可回退到本周周一。
const mondayOf = (dateStr) => {
  const d = new Date(`${dateStr}T00:00:00`)
  d.setDate(d.getDate() - (d.getDay() + 6) % 7)
  return formatDate(d)
}
const weekdayNames = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
const weekdayLabel = (dateStr) => weekdayNames[new Date(`${dateStr}T00:00:00`).getDay()]

const calendarDialogVisible = ref(false)
const calendarLab = ref(null)
const calendarView = ref('week')
const calendarLoading = ref(false)
const calendarAnchor = ref(formatDate(new Date())) // 周视图锚点（所在周的任意一天）
const calendarDay = ref(formatDate(new Date())) // 日视图当前查看的日期
const calToday = ref(formatDate(new Date())) // 打开日历时定格“今天”，避免长时间停留后漂移
const calendarReservations = ref([])
const calendarBlackouts = ref([])
const CAL_DEFAULT_START = 8 * 60 // 时间轴默认 08:00 起
const CAL_DEFAULT_END = 22 * 60 // 22:00 止；有更早/更晚的占用会自动整点扩展

const calendarRange = computed(() => {
  if (calendarView.value === 'day') return { start: calendarDay.value, end: calendarDay.value }
  const monday = mondayOf(calendarAnchor.value)
  return { start: monday, end: addDays(monday, 6) }
})
const calendarRangeLabel = computed(() => `${calendarRange.value.start} ~ ${calendarRange.value.end}`)
const displayDays = computed(() => {
  const days = []
  let cursor = calendarRange.value.start
  while (cursor <= calendarRange.value.end) {
    days.push(cursor)
    cursor = addDays(cursor, 1)
  }
  return days
})

// 把后端返回的预约与不可约时段统一成“分钟区间”，附上所属日期。
const calendarIntervals = computed(() => [
  ...calendarReservations.value.map((r) => ({
    kind: r.status, // pending / approved
    date: r.reservation_date,
    startMin: toMin(r.start_time.slice(0, 5)),
    endMin: toMin(r.end_time.slice(0, 5)),
    info: r,
  })),
  ...calendarBlackouts.value.map((b) => ({
    kind: 'blackout',
    date: b.blackout_date,
    startMin: toMin(b.start_time.slice(0, 5)),
    endMin: toMin(b.end_time.slice(0, 5)),
    info: b,
  })),
])

// 时间轴窗口：默认 8:00-22:00，被事件撑大时按整点扩展，保证所有块都能落进视图。
const calendarWindow = computed(() => {
  let startMin = CAL_DEFAULT_START
  let endMin = CAL_DEFAULT_END
  for (const it of calendarIntervals.value) {
    startMin = Math.min(startMin, Math.floor(it.startMin / 60) * 60)
    endMin = Math.max(endMin, Math.ceil(it.endMin / 60) * 60)
  }
  return { startMin, endMin, spanMin: endMin - startMin }
})
const hourTicks = computed(() => {
  const ticks = []
  for (let m = calendarWindow.value.startMin; m <= calendarWindow.value.endMin; m += 60) ticks.push(m)
  return ticks
})
const tickStyle = (m) => ({ top: `${((m - calendarWindow.value.startMin) / calendarWindow.value.spanMin) * 100}%` })

// 重叠区间分道：按开始时间排序，贪心放进第一条“上一段已结束”的竖道，
// laneCount 决定每道宽度，使同一天的重叠预约并排显示而不是互相遮盖。
const dayBlocks = (day) => {
  const sorted = calendarIntervals.value
    .filter((it) => it.date === day)
    .sort((a, b) => a.startMin - b.startMin || a.endMin - b.endMin)
  const laneEnds = []
  const withLane = sorted.map((it) => {
    let lane = laneEnds.findIndex((end) => end <= it.startMin)
    if (lane === -1) {
      laneEnds.push(it.endMin)
      lane = laneEnds.length - 1
    } else {
      laneEnds[lane] = it.endMin
    }
    return { ...it, lane }
  })
  return withLane.map((it, idx) => ({ key: `${it.kind}-${it.info.id}-${idx}`, ...it, laneCount: laneEnds.length }))
}

// 分钟 → 百分比定位：块的位置全部用百分比表达，时间轴伸缩时无需重算像素。
const blockStyle = (block) => {
  const { startMin, spanMin } = calendarWindow.value
  const width = 100 / block.laneCount
  return {
    top: `${((block.startMin - startMin) / spanMin) * 100}%`,
    height: `${((block.endMin - block.startMin) / spanMin) * 100}%`,
    left: `calc(${block.lane * width}% + 2px)`,
    width: `calc(${width}% - 4px)`,
  }
}

// “现在”红线：仅当展示的日期包含今天、且当前时刻落在时间轴窗口内时显示。
const nowPercent = computed(() => {
  if (!displayDays.value.includes(calToday.value)) return null
  const now = new Date()
  const m = now.getHours() * 60 + now.getMinutes()
  const { startMin, endMin } = calendarWindow.value
  if (m < startMin || m > endMin) return null
  return ((m - startMin) / (endMin - startMin)) * 100
})

const calStatusText = { pending: '待审核', approved: '已通过' }
const blockTitle = (block) => {
  if (block.kind === 'blackout') return `不可约：${block.info.reason}`
  return `${block.info.user_name}｜${calStatusText[block.kind] || block.kind}｜${minToLabel(block.startMin)}-${minToLabel(block.endMin)}\n用途：${block.info.purpose || '-'}`
}
const onBlockClick = (block) => {
  if (block.kind === 'blackout') {
    ElMessage.warning(`该时段不可约：${block.info.reason}`)
    return
  }
  ElMessage.info(`${block.info.user_name}（${calStatusText[block.kind]}）预约 ${block.date} ${minToLabel(block.startMin)}-${minToLabel(block.endMin)}：${block.info.purpose || '无用途说明'}`)
}

// 点击空白处反推时刻：纵向像素占比 × 时间轴跨度，向下取整到 30 分钟格。
const onEmptyClick = (event, day) => {
  const rect = event.currentTarget.getBoundingClientRect()
  const { startMin, endMin, spanMin } = calendarWindow.value
  const offsetMin = ((event.clientY - rect.top) / rect.height) * spanMin
  const slotMin = Math.max(startMin, Math.min(startMin + Math.floor(offsetMin / 30) * 30, endMin - 30))
  if (calendarLab.value.status !== 1) {
    ElMessage.warning('该实验室暂停开放，暂不能预约')
    return
  }
  const now = new Date()
  const nowMin = now.getHours() * 60 + now.getMinutes()
  if (day < calToday.value || (day === calToday.value && slotMin <= nowMin)) {
    ElMessage.warning('不能预约已经过去的时段')
    return
  }
  // 预填 1 小时的草稿时段，进入预约弹窗后仍可继续调整。
  openReservationDialog(calendarLab.value, { date: day, timeRange: [minToTime(slotMin), minToTime(slotMin + 60)] })
  calendarDialogVisible.value = false
}

const loadCalendar = async () => {
  if (!calendarLab.value) return
  calendarLoading.value = true
  try {
    const res = await getReservationCalendarApi({
      lab_id: calendarLab.value.id,
      start_date: calendarRange.value.start,
      end_date: calendarRange.value.end,
    })
    calendarReservations.value = res.data.reservations || []
    calendarBlackouts.value = res.data.blackouts || []
  } finally {
    calendarLoading.value = false
  }
}

const openCalendarDialog = (lab) => {
  calendarLab.value = lab
  calToday.value = formatDate(new Date())
  calendarAnchor.value = mondayOf(calToday.value)
  calendarDay.value = calToday.value
  calendarView.value = 'week'
  calendarDialogVisible.value = true
  loadCalendar()
}

const calNav = (direction) => {
  if (calendarView.value === 'week') {
    calendarAnchor.value = addDays(calendarAnchor.value, direction * 7)
  } else {
    calendarDay.value = addDays(calendarDay.value, direction)
  }
  loadCalendar()
}
const calJumpToday = () => {
  calToday.value = formatDate(new Date())
  calendarAnchor.value = mondayOf(calToday.value)
  calendarDay.value = calToday.value
  loadCalendar()
}

const labRules = {
  name: [{ required: true, message: '请输入实验室名称', trigger: 'blur' }],
  location: [{ required: true, message: '请输入实验室位置', trigger: 'blur' }],
  capacity: [{ required: true, message: '请输入容纳人数', trigger: 'change' }]
}
const reservationRules = {
  reservation_date: [{ required: true, message: '请选择预约日期', trigger: 'change' }],
  timeRange: [{ type: 'array', required: true, len: 2, message: '请选择预约时间', trigger: 'change' }],
  purpose: [{ required: true, message: '请填写预约用途', trigger: 'blur' }]
}

const loadLabList = async () => {
  loadingValue.value = true
  try {
    const res = await getLabListApi({
      keyword: keyword.value,
      only_open: !isAdmin.value,
      favorite_only: favoriteOnly.value || undefined
    })
    labList.value = res.data
  } finally { loadingValue.value = false }
}

// ===== 收藏（实验室）=====
const loadFavorites = async () => {
  try {
    const res = await getFavoritesApi({ target_type: 'lab' })
    const map = {}
    for (const item of res.data || []) map[item.target_id] = item.id
    favoriteMap.value = map
  } catch {
    favoriteMap.value = {}
  }
}

const isFavorited = (labId) => Boolean(favoriteMap.value[labId])

const toggleFavorite = async (lab) => {
  const favoriteId = favoriteMap.value[lab.id]
  if (favoriteId) {
    await deleteFavoriteApi(favoriteId)
    ElMessage.success('已取消收藏')
  } else {
    await addFavoriteApi({ target_type: 'lab', target_id: lab.id })
    ElMessage.success('收藏成功')
  }
  await loadFavorites()
}

const openLabDialog = (lab = null) => {
  Object.assign(labForm, lab || { id: null, name: '', location: '', capacity: 1, description: '', status: 1 })
  labDialogVisible.value = true
}

const saveLab = async () => {
  const valid = await labFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    const data = { name: labForm.name.trim(), location: labForm.location.trim(), capacity: labForm.capacity, description: labForm.description || null, status: labForm.status }
    if (labForm.id) await updateLabApi(labForm.id, data)
    else await createLabApi(data)
    ElMessage.success(labForm.id ? '实验室修改成功' : '实验室新增成功')
    labDialogVisible.value = false
    await loadLabList()
  } finally { savingValue.value = false }
}

const removeLab = async (lab) => {
  // 危险操作：输入当前登录密码二次确认（电子签名），操作日志会记录本次删除
  const password = await promptSignature(`确定删除实验室“${lab.name}”吗？此操作需要输入当前账号密码确认。`)
  if (password === null) return
  await deleteLabApi(lab.id, { signature_password: password })
  ElMessage.success('删除成功')
  await loadLabList()
}

const showEquipment = (lab) => router.push({ path: '/equ', query: { lab_id: lab.id } })

const openBlackoutDialog = async (lab) => {
  blackoutLab.value = lab
  Object.assign(blackoutForm, { blackout_date: '', timeRange: [], reason: '' })
  blackoutDialogVisible.value = true
  const res = await getBlackoutsApi({ lab_id: lab.id })
  blackoutList.value = res.data
}
const addBlackout = async () => {
  if (!blackoutForm.blackout_date || !blackoutForm.timeRange?.length || !blackoutForm.reason.trim()) {
    ElMessage.warning('请填写完整日期、时间和原因')
    return
  }
  await createBlackoutApi({
    lab_id: blackoutLab.value.id,
    blackout_date: blackoutForm.blackout_date,
    start_time: blackoutForm.timeRange[0],
    end_time: blackoutForm.timeRange[1],
    reason: blackoutForm.reason.trim(),
  })
  ElMessage.success('已添加不可约时段')
  const res = await getBlackoutsApi({ lab_id: blackoutLab.value.id })
  blackoutList.value = res.data
  Object.assign(blackoutForm, { blackout_date: '', timeRange: [], reason: '' })
}
const removeBlackout = async (item) => {
  await ElMessageBox.confirm('确定删除这条不可约设置吗？', '确认', { type: 'warning' }).catch(() => null)
  await deleteBlackoutApi(item.id)
  ElMessage.success('已删除')
  const res = await getBlackoutsApi({ lab_id: blackoutLab.value.id })
  blackoutList.value = res.data
}

const openReservationDialog = (lab, prefill = null) => {
  selectedLab.value = lab
  const today = new Date()
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
  Object.assign(reservationForm, {
    reservation_date: prefill?.date || todayStr,
    timeRange: prefill ? prefill.timeRange : [],
    purpose: '',
    repeat_weeks: 1
  })
  gridStartIndex.value = null
  reservationDialogVisible.value = true
  loadOccupiedSlots()
}
const disablePastDate = (date) => date.getTime() < new Date().setHours(0, 0, 0, 0)

const saveReservation = async () => {
  const valid = await reservationFormRef.value?.validate().catch(() => false)
  if (!valid) return
  // 提交前再次确认不与已有预约冲突，避免发出必然失败的请求。
  if (selectionConflict.value) {
    ElMessage.warning('所选时间与已有预约冲突，请重新选择')
    return
  }
  savingValue.value = true
  try {
    const res = await createReservationApi({ lab_id: selectedLab.value.id, reservation_date: reservationForm.reservation_date, start_time: reservationForm.timeRange[0], end_time: reservationForm.timeRange[1], purpose: reservationForm.purpose.trim(), repeat_weeks: reservationForm.repeat_weeks })
    // 重复预约时后端会返回“成功创建 N 条，跳过 M 周（原因…）”，原样展示给用户。
    ElMessage.success(res.message || '预约申请已提交')
    reservationDialogVisible.value = false
    await router.push('/reservation')
  } finally { savingValue.value = false }
}

onMounted(() => {
  loadLabList()
  loadFavorites()
})
</script>

<style scoped>
.dialog-form { margin-top: 20px; }

.slot-panel {
  width: 100%;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 10px 12px;
  background: #fafafa;
}
.slot-panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}
.slot-panel-title { font-size: 13px; font-weight: 600; color: #303133; }
.slot-legend { display: flex; gap: 12px; font-size: 12px; color: #606266; }
.legend-item { display: inline-flex; align-items: center; gap: 4px; }
.legend-dot { width: 10px; height: 10px; border-radius: 3px; display: inline-block; }
.legend-dot.free { background: #e1f3d8; }
.legend-dot.occupied { background: #fde2e2; }
.legend-dot.blackout { background: #c8c9cc; }
.legend-dot.selected { background: #409eff; }

.slot-cells {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(54px, 1fr));
  gap: 4px;
  min-height: 36px;
}
.slot-cell {
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 5px;
  font-size: 12px;
  color: #606266;
  cursor: pointer;
  border: 1px solid transparent;
  user-select: none;
  transition: transform 0.08s ease;
}
.slot-cell.free { background: #e1f3d8; color: #529b2e; }
.slot-cell.free:hover { transform: scale(1.05); border-color: #67c23a; }
.slot-cell.occupied {
  background: #fde2e2;
  color: #b05050;
  cursor: not-allowed;
  text-decoration: line-through;
}
.slot-cell.blackout {
  background: #c8c9cc;
  color: #606266;
  cursor: not-allowed;
}
.slot-cell.selected { background: #409eff; color: #fff; }

.slot-conflict { margin-top: 8px; font-size: 12px; color: #f56c6c; }
.slot-ok { margin-top: 8px; font-size: 12px; color: #67c23a; }
.slot-hint { margin-top: 8px; font-size: 12px; color: #909399; }

/* —— 周/日视图日历 —— */
.cal-toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; flex-wrap: wrap; }
.cal-range { font-size: 14px; font-weight: 600; color: #303133; }
.cal-legend { display: flex; align-items: center; gap: 12px; font-size: 12px; color: #606266; margin-bottom: 8px; }
.cal-dot { width: 10px; height: 10px; border-radius: 3px; display: inline-block; margin-right: 4px; }
.cal-dot.approved { background: #d1edc4; }
.cal-dot.pending { background: #faecd8; }
.cal-dot.blackout { background: #c8c9cc; }
.legend-hint { margin-left: auto; color: #909399; }

.cal-frame { border: 1px solid #ebeef5; border-radius: 8px; overflow: hidden; }
.cal-head-row, .cal-body-row { display: flex; }
.cal-gutter { width: 56px; flex: none; position: relative; }
.cal-day-head {
  flex: 1; text-align: center; padding: 6px 0;
  font-size: 13px; font-weight: 600; color: #303133;
  background: #f5f7fa; border-left: 1px solid #ebeef5; line-height: 1.5;
}
.cal-day-head.today { color: #409eff; background: #ecf5ff; }
.cal-body-row { height: 540px; }
.cal-hour-label {
  position: absolute; right: 8px; transform: translateY(-50%);
  font-size: 11px; color: #909399; pointer-events: none;
}
.cal-day { flex: 1; position: relative; border-left: 1px solid #ebeef5; cursor: pointer; }
.cal-day:hover { background: #fafcff; }
.cal-hour-line { position: absolute; left: 0; right: 0; border-top: 1px dashed #f0f2f5; pointer-events: none; }
.cal-nowline { position: absolute; left: 0; right: 0; border-top: 2px solid #f56c6c; z-index: 3; pointer-events: none; }

.cal-block {
  position: absolute; z-index: 2; border-radius: 6px;
  padding: 3px 6px; font-size: 12px; line-height: 1.3;
  overflow: hidden; border: 1px solid transparent;
}
.cal-block.approved { background: #f0f9eb; border-color: #b3e19d; color: #529b2e; cursor: pointer; }
.cal-block.pending { background: #fdf6ec; border-color: #f3d19e; color: #b88230; cursor: pointer; }
.cal-block.blackout { background: #e9e9eb; border-color: #c8c9cc; color: #606266; cursor: not-allowed; }
.cal-block-time { font-weight: 600; }
.cal-block-user, .cal-block-purpose { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cal-block-purpose { opacity: 0.85; }
</style>
