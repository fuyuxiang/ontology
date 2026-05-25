// Data Plane SSE 事件订阅。
// 用法：
//   const close = subscribeEvents(['asset.*', 'binding.*'], (event, data) => {...})
//   // 路由切换时调用 close()
//
// 后端：GET /api/v1/events/sse?topics=...

const baseURL = (import.meta as any).env?.VITE_API_BASE_URL || '/api/v1'

export type EventHandler = (event: string, data: Record<string, unknown>) => void

export function subscribeEvents(topics: string[], handler: EventHandler): () => void {
  const url = `${baseURL}/events/sse?topics=${encodeURIComponent(topics.join(','))}`
  const es = new EventSource(url)
  // 监听全部 topic（带 . 的事件名）
  es.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data || '{}')
      handler(data.event || ev.type || 'message', data)
    } catch {
      /* noop */
    }
  }
  // SSE 默认 onmessage 仅捕获未命名事件；具名事件通过 addEventListener 单独绑定
  // 我们这里把所有事件都通过 onmessage 路径处理（后端发送时带 data 字段含 event 名）
  return () => es.close()
}
