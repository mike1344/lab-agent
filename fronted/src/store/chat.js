import { defineStore } from 'pinia'
import { ref } from 'vue'
import { streamChatApi } from '@/api/ai'

/**
 * 对话全局状态 + 对话流程。
 * 把消息和 SSE 请求都放在 Pinia store 里，
 * 用户跳到其他页面时组件销毁但 store 不销毁，
 * AI 回答会在后台继续生成，回来时能看到完整内容。
 */
export const useChatStore = defineStore('chat', () => {
  const welcomeMessage = {
    role: 'assistant',
    content: '你好，我是实验室 AI 助手。你可以向我查询实验室、设备、预约规则，也可以让我协助创建预约。',
    events: []
  }

  const messages = ref([{ ...welcomeMessage }])
  const sending = ref(false)
  let abortController = null

  function addMessage(message) {
    messages.value.push(message)
  }

  function clearMessages() {
    messages.value = [{ ...welcomeMessage }]
  }

  async function sendMessage(question) {
    if (!question || sending.value) return

    // 历史消息必须在加入本轮空白回复之前生成。
    const history = messages.value.slice(-10).map(({ role, content }) => ({ role, content }))
    addMessage({ role: 'user', content: question, events: [] })

    // 用普通对象即可，store 的 messages 本身是响应式的，
    // 修改对象属性会触发视图更新。
    const assistantMessage = { role: 'assistant', content: '', events: [] }
    addMessage(assistantMessage)

    sending.value = true
    const currentController = new AbortController()
    abortController = currentController

    try {
      await streamChatApi(
        { message: question, history },
        (eventName, data) => {
          if (eventName === 'token') assistantMessage.content += data.content
          if (eventName === 'status' || eventName === 'tool') assistantMessage.events.push(data.message)
          if (eventName === 'tool_start') assistantMessage.events.push('正在' + data.label + '…')
          if (eventName === 'tool_end') assistantMessage.events.push('✓ ' + data.label + '完成')
          if (eventName === 'error') assistantMessage.content = data.message
        },
        currentController.signal
      )
    } catch (error) {
      if (error.name === 'AbortError') {
        // 在还没有 token 时停止，不要让空白气泡一直显示"正在思考"。
        if (!assistantMessage.content) assistantMessage.content = '已停止生成。'
        assistantMessage.events.push('用户已停止回答')
      } else {
        assistantMessage.content = assistantMessage.content || 'AI 助手暂时无法回答，请稍后重试。'
      }
    } finally {
      // 只允许当前请求清理自己的状态，避免旧请求误清理新请求的控制器。
      if (abortController === currentController) {
        sending.value = false
        abortController = null
      }
    }
  }

  function stop() {
    // 这里只发出取消信号，sending 由请求的 finally 统一收尾。
    abortController?.abort()
  }

  return { messages, sending, sendMessage, stop, addMessage, clearMessages }
})
