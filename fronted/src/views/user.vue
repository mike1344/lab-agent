<template>
  <div class="page-container">
    <div class="page-header"><h1 class="page-title">{{ isAdmin ? '用户与个人中心' : '个人中心' }}</h1></div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="个人信息" name="profile">
        <el-form ref="profileFormRef" :model="profileForm" :rules="profileRules" label-width="90px" class="narrow-form">
          <el-form-item label="用户名"><el-input :model-value="userInfo?.username" disabled /></el-form-item>
          <el-form-item label="姓名" prop="full_name"><el-input v-model="profileForm.full_name" placeholder="请输入姓名" /></el-form-item>
          <el-form-item label="邮箱" prop="email"><el-input v-model="profileForm.email" placeholder="请输入邮箱" /></el-form-item>
          <el-form-item label="账号角色"><el-tag :type="isAdmin ? 'danger' : 'success'">{{ isAdmin ? '管理员' : '普通用户' }}</el-tag></el-form-item>
          <el-form-item><el-button type="primary" :loading="savingValue" @click="saveProfile">保存个人信息</el-button></el-form-item>
        </el-form>

        <el-divider content-position="left">文件上传接口演示</el-divider>
        <div class="upload-demo">
          <el-upload :auto-upload="false" :show-file-list="false" accept="image/jpeg,image/png,image/webp" :on-change="handleUploadChange">
            <el-button :loading="uploadingValue">选择并上传图片</el-button>
          </el-upload>
          <img v-if="uploadedImageUrl" :src="uploadedImageUrl" alt="上传预览" />
          <span v-else>支持 JPG、PNG、WEBP，最大 5MB</span>
        </div>
      </el-tab-pane>

      <el-tab-pane label="修改密码" name="password">
        <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-width="90px" class="narrow-form">
          <el-form-item label="原密码" prop="old_password"><el-input v-model="passwordForm.old_password" type="password" show-password /></el-form-item>
          <el-form-item label="新密码" prop="new_password"><el-input v-model="passwordForm.new_password" type="password" show-password /></el-form-item>
          <el-form-item label="确认密码" prop="confirmPassword"><el-input v-model="passwordForm.confirmPassword" type="password" show-password /></el-form-item>
          <el-form-item><el-button type="primary" :loading="savingValue" @click="savePassword">修改密码</el-button></el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane v-if="isAdmin" label="用户管理" name="manager">
        <div class="toolbar">
          <el-input v-model="searchParams.keyword" clearable placeholder="用户名、姓名或邮箱" style="width: 240px" @keyup.enter="loadUserList" @clear="loadUserList" />
          <el-button @click="loadUserList">查询</el-button>
          <el-button type="primary" @click="openUserDialog()">新增用户</el-button>
        </div>
        <el-table v-loading="loadingValue" :data="userList" stripe>
          <el-table-column prop="username" label="用户名" min-width="110" />
          <el-table-column prop="full_name" label="姓名" min-width="100" />
          <el-table-column prop="email" label="邮箱" min-width="190" />
          <el-table-column label="角色" width="100"><template #default="scope"><el-tag :type="scope.row.is_superuser ? 'danger' : (scope.row.is_teacher ? 'warning' : 'success')">{{ scope.row.is_superuser ? '管理员' : (scope.row.is_teacher ? '教师' : '学生') }}</el-tag></template></el-table-column>
          <el-table-column label="状态" width="90"><template #default="scope"><el-tag :type="scope.row.is_active ? 'success' : 'info'">{{ scope.row.is_active ? '启用' : '禁用' }}</el-tag></template></el-table-column>
          <el-table-column label="注册时间" min-width="170"><template #default="scope">{{ formatDate(scope.row.create_time) }}</template></el-table-column>
          <el-table-column label="操作" width="200" fixed="right"><template #default="scope"><el-button link type="primary" @click="openUserDialog(scope.row)">编辑</el-button><el-button link type="warning" @click="openResetDialog(scope.row)">重置密码</el-button><el-button link type="danger" @click="removeUser(scope.row)">删除</el-button></template></el-table-column>
        </el-table>
        <el-pagination v-model:current-page="searchParams.page" v-model:page-size="searchParams.page_size" layout="total, prev, pager, next" :total="userTotal" class="pagination" @current-change="loadUserList" />
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="userDialogVisible" :title="userForm.id ? '编辑用户' : '新增用户'" width="520px">
      <el-form ref="userFormRef" :model="userForm" :rules="userRules" label-width="90px">
        <el-form-item label="用户名" prop="username"><el-input v-model="userForm.username" :disabled="Boolean(userForm.id)" /></el-form-item>
        <el-form-item v-if="!userForm.id" label="初始密码" prop="password"><el-input v-model="userForm.password" type="password" show-password /></el-form-item>
        <el-form-item label="姓名"><el-input v-model="userForm.full_name" /></el-form-item>
        <el-form-item label="邮箱" prop="email"><el-input v-model="userForm.email" /></el-form-item>
        <el-form-item label="管理员"><el-switch v-model="userForm.is_superuser" /></el-form-item>
        <el-form-item label="教师"><el-switch v-model="userForm.is_teacher" /></el-form-item>
        <el-form-item label="启用账号"><el-switch v-model="userForm.is_active" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="userDialogVisible = false">取消</el-button><el-button type="primary" :loading="savingValue" @click="saveUser">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="resetDialogVisible" title="重置密码" width="420px">
      <el-form label-width="80px">
        <el-form-item label="用户">{{ resetTarget?.username }}</el-form-item>
        <el-form-item label="新密码"><el-input v-model="resetForm.new_password" type="password" show-password placeholder="至少8位" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="resetDialogVisible = false">取消</el-button><el-button type="warning" @click="saveResetPassword">确认重置</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import { adminResetPasswordApi, createUserApi, deleteUserApi, getUserListApi, updatePasswordApi, updateProfileApi, updateUserApi, uploadImageApi } from '@/api/user'
import { useUser } from '@/utils/user'

const router = useRouter()
const { userInfo, isAdmin, updateUser, clearLoginData } = useUser()
const activeTab = ref('profile')
const loadingValue = ref(false)
const savingValue = ref(false)
const uploadingValue = ref(false)
const uploadedImageUrl = ref('')
const userDialogVisible = ref(false)
const profileFormRef = ref(null)
const passwordFormRef = ref(null)
const userFormRef = ref(null)
const userList = ref([])
const userTotal = ref(0)

const profileForm = reactive({ full_name: '', email: '' })
const passwordForm = reactive({ old_password: '', new_password: '', confirmPassword: '' })
const searchParams = reactive({ page: 1, page_size: 10, keyword: '' })
const userForm = reactive({ id: null, username: '', password: '', full_name: '', email: '', is_active: true, is_superuser: false, is_teacher: false })
const resetDialogVisible = ref(false)
const resetTarget = ref(null)
const resetForm = reactive({ new_password: '' })

const profileRules = { email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }] }
const validateNewPassword = (rule, value, callback) => {
  if (!value) callback(new Error('请再次输入新密码'))
  else if (value !== passwordForm.new_password) callback(new Error('两次输入的密码不一致'))
  else callback()
}
const passwordRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [{ required: true, message: '请输入新密码', trigger: 'blur' }, { min: 8, max: 64, message: '密码长度为 8～64 个字符', trigger: 'blur' }],
  confirmPassword: [{ validator: validateNewPassword, trigger: 'blur' }]
}
const userRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }, { min: 3, max: 20, message: '长度为 3～20 个字符', trigger: 'blur' }],
  password: [{ required: true, message: '请输入初始密码', trigger: 'blur' }, { min: 8, max: 64, message: '长度为 8～64 个字符', trigger: 'blur' }],
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }]
}

const saveProfile = async () => {
  const valid = await profileFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    const res = await updateProfileApi({ email: profileForm.email.trim(), full_name: profileForm.full_name.trim() || null })
    updateUser(res.data)
    ElMessage.success('个人信息修改成功')
  } finally { savingValue.value = false }
}

const savePassword = async () => {
  const valid = await passwordFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    await updatePasswordApi({ old_password: passwordForm.old_password, new_password: passwordForm.new_password })
    ElMessage.success('密码修改成功，请重新登录')
    clearLoginData()
    await router.replace('/login')
  } finally { savingValue.value = false }
}

const handleUploadChange = async (uploadFile) => {
  if (!uploadFile.raw) return
  uploadingValue.value = true
  try {
    const res = await uploadImageApi(uploadFile.raw)
    const url = `${import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'}${res.data.url}`
    uploadedImageUrl.value = url
    // 自动保存到用户资料
    const profileRes = await updateProfileApi({ email: profileForm.email.trim(), full_name: profileForm.full_name.trim() || null, avatar_url: url })
    updateUser(profileRes.data)
    ElMessage.success('头像已保存')
  } finally { uploadingValue.value = false }
}

const loadUserList = async () => {
  loadingValue.value = true
  try {
    const res = await getUserListApi(searchParams)
    userList.value = res.data.list
    userTotal.value = res.data.total
  } finally { loadingValue.value = false }
}

const openUserDialog = (user = null) => {
  Object.assign(userForm, user ? { ...user, password: '' } : { id: null, username: '', password: '', full_name: '', email: '', is_active: true, is_superuser: false, is_teacher: false })
  userDialogVisible.value = true
}

const saveUser = async () => {
  const valid = await userFormRef.value?.validate().catch(() => false)
  if (!valid) return
  savingValue.value = true
  try {
    if (userForm.id) {
      await updateUserApi(userForm.id, { email: userForm.email.trim(), full_name: userForm.full_name?.trim() || null, is_active: userForm.is_active, is_superuser: userForm.is_superuser, is_teacher: userForm.is_teacher })
    } else {
      await createUserApi({ username: userForm.username.trim(), password: userForm.password, email: userForm.email.trim(), full_name: userForm.full_name.trim() || null, is_active: userForm.is_active, is_superuser: userForm.is_superuser, is_teacher: userForm.is_teacher })
    }
    ElMessage.success(userForm.id ? '用户修改成功' : '用户新增成功')
    userDialogVisible.value = false
    await loadUserList()
  } finally { savingValue.value = false }
}

const removeUser = async (user) => {
  try {
    await ElMessageBox.confirm(`确定删除用户”${user.username}”吗？`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  await deleteUserApi(user.id)
  ElMessage.success('删除成功')
  await loadUserList()
}

const openResetDialog = (user) => {
  resetTarget.value = user
  resetForm.new_password = ''
  resetDialogVisible.value = true
}
const saveResetPassword = async () => {
  if (!resetForm.new_password || resetForm.new_password.length < 8) {
    ElMessage.warning('新密码至少8位')
    return
  }
  await adminResetPasswordApi(resetTarget.value.id, { new_password: resetForm.new_password })
  ElMessage.success('密码已重置')
  resetDialogVisible.value = false
}

const formatDate = (value) => value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '-'

onMounted(async () => {
  Object.assign(profileForm, { full_name: userInfo.value?.full_name || '', email: userInfo.value?.email || '' })
  uploadedImageUrl.value = userInfo.value?.avatar_url || ''
  if (isAdmin.value) await loadUserList()
})
</script>

<style scoped>
.narrow-form { max-width: 560px; padding-top: 18px; }
.upload-demo { display: flex; align-items: center; gap: 18px; color: #909399; }
.upload-demo img { width: 100px; height: 100px; border-radius: 8px; object-fit: cover; border: 1px solid #e4e7ed; }
.pagination { justify-content: flex-end; margin-top: 20px; }
</style>
