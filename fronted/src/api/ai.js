import router from '@/router'
import { getToken, logout } from '@/utils/auth'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

export async function streamChatApi(data, onEvent, signal) {
  // 浏览器中的 axios 不能像 fetch 一样逐块读取响应体，因此 SSE POST 使用 fetch。
  const response = await fetch(`${apiBaseUrl}/api/ai/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getToken()}`
    },
    body: JSON.stringify(data),
    signal
  })

  // SSE 使用 fetch，不会走 axios 响应拦截器，因此 401 需要在这里单独处理。
  if (response.status === 401) {
    const redirectPath = router.currentRoute.value.fullPath
    logout()
    await router.replace({ path: '/login', query: { redirect: redirectPath } })
    throw new Error('登录已失效，请重新登录')
  }

  if (!response.ok || !response.body) {
    throw new Error('AI 服务请求失败')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  // 把一个 SSE 事件块解析成“事件名 + JSON 数据”。
  // 后端当前每个事件只有一行 data，所以可以直接解析。
  const handleEventBlock = (block) => {
    if (!block.trim()) return

    let eventName = 'message'
    let eventData = null
    for (const line of block.split(/\r?\n/)) {
      if (line.startsWith('event:')) eventName = line.slice(6).trim()
      if (line.startsWith('data:')) eventData = JSON.parse(line.slice(5).trim())
    }
    if (eventData) onEvent(eventName, eventData)
  }

  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
    // 同时兼容 LF 和 CRLF 换行。最后一段可能还没有收到空行，先留在 buffer。
    const eventBlocks = buffer.split(/\r?\n\r?\n/)
    buffer = eventBlocks.pop() || ''

    for (const block of eventBlocks) {
      handleEventBlock(block)
    }
    if (done) {
      // 网关或代理有时会在最后一条事件后直接断开，不再补一个空行。
      // 此时也要消费剩余 buffer，避免丢掉最后一个 token 或 done 事件。
      handleEventBlock(buffer)
      break
    }
  }
}
