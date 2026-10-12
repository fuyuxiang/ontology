import { authenticatedFetch } from '../api/authenticatedFetch'
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { get } from '../api/client'
import { authHeaders } from '../utils/authHeaders'
import { useAuthStore } from '../store/auth'
import { createSseDecoder } from '../components/logic/sseDecoder'

export interface SystemEvent { id: string; time: string; type: string; description: string }

/** Persistent audit history plus the intentionally long-lived EventBus stream. */
export function useSystemEvents() {
  const auth = useAuthStore()
  const events = ref<SystemEvent[]>([])
  const error = ref('')
  const connected = ref(false)
  let controller: AbortController | null = null
  let timer: ReturnType<typeof setTimeout> | null = null
  let stopped = false
  let generation = 0
  function stop() { ++generation; controller?.abort(); controller = null; connected.value = false; if (timer) clearTimeout(timer); timer = null }
  function add(event: SystemEvent) { events.value = [event, ...events.value.filter(item => item.id !== event.id)].slice(0, 100) }
  async function connect() {
    stop()
    if (stopped || !auth.token) return
    const current = generation, ctrl = new AbortController()
    controller = ctrl; error.value = ''
    try {
      if (auth.hasPermission('audit:read')) {
        try {
          const history = await get<{ items: Array<any> }>('/governance/audit-logs?page_size=100', { signal:ctrl.signal })
          if (current !== generation) return
          events.value = history.items.map(record => ({ id:record.id, time:record.timestamp, type:record.target_type === 'system_config' ? 'config' : record.target_type === 'user' || record.target_type === 'auth' ? 'user' : record.action === 'publish' ? 'deploy' : record.target_type, description:`${record.user_name || '系统'} · ${record.action} · ${record.target_name || record.target_id} · ${record.status}` }))
        } catch (exception:any) {
          if (current !== generation) return
          error.value = `历史审计加载失败: ${exception?.response?.data?.detail || exception.message}`
        }
      }
      const response = await authenticatedFetch(`${import.meta.env.VITE_API_BASE_URL || '/api/v1'}/events/sse`, { headers:authHeaders(), signal:ctrl.signal })
      if (!response.ok) throw new Error(`事件订阅失败 (HTTP ${response.status})`)
      if (!response.body) throw new Error('事件订阅没有返回数据流')
      if (current !== generation) return
      connected.value = true
      const decoder = createSseDecoder(raw => {
        const envelope = JSON.parse(raw)
        if (!envelope.event || current !== generation) return // heartbeat
        add({ id:envelope.event_id, time:new Date(envelope.ts).toISOString(), type:envelope.event.split('.')[0], description:[envelope.event, envelope.asset_name || envelope.name || envelope.asset_id || envelope.binding_id || envelope.connection_id || ''].filter(Boolean).join(' · ') })
      })
      const reader = response.body.getReader()
      try { while (true) { const chunk = await reader.read(); if (chunk.done) break; decoder.push(chunk.value) }; decoder.finish() }
      finally { await reader.cancel().catch(() => undefined); reader.releaseLock() }
      throw new Error('事件流已断开，正在重新连接')
    } catch (exception:any) {
      if (!ctrl.signal.aborted && current === generation) { error.value = exception?.response?.data?.detail || exception.message || '事件订阅失败'; connected.value = false; timer = setTimeout(() => { if (!stopped) void connect() },5000) }
    }
  }
  watch(() => auth.token, () => { stop(); events.value = []; if (auth.token && !stopped) void connect() })
  onMounted(() => { void connect() })
  onUnmounted(() => { stopped = true; stop() })
  return { events, error, connected, retry:connect }
}
