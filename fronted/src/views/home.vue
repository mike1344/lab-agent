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
import { computed, markRaw, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, Calendar, Collection, Monitor, User } from '@element-plus/icons-vue'
import { getSummaryApi } from '@/api/stats'
import { useUser } from '@/utils/user'

const router = useRouter()
const { userInfo, isAdmin } = useUser()
const loadingValue = ref(false)
const summary = reactive({})
const displayName = computed(() => userInfo.value?.full_name || userInfo.value?.username || '同学')

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

onMounted(async () => {
  loadingValue.value = true
  try {
    const res = await getSummaryApi()
    Object.assign(summary, res.data)
  } finally {
    loadingValue.value = false
  }
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
</style>
