import { createSseDecoder } from '../components/logic/sseDecoder'
import { authenticatedFetch } from './authenticatedFetch'

export async function readJsonSse(
  response: Response,
  onEvent: (event: any) => void,
  requireResult = false,
) {
  if (!response.ok) {
    let detail = ''
    try { const data = await response.json(); detail = typeof data.detail === 'string' ? data.detail : '' } catch { /* HTTP status remains available */ }
    throw new Error(detail || `请求失败 (HTTP ${response.status})`)
  }
  if (!response.body) throw new Error('响应中没有数据流')
  let terminal = false
  let result = false
  const decoder = createSseDecoder(raw => {
    if (raw === '[DONE]') { terminal = true; return }
    let event: any
    try { event = JSON.parse(raw) } catch { throw new Error('服务返回了无效流式数据') }
    if (event.event === 'error' || event.type === 'error') throw new Error(event.message || event.content || '执行失败')
    if (event.event === 'result') result = true
    onEvent(event)
  })
  const reader = response.body.getReader()
  try {
    while (true) {
      const chunk = await reader.read()
      if (chunk.done) break
      decoder.push(chunk.value)
    }
    decoder.finish()
    if (!terminal) throw new Error('数据流提前结束，请重试')
    if (requireResult && !result) throw new Error('数据流未返回有效结果，请重试')
  } catch (error) {
    await reader.cancel().catch(() => undefined)
    throw error
  } finally { reader.releaseLock() }
}

export function postJsonSse(path: string, payload: unknown, signal?: AbortSignal) {
  const base = import.meta.env.VITE_API_BASE_URL || '/api/v1'
  return authenticatedFetch(`${base}${path}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload), signal,
  })
}
