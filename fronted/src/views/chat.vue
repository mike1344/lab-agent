<template>
  <div class="chat-page">
    <header class="chat-header">
      <div>
        <h1>AI 实验室助手</h1>
        <p>支持知识库问答、实验室/设备查询和智能预约</p>
      </div>
      <div class="header-actions">
        <el-button size="small" @click="clearChat">清空对话</el-button>
        <el-tag type="success" effect="plain">SSE 流式输出</el-tag>
      </div>
    </header>

    <main ref="messageContainer" class="message-container">
      <!-- 上次回答在页面刷新时被中断：历史已恢复，可一键重新生成 -->
      <div v-if="chatStore.interrupted" class="interrupt-banner">
        <span>上一次回答在页面刷新时被中断，历史对话已恢复。</span>
        <el-button link type="primary" @click="chatStore.retryInterrupted()">重新生成上一问</el-button>
      </div>
      <div v-for="(message, index) in chatStore.messages" :key="index" :class="['message-row', message.role]">
        <el-avatar :size="36">{{ message.role === 'user' ? '我' : 'AI' }}</el-avatar>
        <div class="message-content">
          <div class="message-bubble">{{ plainText(message.content) || '正在思考…' }}</div>
          <div v-if="message.events?.length" class="process-events">
            <el-tag v-for="event in message.events" :key="event" size="small" effect="plain">{{ event }}</el-tag>
          </div>
        </div>
      </div>
    </main>

    <div class="suggestions">
      <button v-for="question in suggestions" :key="question" type="button" @click="inputValue = question">{{ question }}</button>
    </div>

    <footer class="chat-input">
      <el-input v-model="inputValue" type="textarea" :autosize="{ minRows: 1, maxRows: 4 }" resize="none" placeholder="输入问题；Enter 发送，Shift+Enter 换行" :disabled="chatStore.sending" @keydown.enter.exact.prevent="sendMessage" />
      <el-button v-if="chatStore.sending" type="danger" plain @click="stopAnswer">停止</el-button>
      <el-button v-else type="primary" :disabled="!inputValue.trim()" @click="sendMessage">发送</el-button>
    </footer>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { useChatStore } from '@/store/chat'

const inputValue = ref('')
const messageContainer = ref(null)
const chatStore = useChatStore()

// 挂载时兜底恢复：内存里只剩欢迎语、但本地有历史时还原（刷新/重开页面后由这里恢复）
onMounted(() => {
  chatStore.restore()
  scrollToBottom()
})

const clearChat = () => {
  chatStore.clearMessages()
  inputValue.value = ''
}

// 模型偶尔仍会输出 Markdown 加粗，这里做一层兜底，避免界面直接显示星号。
const plainText = (text) => (text || '').replace(/\*\*/g, '')

const suggestions = [
  '当前有哪些开放的实验室和设备？',
  '实验室预约需要遵守哪些规则？',
  '设备发生故障时应该怎么处理？'
]

const scrollToBottom = async () => {
  await nextTick()
  if (messageContainer.value) messageContainer.value.scrollTop = messageContainer.value.scrollHeight
}

// 对话逻辑在 store 里，组件只负责渲染。
// 深度监听 messages 变化（包括同一条消息 content 逐 token 增长），自动滚动到底部。
watch(() => chatStore.messages, scrollToBottom, { deep: true })

const sendMessage = () => {
  const question = inputValue.value.trim()
  if (!question || chatStore.sending) return
  inputValue.value = ''
  chatStore.sendMessage(question)
}

const stopAnswer = () => {
  chatStore.stop()
}
</script>

<style scoped>
.chat-page { display: grid; grid-template-rows: auto 1fr auto auto; height: calc(100vh - 108px); overflow: hidden; background: #fff; border-radius: 12px; box-shadow: 0 2px 12px rgba(31, 45, 61, 0.05); }
.chat-header { display: flex; align-items: center; justify-content: space-between; padding: 20px 24px; border-bottom: 1px solid #ebeef5; }
.chat-header h1 { font-size: 20px; }
.chat-header p { margin-top: 5px; color: #909399; }
.header-actions { display: flex; align-items: center; gap: 10px; }
.message-container { overflow-y: auto; padding: 24px; background: #f8fafc; }
.interrupt-banner { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; padding: 10px 14px; border: 1px solid #faecd8; border-radius: 8px; background: #fdf6ec; font-size: 13px; color: #b88230; }
.message-row { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 22px; }
.message-row.user { flex-direction: row-reverse; }
.message-content { max-width: min(720px, 78%); }
.message-bubble { padding: 13px 16px; border: 1px solid #e4e7ed; border-radius: 4px 14px 14px; background: #fff; line-height: 1.75; white-space: pre-wrap; overflow-wrap: anywhere; }
.message-row.user .message-bubble { border-color: #409eff; border-radius: 14px 4px 14px 14px; background: #409eff; color: #fff; }
.process-events { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.suggestions { display: flex; gap: 8px; overflow-x: auto; padding: 10px 18px; border-top: 1px solid #ebeef5; }
.suggestions button { flex: none; padding: 7px 12px; border: 1px solid #dcdfe6; border-radius: 16px; background: #fff; color: #606266; }
.suggestions button:hover { border-color: #409eff; color: #409eff; }
.chat-input { display: flex; align-items: flex-end; gap: 12px; padding: 16px 18px; border-top: 1px solid #ebeef5; }
</style>
