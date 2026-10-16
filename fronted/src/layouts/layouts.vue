<template>
  <el-container class="app-shell">
    <el-header class="app-header">
      <div class="brand">
        <img :src="logo" alt="系统 Logo" />
        <span>智能实验室预约系统</span>
      </div>

      <div class="header-right">
        <!-- 通知铃铛 + 未读角标 -->
        <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99" class="bell-badge">
          <el-button circle @click="openNotificationDrawer">
            <el-icon :size="18"><Bell /></el-icon>
          </el-button>
        </el-badge>

        <el-dropdown trigger="click" @command="handleCommand">
          <button type="button" class="user-button">
            <el-avatar :size="34" :src="userInfo?.avatar_url" :icon="UserFilled" />
            <span class="user-name">{{ displayName }}</span>
            <el-tag :type="isAdmin ? 'danger' : (isTeacher ? 'warning' : 'success')" size="small">
              {{ isAdmin ? '管理员' : (isTeacher ? '教师' : '学生') }}
            </el-tag>
            <el-icon><ArrowDown /></el-icon>
          </button>

          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">个人中心</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <!-- 通知抽屉 -->
      <el-drawer v-model="drawerVisible" title="消息通知" size="400px">
        <div class="drawer-toolbar">
          <el-button size="small" @click="handleMarkAllRead">全部已读</el-button>
        </div>
        <div v-if="notifications.length === 0" class="empty-text">暂无通知</div>
        <div v-else class="notification-list">
          <div
            v-for="n in notifications"
            :key="n.id"
            :class="['notification-item', { unread: !n.is_read }]"
            @click="handleClickNotification(n)"
          >
            <div class="notif-title">{{ n.title }}</div>
            <div class="notif-content">{{ n.content }}</div>
            <div class="notif-time">{{ n.create_time }}</div>
          </div>
        </div>
      </el-drawer>
    </el-header>

    <el-container class="app-body">
      <el-aside class="app-aside" width="220px">
        <el-menu router :default-active="$route.path" class="app-menu">
          <el-menu-item index="/home">
            <el-icon><DataBoard /></el-icon>
            <span>系统首页</span>
          </el-menu-item>
          <el-menu-item index="/lab">
            <el-icon><House /></el-icon>
            <span>{{ isAdmin ? '实验室管理' : '实验室列表' }}</span>
          </el-menu-item>
          <el-menu-item index="/equ">
            <el-icon><Setting /></el-icon>
            <span>{{ isAdmin ? '设备管理' : '设备列表' }}</span>
          </el-menu-item>
          <el-menu-item index="/reservation">
            <el-icon><Calendar /></el-icon>
            <span>{{ isStaff ? '预约审核' : '我的预约' }}</span>
          </el-menu-item>
          <el-menu-item index="/chat">
            <el-icon><ChatDotRound /></el-icon>
            <span>AI 实验室助手</span>
          </el-menu-item>
          <el-menu-item index="/announcement">
            <el-icon><Bell /></el-icon>
            <span>系统公告</span>
          </el-menu-item>
          <el-menu-item index="/repair">
            <el-icon><Tools /></el-icon>
            <span>{{ isAdmin ? '报修管理' : '我的报修' }}</span>
          </el-menu-item>
          <el-menu-item index="/user">
            <el-icon><User /></el-icon>
            <span>{{ isAdmin ? '用户管理' : '个人中心' }}</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <el-main class="app-main">
        <!--
          先确认完当前用户再挂载子页。
          Vue 的子组件 mounted 会早于父组件 mounted；如果立即渲染 router-view，
          子页可能先用 localStorage 中的旧角色请求错误的列表接口。
        -->
        <router-view v-if="userReady" />
        <div v-else v-loading="true" class="page-loading" />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowDown,
  Bell,
  Calendar,
  ChatDotRound,
  DataBoard,
  House,
  Setting,
  Tools,
  User,
  UserFilled
} from '@element-plus/icons-vue'
import { getUserInfoApi } from '@/api/user'
import {
  getMyNotificationsApi,
  getUnreadCountApi,
  markAsReadApi,
  markAllAsReadApi
} from '@/api/notification'
import { useUser } from '@/utils/user'
import logo from '@/assets/css/images/logo.png'

const router = useRouter()
const { userInfo, isAdmin, isTeacher, isStaff, updateUser, clearLoginData } = useUser()
const displayName = computed(() => userInfo.value?.full_name || userInfo.value?.username || '用户')
const userReady = ref(false)

// ===== 通知相关 =====
const unreadCount = ref(0)
const drawerVisible = ref(false)
const notifications = ref([])
let pollTimer = null

async function refreshUnreadCount() {
  try {
    const res = await getUnreadCountApi()
    unreadCount.value = res.data.count
  } catch (_) {
    // 静默失败，不打扰用户
  }
}

async function loadNotifications() {
  try {
    const res = await getMyNotificationsApi()
    notifications.value = res.data || []
  } catch (_) {
    notifications.value = []
  }
}

function openNotificationDrawer() {
  drawerVisible.value = true
  loadNotifications()
}

async function handleClickNotification(n) {
  if (!n.is_read) {
    await markAsReadApi(n.id)
    n.is_read = true
    unreadCount.value = Math.max(0, unreadCount.value - 1)
  }
  // 按通知类型跳转到对应页面
  if (n.type === 'reservation_result' || n.type === 'reservation_reminder') {
    router.push('/reservation')
  } else if (n.type === 'repair_result') {
    router.push('/repair')
  }
}

async function handleMarkAllRead() {
  await markAllAsReadApi()
  notifications.value.forEach(n => (n.is_read = true))
  unreadCount.value = 0
}

onMounted(async () => {
  // 每次进入主框架都向后端确认一次用户信息，避免角色或状态变更后仍使用旧缓存。
  try {
    const res = await getUserInfoApi()
    updateUser(res.data)
    userReady.value = true
  } catch (error) {
    const unauthorized = error?.code === 401 || error?.response?.status === 401
    // 401 会由请求拦截器跳转登录页，此时不再挂载业务子页。
    // 若只是临时网络故障，则允许用已缓存资料进入页面，不让界面永久卡在加载态。
    if (!unauthorized) userReady.value = true
  }
  // 加载未读数并每 30 秒轮询一次
  refreshUnreadCount()
  pollTimer = setInterval(refreshUnreadCount, 30000)
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
})

const handleCommand = async (command) => {
  if (command === 'profile') {
    await router.push('/user')
  }
  if (command === 'logout') {
    clearLoginData()
    await router.replace('/login')
  }
}
</script>

<style scoped>
.app-shell {
  height: 100vh;
}

.app-header {
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #e4e7ed;
  background: #fff;
  box-shadow: 0 2px 10px rgba(31, 45, 61, 0.04);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 21px;
  font-weight: 700;
  color: #1f2d3d;
}

.brand img {
  width: 40px;
  height: 40px;
  object-fit: contain;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}

.user-button {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 8px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #303133;
}

.user-button:hover {
  background: #f5f7fa;
}

.app-body {
  min-height: 0;
}

.app-aside {
  height: 100%;
  border-right: 1px solid #e4e7ed;
  background: #fff;
}

.app-menu {
  height: 100%;
  border-right: 0;
  padding-top: 12px;
}

.app-main {
  overflow: auto;
  padding: 24px;
  background: #f5f7fa;
}

.page-loading {
  min-height: 240px;
}

.bell-badge {
  margin-right: 8px;
}

.drawer-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

.empty-text {
  text-align: center;
  color: #909399;
  padding: 40px 0;
}

.notification-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.notification-item {
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
}

.notification-item:hover {
  background: #f5f7fa;
}

.notification-item.unread {
  border-color: #409eff;
  background: #ecf5ff;
}

.notif-title {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 4px;
}

.notif-content {
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
}

.notif-time {
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
}

@media (max-width: 720px) {
  .brand span,
  .user-name {
    display: none;
  }

  .app-aside {
    width: 64px !important;
  }

  .app-menu :deep(.el-menu-item span) {
    display: none;
  }

  .app-main {
    padding: 12px;
  }
}
</style>
