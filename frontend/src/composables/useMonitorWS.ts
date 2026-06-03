import { ref, onMounted, onUnmounted } from 'vue'

export interface WSMessage {
  type: 'alert' | 'event' | 'ping'
  data?: any
}

export function useMonitorWS() {
  const connected = ref(false)
  const lastMessage = ref<WSMessage | null>(null)
  const alerts = ref<any[]>([])

  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null

  function getWsUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    return `${protocol}//${host}/api/v1/monitor/ws`
  }

  function connect() {
    if (ws?.readyState === WebSocket.OPEN) return

    ws = new WebSocket(getWsUrl())

    ws.onopen = () => {
      connected.value = true
      heartbeatTimer = setInterval(() => {
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send('pong')
        }
      }, 30000)
    }

    ws.onmessage = (event) => {
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
      connected.value = false
      if (heartbeatTimer) clearInterval(heartbeatTimer)
      reconnectTimer = setTimeout(connect, 5000)
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  function disconnect() {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    if (heartbeatTimer) clearInterval(heartbeatTimer)
    ws?.close()
    ws = null
  }

  onMounted(connect)
  onUnmounted(disconnect)

  return { connected, lastMessage, alerts, connect, disconnect }
}
