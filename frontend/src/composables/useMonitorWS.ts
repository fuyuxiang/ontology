import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '../store/auth'
import { captureAuthSession, refreshAccessToken } from '../api/client'

export interface WSMessage {
  type: 'alert' | 'event' | 'ping'
  data?: any
}

export function useMonitorWS() {
  const auth = useAuthStore()
  const connected = ref(false)
  const lastMessage = ref<WSMessage | null>(null)
  const alerts = ref<any[]>([])

  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null
  let stopped = false

  function getWsUrl(): string {
    const url = new URL(`${import.meta.env.VITE_API_BASE_URL || '/api/v1'}/monitor/ws`, window.location.origin)
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    return url.toString()
  }

  async function connect() {
    if (stopped || ws?.readyState === WebSocket.OPEN || ws?.readyState === WebSocket.CONNECTING) return

    if (!auth.token) return
    if (auth.hasPermission && !auth.hasPermission('audit:read')) return
    const session = captureAuthSession()
    try {
      const payload = JSON.parse(atob((auth.token.split('.')[1] || '').replace(/-/g, '+').replace(/_/g, '/')))
      if (typeof payload.exp === 'number' && payload.exp * 1000 <= Date.now()) {
        await refreshAccessToken(session)
        if (!stopped && captureAuthSession().id === session.id) void connect()
        return
      }
    } catch { /* A non-JWT fixture or rejected refresh cannot create a new socket. */
      if (!auth.token || captureAuthSession().id !== session.id) return
    }
    ws = new WebSocket(getWsUrl(), ['ontology-monitor', `jwt.${auth.token}`])

    const socket = ws
    ws.onopen = () => {
      if (ws !== socket || stopped) return
      connected.value = true
      heartbeatTimer = setInterval(() => {
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send('pong')
        }
      }, 30000)
    }

    ws.onmessage = (event) => {
      if (ws !== socket || stopped) return
      try {
        const msg: WSMessage = JSON.parse(event.data)
        lastMessage.value = msg

        if (msg.type === 'ping') return

        if (msg.type === 'alert' && msg.data) {
          alerts.value.unshift(msg.data)
          if (alerts.value.length > 50) alerts.value.pop()
        }
      } catch {
        // Ignore parse errors
      }
    }

    ws.onclose = () => {
      if (ws !== socket) return
      connected.value = false
      if (heartbeatTimer) clearInterval(heartbeatTimer)
      if (!stopped && auth.token) reconnectTimer = setTimeout(connect, 5000)
    }

    ws.onerror = () => {
      if (ws === socket) socket.close()
    }
  }

  function disconnect() {
    stopped = true
    connected.value = false
    if (reconnectTimer) clearTimeout(reconnectTimer)
    if (heartbeatTimer) clearInterval(heartbeatTimer)
    ws?.close()
    ws = null
  }

  watch(() => auth.token, () => {
    disconnect()
    alerts.value = []
    lastMessage.value = null
    if (auth.token) { stopped = false; connect() }
  })
  onMounted(connect)
  onUnmounted(disconnect)

  return { connected, lastMessage, alerts, connect, disconnect }
}
