import { computed, ref } from 'vue'
import { getUserInfo, logout, setRefreshToken, setToken, setUserInfo } from './auth'

// 放在 useUser 外部，使所有组件拿到的是同一个响应式用户对象。
const userInfo = ref(getUserInfo())

export function useUser() {
  const isAdmin = computed(() => Boolean(userInfo.value?.is_superuser))
  const isTeacher = computed(() => Boolean(userInfo.value?.is_teacher))
  // 管理员或教师都算教学管理角色，能看到审核页面
  const isStaff = computed(() => isAdmin.value || isTeacher.value)

  function saveLoginData(data) {
    setToken(data.token)
    // 长效刷新令牌用于 access token 过期后的无感续期
    if (data.refresh_token) setRefreshToken(data.refresh_token)
    updateUser(data.user)
  }

  function updateUser(user) {
    setUserInfo(user)
    userInfo.value = user
  }

  function reloadUser() {
    userInfo.value = getUserInfo()
  }

  function clearLoginData() {
    logout()
    userInfo.value = null
  }

  return {
    userInfo,
    isAdmin,
    isTeacher,
    isStaff,
    saveLoginData,
    updateUser,
    reloadUser,
    clearLoginData
  }
}
