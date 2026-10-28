// 实时通知 WebSocket：自动重连 + 心跳 + 状态回调。
//
// 为什么不用 Authorization 头：浏览器 WebSocket API 不允许自定义请求头，
// JWT 走 ?token= 查询参数（仅握手时出现在 URL 中，与主流做法一致）。
// 为什么有重连上限退避：网络故障时无限密集重连会打爆服务器，指数退避封顶 60s。
import { getToken } from './auth'

const PING_INTERVAL = 25000 // 必须 < nginx 等中间层读超时（默认 60s），否则空闲连接被掐断
const RECONNECT_BASE_DELAY = 3000
const RECONNECT_MAX_DELAY = 60000

export function createNotificationStream({ onNotification, onStatusChange }) {
  let socket = null
  let pingTimer = null
  let reconnectTimer = null
  let attempts = 0
  let manuallyClosed = false

  function buildUrl() {
    const base = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
    // http://x → ws://x，https://x → wss://x；相对路径 "/" 表示同源部署
    const root = base.startsWith('http')
      ? base.replace(/^http/, 'ws').replace(/\/$/, '')
      : `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}`
    return `${root}/api/ws/notifications?token=${encodeURIComponent(getToken() || '')}`
  }

  function clearPing() {
    if (pingTimer) { clearInterval(pingTimer); pingTimer = null }
  }

  function scheduleReconnect() {
    if (manuallyClosed || reconnectTimer) return
    const delay = Math.min(RECONNECT_BASE_DELAY * 2 ** attempts, RECONNECT_MAX_DELAY)
    attempts += 1
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      connect()
    }, delay)
  }

  function connect() {
    if (manuallyClosed || !getToken()) return
    try {
      socket = new WebSocket(buildUrl())
    } catch (_) {
      scheduleReconnect()
      return
    }

    socket.onopen = () => {
      attempts = 0
      onStatusChange?.(true)
      pingTimer = setInterval(() => socket?.readyState === WebSocket.OPEN && socket.send('ping'), PING_INTERVAL)
    }

    socket.onmessage = (event) => {
      if (event.data === 'pong') return
      try {
        const message = JSON.parse(event.data)
        if (message.kind === 'notification') onNotification?.(message.notification)
      } catch (_) {
        // 忽略无法解析的消息，不影响连接
      }
    }

    socket.onclose = (event) => {
      clearPing()
      onStatusChange?.(false)
      // 4401 = 鉴权失败（token 过期/改密）：重连也不会成功，交给轮询兜底
      if (event.code === 4401) return
      scheduleReconnect()
    }

    socket.onerror = () => {
      // 统一交给 onclose 处理重连，这里只兜底未触发 close 的异常状态
      if (socket && socket.readyState === WebSocket.CONNECTING) socket.close()
    }
  }

  connect()

  return {
    close() {
      manuallyClosed = true
      clearPing()
      if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = null }
      socket?.close()
      socket = null
    }
  }
}
