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
      <el-table-column prop="title" label="公告标题" min-width="240" show-overflow-tooltip>
        <template #default="scope">
          <el-tag v-if="!scope.row.is_read" type="warning" size="small" style="margin-right: 6px">未读</el-tag>
          {{ scope.row.title }}
        </template>
      </el-table-column>
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

    <!-- 公告详情弹窗：正文 + 已读回执 + 评论 -->
    <el-dialog v-model="detailVisible" :title="detail.title" width="680px">
      <div class="detail-meta">
        <el-tag v-if="detail.is_pinned" type="danger" size="small">置顶</el-tag>
        <el-tag :type="detail.is_read ? 'success' : 'info'" size="small">{{ detail.is_read ? '已读' : '未读' }}</el-tag>
        <span>发布者：{{ detail.publisher_name }}</span>
        <span>发布时间：{{ formatTime(detail.create_time) }}</span>
        <span v-if="isAdmin">已读 {{ detail.read_count || 0 }} 人</span>
        <el-button v-if="isAdmin" link type="primary" @click="openReceipts">查看回执</el-button>
      </div>
      <el-divider />
      <div class="detail-content">{{ detail.content }}</div>

      <el-divider content-position="left">评论（{{ comments.length }}）</el-divider>

      <div v-if="topComments.length === 0" class="comment-empty">还没有评论，来说两句吧</div>
      <div class="comment-list">
        <div v-for="comment in topComments" :key="comment.id" class="comment-item">
          <el-avatar :size="30" :src="comment.avatar_url" />
          <div class="comment-body">
            <div class="comment-head">
              <span class="comment-user">{{ comment.username }}</span>
              <span class="comment-time">{{ formatTime(comment.create_time) }}</span>
            </div>
            <div class="comment-content">{{ comment.content }}</div>
            <div class="comment-actions">
              <el-button link size="small" type="primary" @click="setReply(comment)">回复</el-button>
              <el-button
                v-if="isAdmin || comment.user_id === currentUserId"
                link
                size="small"
                type="danger"
                @click="removeComment(comment)"
              >
                删除
              </el-button>
            </div>

            <!-- 一级回复：只支持一层嵌套 -->
            <div v-for="reply in comment.replies" :key="reply.id" class="comment-item reply-item">
              <el-avatar :size="24" :src="reply.avatar_url" />
              <div class="comment-body">
                <div class="comment-head">
                  <span class="comment-user">{{ reply.username }}</span>
                  <span class="comment-time">{{ formatTime(reply.create_time) }}</span>
                </div>
                <div class="comment-content">{{ reply.content }}</div>
                <div class="comment-actions">
                  <el-button
                    v-if="isAdmin || reply.user_id === currentUserId"
                    link
                    size="small"
                    type="danger"
                    @click="removeComment(reply)"
                  >
                    删除
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="comment-editor">
        <el-input
          v-model="commentText"
          type="textarea"
          :rows="2"
          maxlength="500"
          show-word-limit
          :placeholder="replyTarget ? `回复 @${replyTarget.username}` : '写下你的评论…'"
        />
        <div class="comment-editor-actions">
          <el-button v-if="replyTarget" link @click="cancelReply">取消回复</el-button>
          <el-button type="primary" size="small" :loading="commenting" @click="submitComment">发表</el-button>
        </div>
      </div>
    </el-dialog>

    <!-- 已读回执弹窗（管理员） -->
    <el-dialog v-model="receiptsVisible" title="公告已读回执" width="480px">
      <p class="receipt-summary">已读 {{ receipts.read_count }} / 在册 {{ receipts.total_users }} 人</p>
      <el-table :data="receipts.readers" size="small" max-height="320">
        <el-table-column prop="username" label="用户" min-width="140" />
        <el-table-column label="阅读时间" width="170">
          <template #default="{ row }">{{ formatTime(row.read_time) }}</template>
        </el-table-column>
        <template #empty><div class="comment-empty">还没有人读过</div></template>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createAnnouncementApi,
  createAnnouncementCommentApi,
  deleteAnnouncementApi,
  deleteAnnouncementCommentApi,
  getAnnouncementCommentsApi,
  getAnnouncementListApi,
  getAnnouncementReadReceiptsApi,
  markAnnouncementReadApi,
  updateAnnouncementApi
} from '@/api/announcement'
import { useUser } from '@/utils/user'
import { promptSignature } from '@/utils/confirm'

const { isAdmin, userInfo } = useUser()
const currentUserId = computed(() => userInfo.value?.id)

const loadingValue = ref(false)
const savingValue = ref(false)
const keyword = ref('')
const list = ref([])
const dialogVisible = ref(false)
const detailVisible = ref(false)
const formRef = ref(null)
const detail = ref({})
const form = reactive({ id: null, title: '', content: '', is_pinned: false })

// ===== 评论与已读回执 =====
const comments = ref([])
const commentText = ref('')
const replyTarget = ref(null)
const commenting = ref(false)
const receiptsVisible = ref(false)
const receipts = reactive({ read_count: 0, total_users: 0, readers: [] })

// 一级评论 + 其回复（parent_id 指向一级评论，后端只允许一层）
const topComments = computed(() =>
  comments.value
    .filter((item) => !item.parent_id)
    .map((item) => ({ ...item, replies: comments.value.filter((reply) => reply.parent_id === item.id) }))
)

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
  const password = await promptSignature(`确定删除公告“${row.title}”吗？此操作需要输入当前账号密码确认。`)
  if (password === null) return
  await deleteAnnouncementApi(row.id, { signature_password: password })
  ElMessage.success('删除成功')
  await loadList()
}

const loadComments = async (announcementId) => {
  const res = await getAnnouncementCommentsApi(announcementId)
  comments.value = res.data || []
}

const viewDetail = async (row) => {
  detail.value = { ...row }
  detailVisible.value = true
  replyTarget.value = null
  commentText.value = ''
  await loadComments(row.id)
  // 打开详情即视为已读：接口幂等，重复打开不会重复计数；失败不阻断查看
  if (!row.is_read) {
    try {
      const res = await markAnnouncementReadApi(row.id)
      row.is_read = true
      row.read_count = res.data?.read_count ?? row.read_count
      detail.value.is_read = true
      detail.value.read_count = row.read_count
    } catch {
      // 忽略标记失败，用户仍可正常阅读
    }
  }
}

const setReply = (comment) => {
  replyTarget.value = comment
}

const cancelReply = () => {
  replyTarget.value = null
}

const submitComment = async () => {
  const content = commentText.value.trim()
  if (!content) {
    ElMessage.warning('评论内容不能为空')
    return
  }
  commenting.value = true
  try {
    await createAnnouncementCommentApi(detail.value.id, {
      content,
      parent_id: replyTarget.value?.id ?? null
    })
    commentText.value = ''
    replyTarget.value = null
    ElMessage.success('评论成功')
    await loadComments(detail.value.id)
  } finally {
    commenting.value = false
  }
}

const removeComment = async (comment) => {
  try {
    await ElMessageBox.confirm('确定删除这条评论吗？删除一级评论会连同其回复一起删除。', '删除确认', {
      type: 'warning'
    })
  } catch {
    return
  }
  await deleteAnnouncementCommentApi(comment.id)
  ElMessage.success('评论删除成功')
  await loadComments(detail.value.id)
}

const openReceipts = async () => {
  const res = await getAnnouncementReadReceiptsApi(detail.value.id)
  receipts.read_count = res.data?.read_count || 0
  receipts.total_users = res.data?.total_users || 0
  receipts.readers = res.data?.readers || []
  receiptsVisible.value = true
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
.comment-empty {
  padding: 12px 0;
  text-align: center;
  font-size: 13px;
  color: #909399;
}
.comment-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.comment-item {
  display: flex;
  gap: 10px;
}
.comment-body {
  flex: 1;
  min-width: 0;
}
.comment-head {
  display: flex;
  align-items: center;
  gap: 10px;
}
.comment-user {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}
.comment-time {
  font-size: 12px;
  color: #909399;
}
.comment-content {
  margin-top: 4px;
  font-size: 13px;
  line-height: 1.6;
  color: #606266;
  white-space: pre-wrap;
  word-break: break-word;
}
.comment-actions {
  margin-top: 2px;
}
.reply-item {
  margin-top: 10px;
  padding: 8px 10px;
  background: #f7f9fc;
  border-radius: 8px;
}
.comment-editor {
  margin-top: 16px;
}
.comment-editor-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}
.receipt-summary {
  margin-bottom: 10px;
  font-size: 13px;
  color: #606266;
}
</style>
