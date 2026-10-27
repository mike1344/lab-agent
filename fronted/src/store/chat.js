import { defineStore } from 'pinia'
import { reactive, ref, watch } from 'vue'
import { streamChatApi } from '@/api/ai'

/**
 * 对话全局状态 + 对话流程。
 *
 * 三层保障，确保"切页面/刷新"不丢对话：
 * 1. Pinia store：SPA 路由切换不销毁，AI 回答在后台继续生成；
 * 2. localStorage：消息实时落盘，整页刷新/重开标签页后自动恢复；
 * 3. restore()：聊天页每次挂载时兜底比对（内存为空但磁盘有历史时恢复），
 *    覆盖极端情况下 store 被重建的场景。
 *
 * 流式回答本身无法跨刷新续传（浏览器会取消在途 fetch），
 * 因此刷新后若检测到未完成的回答，会提示"重新生成上一问"。
 */
const STORAGE_KEY = 'lab_agent_chat_messages'
const MAX_STORED_MESSAGES = 30

export const useChatStore = defineStore('chat', () => {
  const welcomeMessage = {
    role: 'assistant',
    content: '你好，我是实验室 AI 助手。你可以向我查询实验室、设备、预约规则，也可以让我协助创建预约。',
    events: []
  }

  function loadStoredMessages() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) return null
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed) && parsed.length) return parsed
    } catch {
      // 缓存损坏时直接忽略，回落到欢迎语
    }
    return null
  }

  const restored = loadStoredMessages()
  const messages = ref(restored || [{ ...welcomeMessage }])
  const sending = ref(false)
  const interrupted = ref(
    Boolean(
      restored?.length &&
        restored[restored.length - 1]?.role === 'assistant' &&
        restored[restored.length - 1]?.done === false
    )
  )
  let abortController = null

  function persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.value.slice(-MAX_STORED_MESSAGES)))
    } catch {
      // localStorage 不可用（隐私模式/配额满）时不影响对话
    }
  }

  // 任何消息变化（含流式 token 增长）都落盘，刷新后最多丢最后一个 token；
  // 300ms 防抖避免每个 token 都做一次 JSON 序列化造成卡顿。
  let persistTimer = null
  function schedulePersist() {
    clearTimeout(persistTimer)
    persistTimer = setTimeout(persist, 300)
  }
  watch(messages, schedulePersist, { deep: true })

  /**
   * 聊天页挂载时调用：内存里只剩欢迎语、但磁盘有历史时恢复。
   * 正常 SPA 切换不会走到这里（store 本来就在），属于兜底。
   */
  function restore() {
    if (sending.value) return
    const stored = loadStoredMessages()
    if (!stored || stored.length <= 1) return
    const isWelcomeOnly =
      messages.value.length <= 1 && messages.value[0]?.role === 'assistant' && !messages.value[0]?.content?.length
    const hasNoHistory = messages.value.length <= 1
    if (!isWelcomeOnly && !hasNoHistory) return
    if (stored.length <= messages.value.length) return
    messages.value = stored
    const last = stored[stored.length - 1]
    interrupted.value = Boolean(last?.role === 'assistant' && last.done === false)
  }

  function addMessage(message) {
    messages.value.push(message)
  }

  function clearMessages() {
    messages.value = [{ ...welcomeMessage }]
    interrupted.value = false
    persist()
  }

  // 生成中刷新/关闭页面时提醒，避免误把流打断
  function handleBeforeUnload(event) {
    if (!sending.value) return
    event.preventDefault()
    event.returnValue = 'AI 正在回答，离开会中断本次生成'
  }
  if (typeof window !== 'undefined') {
    window.addEventListener('beforeunload', handleBeforeUnload)
  }

  async function sendMessage(question) {
    if (!question || sending.value) return
    interrupted.value = false

    // 历史消息必须在加入本轮空白回复之前生成。
    const history = messages.value.slice(-10).map(({ role, content }) => ({ role, content }))
    addMessage({ role: 'user', content: question, events: [], done: true })

    // 必须用 reactive 包一层：push 进数组的是原始对象时，直接改 content 不会触发
    // 依赖更新，页面要等 sending 变化才一次性刷新，流式输出会失效。
    const assistantMessage = reactive({ role: 'assistant', content: '', events: [], sources: [], done: false })
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
          if (eventName === 'sources') assistantMessage.sources = data.items || []
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
      assistantMessage.done = true
      persist()
    }
  }

  function stop() {
    // 这里只发出取消信号，sending 由请求的 finally 统一收尾。
    abortController?.abort()
  }

  function retryInterrupted() {
    if (sending.value) return
    const lastUser = [...messages.value].reverse().find((message) => message.role === 'user')
    if (!lastUser) {
      interrupted.value = false
      return
    }
    // 删除末尾未完成的助手气泡（可能只有半截内容），再重新提问
    const last = messages.value[messages.value.length - 1]
    if (last?.role === 'assistant' && last.done === false) {
      messages.value.pop()
    }
    interrupted.value = false
    sendMessage(lastUser.content)
  }

  return {
    messages,
    sending,
    interrupted,
    sendMessage,
    stop,
    restore,
    retryInterrupted,
    addMessage,
    clearMessages
  }
})
